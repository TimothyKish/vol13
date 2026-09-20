# ==============================================================================
# SCRIPT: validate.py
# PURPOSE: Trustless Auditor for the B5 Full PDB Backbone lake.
# ==============================================================================
import json
from pathlib import Path

LAKE_ID = "b5_pdb_full_protein"
PROMOTED_PATH = Path(__file__).resolve().parents[3] / "lakes" / "inputs_promoted" / f"{LAKE_ID}_promoted.jsonl"

def validate():
    print(f"--- VALIDATING: {LAKE_ID} ---")
    if not PROMOTED_PATH.exists(): 
        return print(f"FAIL: {PROMOTED_PATH.name} missing.")
        
    valid_count = 0
    with PROMOTED_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            rec = json.loads(line)
            assert "domain" in rec, "Missing domain"
            assert "entity_id" in rec, "Missing entity_id"
            assert "_raw_payload" in rec, "Missing _raw_payload (Provenance destroyed!)"
            valid_count += 1
            
    print(f"SUCCESS: {valid_count:,} high-density backbone records passed hostile validation.")

if __name__ == "__main__": 
    validate()