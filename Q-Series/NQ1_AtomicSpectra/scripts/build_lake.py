# ==============================================================================
# SCRIPT: build_lake.py
# PURPOSE: Sovereign Null Generator for NQ1_AtomicSpectra.
#          Generates randomized synthetic spectral wavelengths to break phase locks.
# ==============================================================================
import json
import random
from pathlib import Path

LAKE_ID = "nq1_atomic_spectra"
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
                "entity_id": f"NULL_SPECTRUM_{i}",
                # Generate random wavelengths between 10.0 nm and 1000.0 nm
                "wavelength_nm": round(random.uniform(10.0, 1000.0), 4),
                "is_synthetic": True
            }
            fout.write(json.dumps(row) + "\n")
            
    print(f"SUCCESS: {SYNTHETIC_COUNT:,} synthetic records written to {OUT_PATH.name}")
    print("FALSIFICATION TARGET: Prove engine rejects non-resonant wavelengths.")

if __name__ == "__main__": 
    build_raw_lake()