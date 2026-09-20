# ==============================================================================
# SCRIPT: fetch_atnf_extensions.py
# PURPOSE: Directly queries the VizieR TAP API to download fresh multi-attribute 
#          ATNF pulsar data, bypassing local Windows SSL certificate errors.
# ==============================================================================
import urllib.request
import json
import ssl
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_PATH = SCRIPT_DIR / "fresh_atnf_raw.jsonl"

def fetch_atnf_data():
    print("=" * 60)
    print(" FETCHING FRESH ATNF PULSAR DATA (VIZIER B/psr/psr) ".center(60))
    print("=" * 60)
    
    # VizieR simple TSV API - extremely robust for astronomical catalogs
    url = "https://vizier.u-strasbg.fr/viz-bin/asu-tsv?-source=B/psr/psr&-out=PSRJ,P0,P1,DM,Age,Bsurf&-out.max=unlimited"
    
    print("Contacting VizieR API...")
    
    # FIX: Create an unverified SSL context to bypass the CERTIFICATE_VERIFY_FAILED error
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(url)
    try:
        # Pass the unverified context into the urlopen request
        with urllib.request.urlopen(req, context=ctx) as response:
            lines = response.read().decode('utf-8').split('\n')
            
        records, headers = [], []
        
        for line in lines:
            if line.startswith('---') or line.startswith('#') or not line.strip(): 
                continue
            
            parts = line.split('\t')
            if not headers:
                headers = [p.strip() for p in parts]
                continue
                
            if len(parts) == len(headers):
                rec = dict(zip(headers, [p.strip() for p in parts]))
                records.append(rec)
                
        count = 0
        with OUT_PATH.open("w", encoding="utf-8") as f:
            for row in records:
                row['entity_id'] = row.get('PSRJ', f'PSR_{count}')
                f.write(json.dumps(row) + "\n")
                count += 1
                
        print("-" * 60)
        print(f"SUCCESS: Wrote {count:,} records to {OUT_PATH.name}")
        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    fetch_atnf_data()