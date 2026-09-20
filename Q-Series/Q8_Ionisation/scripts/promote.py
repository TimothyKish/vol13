# ==============================================================================
# SCRIPT: Q8_Ionisation/scripts/promote.py
# PURPOSE: Promote NIST Ionisation data into the Vol 11 Sovereign Schema.
# ==============================================================================
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone

def promote():
    print("=" * 60)
    print(" Q8 IONISATION PROMOTER ".center(60))
    print("=" * 60)
    
    SCRIPT_DIR = Path(__file__).resolve().parent
    RAW_PATH = SCRIPT_DIR.parent / "lake" / "q8_raw.jsonl"
    
    # Resolving up to vol11 root: scripts(0) -> Q8_Ionisation(1) -> Q-Series(2) -> vol11(3)
    VOL11_DIR = SCRIPT_DIR.parents[2]
    PROMOTED_PATH = VOL11_DIR / "lakes" / "inputs_promoted" / "q8_ionisation_promoted.jsonl"
    
    if not RAW_PATH.exists():
        print(f"CRITICAL ERROR: Raw data not found at {RAW_PATH}")
        return

    now_ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    count = 0
    
    with RAW_PATH.open("r", encoding="utf-8") as fin, PROMOTED_PATH.open("w", encoding="utf-8") as fout:
        for line in fin:
            if not line.strip(): continue
            rec = json.loads(line)
            
            # Entity ID: e.g., "Z_6_C_II"
            entity_id = f"Z_{rec['atomic_number']}_{rec['spectrum'].replace(' ', '_')}"
            
            promoted = {
                "entity_id": entity_id, 
                "domain": "atomic_ionisation", 
                "volume": 11,
                "lake_id": "q8_ionisation", 
                "ionisation_energy_ev": rec["ionisation_energy_ev"],
                "geometry_payload": {"coordinates": [], "dimensionality": 1, "geometry_type": "scalar"},
                "meta": {
                    "source": "NIST Atomic Spectra Database (ASD)", 
                    "ingest_timestamp": now_ts, 
                    "sovereign": True
                },
                "_raw_payload": rec
            }
            fout.write(json.dumps(promoted, ensure_ascii=False) + "\n")
            count += 1
                    
    print(f"SUCCESS: {count:,} records promoted to {PROMOTED_PATH.name}")

if __name__ == "__main__": 
    promote()