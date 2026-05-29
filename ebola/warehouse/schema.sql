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

CREATE TABLE IF NOT EXISTS fact_ebola_outbreaks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    iso3            CHAR(3),
    country         VARCHAR(100),
    year            INTEGER NOT NULL,
    outbreak_id     VARCHAR(100),
    cases_suspected INTEGER DEFAULT 0,
    cases_probable  INTEGER DEFAULT 0,
    cases_confirmed INTEGER DEFAULT 0,
    total_cases     INTEGER DEFAULT 0,
    deaths          INTEGER DEFAULT 0,
    cfr             DOUBLE PRECISION,
    strain          VARCHAR(100),
    source          VARCHAR(200),
    data_quality    VARCHAR(20) DEFAULT 'raw',
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dim_health_facilities (
    id              SERIAL PRIMARY KEY,
    osm_id          BIGINT UNIQUE,
    facility_name   VARCHAR(200),
    facility_type   VARCHAR(50),
    iso3            CHAR(3),
    country         VARCHAR(100),
    region          VARCHAR(100),
    latitude        DOUBLE PRECISION,
    longitude       DOUBLE PRECISION,
    operator        VARCHAR(200),
    beds            VARCHAR(50),
    emergency       VARCHAR(20),
    opening_hours   VARCHAR(200),
    ingested_at     TIMESTAMP DEFAULT NOW()
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

CREATE TABLE IF NOT EXISTS fact_ebola_risk_scores (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    iso3                CHAR(3),
    country             VARCHAR(100),
    year                INTEGER,
    outbreak_score      DOUBLE PRECISION DEFAULT 0,
    population_score    DOUBLE PRECISION DEFAULT 0,
    facility_score      DOUBLE PRECISION DEFAULT 0,
    containment_score   DOUBLE PRECISION DEFAULT 0,
    crossborder_score   DOUBLE PRECISION DEFAULT 0,
    risk_score          DOUBLE PRECISION DEFAULT 0,
    risk_level          VARCHAR(20),
    latitude            DOUBLE PRECISION,
    longitude           DOUBLE PRECISION,
    computed_at         TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raw_ebola_outbreaks (
    id              SERIAL PRIMARY KEY,
    source_dataset  VARCHAR(200),
    iso3            CHAR(3),
    country         VARCHAR(100),
    year            INTEGER,
    cases_suspected DOUBLE PRECISION,
    cases_probable  DOUBLE PRECISION,
    cases_confirmed DOUBLE PRECISION,
    total_cases     DOUBLE PRECISION,
    deaths          DOUBLE PRECISION,
    cfr             DOUBLE PRECISION,
    outbreak_id     VARCHAR(100),
    raw_data        JSONB,
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

CREATE INDEX IF NOT EXISTS idx_ebola_outbreaks_iso3 ON fact_ebola_outbreaks(iso3);
CREATE INDEX IF NOT EXISTS idx_ebola_outbreaks_year ON fact_ebola_outbreaks(year);
CREATE INDEX IF NOT EXISTS idx_ebola_risk_iso3 ON fact_ebola_risk_scores(iso3);
CREATE INDEX IF NOT EXISTS idx_ebola_risk_level ON fact_ebola_risk_scores(risk_level);
