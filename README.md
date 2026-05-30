# 🌍 Disaster Health Nexus
### Real-Time Epidemic Risk & Health Access Pipeline for Displaced Populations

[![Python](https://img.shields.io/badge/Python-3.10-blue)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue)](https://postgresql.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.31-red)](https://streamlit.io)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 🎯 Problem Statement

When disasters strike, displaced populations face deadly epidemics with zero access
to healthcare. Aid organizations respond **reactively** — by the time cholera or
Ebola is confirmed, it has already spread. This pipeline shifts the paradigm to
**proactive risk detection**, flagging high-risk zones before outbreak confirmation
so resources move faster and lives are saved.

---

## 🏗️ Architecture---

## 🦠 Disease Pipelines

### 🔵 Cholera Pipeline
- **Data:** WHO GHO (2,469 records), HDX Regional (6 datasets), 164 countries scored
- **Risk Engine:** Outbreak score + Mortality score + Facility access score
- **Critical Countries:** Somalia (0.860), Haiti (0.720)
- **API:** `http://localhost:8001/docs`
- **Dashboard:** `http://localhost:8501`

### 🔴 Ebola Pipeline
- **Data:** WHO Historical 1976-2023 (31 outbreaks), DRC 2018-2020 (591 records), West Africa 2014 (53 records)
- **Risk Engine:** Outbreak score + Mortality score + Containment score + Cross-border score
- **Critical Countries:** Liberia (0.785), Sierra Leone (0.748)
- **API:** `http://localhost:8002/docs`
- **Dashboard:** `http://localhost:8502`

---

## 📊 Data Sources

| Source | Data | Disease |
|--------|------|---------|
| [WHO GHO API](https://www.who.int/data/gho) | Cases, deaths, CFR | Cholera |
| [HDX](https://data.humdata.org) | Regional outbreak data | Both |
| [UNHCR](https://data.unhcr.org) | Displaced populations | Both |
| [OpenStreetMap](https://overpass-api.de) | Health facility locations | Both |
| [ReliefWeb](https://reliefweb.int) | Situation reports | Both |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Ingestion | Python, Requests, Pandas |
| Warehouse | PostgreSQL 16 + PostGIS |
| Orchestration | Apache Airflow 2.8 (DAGs) |
| Transform | NumPy, Pandas, Custom Risk Engine |
| API | FastAPI + SQLAlchemy |
| Dashboard | Streamlit + Plotly |
| Version Control | Git + GitHub |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- PostgreSQL 16
- Git

### Setup

```bash
# Clone
git clone https://github.com/mbuguakevvz/disaster-health-nexus.git
cd disaster-health-nexus

# Virtual environment
python -m venv venv
venv\Scripts\Activate.ps1  # Windows

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env with your PostgreSQL credentials and HDX API key

# Create databases
psql -U postgres -c "CREATE DATABASE cholera_db;"
psql -U postgres -c "CREATE DATABASE ebola_db;"

# Run schemas
python cholera\warehouse\create_schema.py
python ebola\warehouse\create_schema.py

# Ingest data
python cholera\ingestion\hdx_cholera.py
python cholera\ingestion\who_gho_cholera.py
python ebola\ingestion\hdx_ebola.py

# Load warehouse
python cholera\warehouse\loader.py
python ebola\warehouse\loader.py

# Run risk engines
python cholera\transforms\risk_engine.py
python ebola\transforms\risk_engine.py

# Export dashboard data
python shared\pipeline_runner.py
```

### Run Services

```bash
# Cholera API
uvicorn cholera.api.main:app --port 8001

# Ebola API
uvicorn ebola.api.main:app --port 8002

# Cholera Dashboard
streamlit run cholera\dashboard\app.py --server.port 8501

# Ebola Dashboard
streamlit run ebola\dashboard\app.py --server.port 8502
```

---

## 📁 Project Structure---

## 🌍 Humanitarian Impact

This pipeline enables:
- **Early warning** — detect risk zones 48hrs before outbreak confirmation
- **Resource targeting** — direct medical supplies to highest-risk areas
- **Gap analysis** — identify healthcare deserts in displaced populations
- **Cross-border monitoring** — track epidemic spread across borders

**Target users:** UN Agencies (UNHCR, WHO, UNICEF), NGOs (MSF, IRC),
Government Health Ministries, Humanitarian Data Analysts

---

## 👨‍💻 Author

**Kevin Mbugua**
- GitHub: [@mbuguakevvz](https://github.com/mbuguakevvz)
- Project: Disaster Health Nexus

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.