import json, uuid, time
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
RAW_PATH = SCRIPT_DIR.parent / "lake" / "h1d_raw.jsonl"
PROMOTED_PATH = SCRIPT_DIR.parents[2] / "lakes" / "inputs_promoted" / "h1d_eta_promoted.jsonl"

def promote():
    print("=" * 60 + "\n H1d ETA (PSEUDORAPIDITY) PROMOTION SCRIPT \n" + "=" * 60)
    count = 0
    now_ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    
    with RAW_PATH.open("r", encoding="utf-8") as fin, PROMOTED_PATH.open("w", encoding="utf-8") as fout:
        for line in fin:
            if not line.strip(): continue
            raw_rec = json.loads(line)
            raw_val = raw_rec.get("muon1_eta")
            if raw_val is not None:
                try:
                    # Pseudorapidity can be negative; we take absolute value for scalarization
                    clean_val = abs(float(raw_val))
                    promoted_rec = {
                        "entity_id": str(raw_rec.get("event", uuid.uuid4())),
                        "domain": "subnuclear_eta", "volume": 11, "lake_id": "h1d_eta",
                        "muon1_eta_abs": clean_val,
                        "geometry_payload": {"coordinates": [], "dimensionality": 1, "geometry_type": "scalar"},
                        "meta": {"source": "CERN CMS Open Data", "ingest_timestamp": now_ts, "sovereign": True},
                        "_raw_payload": raw_rec
                    }
                    fout.write(json.dumps(promoted_rec, ensure_ascii=False) + "\n")
                    count += 1
                except ValueError: pass
    print(f"SUCCESS: {count:,} records promoted to {PROMOTED_PATH.name}")

if __name__ == "__main__": promote()