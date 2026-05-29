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

DDL = """
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS dim_countries (
    id          SERIAL PRIMARY KEY,
    iso3        CHAR(3) UNIQUE NOT NULL,
    iso2        CHAR(2),
    country     VARCHAR(100) NOT NULL,
    region      VARCHAR(100),
    continent   VARCHAR(50),
    latitude    DOUBLE PRECISION,
    longitude   DOUBLE PRECISION,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fact_cholera_outbreaks (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    iso3         CHAR(3),
    country      VARCHAR(100),
    year         INTEGER NOT NULL,
    week_number  INTEGER,
    cases        INTEGER,
    deaths       INTEGER,
    cfr          DOUBLE PRECISION,
    source       VARCHAR(200),
    data_quality VARCHAR(20) DEFAULT 'raw',
    created_at   TIMESTAMP DEFAULT NOW(),
    updated_at   TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dim_health_facilities (
    id            SERIAL PRIMARY KEY,
    osm_id        BIGINT UNIQUE,
    facility_name VARCHAR(200),
    facility_type VARCHAR(50),
    iso3          CHAR(3),
    country       VARCHAR(100),
    region        VARCHAR(100),
    latitude      DOUBLE PRECISION,
    longitude     DOUBLE PRECISION,
    operator      VARCHAR(200),
    beds          VARCHAR(50),
    emergency     VARCHAR(20),
    opening_hours VARCHAR(200),
    ingested_at   TIMESTAMP DEFAULT NOW()
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

CREATE TABLE IF NOT EXISTS fact_cholera_risk_scores (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    iso3             CHAR(3),
    country          VARCHAR(100),
    year             INTEGER,
    week_number      INTEGER,
    outbreak_score   DOUBLE PRECISION DEFAULT 0,
    population_score DOUBLE PRECISION DEFAULT 0,
    facility_score   DOUBLE PRECISION DEFAULT 0,
    wash_score       DOUBLE PRECISION DEFAULT 0,
    risk_score       DOUBLE PRECISION DEFAULT 0,
    risk_level       VARCHAR(20),
    latitude         DOUBLE PRECISION,
    longitude        DOUBLE PRECISION,
    computed_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw_cholera_outbreaks (
    id             SERIAL PRIMARY KEY,
    source_dataset VARCHAR(200),
    iso3           CHAR(3),
    country        VARCHAR(100),
    year           INTEGER,
    cases          DOUBLE PRECISION,
    deaths         DOUBLE PRECISION,
    cfr            DOUBLE PRECISION,
    week_number    VARCHAR(10),
    raw_data       JSONB,
    ingested_at    TIMESTAMP DEFAULT NOW()
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

CREATE INDEX IF NOT EXISTS idx_outbreaks_iso3  ON fact_cholera_outbreaks(iso3);
CREATE INDEX IF NOT EXISTS idx_outbreaks_year  ON fact_cholera_outbreaks(year);
CREATE INDEX IF NOT EXISTS idx_risk_iso3       ON fact_cholera_risk_scores(iso3);
CREATE INDEX IF NOT EXISTS idx_risk_level      ON fact_cholera_risk_scores(risk_level);
CREATE INDEX IF NOT EXISTS idx_populations_iso3 ON fact_displaced_populations(iso3);
"""

def create_schema():
    print("Connecting to cholera_db...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    cur = conn.cursor()

    print("Creating tables...")
    cur.execute(DDL)
    print("All tables created successfully!")

    cur.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    tables = cur.fetchall()
    print(f"\nTables in cholera_db:")
    for t in tables:
        print(f"  - {t[0]}")

    conn.close()

if __name__ == "__main__":
    create_schema()
