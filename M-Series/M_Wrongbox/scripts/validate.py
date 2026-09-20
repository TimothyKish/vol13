# ==============================================================================
# SCRIPT: validate.py
# PURPOSE: Trustless Auditor for the M_Wrongbox promoted JSONL.
# ==============================================================================
import json
from pathlib import Path

LAKE_ID = "mat_wrongbox"
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
            assert rec.get("domain") == "materials_wrongbox", "Domain must explicitly declare wrongbox"
            assert "entity_id" in rec, "Missing entity_id"
            assert "geometry_payload" in rec, "Missing geometry_payload"
            valid_count += 1
            
    print(f"SUCCESS: {valid_count:,} records passed hostile structural validation.")

if __name__ == "__main__": 
    validate()