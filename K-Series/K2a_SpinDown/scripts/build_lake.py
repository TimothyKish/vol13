# ==============================================================================
# SCRIPT: build_lake.py
# PURPOSE: Sovereign builder for k2a_spindown.
#          Directly queries VizieR (ATNF) and filters for valid P1 fields.
# ==============================================================================
import urllib.request
import json
import ssl
from pathlib import Path

LAKE_ID = "k2a_spindown"
TARGET_FIELD = "P1"
SOURCE_URL = "https://vizier.u-strasbg.fr/viz-bin/asu-tsv?-source=B/psr/psr&-out=PSRJ,P0,P1,DM,Age,Bsurf&-out.max=unlimited"

OUT_PATH = Path(__file__).resolve().parent.parent / "lake" / f"{LAKE_ID}_raw.jsonl"

def build_raw_lake():
    print("=" * 60)
    print(f" SOVEREIGN BUILD: {LAKE_ID} ".center(60))
    print("=" * 60)
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    print(f"Contacting VizieR API for ATNF Pulsar Catalog...")
    try:
        req = urllib.request.Request(SOURCE_URL)
        with urllib.request.urlopen(req, context=ctx) as response:
            lines = response.read().decode('utf-8').splitlines()
            
        headers = []
        count = 0
        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with OUT_PATH.open("w", encoding="utf-8") as fout:
            for line in lines:
                if line.startswith(('#', '---')) or not line.strip(): continue
                parts = [p.strip() for p in line.split('\t')]
                if not headers:
                    headers = parts
                    continue
                if len(parts) == len(headers):
                    row = dict(zip(headers, parts))
                    val = row.get(TARGET_FIELD)
                    if val and str(val).strip() not in ("", "*"):
                        row['entity_id'] = row.get('PSRJ', f"{LAKE_ID}_{count}")
                        fout.write(json.dumps(row) + "\n")
                        count += 1
        print(f"SUCCESS: {count:,} records written to {OUT_PATH.name}")
    except Exception as e:
        print(f"FATAL: Build failed for {LAKE_ID}: {e}")

if __name__ == "__main__":
    build_raw_lake()