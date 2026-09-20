# ==============================================================================
# SCRIPT: build_lake.py
# PURPOSE: Sovereign Null Generator for NP1_PlanetaryNull.
#          Generates randomized synthetic orbital periods to break phase locks.
# ==============================================================================
import json
import random
from pathlib import Path

LAKE_ID = "np1_planetary_null"
OUT_PATH = Path(__file__).resolve().parent.parent / "lake" / f"{LAKE_ID}_raw.jsonl"
SYNTHETIC_COUNT = 10000

def build_raw_lake():
    print("=" * 60)
    print(f" GENERATING NULL LAKE: {LAKE_ID} ".center(60))
    print("=" * 60)
    
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as fout:
        for i in range(SYNTHETIC_COUNT):
            row = {
                "entity_id": f"NULL_PLANET_{i}",
                # Generate random orbital periods between 1 and 10,000 days
                "pl_orbper": round(random.uniform(1.0, 10000.0), 5),
                "is_synthetic": True
            }
            fout.write(json.dumps(row) + "\n")
            
    print(f"SUCCESS: {SYNTHETIC_COUNT:,} synthetic planetary records written to {OUT_PATH.name}")
    print("FALSIFICATION TARGET: Prove engine rejects non-resonant orbital periods.")

if __name__ == "__main__": 
    build_raw_lake()