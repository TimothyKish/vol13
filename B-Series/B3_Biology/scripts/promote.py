# ==============================================================================
# SCRIPT: promote.py
# PURPOSE: Promotes 3D atomic point clouds of Amino Acids into the KishLattice.
# ==============================================================================
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

DOMAIN = "biology_amino"
LAKE_ID = "b3_amino"

SCRIPT_DIR = Path(__file__).resolve().parent
RAW_PATH = SCRIPT_DIR.parent / "lake" / f"{LAKE_ID}.jsonl"
PROMOTED_DIR = SCRIPT_DIR.parents[3] / "lakes" / "inputs_promoted"
PROMOTED_PATH = PROMOTED_DIR / f"{LAKE_ID}_promoted.jsonl"

def promote():
    print("=" * 60)
    print(f" PROMOTING 3D GEOMETRY: {LAKE_ID} ".center(60))
    print("=" * 60)
    
    if not RAW_PATH.exists(): return print(f"FATAL: {RAW_PATH} missing.")
    count, now = 0, datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    PROMOTED_DIR.mkdir(parents=True, exist_ok=True)
    
    with RAW_PATH.open("r", encoding="utf-8") as fin, PROMOTED_PATH.open("w", encoding="utf-8") as fout:
        for line in fin:
            if not line.strip(): continue
            rec = json.loads(line)
            
            # Extract the raw atomic dictionary into a pure 3D coordinate array
            coords_3d = [[a["x"], a["y"], a["z"]] for a in rec.get("coords", [])]
            if not coords_3d: continue
            
            promoted = {
                "entity_id": f"CID_{rec.get('cid', uuid.uuid4())}",
                "domain": DOMAIN,
                "volume": 11,
                "lake_id": LAKE_ID,
                "name": rec.get("name", "Unknown"),
                "geometry_payload": {
                    "coordinates": coords_3d,
                    "dimensionality": 3,
                    "geometry_type": "point_cloud"
                },
                "meta": {"source": "PubChem/Amino Base", "timestamp": now, "sovereign": True},
                "_raw_payload": rec
            }
            fout.write(json.dumps(promoted) + "\n")
            count += 1
            
    print(f"SUCCESS: {count:,} 3D molecular structures promoted.")

if __name__ == "__main__": 
    promote()