# ==============================================================================
# SCRIPT: promote.py (B5 PDB FULL Protein Deep Survey)
# PURPOSE: Wraps the massive 49.3GB B5 PDB data into the KishLattice Volume 11 
#          schema and pushes it to lakes/inputs_promoted/
# ==============================================================================
import json
import uuid
import time
from datetime import datetime, timezone
from pathlib import Path

# Paths relative to B-Series/B5_PDB_Full/scripts/promote.py
SCRIPT_DIR    = Path(__file__).resolve().parent
RAW_PATH      = SCRIPT_DIR.parent / "lake" / "b5_pdb_full_protein_raw.jsonl"
PROMOTED_DIR  = SCRIPT_DIR.parents[2] / "lakes" / "inputs_promoted"
PROMOTED_PATH = PROMOTED_DIR / "b5_pdb_full_protein_promoted.jsonl"

def promote():
    print("=" * 60)
    print(" B5 FULL PDB PROMOTION SCRIPT (50GB WARNING) ".center(60))
    print("=" * 60)
    
    PROMOTED_DIR.mkdir(parents=True, exist_ok=True)
    
    if not RAW_PATH.exists():
        print(f"ERROR: Raw lake not found at {RAW_PATH}")
        return

    print(f"Source: {RAW_PATH.name}")
    print(f"Target: {PROMOTED_PATH.resolve()}")
    print("Promoting records to schema... this will take a while.")
    
    count = 0
    start_time = time.time()
    now_ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    
    with RAW_PATH.open("r", encoding="utf-8") as fin, \
         PROMOTED_PATH.open("w", encoding="utf-8") as fout:
        
        for line in fin:
            line = line.strip()
            if not line: continue
            
            raw_rec = json.loads(line)
            
            angle = raw_rec.get("angle_degrees")
            if angle is None:
                angle = raw_rec.get("phi") if "phi" in raw_rec else raw_rec.get("psi", 0.0)
            
            promoted_rec = {
                "entity_id": str(raw_rec.get("id", uuid.uuid4())),
                "domain": "biology_backbone",
                "volume": 11,
                "lake_id": "b5_pdb_full_protein",
                "angle_degrees": angle,
                "geometry_payload": {
                    "coordinates": [],
                    "dimensionality": 1,
                    "geometry_type": "dihedral_angle"
                },
                "meta": {
                    "source": "RCSB PDB Full Catalog (125M records)",
                    "ingest_timestamp": now_ts,
                    "sovereign": True
                },
                "_raw_payload": raw_rec
            }
            
            fout.write(json.dumps(promoted_rec, ensure_ascii=False) + "\n")
            count += 1
            
            if count % 5000000 == 0:
                elapsed = time.time() - start_time
                print(f"  -> Wrapped {count:,} records... ({elapsed:.1f}s elapsed)")

    elapsed = time.time() - start_time
    print("-" * 60)
    print(f"SUCCESS: {count:,} records promoted in {elapsed:.1f} seconds.")
    print("=" * 60)

if __name__ == "__main__":
    promote()