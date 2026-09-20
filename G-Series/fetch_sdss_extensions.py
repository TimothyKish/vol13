# ==============================================================================
# SCRIPT: fetch_sdss_mass_data.py
# PURPOSE: Reliable mass data fetcher using SDSS SkyServer API.
# ==============================================================================
import urllib.request
import urllib.parse
import json
from pathlib import Path

def fetch_sdss_mass():
    print("=" * 60)
    print(" FETCHING SDSS MASS DATA ".center(60))
    print("=" * 60)
    
    # Selecting mass and objID specifically
    sql = "SELECT TOP 100000 p.objID, m.logMass FROM Galaxy p JOIN stellarMassFSPSAll m ON p.specObjID = m.specObjID WHERE m.logMass > 0"
    url = f"http://skyserver.sdss.org/dr16/SkyServerWS/SearchTools/SqlSearch?cmd={urllib.parse.quote(sql)}&format=json"
    
    print("Requesting SDSS Mass Data...")
    try:
        with urllib.request.urlopen(url, timeout=120) as response:
            raw_data = json.loads(response.read().decode('utf-8'))
            data = raw_data[0]['Rows']
            
        out_path = Path(__file__).parent / "sdss_mass_data.jsonl"
        with out_path.open("w", encoding="utf-8") as f:
            for row in data:
                # Keep it simple: objID is the join key
                f.write(json.dumps({"objID": row['objID'], "logMass": row['logMass']}) + "\n")
        
        print(f"SUCCESS: Saved {len(data)} mass records to {out_path.name}")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    fetch_sdss_mass()