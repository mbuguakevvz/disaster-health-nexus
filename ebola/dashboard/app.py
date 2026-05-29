import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import os

st.set_page_config(
    page_title="Disaster Health Nexus - Ebola",
    page_icon="🔴",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_URL = "http://localhost:8002"

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

st.sidebar.title("Disaster Health Nexus")
st.sidebar.markdown("**Disease: Ebola**")
st.sidebar.markdown("---")
page = st.sidebar.radio("Navigate", [
    "Global Risk Map",
    "Outbreak Timeline",
    "DRC 2018 Outbreak",
    "Country Deep Dive",
    "API Status"
])
st.sidebar.markdown("---")
st.sidebar.markdown("Built by **Kevin Mbugua**")
st.sidebar.markdown("[@mbuguakevvz](https://github.com/mbuguakevvz)")

color_map = {
    "CRITICAL": "#ff0000",
    "HIGH":     "#ff6600",
    "MEDIUM":   "#ffaa00",
    "LOW":      "#00aa00"
}

if page == "Global Risk Map":
    st.title("🔴 Ebola Global Risk Map")
    st.markdown("Epidemic risk scores based on WHO historical outbreak data 1976-2023")

    summary = fetch("/ebola/summary")
    if summary:
        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("Countries Affected", summary["countries_with_outbreaks"])
        c2.metric("Total Cases (1976-2023)", f"{summary['total_cases_1976_2023']:,}")
        c3.metric("Total Deaths", f"{summary['total_deaths_1976_2023']:,}")
        c4.metric("Avg CFR", f"{summary['average_cfr_percent']}%")
        c5.metric("CRITICAL Countries", summary["risk_distribution"]["CRITICAL"], delta="High Alert", delta_color="inverse")

    st.markdown("---")
    df = load_csv("ebola/dashboard/data/risk_scores.csv")
    if not df.empty:
        col1, col2 = st.columns([3,1])
        with col1:
            df_map = df.dropna(subset=["latitude","longitude"])
            fig = px.scatter_geo(
                df_map,
                lat="latitude", lon="longitude",
                color="risk_level",
                size="risk_score",
                hover_name="country",
                hover_data={"risk_score":":.3f","year":True,"iso3":True},
                color_discrete_map=color_map,
                size_max=30,
                projection="natural earth",
                title="Ebola Risk Scores by Country"
            )
            fig.update_layout(height=500, margin={"r":0,"t":40,"l":0,"b":0})
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Risk Distribution")
            if summary:
                risk_data = summary["risk_distribution"]
                fig_pie = px.pie(
                    values=list(risk_data.values()),
                    names=list(risk_data.keys()),
                    color=list(risk_data.keys()),
                    color_discrete_map=color_map,
                    hole=0.4,
                )
                fig_pie.update_layout(height=280)
                st.plotly_chart(fig_pie, use_container_width=True)

            st.subheader("CRITICAL")
            for _, r in df[df["risk_level"]=="CRITICAL"].iterrows():
                st.error(f"🔴 {r['iso3']} {str(r['country'])} — {r['risk_score']:.3f}")
            st.subheader("HIGH")
            for _, r in df[df["risk_level"]=="HIGH"].head(6).iterrows():
                st.warning(f"🟠 {r['iso3']} {str(r['country'])} — {r['risk_score']:.3f}")

elif page == "Outbreak Timeline":
    st.title("📅 Ebola Outbreak Timeline (1976-2023)")
    df = load_csv("ebola/dashboard/data/outbreaks.csv")
    if not df.empty:
        fig = px.scatter(
            df, x="year", y="total_cases",
            size="total_cases", color="iso3",
            hover_name="country",
            hover_data={"deaths":True,"cfr":True,"strain":True},
            title="Ebola Outbreaks by Country and Year",
            size_max=60,
            labels={"total_cases":"Total Cases","year":"Year"}
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.subheader("Cases vs Deaths by Country")
        agg = df.groupby(["iso3","country"]).agg(
            total_cases=("total_cases","sum"),
            total_deaths=("deaths","sum")
        ).reset_index().sort_values("total_cases", ascending=False)

        fig2 = px.bar(agg, x="country", y=["total_cases","total_deaths"],
            barmode="group", title="Total Cases and Deaths by Country (1976-2023)",
            color_discrete_map={"total_cases":"#ff6600","total_deaths":"#cc0000"})
        fig2.update_layout(height=450)
        st.plotly_chart(fig2, use_container_width=True)

elif page == "DRC 2018 Outbreak":
    st.title("🇨🇩 DRC 2018-2020 Ebola Outbreak")
    st.markdown("The second largest Ebola outbreak in history — 3,481 cases, 2,299 deaths")
    df = load_csv("ebola/dashboard/data/drc_timeseries.csv")
    if not df.empty:
        st.subheader(f"Health Zone Data — {len(df)} records")
        c1,c2,c3 = st.columns(3)
        c1.metric("Total Records", len(df))
        c2.metric("Total Cases", f"{df['total_cases'].sum():,}")
        c3.metric("Total Deaths", f"{df['deaths'].sum():,}")

        st.markdown("---")
        st.subheader("Cases by Health Zone")
        zone_agg = df.groupby("health_zone").agg(
            total_cases=("total_cases","sum"),
            deaths=("deaths","sum")
        ).reset_index().sort_values("total_cases", ascending=False).head(20)

        fig = px.bar(zone_agg, x="health_zone", y="total_cases",
            color="deaths", color_continuous_scale="Reds",
            title="Top 20 Health Zones by Cases")
        fig.update_layout(height=450, xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Raw Data")
        st.dataframe(df.head(50), use_container_width=True)

elif page == "Country Deep Dive":
    st.title("🔍 Country Deep Dive")
    iso3 = st.text_input("Enter ISO3 code (e.g. COD, GIN, LBR, SLE)", value="COD").upper()
    if iso3:
        data = fetch(f"/ebola/outbreaks/{iso3}")
        risk  = fetch(f"/ebola/risk/{iso3}")
        if data:
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Country", data.get("country", iso3))
            c2.metric("Total Outbreaks", data["total_outbreaks"])
            c3.metric("Total Cases", f"{data['total_cases']:,}")
            c4.metric("Total Deaths", f"{data['total_deaths']:,}")
            if risk:
                st.metric("Latest Risk Level",
                    f"{risk['latest_risk_level']} ({risk['latest_risk_score']:.3f})")

            df_c = pd.DataFrame(data["data"])
            if not df_c.empty:
                fig = px.bar(df_c, x="year", y=["total_cases","deaths"],
                    barmode="group", title=f"{iso3} — Ebola Cases and Deaths by Year",
                    color_discrete_map={"total_cases":"#ff6600","deaths":"#cc0000"})
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.error(f"No data for {iso3}. Try: COD, GIN, LBR, SLE, NGA, UGA")

elif page == "API Status":
    st.title("API Status")
    health = fetch("/health")
    if health:
        st.success(f"Ebola API: {health['status'].upper()}")
        st.json(health)
    else:
        st.error("Ebola API not reachable. Run: uvicorn ebola.api.main:app --port 8002")
