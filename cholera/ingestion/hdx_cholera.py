import requests
import pandas as pd
from datetime import datetime
import os, sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from dotenv import load_dotenv
load_dotenv()

HDX_API_KEY = os.getenv("HDX_API_KEY", "")
HDX_BASE_URL = "https://data.humdata.org/api/3"

# Real HDX dataset slugs we confirmed exist
TARGET_DATASETS = [
    "world-health-organization-who-cholera-data",
    "cholera-outbreaks-in-central-and-west-africa-2016-regional-update",
    "cholera-outbreaks-in-central-and-west-africa-2017-regional-update",
    "cholera-outbreaks-in-central-and-west-africa-2015-regional-update",
    "cholera-outbreaks-in-central-and-west-africa-2014-regional-update",
    "cholera-outbreaks-in-central-and-west-africa-2013-regional-update",
    "cholera-outbreaks-in-central-and-west-africa-2012-regional-update",
]

def fetch_cholera_datasets():
    print("Searching HDX for cholera datasets...")
    url = f"{HDX_BASE_URL}/action/package_search"
    params = {"q": "cholera Africa", "rows": 20, "sort": "metadata_modified desc"}
    headers = {"X-CKAN-API-Key": HDX_API_KEY} if HDX_API_KEY else {}
    response = requests.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    datasets = response.json()["result"]["results"]
    print(f"Found {len(datasets)} cholera datasets on HDX")
    return datasets

def download_dataset(dataset_slug):
    print(f"\nFetching: {dataset_slug}")
    url = f"{HDX_BASE_URL}/action/package_show"
    params = {"id": dataset_slug}
    headers = {"X-CKAN-API-Key": HDX_API_KEY} if HDX_API_KEY else {}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()["result"]
        resources = result.get("resources", [])
        title = result.get("title", dataset_slug)

        for res in resources:
            fmt = res.get("format", "").upper()
            dl_url = res.get("url", "")
            name = res.get("name", "unnamed")

            if fmt not in ["CSV", "XLSX", "XLS"] or not dl_url:
                continue

            print(f"  Downloading: {name} [{fmt}]")
            try:
                headers_dl = {}
                r = requests.get(dl_url, headers=headers_dl, timeout=60)
                r.raise_for_status()

                # Save raw file first
                safe_slug = dataset_slug[:40].replace("-", "_")
                raw_path = f"cholera/ingestion/data/raw_{safe_slug}.{fmt.lower()}"

                with open(raw_path, "wb") as f:
                    f.write(r.content)
                print(f"  Saved raw file: {raw_path}")

                # Parse to dataframe
                if fmt == "CSV":
                    df = pd.read_csv(raw_path, encoding="utf-8", errors="replace")
                else:
                    df = pd.read_excel(raw_path, engine="openpyxl")

                # Save as clean CSV
                csv_path = f"cholera/ingestion/data/{safe_slug}.csv"
                df.to_csv(csv_path, index=False)

                print(f"  Parsed {len(df)} rows, {len(df.columns)} columns")
                print(f"  Columns: {list(df.columns)}")
                print(f"  Saved CSV: {csv_path}")
                return df

            except Exception as e:
                print(f"  Download error: {e}")

    except Exception as e:
        print(f"  Dataset fetch error: {e}")

    return pd.DataFrame()

def run_cholera_ingestion():
    print("=" * 50)
    print("CHOLERA INGESTION PIPELINE STARTED")
    print("=" * 50)

    os.makedirs("cholera/ingestion/data", exist_ok=True)

    all_frames = []
    success_count = 0

    for slug in TARGET_DATASETS:
        df = download_dataset(slug)
        if not df.empty:
            df["source_dataset"] = slug
            df["ingested_at"] = datetime.utcnow().isoformat()
            all_frames.append(df)
            success_count += 1

    print("\n" + "=" * 50)
    print(f"INGESTION COMPLETE: {success_count}/{len(TARGET_DATASETS)} datasets downloaded")

    if all_frames:
        print("\nDataset summaries:")
        for i, df in enumerate(all_frames):
            print(f"  {i+1}. {df['source_dataset'].iloc[0]} -> {len(df)} rows")

    print("=" * 50)
    return all_frames

if __name__ == "__main__":
    run_cholera_ingestion()
