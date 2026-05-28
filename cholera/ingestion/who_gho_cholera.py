import requests
import pandas as pd
import os

os.makedirs("cholera/ingestion/data", exist_ok=True)

# WHO Cholera data - alternative direct sources
sources = [
    {
        "name": "WHO_GHO_Cholera",
        "url": "https://ghoapi.azureedge.net/api/CHOLERA_0000000001",
        "type": "json"
    },
    {
        "name": "WHO_GHO_Cholera_Deaths", 
        "url": "https://ghoapi.azureedge.net/api/CHOLERA_0000000002",
        "type": "json"
    },
    {
        "name": "WHO_GHO_Cholera_CFR",
        "url": "https://ghoapi.azureedge.net/api/CHOLERA_0000000003",
        "type": "json"
    }
]

for source in sources:
    print(f"Fetching {source['name']}...")
    try:
        r = requests.get(source["url"], timeout=30)
        r.raise_for_status()
        data = r.json()
        
        records = data.get("value", [])
        df = pd.DataFrame(records)
        
        out = f"cholera/ingestion/data/{source['name']}.csv"
        df.to_csv(out, index=False)
        print(f"  Saved {len(df)} rows -> {out}")
        print(f"  Columns: {list(df.columns)}")
        print(df.head(3).to_string())
        print()
        
    except Exception as e:
        print(f"  Error: {e}")

print("WHO GHO ingestion complete!")
