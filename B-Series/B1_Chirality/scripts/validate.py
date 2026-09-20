# ==============================================================================
# SCRIPT: B1_Chirality/scripts/validate.py
# PURPOSE: Ensure the chiral lake exceeds the minimum statistical threshold.
# ==============================================================================
import json
from pathlib import Path

def validate():
    print("=" * 60)
    print(" B1 CHIRALITY VALIDATION ".center(60))
    print("=" * 60)
    
    SCRIPT_DIR = Path(__file__).resolve().parent
    VOL11_DIR = SCRIPT_DIR.parents[2]
    PROMOTED_PATH = VOL11_DIR / "lakes" / "inputs_promoted" / "b1_chirality_promoted.jsonl"
    
    if not PROMOTED_PATH.exists():
        print(f"CRITICAL ERROR: Promoted file not found at {PROMOTED_PATH}")
        return

    valid = 0
    with PROMOTED_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            rec = json.loads(line)
            if "specific_rotation_deg" in rec and rec["specific_rotation_deg"] >= 0:
                if rec.get("domain") == "biology_chirality":
                    valid += 1
    
    if valid >= 60:
        print(f"VALIDATION PASSED: {valid} verified records.")
        print("Statistical power threshold exceeded. B1 Chirality is fully deepened.")
    elif valid > 0:
        print(f"VALIDATION WARNING: Only {valid} records found. Expected >= 60.")
    else:
        print(f"VALIDATION FAILED: 0 valid records found.")

if __name__ == "__main__": 
    validate()