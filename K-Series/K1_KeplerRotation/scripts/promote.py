# ==============================================================================
# SCRIPT: promote.py
# PURPOSE: Maps raw K1 Kepler Rotation data to the KishLattice schema.
# ==============================================================================
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

DOMAIN = "stellar_rotation"
LAKE_ID = "k1_kepler_rotation"
TARGET_FIELD = "Prot_days"

SCRIPT_DIR = Path(__file__).resolve().parent
RAW_PATH = SCRIPT_DIR.parent / "lake" / f"{LAKE_ID}_raw.jsonl"
PROMOTED_DIR = SCRIPT_DIR.parents[3] / "lakes" / "inputs_promoted"
PROMOTED_PATH = PROMOTED_DIR / f"{LAKE_ID}_promoted.jsonl"

def promote():
    print("=" * 60)
    print(f" PROMOTING: {LAKE_ID} ".center(60))
    print("=" * 60)
    
    if not RAW_PATH.exists():
        print(f"FATAL: Raw lake not found at {RAW_PATH}")
        return
        
    count = 0
    now_ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    
    PROMOTED_DIR.mkdir(parents=True, exist_ok=True)
    with RAW_PATH.open("r", encoding="utf-8") as fin, PROMOTED_PATH.open("w", encoding="utf-8") as fout:
        for line in fin:
            if not line.strip(): continue
            raw_rec = json.loads(line)
            
            raw_val = raw_rec.get("Prot")
            if raw_val:
                try:
                    clean_val = float(str(raw_val).strip())
                    if clean_val <= 0: continue
                    
                    promoted_rec = {
                        "entity_id": raw_rec.get("entity_id", str(uuid.uuid4())),
                        "domain": DOMAIN,
                        "volume": 11,
                        "lake_id": LAKE_ID,
                        TARGET_FIELD: clean_val, 
                        "geometry_payload": {"coordinates": [], "dimensionality": 1, "geometry_type": "scalar"},
                        "meta": {"source": "VizieR J/ApJS/211/24/table1 (McQuillan 2014)", "ingest_timestamp": now_ts, "sovereign": True},
                        "_raw_payload": raw_rec
                    }
                    fout.write(json.dumps(promoted_rec) + "\n")
                    count += 1
                except ValueError:
                    continue
                    
    print(f"SUCCESS: {count:,} records promoted to {PROMOTED_PATH.name}")

if __name__ == "__main__":
    promote()