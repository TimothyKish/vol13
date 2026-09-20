# ==============================================================================
# SCRIPT: G1c_Mass/scripts/build_lake.py
# PURPOSE: Build the local raw JSONL lake for Galactic Mass data.
# METHOD: Local Extraction (Bypassing SDSS API 403 Forbidden Ban)
# ==============================================================================
import json
from pathlib import Path

def build_lake():
    print("=" * 60)
    print(" G1c BUILDING RAW LAKE (LOCAL VIRIAL FALLBACK) ".center(60))
    print("=" * 60)
    
    SCRIPT_DIR = Path(__file__).resolve().parent
    RAW_PATH = SCRIPT_DIR.parent / "lake" / "g1c_raw.jsonl"
    
    # Read from the existing g1 promoted file to extract the raw SDSS payload
    SOURCE_PATH = SCRIPT_DIR.parents[2] / "lakes" / "inputs_promoted" / "g1_galaxy_kinematics_promoted.jsonl"
    
    if not SOURCE_PATH.exists():
        print(f"CRITICAL ERROR: Source not found at {SOURCE_PATH}")
        return

    count = 0
    with SOURCE_PATH.open("r", encoding="utf-8") as fin, RAW_PATH.open("w", encoding="utf-8") as fout:
        for line in fin:
            if not line.strip(): continue
            rec = json.loads(line)
            
            raw_payload = rec.get("_raw_payload")
            # Ensure we only pull records that have the vdisp (velocity dispersion) field
            if raw_payload and "vdisp" in raw_payload:
                fout.write(json.dumps(raw_payload) + "\n")
                count += 1
                
    print(f"SUCCESS: Raw lake built locally at {RAW_PATH.name} with {count:,} records.")

if __name__ == "__main__": 
    build_lake()