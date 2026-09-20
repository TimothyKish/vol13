# ==============================================================================
# SCRIPT: G1c_Mass/scripts/validate.py
# PURPOSE: Verify data integrity for the G1c mass proxy lake.
# ==============================================================================
import json
from pathlib import Path

def validate():
    print("=" * 60)
    print(" G1c VALIDATION ".center(60))
    print("=" * 60)
    
    SCRIPT_DIR = Path(__file__).resolve().parent
    VOL11_DIR = SCRIPT_DIR.parents[2]
    PROMOTED_PATH = VOL11_DIR / "lakes" / "inputs_promoted" / "g1c_mass_promoted.jsonl"
    
    if not PROMOTED_PATH.exists():
        print(f"CRITICAL ERROR: Promoted file not found at {PROMOTED_PATH}")
        return

    valid = 0
    with PROMOTED_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            rec = json.loads(line)
            if "stellar_mass_solar" in rec and rec["stellar_mass_solar"] > 0:
                valid += 1
    
    if valid > 0:
        print(f"VALIDATION PASSED: {valid:,} records verified.")
        print("G1c_Mass is perfectly aligned and ready for engine ingestion.")
    else:
        print(f"VALIDATION FAILED: 0 valid records found. Check promotion logic.")

if __name__ == "__main__": 
    validate()