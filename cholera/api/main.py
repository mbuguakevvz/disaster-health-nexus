"""
Cholera Risk API
FastAPI serving layer for cholera risk scores and outbreak data
Endpoints:
  GET /health
  GET /cholera/risk
  GET /cholera/risk/{iso3}
  GET /cholera/outbreaks
  GET /cholera/outbreaks/{iso3}
  GET /cholera/summary
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy import create_engine, text
import pandas as pd
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from dotenv import load_dotenv
load_dotenv()

# ── Database ────────────────────────────────────────────────
DB_URL = (
    f"postgresql+psycopg2://"
    f"{os.getenv('DB_USER','postgres')}:{os.getenv('DB_PASSWORD','')}@"
    f"{os.getenv('DB_HOST','localhost')}:{os.getenv('DB_PORT','5432')}/"
    f"{os.getenv('CHOLERA_DB','cholera_db')}"
)
engine = create_engine(DB_URL, echo=False)

# ── App ─────────────────────────────────────────────────────
app = FastAPI(
    title="Disaster Health Nexus - Cholera API",
    description="Real-time cholera epidemic risk & health access pipeline for displaced populations",
    version="1.0.0",
    contact={"name": "Kevin Mbugua", "url": "https://github.com/mbuguakevvz"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Response Models ─────────────────────────────────────────
class RiskScore(BaseModel):
    iso3: str
    country: Optional[str]
    year: int
    risk_score: float
    risk_level: str
    outbreak_score: float
    facility_score: float
    latitude: Optional[float]
    longitude: Optional[float]

class OutbreakRecord(BaseModel):
    iso3: str
    country: Optional[str]
    year: int
    cases: Optional[int]
    deaths: Optional[int]
    cfr: Optional[float]

class SummaryStats(BaseModel):
    total_countries_monitored: int
    critical_countries: int
    high_risk_countries: int
    total_cases_all_time: int
    total_deaths_all_time: int
    last_updated: Optional[str]

# ── Helpers ─────────────────────────────────────────────────
def query_df(sql: str, params: dict = {}) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)

# ── Endpoints ───────────────────────────────────────────────

@app.get("/", tags=["Info"])
def root():
    return {
        "project": "Disaster Health Nexus",
        "disease": "Cholera",
        "author":  "Kevin Mbugua (@mbuguakevvz)",
        "version": "1.0.0",
        "endpoints": [
            "/health",
            "/cholera/risk",
            "/cholera/risk/{iso3}",
            "/cholera/outbreaks",
            "/cholera/outbreaks/{iso3}",
            "/cholera/summary",
            "/cholera/top-countries",
            "/docs"
        ]
    }

@app.get("/health", tags=["Health"])
def health_check():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM fact_cholera_outbreaks"))
            count = result.fetchone()[0]
        return {
            "status": "healthy",
            "database": "connected",
            "outbreak_records": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cholera/risk", tags=["Risk Scores"])
def get_all_risk_scores(
    risk_level: Optional[str] = Query(None, description="Filter by: LOW, MEDIUM, HIGH, CRITICAL"),
    limit: int = Query(100, le=500)
):
    """Get latest risk scores for all countries."""
    sql = """
        SELECT DISTINCT ON (iso3)
            iso3, country, year, risk_score, risk_level,
            outbreak_score, wash_score as facility_score,
            latitude, longitude
        FROM fact_cholera_risk_scores
        ORDER BY iso3, year DESC
    """
    df = query_df(sql)
    if risk_level:
        df = df[df["risk_level"] == risk_level.upper()]
    df = df.sort_values("risk_score", ascending=False).head(limit)
    return {
        "total": len(df),
        "filter": risk_level,
        "data": df.fillna("").to_dict(orient="records")
    }

@app.get("/cholera/risk/{iso3}", tags=["Risk Scores"])
def get_country_risk(iso3: str):
    """Get full risk history for a specific country."""
    sql = """
        SELECT iso3, country, year, risk_score, risk_level,
               outbreak_score, wash_score as facility_score,
               latitude, longitude, computed_at
        FROM fact_cholera_risk_scores
        WHERE UPPER(iso3) = UPPER(:iso3)
        ORDER BY year DESC
    """
    df = query_df(sql, {"iso3": iso3.upper()})
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No risk data found for {iso3}")
    return {
        "iso3": iso3.upper(),
        "country": df.iloc[0]["country"],
        "latest_risk_level": df.iloc[0]["risk_level"],
        "latest_risk_score": df.iloc[0]["risk_score"],
        "history": df.fillna("").to_dict(orient="records")
    }

@app.get("/cholera/outbreaks", tags=["Outbreaks"])
def get_outbreaks(
    year: Optional[int] = Query(None, description="Filter by year"),
    min_cases: Optional[int] = Query(None, description="Minimum case count"),
    limit: int = Query(100, le=1000)
):
    """Get cholera outbreak records."""
    sql = """
        SELECT iso3, country, year,
               SUM(cases) as cases,
               SUM(deaths) as deaths,
               AVG(cfr) as cfr
        FROM fact_cholera_outbreaks
        WHERE 1=1
        GROUP BY iso3, country, year
        ORDER BY cases DESC
        LIMIT :limit
    """
    df = query_df(sql, {"limit": limit})
    if year:
        df = df[df["year"] == year]
    if min_cases:
        df = df[df["cases"] >= min_cases]
    return {
        "total": len(df),
        "data": df.fillna(0).to_dict(orient="records")
    }

@app.get("/cholera/outbreaks/{iso3}", tags=["Outbreaks"])
def get_country_outbreaks(iso3: str):
    """Get full outbreak history for a specific country."""
    sql = """
        SELECT iso3, country, year, week_number,
               cases, deaths, cfr, source, data_quality
        FROM fact_cholera_outbreaks
        WHERE UPPER(iso3) = UPPER(:iso3)
        ORDER BY year DESC, week_number ASC
    """
    df = query_df(sql, {"iso3": iso3.upper()})
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No outbreak data for {iso3}")
    return {
        "iso3": iso3.upper(),
        "country": df.iloc[0]["country"],
        "total_records": len(df),
        "total_cases": int(df["cases"].sum()),
        "total_deaths": int(df["deaths"].sum()),
        "years_active": sorted(df["year"].unique().tolist(), reverse=True),
        "data": df.fillna(0).to_dict(orient="records")
    }

@app.get("/cholera/summary", tags=["Summary"])
def get_summary():
    """Global cholera summary statistics."""
    sql1 = """
        SELECT COUNT(DISTINCT iso3) as countries,
               SUM(cases) as total_cases,
               SUM(deaths) as total_deaths
        FROM fact_cholera_outbreaks
    """
    sql2 = """
        SELECT risk_level, COUNT(*) as count
        FROM (
            SELECT DISTINCT ON (iso3) iso3, risk_level
            FROM fact_cholera_risk_scores
            ORDER BY iso3, year DESC
        ) t
        GROUP BY risk_level
    """
    df1 = query_df(sql1)
    df2 = query_df(sql2)
    risk_counts = dict(zip(df2["risk_level"], df2["count"]))
    return {
        "countries_monitored":  int(df1.iloc[0]["countries"]),
        "total_cases_all_time": int(df1.iloc[0]["total_cases"] or 0),
        "total_deaths_all_time":int(df1.iloc[0]["total_deaths"] or 0),
        "risk_distribution": {
            "CRITICAL": int(risk_counts.get("CRITICAL", 0)),
            "HIGH":     int(risk_counts.get("HIGH", 0)),
            "MEDIUM":   int(risk_counts.get("MEDIUM", 0)),
            "LOW":      int(risk_counts.get("LOW", 0)),
        }
    }

@app.get("/cholera/top-countries", tags=["Summary"])
def get_top_countries(limit: int = Query(10, le=50)):
    """Top countries by total cholera cases."""
    sql = """
        SELECT iso3, country,
               SUM(cases) as total_cases,
               SUM(deaths) as total_deaths,
               AVG(cfr) as avg_cfr,
               COUNT(DISTINCT year) as years_affected
        FROM fact_cholera_outbreaks
        WHERE year >= 2000
        GROUP BY iso3, country
        ORDER BY total_cases DESC
        LIMIT :limit
    """
    df = query_df(sql, {"limit": limit})
    return {
        "total": len(df),
        "data": df.fillna(0).to_dict(orient="records")
    }
