"""
Ebola Risk Scoring Engine
Ebola-specific risk factors differ from cholera:
  - outbreak_score   : case volume and outbreak frequency
  - mortality_score  : CFR (Ebola CFR 25-90% vs cholera 1-3%)
  - containment_score: how quickly outbreaks were contained
  - crossborder_score: proximity to active outbreak countries
  - facility_score   : healthcare access gap
"""
import pandas as pd
import psycopg2
import numpy as np
from datetime import datetime
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from dotenv import load_dotenv
load_dotenv()

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     os.getenv("DB_PORT", "5432"),
    "user":     os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
    "dbname":   os.getenv("EBOLA_DB", "ebola_db")
}

COUNTRY_COORDS = {
    "COD": (-4.0,21.7),  "GIN": (11.0,-10.9), "LBR": (6.4,-9.4),
    "SLE": (8.4,-11.7),  "NGA": (9.0,8.6),    "SDN": (15.5,32.5),
    "GAB": (-0.8,11.6),  "COG": (-0.2,15.8),  "UGA": (1.3,32.3),
    "SEN": (14.5,-14.4), "MLI": (17.5,-4.0),  "GBR": (51.5,-0.1),
    "USA": (37.1,-95.7), "ITA": (41.9,12.5),  "ESP": (40.4,-3.7),
    "CMR": (3.8,11.5),   "CAF": (6.6,20.9),   "RWA": (-1.9,29.9),
    "BDI": (-3.4,29.9),  "TZA": (-6.3,34.8),  "KEN": (0.0,37.9),
}

# Countries bordering known Ebola hotspots
CROSSBORDER_HIGH = ["COD","CAF","COG","GAB","CMR","UGA","RWA","BDI","TZA","KEN"]
CROSSBORDER_MED  = ["NGA","SDN","ETH","SOM","MOZ","ZMB","AGO"]

def get_conn():
    return psycopg2.connect(**DB_CONFIG)

def load_ebola_data(conn):
    print("Loading Ebola outbreak data from warehouse...")
    cur = conn.cursor()
    cur.execute("""
        SELECT iso3, country, year, total_cases, deaths, cfr, strain, outbreak_id
        FROM fact_ebola_outbreaks
        ORDER BY iso3, year
    """)
    rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=[
        "iso3","country","year","total_cases","deaths","cfr","strain","outbreak_id"
    ])
    print(f"  Loaded {len(df)} outbreak records")
    print(f"  Countries: {df['iso3'].nunique()}")
    print(f"  Years: {df['year'].min()} - {df['year'].max()}")
    return df

def compute_outbreak_score(df):
    print("\nComputing outbreak scores...")
    agg = df.groupby(["iso3","country","year"]).agg(
        total_cases=("total_cases","sum"),
        deaths=("deaths","sum"),
        cfr=("cfr","mean"),
        outbreak_count=("outbreak_id","count")
    ).reset_index()

    # Log-normalize cases
    agg["log_cases"] = np.log1p(agg["total_cases"])
    max_log = agg["log_cases"].max()
    agg["outbreak_score"] = (agg["log_cases"] / max_log).round(4) if max_log > 0 else 0

    # Boost for repeat outbreaks in same country
    country_freq = df.groupby("iso3")["year"].count().reset_index()
    country_freq.columns = ["iso3","freq"]
    country_freq["freq_score"] = np.clip(country_freq["freq"] / 10.0, 0, 0.3)
    agg = agg.merge(country_freq[["iso3","freq_score"]], on="iso3", how="left")
    agg["freq_score"] = agg["freq_score"].fillna(0)
    agg["outbreak_score"] = np.clip(agg["outbreak_score"] + agg["freq_score"], 0, 1).round(4)

    print(f"  Computed for {len(agg)} country-year records")
    return agg

def compute_mortality_score(agg):
    """
    Ebola CFR ranges 25-90% — much higher than cholera.
    WHO benchmark: CFR > 50% = inadequate response/healthcare
    """
    print("Computing mortality scores...")
    agg["cfr_score"]   = np.clip(agg["cfr"] / 90.0, 0, 1).round(4)
    agg["log_deaths"]  = np.log1p(agg["deaths"])
    max_d = agg["log_deaths"].max()
    agg["death_score"] = (agg["log_deaths"] / max_d).round(4) if max_d > 0 else 0
    agg["mortality_score"] = (
        0.6 * agg["cfr_score"] +
        0.4 * agg["death_score"]
    ).round(4)
    print(f"  Max CFR in data: {agg['cfr'].max():.1f}%")
    print(f"  Avg CFR in data: {agg['cfr'].mean():.1f}%")
    return agg

def compute_containment_score(agg, df):
    """
    Containment score based on:
    - Outbreak duration proxy (large outbreaks = poor containment)
    - West Africa 2014 = worst containment
    - DRC outbreaks = variable containment
    """
    print("Computing containment scores...")

    def containment(row):
        # West Africa 2014 outbreak — worst containment in history
        if row["outbreak_id"] in ["west_africa"] or (
            row["iso3"] in ["GIN","LBR","SLE"] and row["year"] == 2014
        ):
            return 0.9
        # DRC 2018 — second largest ever
        if row["outbreak_id"] == "drc_2018":
            return 0.75
        # Large outbreaks
        if row["total_cases"] > 500:
            return 0.7
        if row["total_cases"] > 100:
            return 0.5
        if row["total_cases"] > 50:
            return 0.35
        return 0.2

    # Merge outbreak_id back
    outbreak_meta = df[["iso3","year","outbreak_id"]].drop_duplicates()
    agg = agg.merge(outbreak_meta, on=["iso3","year"], how="left")
    agg["outbreak_id"]       = agg["outbreak_id"].fillna("")
    agg["containment_score"] = agg.apply(containment, axis=1)
    return agg

def compute_composite_risk(agg):
    print("Computing composite risk scores...")

    def facility_score(iso3):
        LOW  = ["COD","CAF","SDN","GIN","SLE","LBR","MLI","BDI"]
        MED  = ["NGA","UGA","COG","GAB","CMR","TZA","KEN","RWA"]
        if iso3 in LOW:  return 0.85
        if iso3 in MED:  return 0.55
        return 0.25

    def crossborder(iso3):
        if iso3 in CROSSBORDER_HIGH: return 0.7
        if iso3 in CROSSBORDER_MED:  return 0.4
        return 0.1

    agg["facility_score"]   = agg["iso3"].apply(facility_score)
    agg["crossborder_score"]= agg["iso3"].apply(crossborder)

    # Composite weights — Ebola weighting
    # 30% outbreak + 30% mortality + 20% containment + 10% facility + 10% crossborder
    agg["risk_score"] = (
        0.30 * agg["outbreak_score"]    +
        0.30 * agg["mortality_score"]   +
        0.20 * agg["containment_score"] +
        0.10 * agg["facility_score"]    +
        0.10 * agg["crossborder_score"]
    ).round(4)

    def risk_level(score):
        if score >= 0.65: return "CRITICAL"
        if score >= 0.40: return "HIGH"
        if score >= 0.20: return "MEDIUM"
        return "LOW"

    agg["risk_level"] = agg["risk_score"].apply(risk_level)
    agg["latitude"]   = agg["iso3"].map(lambda x: COUNTRY_COORDS.get(x,(0,0))[0])
    agg["longitude"]  = agg["iso3"].map(lambda x: COUNTRY_COORDS.get(x,(0,0))[1])

    print(f"  Risk distribution:")
    print(agg["risk_level"].value_counts().to_string())
    return agg

def save_risk_scores(conn, agg):
    print("\nSaving Ebola risk scores...")
    cur = conn.cursor()
    cur.execute("TRUNCATE TABLE fact_ebola_risk_scores")
    inserted = 0
    for _, row in agg.iterrows():
        try:
            cur.execute("""
                INSERT INTO fact_ebola_risk_scores
                (iso3, country, year, outbreak_score, mortality_score,
                 facility_score, containment_score, crossborder_score,
                 risk_score, risk_level, latitude, longitude, computed_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                row["iso3"], str(row.get("country","")), int(row["year"]),
                float(row["outbreak_score"]),
                float(row["mortality_score"]),
                float(row["facility_score"]),
                float(row["containment_score"]),
                float(row["crossborder_score"]),
                float(row["risk_score"]),
                row["risk_level"],
                float(row["latitude"]),
                float(row["longitude"]),
                datetime.utcnow()
            ))
            inserted += 1
        except Exception as e:
            print(f"  Error {row['iso3']} {row['year']}: {e}")
    conn.commit()
    print(f"  Saved {inserted} risk score records")
    return inserted

def print_risk_report(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT ON (iso3)
            iso3, country, year, risk_score, risk_level,
            outbreak_score, mortality_score, containment_score
        FROM fact_ebola_risk_scores
        ORDER BY iso3, year DESC
    """)
    rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=[
        "iso3","country","year","risk_score","risk_level",
        "outbreak_score","mortality_score","containment_score"
    ])
    df = df.sort_values("risk_score", ascending=False)

    print("\n" + "=" * 65)
    print("EBOLA RISK REPORT — LATEST YEAR PER COUNTRY")
    print("=" * 65)
    print(f"{'ISO3':<6} {'Country':<20} {'Year':<6} {'Score':>6}  {'Level':<10}")
    print("-" * 65)
    for _, row in df.iterrows():
        print(f"{row['iso3']:<6} {str(row['country']):<20} {int(row['year']):<6} {row['risk_score']:>6.3f}  {row['risk_level']:<10}")

    print("\n--- CRITICAL ---")
    for _, r in df[df["risk_level"]=="CRITICAL"].iterrows():
        print(f"  {r['iso3']}  {r['country']}  ({int(r['year'])})  score: {r['risk_score']:.3f}")

    print("\n--- HIGH RISK ---")
    for _, r in df[df["risk_level"]=="HIGH"].iterrows():
        print(f"  {r['iso3']}  {r['country']}  ({int(r['year'])})  score: {r['risk_score']:.3f}")

    print(f"\nTotal countries: {len(df)}")
    for lvl in ["CRITICAL","HIGH","MEDIUM","LOW"]:
        print(f"  {lvl:<10}: {len(df[df['risk_level']==lvl])}")

def run_ebola_transforms():
    print("=" * 60)
    print("EBOLA TRANSFORM & RISK SCORING ENGINE STARTED")
    print("=" * 60)

    conn = get_conn()
    print("Connected to ebola_db!")

    df  = load_ebola_data(conn)
    agg = compute_outbreak_score(df)
    agg = compute_mortality_score(agg)
    agg = compute_containment_score(agg, df)
    agg = compute_composite_risk(agg)
    save_risk_scores(conn, agg)
    print_risk_report(conn)

    os.makedirs("ebola/transforms/output", exist_ok=True)
    agg.to_csv("ebola/transforms/output/ebola_risk_scores.csv", index=False)
    print(f"\nExported to ebola/transforms/output/ebola_risk_scores.csv")

    conn.close()
    print("\n" + "=" * 60)
    print("EBOLA TRANSFORM COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    run_ebola_transforms()
