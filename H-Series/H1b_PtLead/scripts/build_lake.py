# ==============================================================================
# SCRIPT: build_lake.py
# PURPOSE: Sovereign builder for h1b_pt_lead.
#          Fetches the CMS Di-Muon dataset directly from CERN Open Data.
# ==============================================================================
import urllib.request
import json
import ssl
from pathlib import Path

LAKE_ID = "h1b_pt_lead"
TARGET_FIELD = "pt1"
CERN_URL = "http://opendata.cern.ch/record/545/files/Dimuon_DoubleMu.csv"

OUT_PATH = Path(__file__).resolve().parent.parent / "lake" / f"{LAKE_ID}_raw.jsonl"

def build_raw_lake():
    print("=" * 60)
    print(f" SOVEREIGN BUILD: {LAKE_ID} ".center(60))
    print("=" * 60)
    ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    try:
        print("Contacting CERN Open Data Portal (CMS 2010 Di-Muon)...")
        req = urllib.request.Request(CERN_URL)
        with urllib.request.urlopen(req, context=ctx) as response:
            lines = response.read().decode('utf-8').splitlines()
        
        headers = []
        count = 0
        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with OUT_PATH.open("w", encoding="utf-8") as fout:
            for line in lines:
                if not line.strip(): continue
                parts = [p.strip() for p in line.split(',')]
                if not headers:
                    headers = parts
                    continue
                if len(parts) == len(headers):
                    row = dict(zip(headers, parts))
                    if row.get(TARGET_FIELD):
                        row['entity_id'] = f"CMS_Event_{row.get('Run', count)}_{row.get('Event', count)}"
                        fout.write(json.dumps(row) + "\n")
                        count += 1
        print(f"SUCCESS: {count:,} records written to {OUT_PATH.name}")
    except Exception as e:
        print(f"FATAL: Build failed for {LAKE_ID}: {e}")

if __name__ == "__main__": build_raw_lake()