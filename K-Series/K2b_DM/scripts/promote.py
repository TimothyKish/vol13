import json, uuid, time
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
RAW_PATH = SCRIPT_DIR.parent / "lake" / "k2b_raw.jsonl"
PROMOTED_PATH = SCRIPT_DIR.parents[2] / "lakes" / "inputs_promoted" / "k2b_dm_promoted.jsonl"

def promote():
    print("=" * 60 + "\n K2B DM PROMOTION SCRIPT \n" + "=" * 60)
    count = 0
    now_ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    
    with RAW_PATH.open("r", encoding="utf-8") as fin, PROMOTED_PATH.open("w", encoding="utf-8") as fout:
        for line in fin:
            if not line.strip(): continue
            raw_rec = json.loads(line)
            raw_val = raw_rec.get("DM")
            if raw_val:
                try:
                    clean_val = float(raw_val)
                    if clean_val <= 0: continue
                    promoted_rec = {
                        "entity_id": str(raw_rec.get("PSRJ", uuid.uuid4())),
                        "domain": "stellar_dm", "volume": 11, "lake_id": "k2b_dm",
                        "dispersion_measure": clean_val,
                        "geometry_payload": {"coordinates": [], "dimensionality": 1, "geometry_type": "scalar"},
                        "meta": {"source": "ATNF (VizieR B/psr/psr)", "ingest_timestamp": now_ts, "sovereign": True},
                        "_raw_payload": raw_rec
                    }
                    fout.write(json.dumps(promoted_rec, ensure_ascii=False) + "\n")
                    count += 1
                except ValueError: pass
    print(f"SUCCESS: {count:,} records promoted to {PROMOTED_PATH.name}")

if __name__ == "__main__": promote()