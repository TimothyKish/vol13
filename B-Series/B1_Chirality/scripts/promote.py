# ==============================================================================
# SCRIPT: B1_Chirality/scripts/promote.py
# PURPOSE: Promote Chiral records to Sovereign Schema (Magnitude Absolute).
# ==============================================================================
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone

def promote():
    print("=" * 60)
    print(" B1 CHIRALITY PROMOTER ".center(60))
    print("=" * 60)
    
    SCRIPT_DIR = Path(__file__).resolve().parent
    RAW_PATH = SCRIPT_DIR.parent / "lake" / "b1_raw.jsonl"
    VOL11_DIR = SCRIPT_DIR.parents[2]
    PROMOTED_PATH = VOL11_DIR / "lakes" / "inputs_promoted" / "b1_chirality_promoted.jsonl"
    
    if not RAW_PATH.exists():
        print(f"CRITICAL ERROR: Raw data not found at {RAW_PATH}")
        return

    now_ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    count = 0
    
    with RAW_PATH.open("r", encoding="utf-8") as fin, PROMOTED_PATH.open("w", encoding="utf-8") as fout:
        for line in fin:
            if not line.strip(): continue
            rec = json.loads(line)
            
            # The engine evaluates the absolute magnitude of the topological twist
            raw_rotation = rec["specific_rotation_deg"]
            abs_rotation = abs(raw_rotation)
            
            # Entity ID: e.g., "MOL_L-Alanine"
            entity_id = f"MOL_{rec['molecule_name'].replace(' ', '_').replace('(', '').replace(')', '')}"
            
            promoted = {
                "entity_id": entity_id, 
                "domain": "biology_chirality", 
                "volume": 11,
                "lake_id": "b1_chirality", 
                "specific_rotation_deg": abs_rotation,
                "geometry_payload": {"coordinates": [], "dimensionality": 1, "geometry_type": "scalar"},
                "meta": {
                    "source": rec["source"],
                    "original_rotation": raw_rotation, # Preserve original sign for audit
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