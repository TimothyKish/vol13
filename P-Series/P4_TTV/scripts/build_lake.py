# ==============================================================================
# SCRIPT: build_lake.py (P4_TTV)
# TARGET: Pull Kepler Transit Timing Variations (TTVs) from VizieR (CDS).
#         Bypasses broken NASA Exoplanet Archive to use the immutable
#         Holczer et al. (2016) catalog (J/ApJS/225/9/table3).
# AUTHORS: Timothy John Kish & Lyra Aurora Kish
# AUDIT STATUS: Pre-Promote Raw Build (Calibrated for O-C header)
# ==============================================================================

import requests
import json
from pathlib import Path

LAKE_NAME = "p4_ttv"

# VizieR (CDS) API - Immutable Astronomical Catalogs
# Catalog J/ApJS/225/9 : Kepler transit timing variations (Holczer+, 2016)
# Table 3: Epoch-by-epoch TTVs (295,187 rows)
VIZIER_URL = "https://vizier.cds.unistra.fr/viz-bin/asu-tsv"

# Relative pathing: resolves to P-Series/P4_TTV/lake/
SCRIPT_DIR = Path(__file__).resolve().parent
LAKE_DIR = SCRIPT_DIR.parent / "lake"
LAKE_DIR.mkdir(parents=True, exist_ok=True)

OUT_PATH = LAKE_DIR / f"{LAKE_NAME}_raw.jsonl"

def build():
    print(f"\n[{LAKE_NAME.upper()}] NASA API is offline. Redirecting to sovereign VizieR (CDS) archive...")
    print("  -> Target Catalog: J/ApJS/225/9/table3 (Holczer+, 2016 Epoch TTVs)")
    
    params = {
        "-source": "J/ApJS/225/9/table3",
        "-out.max": "unlimited",
    }

    try:
        response = requests.get(VIZIER_URL, params=params, stream=True, timeout=120)
        response.raise_for_status()
    except Exception as e:
        print(f"  [ERROR] VizieR request failed: {e}")
        return

    written = 0
    excluded_zero = 0
    excluded_missing = 0
    excluded_unphysical = 0

    print("  -> Connection established. Downloading and processing ~300,000 transits...")

    with OUT_PATH.open("w", encoding="utf-8") as f:
        lines = response.text.splitlines()
        
        data_start_idx = 0
        headers = []
        
        # Hunt for the dashes, then step exactly TWO lines up to grab the real headers
        # bypassing the unit row.
        for i, line in enumerate(lines):
            if line.startswith("---") or line.startswith("___"):
                data_start_idx = i + 1
                headers = [h.strip() for h in lines[i-2].split("\t")]
                break
                
        if not headers:
            print("  [ERROR] Could not locate header row in VizieR TSV.")
            return
            
        for line in lines[data_start_idx:]:
            if not line.strip() or line.startswith("#"):
                continue
                
            cols = [c.strip() for c in line.split("\t")]
            
            # VizieR sometimes drops trailing empty tabs. Pad the columns if necessary.
            if len(cols) < len(headers):
                cols.extend([""] * (len(headers) - len(cols)))
                
            row = dict(zip(headers, cols))
            
            # Extract TTV (Labeled 'O-C' for Observed minus Calculated)
            ttv_str = row.get("O-C", "")
            
            if not ttv_str:
                excluded_missing += 1
                continue
                
            try:
                ttv_minutes = float(ttv_str)
            except ValueError:
                excluded_missing += 1
                continue

            # Mondy's spec: take absolute magnitude
            ttv_absolute_minutes = abs(ttv_minutes)
            
            if ttv_absolute_minutes == 0.0:
                excluded_zero += 1
                continue
                
            # Exclude unphysical variations (> 24 hours / 1440 minutes)
            if ttv_absolute_minutes > 1440.0:
                excluded_unphysical += 1
                continue

            # Construct Raw Sovereign Record
            raw_record = {
                "planet_id": row.get("KOI", "unknown"),
                "transit_number": row.get("N", ""),
                "observation_time_jd": row.get("tn", ""),
                "ttv_absolute_minutes": ttv_absolute_minutes,
                "raw_ttv_minutes": ttv_minutes,
                "uncertainty_minutes": row.get("e_O-C", "")
            }
            
            f.write(json.dumps(raw_record, ensure_ascii=False) + "\n")
            written += 1

    print(f"  -> Lake built: {OUT_PATH.name}")
    print(f"  -> Total intervals recorded: {written:,}")
    print(f"  -> Excluded {excluded_zero:,} records (TTV = 0.0 placeholder).")
    print(f"  -> Excluded {excluded_unphysical:,} records (|TTV| > 1440 minutes).")
    print(f"  -> Excluded {excluded_missing:,} records (Missing data).")

if __name__ == "__main__":
    build()