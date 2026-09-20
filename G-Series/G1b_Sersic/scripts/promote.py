import json, uuid, time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
RAW_PATH = SCRIPT_DIR.parent / "lake" / "g1b_raw.jsonl"
PROMOTED_PATH = SCRIPT_DIR.parents[2] / "lakes" / "inputs_promoted" / "g1b_sersic_promoted.jsonl"

def promote():
    count = 0
    with RAW_PATH.open("r") as fin, PROMOTED_PATH.open("w") as fout:
        for line in fin:
            if not line.strip(): continue
            raw_rec = json.loads(line)
            # Use fracDeV_r as sersic proxy (0=exponential/disk, 1=deVaucouleurs/elliptical)
            val = raw_rec.get("fracDeV_r")
            if val is not None:
                promoted = {
                    "entity_id": raw_rec["entity_id"], "domain": "galactic_sersic", "volume": 11,
                    "lake_id": "g1b_sersic", "sersic_index": float(val),
                    "meta": {"sovereign": True}, "_raw_payload": raw_rec
                }
                fout.write(json.dumps(promoted) + "\n")
                count += 1
    print(f"G1b Success: {count:,} records.")
if __name__ == "__main__": promote()