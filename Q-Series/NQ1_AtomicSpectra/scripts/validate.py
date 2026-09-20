import json
from pathlib import Path

LAKE_ID = "nq1_atomic_spectra"
PROMOTED_PATH = Path(__file__).resolve().parents[3] / "lakes" / "inputs_promoted" / f"{LAKE_ID}_promoted.jsonl"

def validate():
    print(f"--- VALIDATING: {LAKE_ID} ---")
    if not PROMOTED_PATH.exists(): return print("FAIL: missing.")
    valid_count = sum(1 for line in PROMOTED_PATH.open("r", encoding="utf-8") if line.strip() and all(k in json.loads(line) for k in ["domain", "entity_id", "_raw_payload"]))
    print(f"SUCCESS: {valid_count:,} synthetic spectral transitions passed validation.")

if __name__ == "__main__": 
    validate()