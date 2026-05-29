import pandas as pd
import psycopg2
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

def get_conn():
    return psycopg2.connect(**DB_CONFIG)

def load_countries(conn):
    print("Loading countries...")
    countries = [
        ("COD","CD","DR Congo","Central Africa","Africa",-4.0,21.7),
        ("GIN","GN","Guinea","West Africa","Africa",11.0,-10.9),
        ("LBR","LR","Liberia","West Africa","Africa",6.4,-9.4),
        ("SLE","SL","Sierra Leone","West Africa","Africa",8.4,-11.7),
        ("NGA","NG","Nigeria","West Africa","Africa",9.0,8.6),
        ("SDN","SD","Sudan","North Africa","Africa",15.5,32.5),
        ("GAB","GA","Gabon","Central Africa","Africa",-0.8,11.6),
        ("COG","CG","Congo","Central Africa","Africa",-0.2,15.8),
        ("UGA","UG","Uganda","East Africa","Africa",1.3,32.3),
        ("SEN","SN","Senegal","West Africa","Africa",14.5,-14.4),
        ("MLI","ML","Mali","West Africa","Africa",17.5,-4.0),
        ("GBR","GB","United Kingdom","Europe","Europe",51.5,-0.1),
        ("USA","US","United States","North America","Americas",37.1,-95.7),
        ("ITA","IT","Italy","Europe","Europe",41.9,12.5),
        ("ESP","ES","Spain","Europe","Europe",40.4,-3.7),
    ]
    cur = conn.cursor()
    inserted = 0
    for c in countries:
        try:
            cur.execute("""
                INSERT INTO dim_countries
                (iso3,iso2,country,region,continent,latitude,longitude)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (iso3) DO NOTHING
            """, c)
            inserted += 1
        except Exception as e:
            print(f"  Skip {c[0]}: {e}")
    conn.commit()
    print(f"  Loaded {inserted} countries")

def load_who_historical(conn):
    print("\nLoading WHO historical Ebola outbreaks...")
    df = pd.read_csv("ebola/ingestion/data/WHO_Ebola_Historical.csv")
    cur = conn.cursor()
    inserted = 0
    for _, row in df.iterrows():
        try:
            cur.execute("""
                INSERT INTO fact_ebola_outbreaks
                (iso3, country, year, outbreak_id, total_cases,
                 deaths, cfr, strain, source, data_quality)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                row["iso3"], row["country"], int(row["year"]),
                row["outbreak_id"], int(row["total_cases"]),
                int(row["deaths"]), float(row["cfr"]),
                row["strain"], "WHO_Historical", "verified"
            ))
            inserted += 1
        except Exception as e:
            print(f"  Error: {e}")
    conn.commit()
    print(f"  Inserted {inserted} historical outbreak records")
    return inserted

def load_drc_timeseries(conn):
    print("\nLoading DRC 2018 Ebola timeseries...")
    path = "ebola/ingestion/data/drc_ebola_2018.csv"
    df = pd.read_csv(path)
    print(f"  Columns: {list(df.columns)}")

    cur = conn.cursor()
    inserted = 0
    for _, row in df.iterrows():
        try:
            # Map flexibly — different HDX datasets have different column names
            total  = int(pd.to_numeric(row.get("Total confirmed cases",
                     row.get("total_cases",
                     row.get("Confirmed cases", 0))), errors="coerce") or 0)
            deaths = int(pd.to_numeric(row.get("Total confirmed deaths",
                     row.get("deaths",
                     row.get("Confirmed deaths", 0))), errors="coerce") or 0)
            zone   = str(row.get("Health zone",
                     row.get("health_zone",
                     row.get("Zone de sante", ""))))
            prov   = str(row.get("Province",""))
            date   = str(row.get("Report date",
                     row.get("report_date",
                     row.get("Date", ""))))
            cur.execute("""
                INSERT INTO fact_ebola_drc_timeseries
                (report_date, health_zone, province,
                 total_cases, deaths, iso3)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (date, zone, prov, total, deaths, "COD"))
            inserted += 1
        except Exception as e:
            pass
    conn.commit()
    print(f"  Inserted {inserted} DRC timeseries records")
    return inserted

def load_west_africa_timeseries(conn):
    print("\nLoading 2014 West Africa timeseries...")
    path = "ebola/ingestion/data/ebola_timeseries_global.csv"
    if not os.path.exists(path):
        print("  File not found, skipping")
        return 0
    df = pd.read_csv(path)
    print(f"  Columns: {list(df.columns)}")
    cur = conn.cursor()
    inserted = 0
    for _, row in df.iterrows():
        try:
            cur.execute("""
                INSERT INTO fact_ebola_west_africa
                (report_date, guinea_cases, guinea_deaths,
                 liberia_cases, liberia_deaths,
                 sierraleone_cases, sierraleone_deaths)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (
                str(row.get("Date","")),
                int(pd.to_numeric(row.get("Cases_Guinea",0),      errors="coerce") or 0),
                int(pd.to_numeric(row.get("Deaths_Guinea",0),     errors="coerce") or 0),
                int(pd.to_numeric(row.get("Cases_Liberia",0),     errors="coerce") or 0),
                int(pd.to_numeric(row.get("Deaths_Liberia",0),    errors="coerce") or 0),
                int(pd.to_numeric(row.get("Cases_SierraLeone",0), errors="coerce") or 0),
                int(pd.to_numeric(row.get("Deaths_SierraLeone",0),errors="coerce") or 0),
            ))
            inserted += 1
        except Exception as e:
            pass
    conn.commit()
    print(f"  Inserted {inserted} West Africa timeseries records")
    return inserted

def log_run(conn, status, rows):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO pipeline_runs
        (pipeline,status,rows_ingested,finished_at)
        VALUES (%s,%s,%s,%s)
    """, ("ebola_loader", status, rows, datetime.utcnow()))
    conn.commit()

def run_loader():
    print("=" * 55)
    print("EBOLA WAREHOUSE LOADER STARTED")
    print("=" * 55)
    conn = get_conn()
    print("Connected to ebola_db!")

    load_countries(conn)
    r1 = load_who_historical(conn)
    r2 = load_drc_timeseries(conn)
    r3 = load_west_africa_timeseries(conn)
    total = r1 + r2 + r3

    log_run(conn, "SUCCESS", total)

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM fact_ebola_outbreaks")
    c1 = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM fact_ebola_drc_timeseries")
    c2 = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM fact_ebola_west_africa")
    c3 = cur.fetchone()[0]

    print("\n" + "=" * 55)
    print("EBOLA WAREHOUSE LOAD COMPLETE")
    print(f"  fact_ebola_outbreaks      : {c1} rows")
    print(f"  fact_ebola_drc_timeseries : {c2} rows")
    print(f"  fact_ebola_west_africa    : {c3} rows")
    print(f"  pipeline_runs             : logged")
    print("=" * 55)
    conn.close()

if __name__ == "__main__":
    run_loader()
