# ==============================================================================
# SCRIPT: build_lake.py
# PURPOSE: Provenance Validator for M_Wrongbox (Orthogonal Null Falsification).
# ==============================================================================
import sys
from pathlib import Path

LAKE_ID = "mat_wrongbox"
OUT_PATH = Path(__file__).resolve().parents[1] / "lake" / f"{LAKE_ID}_raw.jsonl"

def build():
    print("=" * 60)
    print(f" PROVENANCE AUDIT: {LAKE_ID} ".center(60))
    print("=" * 60)
    
    if not OUT_PATH.exists():
        print(f"FATAL: Wrongbox raw data missing at {OUT_PATH.name}")
        print("\nPROVENANCE NOTE: This Orthogonal Null lake utilizes the exact")
        print("same raw bulk modulus data as the Master Materials lake. It exists")
        print("as a sovereign file to force the engine to apply a 1D linear")
        print("scalarization to a 3D volumetric property, proving intentional")
        print("phase destruction. Please ensure the raw file is present.")
        sys.exit(1)
        
    print(f"SUCCESS: Sovereign {LAKE_ID} data verified on disk.")
    print("FALSIFICATION TARGET: Induce noise floor via dimensional mismatch.")

if __name__ == "__main__":
    build()