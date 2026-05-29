import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import os

st.set_page_config(page_title="Disaster Health Nexus - Cholera", page_icon="🔵", layout="wide")

API_URL = "http://localhost:8001"

def fetch(endpoint):
    try:
        r = requests.get(f"{API_URL}{endpoint}", timeout=10)
        return r.json()
    except:
        return None

def load_csv(path):
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()

color_map = {"CRITICAL": "#ff0000", "HIGH": "#ff6600", "MEDIUM": "#ffaa00", "LOW": "#00aa00"}

st.sidebar.title("Disaster Health Nexus")
st.sidebar.markdown("**Disease: Cholera**")
st.sidebar.markdown("---")
page = st.sidebar.radio("Navigate", ["Global Risk Map","Outbreak Trends","Country Deep Dive","Top Countries","API Status"])
st.sidebar.markdown("---")
st.sidebar.markdown("Built by **Kevin Mbugua**")
st.sidebar.markdown("[@mbuguakevvz](https://github.com/mbuguakevvz)")

if page == "Global Risk Map":
    st.title("🔵 Cholera Global Risk Map")
    st.markdown("Real-time epidemic risk scores for displaced populations — powered by WHO GHO data")
    summary = fetch("/cholera/summary")
    if summary:
        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("Countries", summary["countries_monitored"])
        c2.metric("Total Cases", f"{summary['total_cases_all_time']:,}")
        c3.metric("Total Deaths", f"{summary['total_deaths_all_time']:,}")
        c4.metric("CRITICAL", summary["risk_distribution"]["CRITICAL"])
        c5.metric("HIGH", summary["risk_distribution"]["HIGH"])
    st.markdown("---")
    df = load_csv("cholera/dashboard/data/risk_scores.csv")
    if not df.empty:
        df["risk_score"] = pd.to_numeric(df["risk_score"], errors="coerce").fillna(0.1)
        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
        df_map = df.dropna(subset=["latitude","longitude"])
        df_map = df_map[df_map["risk_score"] > 0].copy()
        col1, col2 = st.columns([3,1])
        with col1:
            fig = px.scatter_geo(
                df_map, lat="latitude", lon="longitude",
                color="risk_level", size="risk_score",
                hover_name="country",
                color_discrete_map=color_map,
                size_max=25, projection="natural earth",
                title="Cholera Risk Scores by Country"
            )
            fig.update_layout(height=500, margin={"r":0,"t":40,"l":0,"b":0})
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            st.subheader("CRITICAL Countries")
            for _, r in df[df["risk_level"]=="CRITICAL"].sort_values("risk_score",ascending=False).iterrows():
                st.error(f"🔴 {r['iso3']} {r['country']} — {r['risk_score']:.3f}")
            st.subheader("HIGH Risk")
            for _, r in df[df["risk_level"]=="HIGH"].sort_values("risk_score",ascending=False).head(8).iterrows():
                st.warning(f"🟠 {r['iso3']} {r['country']} — {r['risk_score']:.3f}")

elif page == "Outbreak Trends":
    st.title("📈 Cholera Outbreak Trends")
    df = load_csv("cholera/dashboard/data/outbreak_trends.csv")
    if not df.empty:
        yearly = df.groupby("year").agg(
            total_cases=("cases","sum"),
            total_deaths=("deaths","sum")
        ).reset_index()
        yearly = yearly[yearly["year"] >= 2000]
        fig = go.Figure()
        fig.add_trace(go.Bar(x=yearly["year"], y=yearly["total_cases"], name="Cases", marker_color="#2196F3"))
        fig.add_trace(go.Scatter(x=yearly["year"], y=yearly["total_deaths"], name="Deaths", mode="lines+markers", line=dict(color="red"), yaxis="y2"))
        fig.update_layout(title="Global Cholera Cases and Deaths", yaxis2=dict(overlaying="y", side="right"), height=450)
        st.plotly_chart(fig, use_container_width=True)
        top_iso3 = df.groupby("iso3")["cases"].sum().nlargest(10).index.tolist()
        fig2 = px.line(df[df["iso3"].isin(top_iso3)], x="year", y="cases", color="iso3", markers=True, title="Top 10 Countries Over Time")
        fig2.update_layout(height=400)
        st.plotly_chart(fig2, use_container_width=True)

elif page == "Country Deep Dive":
    st.title("🔍 Country Deep Dive")
    iso3 = st.text_input("ISO3 code (e.g. HTI, COD, SOM)", value="HTI").upper()
    if iso3:
        data = fetch(f"/cholera/outbreaks/{iso3}")
        risk = fetch(f"/cholera/risk/{iso3}")
        if data and risk:
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Country", data.get("country", iso3))
            c2.metric("Total Cases", f"{data['total_cases']:,}")
            c3.metric("Total Deaths", f"{data['total_deaths']:,}")
            c4.metric("Risk Level", risk.get("latest_risk_level","N/A"))
            df_c = pd.DataFrame(data["data"])
            if not df_c.empty:
                df_y = df_c.groupby("year").agg(cases=("cases","sum"), deaths=("deaths","sum")).reset_index()
                fig = px.bar(df_y, x="year", y=["cases","deaths"], barmode="group", title=f"{iso3} Cases and Deaths by Year")
                st.plotly_chart(fig, use_container_width=True)
            df_risk = pd.DataFrame(risk["history"])
            if not df_risk.empty:
                fig2 = px.line(df_risk, x="year", y="risk_score", markers=True, title=f"{iso3} Risk Score Over Time", color_discrete_sequence=["#ff6600"])
                fig2.add_hline(y=0.70, line_dash="dash", line_color="red", annotation_text="CRITICAL")
                fig2.add_hline(y=0.45, line_dash="dash", line_color="orange", annotation_text="HIGH")
                st.plotly_chart(fig2, use_container_width=True)
        else:
            st.error(f"No data for {iso3}. Try: HTI, COD, SOM, NGA, ETH")

elif page == "Top Countries":
    st.title("🏆 Top Countries by Cholera Burden")
    df = load_csv("cholera/dashboard/data/top_countries.csv")
    if not df.empty:
        fig = px.bar(df.head(15), x="country", y="total_cases", color="total_deaths", color_continuous_scale="Reds", title="Top 15 Countries — Total Cholera Cases")
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True)

elif page == "API Status":
    st.title("API Status")
    health = fetch("/health")
    if health:
        st.success(f"Cholera API: {health['status'].upper()}")
        st.json(health)
    else:
        st.error("API not reachable. Run: uvicorn cholera.api.main:app --port 8001")