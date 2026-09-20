# ==============================================================================
# SCRIPT: build_lake.py
# PURPOSE: Sovereign builder for g1b_sersic.
#          Queries the SDSS SkyServer API for De Vaucouleurs/Sersic profiles.
# ==============================================================================
import urllib.request
import urllib.parse
import json
import ssl
from pathlib import Path

LAKE_ID = "g1b_sersic"
# Using fracDeV_r as the SDSS proxy for Sersic profile dominance
SDSS_SQL = "SELECT TOP 100000 objID, fracDeV_r FROM Galaxy WITH(NOLOCK) WHERE clean=1 AND fracDeV_r > 0"
SDSS_API_URL = f"http://skyserver.sdss.org/dr17/SkyServerWS/SearchTools/SqlSearch?cmd={urllib.parse.quote(SDSS_SQL)}&format=csv"

OUT_PATH = Path(__file__).resolve().parent.parent / "lake" / f"{LAKE_ID}_raw.jsonl"

def build_raw_lake():
    print(f"--- SOVEREIGN BUILD: {LAKE_ID} ---")
    ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(urllib.request.Request(SDSS_API_URL), context=ctx) as response:
            lines = response.read().decode('utf-8').splitlines()
        headers, count = [], 0
        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with OUT_PATH.open("w", encoding="utf-8") as fout:
            for line in lines:
                if line.startswith('#') or not line.strip(): continue
                parts = [p.strip() for p in line.split(',')]
                if not headers: headers = parts; continue
                if len(parts) == len(headers):
                    row = dict(zip(headers, parts))
                    row['entity_id'] = f"SDSS_{row.get('objID', count)}"
                    fout.write(json.dumps(row) + "\n")
                    count += 1
        print(f"SUCCESS: {count:,} records written to {OUT_PATH.name}")
    except Exception as e: print(f"FATAL: Build failed for {LAKE_ID}: {e}")

if __name__ == "__main__": build_raw_lake()