"""
Ebola Risk API
FastAPI serving layer for Ebola risk scores and outbreak data
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
import pandas as pd
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from dotenv import load_dotenv
load_dotenv()
from typing import Optional

DB_URL = (
    f"postgresql+psycopg2://"
    f"{os.getenv('DB_USER','postgres')}:{os.getenv('DB_PASSWORD','')}@"
    f"{os.getenv('DB_HOST','localhost')}:{os.getenv('DB_PORT','5432')}/"
    f"{os.getenv('EBOLA_DB','ebola_db')}"
)
engine = create_engine(DB_URL, echo=False)

app = FastAPI(
    title="Disaster Health Nexus - Ebola API",
    description="Real-time Ebola epidemic risk pipeline for displaced populations",
    version="1.0.0",
    contact={"name": "Kevin Mbugua", "url": "https://github.com/mbuguakevvz"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def query_df(sql, params={}):
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)

@app.get("/", tags=["Info"])
def root():
    return {
        "project": "Disaster Health Nexus",
        "disease": "Ebola",
        "author":  "Kevin Mbugua (@mbuguakevvz)",
        "endpoints": [
            "/health",
            "/ebola/risk",
            "/ebola/risk/{iso3}",
            "/ebola/outbreaks",
            "/ebola/outbreaks/{iso3}",
            "/ebola/drc-timeseries",
            "/ebola/summary",
            "/docs"
        ]
    }

@app.get("/health", tags=["Health"])
def health_check():
    try:
        with engine.connect() as conn:
            r = conn.execute(text("SELECT COUNT(*) FROM fact_ebola_outbreaks"))
            count = r.fetchone()[0]
        return {"status": "healthy", "database": "connected", "outbreak_records": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ebola/risk", tags=["Risk Scores"])
def get_all_risk_scores(
    risk_level: Optional[str] = Query(None, description="LOW, MEDIUM, HIGH, CRITICAL")
):
    sql = """
        SELECT DISTINCT ON (iso3)
            iso3, country, year, risk_score, risk_level,
            outbreak_score, mortality_score, containment_score,
            crossborder_score, latitude, longitude
        FROM fact_ebola_risk_scores
        ORDER BY iso3, year DESC
    """
    df = query_df(sql)
    if risk_level:
        df = df[df["risk_level"] == risk_level.upper()]
    df = df.sort_values("risk_score", ascending=False)
    return {"total": len(df), "data": df.fillna("").to_dict(orient="records")}

@app.get("/ebola/risk/{iso3}", tags=["Risk Scores"])
def get_country_risk(iso3: str):
    sql = """
        SELECT iso3, country, year, risk_score, risk_level,
               outbreak_score, mortality_score, containment_score,
               crossborder_score, latitude, longitude
        FROM fact_ebola_risk_scores
        WHERE UPPER(iso3) = UPPER(:iso3)
        ORDER BY year DESC
    """
    df = query_df(sql, {"iso3": iso3.upper()})
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No risk data for {iso3}")
    return {
        "iso3": iso3.upper(),
        "country": df.iloc[0]["country"],
        "latest_risk_level": df.iloc[0]["risk_level"],
        "latest_risk_score": float(df.iloc[0]["risk_score"]),
        "history": df.fillna("").to_dict(orient="records")
    }

@app.get("/ebola/outbreaks", tags=["Outbreaks"])
def get_outbreaks(year: Optional[int] = None):
    sql = """
        SELECT iso3, country, year, total_cases,
               deaths, cfr, strain, outbreak_id
        FROM fact_ebola_outbreaks
        ORDER BY year DESC, total_cases DESC
    """
    df = query_df(sql)
    if year:
        df = df[df["year"] == year]
    return {"total": len(df), "data": df.fillna("").to_dict(orient="records")}

@app.get("/ebola/outbreaks/{iso3}", tags=["Outbreaks"])
def get_country_outbreaks(iso3: str):
    sql = """
        SELECT iso3, country, year, total_cases,
               deaths, cfr, strain, outbreak_id
        FROM fact_ebola_outbreaks
        WHERE UPPER(iso3) = UPPER(:iso3)
        ORDER BY year DESC
    """
    df = query_df(sql, {"iso3": iso3.upper()})
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data for {iso3}")
    return {
        "iso3": iso3.upper(),
        "country": df.iloc[0]["country"],
        "total_outbreaks": len(df),
        "total_cases": int(df["total_cases"].sum()),
        "total_deaths": int(df["deaths"].sum()),
        "data": df.fillna("").to_dict(orient="records")
    }

@app.get("/ebola/drc-timeseries", tags=["DRC 2018"])
def get_drc_timeseries(limit: int = Query(100, le=591)):
    sql = """
        SELECT report_date, health_zone, province,
               total_cases, deaths
        FROM fact_ebola_drc_timeseries
        ORDER BY report_date DESC
        LIMIT :limit
    """
    df = query_df(sql, {"limit": limit})
    return {"total": len(df), "data": df.fillna("").to_dict(orient="records")}

@app.get("/ebola/summary", tags=["Summary"])
def get_summary():
    sql1 = """
        SELECT COUNT(DISTINCT iso3) as countries,
               SUM(total_cases) as total_cases,
               SUM(deaths) as total_deaths,
               AVG(cfr) as avg_cfr
        FROM fact_ebola_outbreaks
    """
    sql2 = """
        SELECT risk_level, COUNT(*) as count
        FROM (
            SELECT DISTINCT ON (iso3) iso3, risk_level
            FROM fact_ebola_risk_scores
            ORDER BY iso3, year DESC
        ) t
        GROUP BY risk_level
    """
    df1 = query_df(sql1)
    df2 = query_df(sql2)
    risk_counts = dict(zip(df2["risk_level"], df2["count"]))
    return {
        "countries_with_outbreaks": int(df1.iloc[0]["countries"]),
        "total_cases_1976_2023":    int(df1.iloc[0]["total_cases"] or 0),
        "total_deaths_1976_2023":   int(df1.iloc[0]["total_deaths"] or 0),
        "average_cfr_percent":      round(float(df1.iloc[0]["avg_cfr"] or 0), 2),
        "risk_distribution": {
            "CRITICAL": int(risk_counts.get("CRITICAL", 0)),
            "HIGH":     int(risk_counts.get("HIGH", 0)),
            "MEDIUM":   int(risk_counts.get("MEDIUM", 0)),
            "LOW":      int(risk_counts.get("LOW", 0)),
        }
    }
