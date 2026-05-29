"""
Cholera Risk Scoring Engine
Computes composite risk scores per country per year
Risk components:
  - outbreak_score   : based on case counts and trends
  - mortality_score  : based on CFR and death counts
  - population_score : based on displaced population vulnerability
  - facility_score   : based on healthcare access gap
Final risk_level: LOW / MEDIUM / HIGH / CRITICAL
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
    "dbname":   os.getenv("CHOLERA_DB", "cholera_db")
}

# Country coordinates for geo output
COUNTRY_COORDS = {
    "COD": (-4.0, 21.7),   "SOM": (5.1, 46.1),    "ETH": (9.1, 40.4),
    "SDN": (15.5, 32.5),   "NGA": (9.0, 8.6),     "MOZ": (-18.6, 35.5),
    "ZWE": (-20.0, 30.0),  "HTI": (18.9, -72.3),  "YEM": (15.5, 48.5),
    "SYR": (34.8, 38.9),   "CMR": (3.8, 11.5),    "TCD": (15.4, 18.7),
    "NER": (17.6, 8.0),    "MLI": (17.5, -4.0),   "GIN": (11.0, -10.9),
    "COG": (-0.2, 15.8),   "CAF": (6.6, 20.9),    "BDI": (-3.4, 29.9),
    "TZA": (-6.3, 34.8),   "KEN": (0.0, 37.9),    "UGA": (1.3, 32.3),
    "ZMB": (-13.1, 27.8),  "MWI": (-13.2, 34.3),  "AGO": (-11.2, 17.9),
    "BGD": (23.6, 90.3),   "IND": (20.5, 78.9),   "AFG": (33.9, 67.7),
    "PAK": (30.3, 69.3),   "PHL": (12.8, 121.7),  "GHA": (7.9, -1.0),
    "SLE": (8.4, -11.7),   "LBR": (6.4, -9.4),    "CIV": (7.5, -5.5),
    "TGO": (8.6, 0.8),     "BEN": (9.3, 2.3),     "HTI": (18.9, -72.3),
}

def get_conn():
    return psycopg2.connect(**DB_CONFIG)

def load_outbreak_data(conn) -> pd.DataFrame:
    """Load all outbreak facts from warehouse."""
    query = """
        SELECT iso3, country, year, cases, deaths, cfr
        FROM fact_cholera_outbreaks
        WHERE year > 0 AND iso3 IS NOT NULL
        ORDER BY iso3, year
    """
    df = pd.read_sql(query, conn)
    print(f"Loaded {len(df)} outbreak records from warehouse")
    return df

def compute_outbreak_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Outbreak score based on:
    - Raw case count (normalized 0-1)
    - Year-over-year trend (rising = higher risk)
    - Frequency of outbreaks (how many years active)
    """
    print("Computing outbreak scores...")

    # Aggregate to country-year level
    agg = df.groupby(["iso3","year"]).agg(
        cases=("cases","sum"),
        deaths=("deaths","sum"),
        cfr=("cfr","mean")
    ).reset_index()

    # Normalize cases 0-1 using log scale
    agg["log_cases"] = np.log1p(agg["cases"])
    max_log = agg["log_cases"].max()
    agg["outbreak_score"] = (agg["log_cases"] / max_log).round(4) if max_log > 0 else 0

    # YoY trend — compare to previous year
    agg = agg.sort_values(["iso3","year"])
    agg["prev_cases"] = agg.groupby("iso3")["cases"].shift(1).fillna(0)
    agg["trend"] = np.where(
        agg["prev_cases"] > 0,
        (agg["cases"] - agg["prev_cases"]) / (agg["prev_cases"] + 1),
        0
    )
    # Boost score if trend is rising
    agg["trend_boost"] = np.clip(agg["trend"] * 0.1, 0, 0.2)
    agg["outbreak_score"] = np.clip(agg["outbreak_score"] + agg["trend_boost"], 0, 1).round(4)

    print(f"  Outbreak scores computed for {len(agg)} country-year records")
    return agg

def compute_mortality_score(agg: pd.DataFrame) -> pd.DataFrame:
    """
    Mortality score based on:
    - Case Fatality Rate (CFR) — high CFR = poor healthcare access
    - Absolute death count
    WHO threshold: CFR > 1% = inadequate response
    """
    print("Computing mortality scores...")

    # Normalize CFR — WHO alarm threshold is 1%
    agg["cfr_score"] = np.clip(agg["cfr"] / 3.0, 0, 1).round(4)

    # Normalize deaths
    agg["log_deaths"] = np.log1p(agg["deaths"])
    max_log_d = agg["log_deaths"].max()
    agg["death_score"] = (agg["log_deaths"] / max_log_d).round(4) if max_log_d > 0 else 0

    # Combined mortality score (60% CFR, 40% deaths)
    agg["mortality_score"] = (
        0.6 * agg["cfr_score"] +
        0.4 * agg["death_score"]
    ).round(4)

    print(f"  Mortality scores computed")
    return agg

def compute_composite_risk(agg: pd.DataFrame) -> pd.DataFrame:
    """
    Composite risk score combining all components.
    Weights:
      40% outbreak score  (case volume and trend)
      35% mortality score (CFR and deaths)
      25% facility score  (fixed penalty for known low-access countries)
    """
    print("Computing composite risk scores...")

    # Known low healthcare access countries get a facility penalty
    LOW_ACCESS = ["COD","SOM","CAF","SDN","NER","MLI","TCD","GIN","BDI","SLE","LBR","AFG","YEM","HTI"]
    MED_ACCESS = ["ETH","UGA","MOZ","ZWE","CMR","COG","MWI","ZMB","AGO","TZA","NGA"]

    def facility_score(iso3):
        if iso3 in LOW_ACCESS: return 0.8
        if iso3 in MED_ACCESS: return 0.5
        return 0.3

    agg["facility_score"]   = agg["iso3"].apply(facility_score)
    agg["population_score"] = agg["facility_score"] * 0.8  # correlated proxy

    # Composite
    agg["risk_score"] = (
        0.40 * agg["outbreak_score"] +
        0.35 * agg["mortality_score"] +
        0.25 * agg["facility_score"]
    ).round(4)

    # Risk levels
    def risk_level(score):
        if score >= 0.70: return "CRITICAL"
        if score >= 0.45: return "HIGH"
        if score >= 0.20: return "MEDIUM"
        return "LOW"

    agg["risk_level"] = agg["risk_score"].apply(risk_level)

    # Add coordinates
    agg["latitude"]  = agg["iso3"].map(lambda x: COUNTRY_COORDS.get(x, (0,0))[0])
    agg["longitude"] = agg["iso3"].map(lambda x: COUNTRY_COORDS.get(x, (0,0))[1])

    print(f"  Risk levels distribution:")
    print(agg["risk_level"].value_counts().to_string())
    return agg

def save_risk_scores(conn, agg: pd.DataFrame):
    """Save computed risk scores to fact_cholera_risk_scores."""
    print("\nSaving risk scores to warehouse...")
    cur = conn.cursor()

    # Clear previous scores
    cur.execute("TRUNCATE TABLE fact_cholera_risk_scores")

    inserted = 0
    for _, row in agg.iterrows():
        try:
            cur.execute("""
                INSERT INTO fact_cholera_risk_scores
                (iso3, country, year, outbreak_score, population_score,
                 facility_score, wash_score, risk_score, risk_level,
                 latitude, longitude, computed_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                row["iso3"],
                row.get("country", ""),
                int(row["year"]),
                float(row["outbreak_score"]),
                float(row["population_score"]),
                float(row["facility_score"]),
                float(row["mortality_score"]),
                float(row["risk_score"]),
                row["risk_level"],
                float(row["latitude"]),
                float(row["longitude"]),
                datetime.utcnow()
            ))
            inserted += 1
        except Exception as e:
            print(f"  Error inserting {row['iso3']} {row['year']}: {e}")

    conn.commit()
    print(f"  Saved {inserted} risk score records")
    return inserted

def print_risk_report(conn):
    """Print a summary risk report from the warehouse."""
    print("\n" + "=" * 60)
    print("CHOLERA RISK REPORT — MOST RECENT YEAR PER COUNTRY")
    print("=" * 60)

    query = """
        SELECT DISTINCT ON (iso3)
            iso3, country, year, risk_score, risk_level,
            outbreak_score, mortality_score, facility_score
        FROM fact_cholera_risk_scores
        ORDER BY iso3, year DESC
    """
    df = pd.read_sql(query, conn)
    df = df.sort_values("risk_score", ascending=False)

    print(f"\n{'ISO3':<6} {'Country':<25} {'Year':<6} {'Risk':>6} {'Level':<10}")
    print("-" * 60)
    for _, row in df.iterrows():
        print(f"{row['iso3']:<6} {str(row['country']):<25} {int(row['year']):<6} {row['risk_score']:>6.3f} {row['risk_level']:<10}")

    print("\nCRITICAL countries:")
    critical = df[df["risk_level"] == "CRITICAL"]
    for _, r in critical.iterrows():
        print(f"  {r['iso3']} {r['country']} ({int(r['year'])}) — score: {r['risk_score']:.3f}")

def run_transforms():
    print("=" * 60)
    print("CHOLERA TRANSFORM & RISK SCORING ENGINE STARTED")
    print("=" * 60)

    conn = get_conn()
    print("Connected to cholera_db!")

    # Load
    df = load_outbreak_data(conn)

    # Transform
    agg = compute_outbreak_score(df)
    agg = compute_mortality_score(agg)
    agg = compute_composite_risk(agg)

    # Save
    save_risk_scores(conn, agg)

    # Report
    print_risk_report(conn)

    # Export to CSV for dashboard
    os.makedirs("cholera/transforms/output", exist_ok=True)
    agg.to_csv("cholera/transforms/output/cholera_risk_scores.csv", index=False)
    print(f"\nExported risk scores to cholera/transforms/output/cholera_risk_scores.csv")

    conn.close()
    print("\n" + "=" * 60)
    print("TRANSFORM COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    run_transforms()
