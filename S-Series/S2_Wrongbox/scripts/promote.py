# ==============================================================================
# SCRIPT: promote.py (S2 Kinematic Wrongbox)
# PURPOSE: Applies the WRONG dimensionality to the S2 Stellar Kinematics lake.
# ==============================================================================
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

DOMAIN = "kinematic_wrongbox"
LAKE_ID = "s2_wrongbox"
TARGET_FIELD = "v_perp"

SCRIPT_DIR = Path(__file__).resolve().parent
RAW_PATH = SCRIPT_DIR.parent / "lake" / "s2_wrongbox_raw.jsonl"
PROMOTED_DIR = SCRIPT_DIR.parents[2] / "lakes" / "inputs_promoted"
PROMOTED_PATH = PROMOTED_DIR / f"{LAKE_ID}_promoted.jsonl"

def promote():
    print("=" * 60)
    print(f" {LAKE_ID.upper()} PROMOTION SCRIPT ".center(60))
    print("=" * 60)
    
    if not RAW_PATH.exists():
        print(f"ERROR: Raw lake not found at {RAW_PATH}")
        return
        
    count = 0
    now_ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    
    with RAW_PATH.open("r", encoding="utf-8") as fin, PROMOTED_PATH.open("w", encoding="utf-8") as fout:
        for line in fin:
            if not line.strip(): continue
            raw_rec = json.loads(line)
            
            data_source = raw_rec.get("_raw_payload", raw_rec)
            if "payload" in raw_rec: data_source = raw_rec["payload"]
            
            # Extract from the actual field name "val"
            raw_val = data_source.get("val")
            
            if raw_val is not None and str(raw_val).strip() != "":
                try:
                    clean_val = float(raw_val)
                    if clean_val <= 0: continue
                    
                    promoted_rec = {
                        "entity_id": str(raw_rec.get("entity_id", uuid.uuid4())),
                        "domain": DOMAIN,
                        "volume": 11,
                        "lake_id": LAKE_ID,
                        TARGET_FIELD: clean_val,  # Mapped so the engine finds it
                        "geometry_payload": {"coordinates": [], "dimensionality": 1, "geometry_type": "scalar"},
                        "meta": {"source": "Gaia S2 (FALSIFICATION RUN)", "ingest_timestamp": now_ts, "sovereign": True},
                        "_raw_payload": data_source
                    }
                    fout.write(json.dumps(promoted_rec, ensure_ascii=False) + "\n")
                    count += 1
                except ValueError:
                    pass
                    
    print(f"SUCCESS: {count:,} records promoted to {PROMOTED_PATH.name}")

if __name__ == "__main__":
    promote()