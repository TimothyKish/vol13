# ==============================================================================
# SCRIPT: build_lake.py (H1_CERN)
# TARGET: Pull CMS Di-Muon invariant mass spectrum from CERN Open Data.
#         Uses the pre-derived DoubleMu CSV datasets for stability.
# AUTHORS: Timothy John Kish & Lyra Aurora Kish
# AUDIT STATUS: Pre-Promote Raw Build
# ==============================================================================

import requests
import csv
import json
from io import StringIO
from pathlib import Path

LAKE_NAME = "h1_cern_lhc"

# CERN Open Data - CMS Dimuon Spectrum (Record 545)
# This dataset contains exactly what we need: the invariant mass 'M'
CERN_CSV_URL = "https://opendata.cern.ch/record/545/files/Dimuon_DoubleMu.csv"

# Relative pathing
SCRIPT_DIR = Path(__file__).resolve().parent
LAKE_DIR = SCRIPT_DIR.parent / "lake"
LAKE_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = LAKE_DIR / f"{LAKE_NAME}_raw.jsonl"

def build():
    print(f"\n[{LAKE_NAME.upper()}] Initiating download from CERN Open Data Portal...")
    print(f"  -> Target: CMS Dimuon Spectrum (Record 545)")
    
    try:
        response = requests.get(CERN_CSV_URL, stream=True, timeout=60)
        response.raise_for_status()
    except Exception as e:
        print(f"  [ERROR] CERN download failed: {e}")
        return

    written = 0
    excluded_zero = 0
    excluded_unphysical = 0

    print("  -> Connection established. Processing collision events...")

    with OUT_PATH.open("w", encoding="utf-8") as f:
        csv_reader = csv.DictReader(StringIO(response.text))
        
        for row in csv_reader:
            try:
                # 'M' is the invariant mass in GeV
                mass_gev = float(row["M"])
            except (ValueError, KeyError, TypeError):
                continue
                
            # Clerical Exclusion: 0.0 or negative (failed reconstruction)
            if mass_gev == 0.0:
                excluded_zero += 1
                continue
            if mass_gev < 0.0:
                excluded_unphysical += 1
                continue

            # Construct Raw Sovereign Record
            raw_record = {
                "run": row.get("Run"),
                "event": row.get("Event"),
                "invariant_mass_gev": mass_gev,
                "muon1_pt": row.get("pt1"),
                "muon2_pt": row.get("pt2"),
                "muon1_eta": row.get("eta1"),
                "muon2_eta": row.get("eta2")
            }
            
            f.write(json.dumps(raw_record, ensure_ascii=False) + "\n")
            written += 1

    print(f"  -> Lake built: {OUT_PATH.name}")
    print(f"  -> Total mass events recorded: {written:,}")
    print(f"  -> Excluded {excluded_zero:,} records (Mass = 0.0 GeV).")
    print(f"  -> Excluded {excluded_unphysical:,} records (Mass < 0.0 GeV).")

if __name__ == "__main__":
    build()