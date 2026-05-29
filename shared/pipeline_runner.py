import os, sys
sys.path.insert(0, os.path.abspath("."))
from dotenv import load_dotenv
load_dotenv()
import psycopg2
import pandas as pd

def export_cholera_dashboard():
    print("Exporting cholera dashboard data...")
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST","localhost"),
        port=os.getenv("DB_PORT","5432"),
        user=os.getenv("DB_USER","postgres"),
        password=os.getenv("DB_PASSWORD",""),
        dbname=os.getenv("CHOLERA_DB","cholera_db")
    )
    df_risk = pd.read_sql("""
        SELECT DISTINCT ON (iso3)
            iso3, country, year, risk_score, risk_level,
            outbreak_score, wash_score, facility_score,
            latitude, longitude
        FROM fact_cholera_risk_scores
        ORDER BY iso3, year DESC
    """, conn)
    df_trends = pd.read_sql("""
        SELECT iso3, country, year,
               SUM(cases) as cases,
               SUM(deaths) as deaths,
               AVG(cfr) as cfr
        FROM fact_cholera_outbreaks
        WHERE year >= 2000
        GROUP BY iso3, country, year
        ORDER BY year DESC
    """, conn)
    df_top = pd.read_sql("""
        SELECT iso3, country,
               SUM(cases) as total_cases,
               SUM(deaths) as total_deaths
        FROM fact_cholera_outbreaks
        WHERE year >= 2010
        GROUP BY iso3, country
        ORDER BY total_cases DESC
        LIMIT 20
    """, conn)
    os.makedirs("cholera/dashboard/data", exist_ok=True)
    df_risk.to_csv("cholera/dashboard/data/risk_scores.csv", index=False)
    df_trends.to_csv("cholera/dashboard/data/outbreak_trends.csv", index=False)
    df_top.to_csv("cholera/dashboard/data/top_countries.csv", index=False)
    conn.close()
    print(f"  Risk scores    : {len(df_risk)} rows")
    print(f"  Trends         : {len(df_trends)} rows")
    print(f"  Top countries  : {len(df_top)} rows")

def export_ebola_dashboard():
    print("Exporting ebola dashboard data...")
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST","localhost"),
        port=os.getenv("DB_PORT","5432"),
        user=os.getenv("DB_USER","postgres"),
        password=os.getenv("DB_PASSWORD",""),
        dbname=os.getenv("EBOLA_DB","ebola_db")
    )
    df_risk = pd.read_sql("""
        SELECT DISTINCT ON (iso3)
            iso3, country, year, risk_score, risk_level,
            outbreak_score, mortality_score, containment_score,
            crossborder_score, latitude, longitude
        FROM fact_ebola_risk_scores
        ORDER BY iso3, year DESC
    """, conn)
    df_outbreaks = pd.read_sql("""
        SELECT iso3, country, year,
               total_cases, deaths, cfr, strain
        FROM fact_ebola_outbreaks
        ORDER BY year DESC
    """, conn)
    df_drc = pd.read_sql("""
        SELECT report_date, health_zone, province,
               total_cases, deaths
        FROM fact_ebola_drc_timeseries
        ORDER BY report_date DESC
        LIMIT 200
    """, conn)
    os.makedirs("ebola/dashboard/data", exist_ok=True)
    df_risk.to_csv("ebola/dashboard/data/risk_scores.csv", index=False)
    df_outbreaks.to_csv("ebola/dashboard/data/outbreaks.csv", index=False)
    df_drc.to_csv("ebola/dashboard/data/drc_timeseries.csv", index=False)
    conn.close()
    print(f"  Risk scores    : {len(df_risk)} rows")
    print(f"  Outbreaks      : {len(df_outbreaks)} rows")
    print(f"  DRC timeseries : {len(df_drc)} rows")

if __name__ == "__main__":
    print("=" * 55)
    print("PIPELINE RUNNER - EXPORTING DASHBOARD DATA")
    print("=" * 55)
    export_cholera_dashboard()
    export_ebola_dashboard()
    print("\n" + "=" * 55)
    print("ALL EXPORTS COMPLETE")
    print("Files ready in:")
    print("  cholera/dashboard/data/")
    print("  ebola/dashboard/data/")
    print("=" * 55)
