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
    "dbname":   os.getenv("EBOLA_DB", "ebola_db")
}

DDL = """
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS dim_countries (
    id         SERIAL PRIMARY KEY,
    iso3       CHAR(3) UNIQUE NOT NULL,
    iso2       CHAR(2),
    country    VARCHAR(100) NOT NULL,
    region     VARCHAR(100),
    continent  VARCHAR(50),
    latitude   DOUBLE PRECISION,
    longitude  DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fact_ebola_outbreaks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    iso3            CHAR(3),
    country         VARCHAR(100),
    year            INTEGER NOT NULL,
    outbreak_id     VARCHAR(100),
    total_cases     INTEGER DEFAULT 0,
    deaths          INTEGER DEFAULT 0,
    cfr             DOUBLE PRECISION,
    strain          VARCHAR(100),
    source          VARCHAR(200),
    data_quality    VARCHAR(20) DEFAULT 'verified',
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fact_ebola_drc_timeseries (
    id           SERIAL PRIMARY KEY,
    report_date  VARCHAR(50),
    health_zone  VARCHAR(200),
    province     VARCHAR(200),
    cases_confirmed INTEGER DEFAULT 0,
    cases_probable  INTEGER DEFAULT 0,
    cases_suspected INTEGER DEFAULT 0,
    total_cases     INTEGER DEFAULT 0,
    deaths          INTEGER DEFAULT 0,
    iso3            CHAR(3) DEFAULT 'COD',
    ingested_at     TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fact_ebola_west_africa (
    id              SERIAL PRIMARY KEY,
    report_date     VARCHAR(50),
    guinea_cases    INTEGER DEFAULT 0,
    guinea_deaths   INTEGER DEFAULT 0,
    liberia_cases   INTEGER DEFAULT 0,
    liberia_deaths  INTEGER DEFAULT 0,
    sierraleone_cases  INTEGER DEFAULT 0,
    sierraleone_deaths INTEGER DEFAULT 0,
    total_cases     INTEGER DEFAULT 0,
    total_deaths    INTEGER DEFAULT 0,
    ingested_at     TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fact_ebola_risk_scores (
    id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    iso3               CHAR(3),
    country            VARCHAR(100),
    year               INTEGER,
    outbreak_score     DOUBLE PRECISION DEFAULT 0,
    mortality_score    DOUBLE PRECISION DEFAULT 0,
    facility_score     DOUBLE PRECISION DEFAULT 0,
    containment_score  DOUBLE PRECISION DEFAULT 0,
    crossborder_score  DOUBLE PRECISION DEFAULT 0,
    risk_score         DOUBLE PRECISION DEFAULT 0,
    risk_level         VARCHAR(20),
    latitude           DOUBLE PRECISION,
    longitude          DOUBLE PRECISION,
    computed_at        TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fact_displaced_populations (
    id              SERIAL PRIMARY KEY,
    iso3            CHAR(3),
    country         VARCHAR(100),
    year            INTEGER,
    refugees        BIGINT DEFAULT 0,
    idps            BIGINT DEFAULT 0,
    total_displaced BIGINT DEFAULT 0,
    source          VARCHAR(100) DEFAULT 'UNHCR',
    ingested_at     TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id            SERIAL PRIMARY KEY,
    pipeline      VARCHAR(100),
    status        VARCHAR(20),
    rows_ingested INTEGER,
    error_msg     TEXT,
    started_at    TIMESTAMP DEFAULT NOW(),
    finished_at   TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ebola_iso3  ON fact_ebola_outbreaks(iso3);
CREATE INDEX IF NOT EXISTS idx_ebola_year  ON fact_ebola_outbreaks(year);
CREATE INDEX IF NOT EXISTS idx_ebola_risk  ON fact_ebola_risk_scores(iso3);
CREATE INDEX IF NOT EXISTS idx_ebola_level ON fact_ebola_risk_scores(risk_level);
"""

def create_schema():
    print("Connecting to ebola_db...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    cur = conn.cursor()
    print("Creating tables...")
    cur.execute(DDL)
    cur.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' ORDER BY table_name
    """)
    tables = cur.fetchall()
    print(f"\nTables in ebola_db:")
    for t in tables:
        print(f"  - {t[0]}")
    conn.close()
    print("\nSchema created successfully!")

if __name__ == "__main__":
    create_schema()
