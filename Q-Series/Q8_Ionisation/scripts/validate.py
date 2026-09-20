# ==============================================================================
# SCRIPT: Q8_Ionisation/scripts/validate.py
# PURPOSE: Ensure the deep lake exceeds the minimum statistical power threshold.
# ==============================================================================
import json
from pathlib import Path

def validate():
    print("=" * 60)
    print(" Q8 IONISATION VALIDATION ".center(60))
    print("=" * 60)
    
    SCRIPT_DIR = Path(__file__).resolve().parent
    VOL11_DIR = SCRIPT_DIR.parents[2]
    PROMOTED_PATH = VOL11_DIR / "lakes" / "inputs_promoted" / "q8_ionisation_promoted.jsonl"
    
    if not PROMOTED_PATH.exists():
        print(f"CRITICAL ERROR: Promoted file not found at {PROMOTED_PATH}")
        return

    valid = 0
    with PROMOTED_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            rec = json.loads(line)
            if "ionisation_energy_ev" in rec and rec["ionisation_energy_ev"] > 0:
                if rec.get("domain") == "atomic_ionisation":
                    valid += 1
    
    if valid >= 300:
        print(f"VALIDATION PASSED: {valid} verified records.")
        print("Statistical power threshold exceeded. Q8 is fully deepened.")
    elif valid > 0:
        print(f"VALIDATION WARNING: Only {valid} records found. Expected > 300.")
    else:
        print(f"VALIDATION FAILED: 0 valid records found.")

if __name__ == "__main__": 
    validate()