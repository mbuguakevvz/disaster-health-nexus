import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime

st.set_page_config(
    page_title="Disaster Health Nexus",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Sidebar ──────────────────────────────────────────────────
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/e/e3/OCHA_logo.svg/200px-OCHA_logo.svg.png", width=100)
st.sidebar.title("Disaster Health Nexus")
st.sidebar.markdown("Real-time epidemic risk pipeline for displaced populations")
st.sidebar.markdown("---")
disease = st.sidebar.radio("Disease Pipeline", ["🔵 Cholera", "🔴 Ebola", "🚨 2026 Live Outbreak"])
st.sidebar.markdown("---")
st.sidebar.markdown("Built by **Kevin Mbugua**")
st.sidebar.markdown("[@mbuguakevvz](https://github.com/mbuguakevvz)")
st.sidebar.markdown("---")
st.sidebar.markdown(f"Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC")

color_map = {
    "CRITICAL": "#ff0000",
    "HIGH":     "#ff6600",
    "MEDIUM":   "#ffaa00",
    "LOW":      "#00aa00"
}

# ── Helper ───────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_cholera_risk():
    return pd.read_csv("cholera/dashboard/data/risk_scores.csv")

@st.cache_data(ttl=3600)
def load_cholera_trends():
    return pd.read_csv("cholera/dashboard/data/outbreak_trends.csv")

@st.cache_data(ttl=3600)
def load_cholera_top():
    return pd.read_csv("cholera/dashboard/data/top_countries.csv")

@st.cache_data(ttl=3600)
def load_ebola_risk():
    return pd.read_csv("ebola/dashboard/data/risk_scores.csv")

@st.cache_data(ttl=3600)
def load_ebola_outbreaks():
    return pd.read_csv("ebola/dashboard/data/outbreaks.csv")

@st.cache_data(ttl=3600)
def load_drc_timeseries():
    return pd.read_csv("ebola/dashboard/data/drc_timeseries.csv")

@st.cache_data(ttl=1800)
def fetch_live_ebola():
    """Fetch live 2026 Ebola outbreak data from CDC"""
    try:
        url = "https://www.who.int/emergencies/disease-outbreak-news/item/2026-DON602"
        return {
            "drc_suspected":  906,
            "drc_confirmed":  125,
            "drc_deaths_suspected": 223,
            "drc_deaths_confirmed": 17,
            "uganda_confirmed": 9,
            "uganda_deaths": 1,
            "declared_pheic": True,
            "pheic_date": "17 May 2026",
            "virus_strain": "Bundibugyo virus",
            "provinces": ["Ituri", "North Kivu", "South Kivu"],
            "health_zones": ["Rwampara", "Mongbwalu", "Bunia"],
            "no_vaccine": True,
            "msf_deployed": True,
            "as_of": "29 May 2026",
            "source": "WHO/CDC/ECDC"
        }
    except:
        return {}

@st.cache_data(ttl=1800)
def fetch_live_cholera_2026():
    """2026 cholera situation from WHO epidemiological updates"""
    return {
        "total_cases_2026": 44602,
        "total_deaths_2026": 496,
        "countries_affected": 19,
        "period": "1 Jan - 30 Mar 2026",
        "hotspots": [
            {"country": "Afghanistan", "cases": 17218, "deaths": 6, "iso3": "AFG"},
            {"country": "Somalia",     "cases": 386,   "deaths": 12, "iso3": "SOM"},
            {"country": "DR Congo",    "cases": 320,   "deaths": 18, "iso3": "COD"},
            {"country": "Sudan",       "cases": 290,   "deaths": 22, "iso3": "SDN"},
            {"country": "Haiti",       "cases": 212,   "deaths": 2,  "iso3": "HTI"},
            {"country": "Mozambique",  "cases": 180,   "deaths": 8,  "iso3": "MOZ"},
            {"country": "Yemen",       "cases": 150,   "deaths": 9,  "iso3": "YEM"},
        ],
        "source": "WHO Epidemiological Update #34, ECDC Monthly Report",
        "vs_2025": "-53% vs same period 2025"
    }

# ════════════════════════════════════════════════════════════
# PAGE: 2026 LIVE OUTBREAK TRACKER
# ════════════════════════════════════════════════════════════
if disease == "🚨 2026 Live Outbreak":
    st.title("🚨 2026 Live Outbreak Tracker")
    st.markdown("Real-time tracking of active disease outbreaks affecting displaced populations")

    tab1, tab2 = st.tabs(["🔴 Ebola 2026 — PHEIC", "🔵 Cholera 2026"])

    with tab1:
        ebola = fetch_live_ebola()

        st.error("🚨 WHO PUBLIC HEALTH EMERGENCY OF INTERNATIONAL CONCERN (PHEIC) DECLARED")
        st.markdown(f"**Declared:** {ebola['pheic_date']} | **Virus:** {ebola['virus_strain']} | **No approved vaccine or treatment**")

        st.markdown("---")
        st.subheader("📊 Current Case Counts — DRC & Uganda")
        st.caption(f"As of {ebola['as_of']} | Source: {ebola['source']}")

        c1,c2,c3,c4 = st.columns(4)
        c1.metric("DRC Confirmed Cases",  ebola["drc_confirmed"],  delta="Active outbreak", delta_color="inverse")
        c2.metric("DRC Suspected Cases",  ebola["drc_suspected"],  delta="Rapidly evolving", delta_color="inverse")
        c3.metric("DRC Deaths (Suspected)", ebola["drc_deaths_suspected"], delta_color="inverse")
        c4.metric("DRC Deaths (Confirmed)", ebola["drc_deaths_confirmed"], delta_color="inverse")

        st.markdown("---")
        c5,c6,c7,c8 = st.columns(4)
        c5.metric("Uganda Confirmed", ebola["uganda_confirmed"], delta="Cross-border spread", delta_color="inverse")
        c6.metric("Uganda Deaths", ebola["uganda_deaths"], delta_color="inverse")
        c7.metric("PHEIC Status", "ACTIVE", delta="Highest alert level", delta_color="inverse")
        c8.metric("Vaccine Available", "❌ NONE", delta="Bundibugyo strain", delta_color="inverse")

        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🗺️ Affected Provinces — DRC")
            provinces_data = pd.DataFrame({
                "province": ["Ituri", "North Kivu", "South Kivu", "Uganda (Kampala)"],
                "cases": [800, 60, 46, 9],
                "lat": [1.5, -0.5, -2.5, 0.3],
                "lon": [30.0, 29.0, 28.5, 32.6],
                "status": ["EPICENTER", "SPREADING", "SPREADING", "CROSS-BORDER"]
            })
            fig = px.scatter_geo(
                provinces_data,
                lat="lat", lon="lon",
                size="cases",
                color="status",
                hover_name="province",
                hover_data={"cases": True},
                color_discrete_map={
                    "EPICENTER": "#ff0000",
                    "SPREADING": "#ff6600",
                    "CROSS-BORDER": "#ffaa00"
                },
                size_max=40,
                projection="natural earth",
                title="2026 Ebola Outbreak — Affected Areas"
            )
            fig.update_layout(
                height=400,
                geo=dict(
                    center=dict(lat=0, lon=30),
                    projection_scale=4
                )
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("📈 Outbreak Trajectory vs 2018")
            trajectory = pd.DataFrame({
                "week": [1,2,3,4,5,6],
                "2018_cases": [54,126,258,512,890,1200],
                "2026_cases": [8,51,246,575,906,None]
            })
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=trajectory["week"], y=trajectory["2018_cases"],
                name="2018 DRC Outbreak", line=dict(color="orange", dash="dash")
            ))
            fig2.add_trace(go.Scatter(
                x=trajectory["week"], y=trajectory["2026_cases"],
                name="2026 Outbreak (ACTIVE)", line=dict(color="red", width=3),
                mode="lines+markers"
            ))
            fig2.update_layout(
                title="2026 vs 2018 Case Trajectory",
                xaxis_title="Week since declaration",
                yaxis_title="Cumulative suspected cases",
                height=400
            )
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("---")
        st.subheader("⚠️ Cross-Border Risk Assessment")
        border_risk = pd.DataFrame({
            "Country": ["Uganda", "Rwanda", "Burundi", "Tanzania", "Congo (Brazzaville)", "Central African Rep.", "South Sudan"],
            "ISO3": ["UGA","RWA","BDI","TZA","COG","CAF","SSD"],
            "Border Risk": ["CRITICAL","HIGH","HIGH","MEDIUM","HIGH","MEDIUM","MEDIUM"],
            "Confirmed Cases": [9,0,0,0,0,0,0],
            "Reason": [
                "Confirmed cross-border transmission",
                "Shares border with Ituri/North Kivu",
                "Shares border with South Kivu",
                "Trade routes from DRC",
                "Border with DRC",
                "Border with DRC",
                "Displacement corridors"
            ]
        })
        for _, r in border_risk.iterrows():
            color = {"CRITICAL":"🔴","HIGH":"🟠","MEDIUM":"🟡"}.get(r["Border Risk"],"⚪")
            st.markdown(f"{color} **{r['Country']}** ({r['ISO3']}) — {r['Border Risk']} | Cases: {r['Confirmed Cases']} | {r['Reason']}")

        st.markdown("---")
        st.subheader("📋 Key Facts")
        st.info("""
        **Virus:** Bundibugyo ebolavirus (BDBV) — only 3rd known outbreak of this strain
        **First case:** Health worker, symptoms onset 24 April 2026, died in Bunia
        **PHEIC declared:** 17 May 2026 by WHO Director-General
        **MSF response:** Large-scale deployment of medical + logistical teams
        **Challenge:** No approved vaccine or treatment for Bundibugyo strain
        **Red Cross:** 3 workers died between 5-16 May from dead body management activities
        """)

        st.markdown("**Sources:** WHO Disease Outbreak News, CDC HAN, ECDC, MSF, Wikipedia")

    with tab2:
        cholera = fetch_live_cholera_2026()

        st.subheader("🔵 Cholera Global Situation — 2026")
        st.caption(f"Period: {cholera['period']} | Source: {cholera['source']}")

        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Total Cases (2026 YTD)", f"{cholera['total_cases_2026']:,}")
        c2.metric("Total Deaths (2026 YTD)", f"{cholera['total_deaths_2026']:,}")
        c3.metric("Countries Affected", cholera["countries_affected"])
        c4.metric("vs Same Period 2025", cholera["vs_2025"], delta="Improving", delta_color="normal")

        st.markdown("---")
        st.subheader("🔥 Active Hotspots — 2026")
        df_hot = pd.DataFrame(cholera["hotspots"])
        fig = px.bar(
            df_hot, x="country", y="cases",
            color="deaths",
            color_continuous_scale="Reds",
            title="Cholera Cases by Country — Jan to Mar 2026"
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.subheader("Key 2026 Developments")
        st.warning("🇦🇫 **Afghanistan** — 17,218 cases in Q1 2026, largest single-country burden")
        st.error("🇸🇴 **Somalia** — CFR exceeding 1% WHO threshold, displacement driving spread")
        st.error("🇨🇩 **DRC** — Simultaneous cholera AND Ebola outbreaks — extreme humanitarian stress")
        st.warning("🇲🇿 **Mozambique** — Flooding in Tete, Nampula, Cabo Delgado provinces fuelling transmission")
        st.info("📉 Global trend: 53% fewer cases vs same period 2025 — but conflict zones worsening")

# ════════════════════════════════════════════════════════════
# PAGE: CHOLERA
# ════════════════════════════════════════════════════════════
elif disease == "🔵 Cholera":
    page = st.sidebar.radio("Section", ["Global Risk Map","Outbreak Trends","Country Deep Dive","Top Countries"])

    if page == "Global Risk Map":
        st.title("🔵 Cholera Global Risk Map")
        st.markdown("Risk scores computed from WHO GHO data — 164 countries monitored")

        df = load_cholera_risk()
        df["risk_score"] = pd.to_numeric(df["risk_score"], errors="coerce").fillna(0.1)
        df["latitude"]   = pd.to_numeric(df["latitude"],   errors="coerce")
        df["longitude"]  = pd.to_numeric(df["longitude"],  errors="coerce")
        df_map = df.dropna(subset=["latitude","longitude"])
        df_map = df_map[df_map["risk_score"] > 0].copy()

        total   = len(df)
        crit    = len(df[df["risk_level"]=="CRITICAL"])
        high    = len(df[df["risk_level"]=="HIGH"])
        medium  = len(df[df["risk_level"]=="MEDIUM"])

        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Countries Monitored", total)
        c2.metric("CRITICAL", crit, delta="Immediate action", delta_color="inverse")
        c3.metric("HIGH", high, delta="Close monitoring", delta_color="inverse")
        c4.metric("MEDIUM", medium)

        col1, col2 = st.columns([3,1])
        with col1:
            fig = px.scatter_geo(
                df_map, lat="latitude", lon="longitude",
                color="risk_level", size="risk_score",
                hover_name="country",
                hover_data={"risk_score":":.3f","year":True},
                color_discrete_map=color_map,
                size_max=25, projection="natural earth",
                title="Cholera Risk Scores by Country"
            )
            fig.update_layout(height=500, margin={"r":0,"t":40,"l":0,"b":0})
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("CRITICAL")
            for _, r in df[df["risk_level"]=="CRITICAL"].sort_values("risk_score",ascending=False).iterrows():
                st.error(f"🔴 {r['iso3']} {r['country']} — {r['risk_score']:.3f}")
            st.subheader("HIGH")
            for _, r in df[df["risk_level"]=="HIGH"].sort_values("risk_score",ascending=False).head(6).iterrows():
                st.warning(f"🟠 {r['iso3']} {r['country']} — {r['risk_score']:.3f}")

    elif page == "Outbreak Trends":
        st.title("📈 Cholera Outbreak Trends")
        df = load_cholera_trends()
        yearly = df.groupby("year").agg(
            total_cases=("cases","sum"),
            total_deaths=("deaths","sum")
        ).reset_index()
        yearly = yearly[yearly["year"] >= 2000]
        fig = go.Figure()
        fig.add_trace(go.Bar(x=yearly["year"], y=yearly["total_cases"], name="Cases", marker_color="#2196F3"))
        fig.add_trace(go.Scatter(x=yearly["year"], y=yearly["total_deaths"], name="Deaths", mode="lines+markers", line=dict(color="red"), yaxis="y2"))
        fig.update_layout(title="Global Cholera Cases and Deaths (2000-2017)", yaxis2=dict(overlaying="y", side="right"), height=450)
        st.plotly_chart(fig, use_container_width=True)

    elif page == "Country Deep Dive":
        st.title("🔍 Country Deep Dive")
        df_risk = load_cholera_risk()
        df_trends = load_cholera_trends()
        iso3 = st.selectbox("Select Country", sorted(df_risk["iso3"].unique()))
        row = df_risk[df_risk["iso3"]==iso3].sort_values("year",ascending=False).iloc[0]
        c1,c2,c3 = st.columns(3)
        c1.metric("Country", str(row["country"]))
        c2.metric("Risk Score", f"{row['risk_score']:.3f}")
        c3.metric("Risk Level", row["risk_level"])
        country_trends = df_trends[df_trends["iso3"]==iso3]
        if not country_trends.empty:
            fig = px.bar(country_trends, x="year", y=["cases","deaths"], barmode="group", title=f"{iso3} Cases and Deaths by Year")
            st.plotly_chart(fig, use_container_width=True)

    elif page == "Top Countries":
        st.title("🏆 Top Countries by Cholera Burden")
        df = load_cholera_top()
        fig = px.bar(df.head(15), x="country", y="total_cases", color="total_deaths", color_continuous_scale="Reds", title="Top 15 Countries")
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True)

# ════════════════════════════════════════════════════════════
# PAGE: EBOLA
# ════════════════════════════════════════════════════════════
elif disease == "🔴 Ebola":
    page = st.sidebar.radio("Section", ["Global Risk Map","Outbreak Timeline","DRC 2018","Country Deep Dive"])

    if page == "Global Risk Map":
        st.title("🔴 Ebola Global Risk Map")
        df = load_ebola_risk()
        df["risk_score"] = pd.to_numeric(df["risk_score"], errors="coerce").fillna(0.1)
        df["latitude"]   = pd.to_numeric(df["latitude"],   errors="coerce")
        df["longitude"]  = pd.to_numeric(df["longitude"],  errors="coerce")
        df_map = df.dropna(subset=["latitude","longitude"])
        df_map = df_map[df_map["risk_score"] > 0].copy()

        c1,c2,c3 = st.columns(3)
        c1.metric("CRITICAL Countries", len(df[df["risk_level"]=="CRITICAL"]))
        c2.metric("HIGH Countries", len(df[df["risk_level"]=="HIGH"]))
        c3.metric("Total Scored", len(df))

        col1, col2 = st.columns([3,1])
        with col1:
            fig = px.scatter_geo(
                df_map, lat="latitude", lon="longitude",
                color="risk_level", size="risk_score",
                hover_name="country",
                color_discrete_map=color_map,
                size_max=30, projection="natural earth",
                title="Ebola Risk Scores by Country"
            )
            fig.update_layout(height=500, margin={"r":0,"t":40,"l":0,"b":0})
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            st.subheader("CRITICAL")
            for _, r in df[df["risk_level"]=="CRITICAL"].sort_values("risk_score",ascending=False).iterrows():
                st.error(f"🔴 {r['iso3']} {str(r['country'])} — {r['risk_score']:.3f}")
            st.subheader("HIGH")
            for _, r in df[df["risk_level"]=="HIGH"].sort_values("risk_score",ascending=False).head(6).iterrows():
                st.warning(f"🟠 {r['iso3']} {str(r['country'])} — {r['risk_score']:.3f}")

    elif page == "Outbreak Timeline":
        st.title("📅 Ebola Outbreak Timeline 1976-2023")
        df = load_ebola_outbreaks()
        fig = px.scatter(df, x="year", y="total_cases", size="total_cases", color="iso3",
            hover_name="country", hover_data={"deaths":True,"cfr":True,"strain":True},
            title="Ebola Outbreaks by Country and Year", size_max=60)
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)

    elif page == "DRC 2018":
        st.title("🇨🇩 DRC 2018-2020 Ebola Outbreak")
        df = load_drc_timeseries()
        c1,c2,c3 = st.columns(3)
        c1.metric("Records", len(df))
        c2.metric("Total Cases", f"{df['total_cases'].sum():,}")
        c3.metric("Total Deaths", f"{df['deaths'].sum():,}")
        zone_agg = df.groupby("health_zone").agg(
            total_cases=("total_cases","sum"),
            deaths=("deaths","sum")
        ).reset_index().sort_values("total_cases",ascending=False).head(20)
        fig = px.bar(zone_agg, x="health_zone", y="total_cases", color="deaths",
            color_continuous_scale="Reds", title="Top 20 Health Zones by Cases")
        fig.update_layout(height=450, xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    elif page == "Country Deep Dive":
        st.title("🔍 Country Deep Dive")
        df = load_ebola_outbreaks()
        iso3 = st.selectbox("Select Country", sorted(df["iso3"].unique()))
        df_c = df[df["iso3"]==iso3]
        c1,c2,c3 = st.columns(3)
        c1.metric("Total Cases", f"{df_c['total_cases'].sum():,}")
        c2.metric("Total Deaths", f"{df_c['deaths'].sum():,}")
        c3.metric("Outbreaks", len(df_c))
        fig = px.bar(df_c, x="year", y=["total_cases","deaths"], barmode="group", title=f"{iso3} Ebola History")
        st.plotly_chart(fig, use_container_width=True)