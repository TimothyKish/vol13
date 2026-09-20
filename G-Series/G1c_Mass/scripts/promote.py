# ==============================================================================
# SCRIPT: G1c_Mass/scripts/promote.py
# PURPOSE: Promote raw G1c data to promoted JSONL using Virial Mass Proxy.
# ==============================================================================
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone

def promote():
    print("=" * 60)
    print(" G1c STELLAR MASS PROMOTER (VIRIAL M ~ vdisp^4) ".center(60))
    print("=" * 60)
    
    # Path Resolution
    SCRIPT_DIR = Path(__file__).resolve().parent
    RAW_PATH = SCRIPT_DIR.parent / "lake" / "g1c_raw.jsonl"
    
    # Resolving up to vol11 root: scripts(1) -> G1c_Mass(2) -> G-Series(3) -> vol11(4)
    VOL11_DIR = SCRIPT_DIR.parents[2]
    PROMOTED_PATH = VOL11_DIR / "lakes" / "inputs_promoted" / "g1c_mass_promoted.jsonl"
    
    now_ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    count = 0
    
    if not RAW_PATH.exists():
        print(f"CRITICAL ERROR: Raw data not found at {RAW_PATH}")
        return

    # Ensure output directory exists
    PROMOTED_PATH.parent.mkdir(parents=True, exist_ok=True)

    with RAW_PATH.open("r", encoding="utf-8") as fin, PROMOTED_PATH.open("w", encoding="utf-8") as fout:
        for line in fin:
            if not line.strip(): continue
            rec = json.loads(line)
            
            # The raw file built from the fallback contains the _raw_payload from G1 directly
            vdisp = rec.get("vdisp")
            if vdisp is not None:
                try:
                    # Virial Mass Proxy Transformation
                    stellar_mass_proxy = float(vdisp) ** 4
                    
                    promoted = {
                        "entity_id": str(rec.get('objID', uuid.uuid4())), 
                        "domain": "galactic_mass", 
                        "volume": 11,
                        "lake_id": "g1c_mass", 
                        "stellar_mass_solar": stellar_mass_proxy,
                        "geometry_payload": {"coordinates": [], "dimensionality": 1, "geometry_type": "scalar"},
                        "meta": {
                            "source": "Local G1 Master (Virial Proxy)", 
                            "ingest_timestamp": now_ts, 
                            "sovereign": True
                        },
                        "_raw_payload": rec
                    }
                    fout.write(json.dumps(promoted, ensure_ascii=False) + "\n")
                    count += 1
                except (ValueError, TypeError):
                    pass
                    
    print(f"SUCCESS: {count:,} records promoted to {PROMOTED_PATH.name}")

if __name__ == "__main__": 
    promote()