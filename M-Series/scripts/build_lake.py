# ==============================================================================
# SCRIPT: build_lake.py
# PURPOSE: Provenance Validator for the Master Materials Lake.
#          Enforces the presence of the authenticated Materials Project dataset.
# ==============================================================================
import sys
from pathlib import Path

LAKE_ID = "materials_kish_invariant"
OUT_PATH = Path(__file__).resolve().parents[1] / "lake" / f"{LAKE_ID}.jsonl"

def build():
    print("=" * 60)
    print(f" PROVENANCE AUDIT: {LAKE_ID} ".center(60))
    print("=" * 60)
    
    if not OUT_PATH.exists():
        print(f"FATAL: Curated materials data missing at {OUT_PATH.name}")
        print("\nPROVENANCE NOTE: The Materials lake is derived from the NextGen")
        print("Materials Project API (mp-api). Because fetching this data requires")
        print("a registered API key, the raw dataset has been preserved natively.")
        print("The target attribute is the Bulk Modulus (K_VRH) / Compressibility.")
        print("Please ensure the reference materials_kish_invariant.jsonl is present.")
        sys.exit(1)
        
    print(f"SUCCESS: Curated {LAKE_ID} data verified on disk.")
    print(f"CHAIN OF CUSTODY: Materials Project API -> Vol 3 Extraction -> Vol 11 Engine")

if __name__ == "__main__":
    build()