# ==============================================================================
# SCRIPT: fetch_nasa_extensions.py
# PURPOSE: Directly queries the NASA Exoplanet Archive TAP API to download
#          fresh multi-attribute data (Eccentricity, Inclination, Transit).
# ==============================================================================
import urllib.request
import urllib.parse
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_PATH = SCRIPT_DIR / "fresh_exoplanets_raw.jsonl"

def fetch_nasa_data():
    print("=" * 60)
    print(" FETCHING FRESH NASA EXOPLANET DATA ".center(60))
    print("=" * 60)
    
    # ADQL Query targeting the Composite Parameters table
    query = "SELECT pl_name, pl_orbper, pl_orbeccen, pl_orbincl, pl_trandur FROM pscomppars"
    url = f"https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query={urllib.parse.quote(query)}&format=json"
    
    print("Contacting NASA Exoplanet Archive TAP API...")
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        print(f"Successfully downloaded {len(data)} planetary records.")
        
        count = 0
        with OUT_PATH.open("w", encoding="utf-8") as f:
            for row in data:
                # Add a clean entity_id based on the planet name
                row['entity_id'] = row.get('pl_name', f'EXO_{count}')
                f.write(json.dumps(row) + "\n")
                count += 1
                
        print("-" * 60)
        print(f"SUCCESS: Wrote {count:,} records to {OUT_PATH.name}")
        print("Ready to distribute to Sovereign Lakes.")
        print("=" * 60)
        
    except Exception as e:
        print(f"ERROR downloading data: {e}")

if __name__ == "__main__":
    fetch_nasa_data()