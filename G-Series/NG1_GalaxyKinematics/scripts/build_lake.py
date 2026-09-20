# ==============================================================================
# SCRIPT: build_lake.py
# PURPOSE: Sovereign Null Generator for NG1_GalaxyKinematics.
#          Generates random synthetic velocity dispersions to break phase locks.
# ==============================================================================
import json
import random
from pathlib import Path

LAKE_ID = "ng1_galaxy_kinematics"
OUT_PATH = Path(__file__).resolve().parent.parent / "lake" / f"{LAKE_ID}_raw.jsonl"
SYNTHETIC_COUNT = 100000

def build_raw_lake():
    print(f"--- GENERATING NULL LAKE: {LAKE_ID} ---")
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as fout:
        for i in range(SYNTHETIC_COUNT):
            row = {
                "entity_id": f"NULL_GAL_{i}",
                # Random velocity dispersion between 10 and 400 km/s
                "velDisp": round(random.uniform(10.0, 400.0), 4),
                "is_synthetic": True
            }
            fout.write(json.dumps(row) + "\n")
    print(f"SUCCESS: {SYNTHETIC_COUNT:,} synthetic records written to {OUT_PATH.name}")

if __name__ == "__main__": build_raw_lake()