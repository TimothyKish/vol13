# ==============================================================================
# SCRIPT: validate.py (B5 PDB Protein Tactical Strike)
# PURPOSE: Validates the structural integrity and schema compliance of the 
#          promoted B5 lake prior to global engine execution.
# ==============================================================================
import json
import statistics
from pathlib import Path

# Paths relative to B-Series/B5_PDB/scripts/validate.py
SCRIPT_DIR = Path(__file__).resolve().parent
# FIX: Use .parents[2] to target Unification/vol11/lakes/inputs_promoted/
PROMOTED_PATH = SCRIPT_DIR.parents[2] / "lakes" / "inputs_promoted" / "b5_pdb_protein_promoted.jsonl"

def validate():
    print("=" * 60)
    print(" B5 PDB PROMOTED LAKE VALIDATION ".center(60))
    print("=" * 60)

    if not PROMOTED_PATH.exists():
        print(f"ERROR: Promoted lake not found at {PROMOTED_PATH.resolve()}")
        print("Run promote.py first!")
        return

    count = 0
    angles = []
    errors = 0
    
    # Base schema keys expected pre-global-scalarization
    required_keys = {"entity_id", "domain", "volume", "lake_id", "angle_degrees", "meta"}

    print("Scanning promoted payload...")

    with PROMOTED_PATH.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line: continue
            
            try:
                rec = json.loads(line)
                count += 1
                
                # Check for missing required keys
                missing = required_keys - set(rec.keys())
                if missing:
                    print(f"[!] Row {line_no} missing keys: {missing}")
                    errors += 1
                    if errors > 10:
                        print("Too many errors. Aborting scan.")
                        return
                
                # Collect attributes for statistical sanity check
                if "angle_degrees" in rec and rec["angle_degrees"] is not None:
                    angles.append(rec["angle_degrees"])

            except json.JSONDecodeError:
                print(f"[!] Row {line_no} is invalid JSON.")
                errors += 1

    print("-" * 60)
    if errors == 0:
        print(f"SUCCESS: {count:,} records validated flawlessly.")
        if count > 0:
            print(f"  Domain Target : {rec.get('domain')}")
            print(f"  Lake ID       : {rec.get('lake_id')}")
            if angles:
                print(f"  Angle Stats   : Min={min(angles):.2f}°, Max={max(angles):.2f}°, Mean={statistics.mean(angles):.2f}°")
        print("\nAll systems green. Proceed to engine/run_pipeline.py!")
    else:
        print(f"FAILED: {errors} structural errors detected. Do not run pipeline.")
    print("=" * 60)

if __name__ == "__main__":
    validate()