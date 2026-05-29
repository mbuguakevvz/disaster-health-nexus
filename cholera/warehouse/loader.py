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
    "dbname":   os.getenv("CHOLERA_DB", "cholera_db")
}

def get_conn():
    return psycopg2.connect(**DB_CONFIG)

def load_countries_reference(conn):
    print("Loading country reference data...")
    countries = [
        ("COD","CD","DR Congo","Central Africa","Africa",-4.0,21.7),
        ("SOM","SO","Somalia","East Africa","Africa",5.1,46.1),
        ("ETH","ET","Ethiopia","East Africa","Africa",9.1,40.4),
        ("SDN","SD","Sudan","North Africa","Africa",15.5,32.5),
        ("NGA","NG","Nigeria","West Africa","Africa",9.0,8.6),
        ("MOZ","MZ","Mozambique","Southern Africa","Africa",-18.6,35.5),
        ("ZWE","ZW","Zimbabwe","Southern Africa","Africa",-20.0,30.0),
        ("HTI","HT","Haiti","Caribbean","Americas",18.9,-72.3),
        ("YEM","YE","Yemen","Middle East","Asia",15.5,48.5),
        ("SYR","SY","Syria","Middle East","Asia",34.8,38.9),
        ("CMR","CM","Cameroon","Central Africa","Africa",3.8,11.5),
        ("TCD","TD","Chad","Central Africa","Africa",15.4,18.7),
        ("NER","NE","Niger","West Africa","Africa",17.6,8.0),
        ("MLI","ML","Mali","West Africa","Africa",17.5,-4.0),
        ("GIN","GN","Guinea","West Africa","Africa",11.0,-10.9),
        ("COG","CG","Congo","Central Africa","Africa",-0.2,15.8),
        ("CAF","CF","Central African Republic","Central Africa","Africa",6.6,20.9),
        ("BDI","BI","Burundi","East Africa","Africa",-3.4,29.9),
        ("TZA","TZ","Tanzania","East Africa","Africa",-6.3,34.8),
        ("KEN","KE","Kenya","East Africa","Africa",0.0,37.9),
        ("UGA","UG","Uganda","East Africa","Africa",1.3,32.3),
        ("ZMB","ZM","Zambia","Southern Africa","Africa",-13.1,27.8),
        ("MWI","MW","Malawi","Southern Africa","Africa",-13.2,34.3),
        ("AGO","AO","Angola","Central Africa","Africa",-11.2,17.9),
        ("BGD","BD","Bangladesh","South Asia","Asia",23.6,90.3),
        ("IND","IN","India","South Asia","Asia",20.5,78.9),
        ("AFG","AF","Afghanistan","Central Asia","Asia",33.9,67.7),
        ("PAK","PK","Pakistan","South Asia","Asia",30.3,69.3),
        ("PHL","PH","Philippines","Southeast Asia","Asia",12.8,121.7),
        ("COL","CO","Colombia","South America","Americas",4.5,-74.0),
    ]
    cur = conn.cursor()
    inserted = 0
    for c in countries:
        try:
            cur.execute("""
                INSERT INTO dim_countries
                (iso3, iso2, country, region, continent, latitude, longitude)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (iso3) DO NOTHING
            """, c)
            inserted += 1
        except Exception as e:
            print(f"  Skipping {c[0]}: {e}")
    conn.commit()
    print(f"  Loaded {inserted} countries")

def load_who_gho_cases():
    path = "cholera/ingestion/data/WHO_GHO_Cholera.csv"
    print(f"\nLoading WHO GHO Cases...")
    df = pd.read_csv(path)
    df = df[df["SpatialDimType"] == "COUNTRY"].copy()
    df = df.rename(columns={"SpatialDim":"iso3","TimeDim":"year","NumericValue":"cases"})
    df = df[["iso3","year","cases"]].dropna(subset=["iso3","year"])
    df["cases"] = pd.to_numeric(df["cases"], errors="coerce").fillna(0).astype(int)
    df["year"]  = pd.to_numeric(df["year"],  errors="coerce").fillna(0).astype(int)
    print(f"  {len(df)} records | Years: {df['year'].min()}-{df['year'].max()} | Countries: {df['iso3'].nunique()}")
    return df

def load_who_gho_deaths():
    path = "cholera/ingestion/data/WHO_GHO_Cholera_Deaths.csv"
    print(f"Loading WHO GHO Deaths...")
    df = pd.read_csv(path)
    df = df[df["SpatialDimType"] == "COUNTRY"].copy()
    df = df.rename(columns={"SpatialDim":"iso3","TimeDim":"year","NumericValue":"deaths"})
    df = df[["iso3","year","deaths"]].dropna(subset=["iso3","year"])
    df["deaths"] = pd.to_numeric(df["deaths"], errors="coerce").fillna(0).astype(int)
    df["year"]   = pd.to_numeric(df["year"],   errors="coerce").fillna(0).astype(int)
    print(f"  {len(df)} records")
    return df

def load_who_gho_cfr():
    path = "cholera/ingestion/data/WHO_GHO_Cholera_CFR.csv"
    print(f"Loading WHO GHO CFR...")
    df = pd.read_csv(path)
    df = df[df["SpatialDimType"] == "COUNTRY"].copy()
    df = df.rename(columns={"SpatialDim":"iso3","TimeDim":"year","NumericValue":"cfr"})
    df = df[["iso3","year","cfr"]].dropna(subset=["iso3","year"])
    df["cfr"]  = pd.to_numeric(df["cfr"],  errors="coerce").fillna(0)
    df["year"] = pd.to_numeric(df["year"], errors="coerce").fillna(0).astype(int)
    print(f"  {len(df)} records")
    return df

def merge_and_load_facts(conn, cases_df, deaths_df, cfr_df):
    print("\nMerging and loading into fact_cholera_outbreaks...")
    merged = cases_df.merge(deaths_df, on=["iso3","year"], how="outer")
    merged = merged.merge(cfr_df,    on=["iso3","year"], how="outer")
    merged = merged.fillna(0)
    print(f"  Merged: {len(merged)} rows")

    cur = conn.cursor()
    inserted = 0
    skipped  = 0
    for _, row in merged.iterrows():
        try:
            cur.execute("""
                INSERT INTO fact_cholera_outbreaks
                (iso3, country, year, cases, deaths, cfr, source, data_quality)
                VALUES (%s,
                    (SELECT country FROM dim_countries WHERE iso3=%s LIMIT 1),
                    %s,%s,%s,%s,%s,%s)
            """, (
                row["iso3"], row["iso3"],
                int(row["year"]),
                int(row.get("cases",0)),
                int(row.get("deaths",0)),
                float(row.get("cfr",0)),
                "WHO_GHO", "verified"
            ))
            inserted += 1
        except Exception as e:
            skipped += 1
    conn.commit()
    print(f"  Inserted: {inserted} | Skipped: {skipped}")
    return inserted

def load_weekly_outbreaks(conn):
    path = "cholera/ingestion/data/cholera_outbreaks_in_central_and_west_af.csv"
    if not os.path.exists(path):
        print("Weekly file not found, skipping")
        return 0
    print("\nLoading weekly outbreak data...")
    df = pd.read_csv(path)
    week_cols = [c for c in df.columns if c.startswith("W")]
    melted = df.melt(
        id_vars=["ISO3","Country"],
        value_vars=week_cols,
        var_name="week",
        value_name="cases"
    )
    melted = melted.rename(columns={"ISO3":"iso3","Country":"country"})
    melted["week_number"] = melted["week"].str.replace("W","").astype(int)
    melted["year"]  = 2017
    melted["cases"] = pd.to_numeric(melted["cases"], errors="coerce").fillna(0).astype(int)
    melted = melted[melted["cases"] > 0]
    print(f"  Weekly records with cases > 0: {len(melted)}")

    cur = conn.cursor()
    inserted = 0
    for _, row in melted.iterrows():
        try:
            cur.execute("""
                INSERT INTO fact_cholera_outbreaks
                (iso3, country, year, week_number, cases, source, data_quality)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (
                row["iso3"], row["country"],
                int(row["year"]), int(row["week_number"]),
                int(row["cases"]), "HDX_Regional", "raw"
            ))
            inserted += 1
        except Exception as e:
            pass
    conn.commit()
    print(f"  Inserted {inserted} weekly records")
    return inserted

def log_pipeline_run(conn, status, rows, error=None):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO pipeline_runs
        (pipeline, status, rows_ingested, error_msg, finished_at)
        VALUES (%s,%s,%s,%s,%s)
    """, ("cholera_loader", status, rows, error, datetime.utcnow()))
    conn.commit()

def run_loader():
    print("=" * 50)
    print("CHOLERA WAREHOUSE LOADER STARTED")
    print("=" * 50)
    try:
        conn = get_conn()
        print("Connected to cholera_db!")

        load_countries_reference(conn)
        cases_df  = load_who_gho_cases()
        deaths_df = load_who_gho_deaths()
        cfr_df    = load_who_gho_cfr()
        rows      = merge_and_load_facts(conn, cases_df, deaths_df, cfr_df)
        weekly    = load_weekly_outbreaks(conn)
        total     = rows + weekly

        log_pipeline_run(conn, "SUCCESS", total)

        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM fact_cholera_outbreaks")
        count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM dim_countries")
        countries = cur.fetchone()[0]

        print("\n" + "=" * 50)
        print("WAREHOUSE LOAD COMPLETE")
        print(f"  fact_cholera_outbreaks : {count} rows")
        print(f"  dim_countries          : {countries} rows")
        print(f"  pipeline_runs          : logged")
        print("=" * 50)
        conn.close()

    except Exception as e:
        print(f"LOADER FAILED: {e}")
        raise

if __name__ == "__main__":
    run_loader()
