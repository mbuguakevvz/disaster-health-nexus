import pandas as pd
import psycopg2
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

def print_risk_report():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT ON (iso3)
            iso3, country, year, risk_score, risk_level,
            outbreak_score, wash_score, facility_score
        FROM fact_cholera_risk_scores
        ORDER BY iso3, year DESC
    """)
    rows = cur.fetchall()
    cols = ["iso3","country","year","risk_score","risk_level","outbreak_score","mortality_score","facility_score"]
    df = pd.DataFrame(rows, columns=cols)
    df = df.sort_values("risk_score", ascending=False)

    print("\n" + "=" * 65)
    print("CHOLERA RISK REPORT — LATEST YEAR PER COUNTRY")
    print("=" * 65)
    print(f"{'ISO3':<6} {'Country':<25} {'Year':<6} {'Score':>6}  {'Level':<10}")
    print("-" * 65)
    for _, row in df.iterrows():
        print(f"{row['iso3']:<6} {str(row['country']):<25} {int(row['year']):<6} {row['risk_score']:>6.3f}  {row['risk_level']:<10}")

    print("\n--- CRITICAL COUNTRIES ---")
    for _, r in df[df["risk_level"]=="CRITICAL"].iterrows():
        print(f"  {r['iso3']}  {r['country']}  ({int(r['year'])})  score: {r['risk_score']:.3f}")

    print("\n--- HIGH RISK COUNTRIES ---")
    for _, r in df[df["risk_level"]=="HIGH"].iterrows():
        print(f"  {r['iso3']}  {r['country']}  ({int(r['year'])})  score: {r['risk_score']:.3f}")

    print(f"\nTotal countries scored : {len(df)}")
    print(f"CRITICAL               : {len(df[df['risk_level']=='CRITICAL'])}")
    print(f"HIGH                   : {len(df[df['risk_level']=='HIGH'])}")
    print(f"MEDIUM                 : {len(df[df['risk_level']=='MEDIUM'])}")
    print(f"LOW                    : {len(df[df['risk_level']=='LOW'])}")

    conn.close()

if __name__ == "__main__":
    print_risk_report()
