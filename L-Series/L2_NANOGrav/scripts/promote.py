import json, uuid
from datetime import datetime, timezone
from pathlib import Path

DOMAIN = "gravitational_wave"
LAKE_ID = "l2_nanograv"
TARGET_FIELD = "timing_residual_s" # Change if your Vol 10 key was different

SCRIPT_DIR = Path(__file__).resolve().parent
RAW_PATH = SCRIPT_DIR.parent / "lake" / f"{LAKE_ID}_raw.jsonl"
PROMOTED_DIR = SCRIPT_DIR.parents[3] / "lakes" / "inputs_promoted"
PROMOTED_PATH = PROMOTED_DIR / f"{LAKE_ID}_promoted.jsonl"

def promote():
    print(f"--- PROMOTING: {LAKE_ID} ---")
    if not RAW_PATH.exists(): return print(f"FATAL: {RAW_PATH} missing.")
    count, now = 0, datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    PROMOTED_DIR.mkdir(parents=True, exist_ok=True)
    with RAW_PATH.open("r", encoding="utf-8") as fin, PROMOTED_PATH.open("w", encoding="utf-8") as fout:
        for line in fin:
            if not line.strip(): continue
            rec = json.loads(line)
            if TARGET_FIELD in rec:
                promoted = {
                    "entity_id": rec.get("entity_id", str(uuid.uuid4())), "domain": DOMAIN, 
                    "volume": 11, "lake_id": LAKE_ID, TARGET_FIELD: float(rec[TARGET_FIELD]), 
                    "geometry_payload": {"coordinates": [], "dimensionality": 1, "geometry_type": "scalar"},
                    "meta": {"source": "NANOGrav 15-Year", "timestamp": now, "sovereign": True},
                    "_raw_payload": rec
                }
                fout.write(json.dumps(promoted) + "\n"); count += 1
    print(f"SUCCESS: {count:,} records promoted.")

if __name__ == "__main__": promote()