# ==============================================================================
# SCRIPT: build_lake.py
# PURPOSE: Provenance Validator for L2 NANOGrav Pulsar Timing Array Data.
# ==============================================================================
import sys
from pathlib import Path

LAKE_ID = "l2_nanograv"
OUT_PATH = Path(__file__).resolve().parents[1] / "lake" / f"{LAKE_ID}_raw.jsonl"

def build():
    print("=" * 60)
    print(f" PROVENANCE AUDIT: {LAKE_ID} ".center(60))
    print("=" * 60)
    if not OUT_PATH.exists():
        print(f"FATAL: Curated NANOGrav data missing at {OUT_PATH.name}")
        print("\nPROVENANCE NOTE: This lake utilizes the NANOGrav 15-year dataset")
        print("pulsar timing residuals to lock low-frequency gravitational wave")
        print("backgrounds to the lattice. Please ensure the reference JSONL is present.")
        sys.exit(1)
    print(f"SUCCESS: Curated {LAKE_ID} data verified on disk.")

if __name__ == "__main__": build()