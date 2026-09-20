# ==============================================================================
# SCRIPT: promote.py (B5 PDB Protein Tactical Strike)
# PURPOSE: Wraps raw B5 PDB data into the KishLattice Volume 11 schema and 
#          pushes it to lakes/inputs_promoted/ for engine scalarization.
# ==============================================================================
import json
import uuid
import time
from datetime import datetime, timezone
from pathlib import Path

# Paths relative to B-Series/B5_PDB/scripts/promote.py
SCRIPT_DIR    = Path(__file__).resolve().parent
RAW_PATH      = SCRIPT_DIR.parent / "lake" / "b5_pdb_protein_raw.jsonl"
# FIX: Use .parents[2] to target Unification/vol11/lakes/inputs_promoted/
PROMOTED_DIR  = SCRIPT_DIR.parents[2] / "lakes" / "inputs_promoted"
PROMOTED_PATH = PROMOTED_DIR / "b5_pdb_protein_promoted.jsonl"

def promote():
    print("=" * 60)
    print(" B5 PDB PROMOTION SCRIPT ".center(60))
    print("=" * 60)
    
    PROMOTED_DIR.mkdir(parents=True, exist_ok=True)
    
    if not RAW_PATH.exists():
        print(f"ERROR: Raw lake not found at {RAW_PATH}")
        print("Did you run build_lake.py first?")
        return

    print(f"Source: {RAW_PATH.name}")
    print(f"Target: {PROMOTED_PATH.resolve()}")
    print("Promoting records to schema...")
    
    count = 0
    start_time = time.time()
    now_ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    
    with RAW_PATH.open("r", encoding="utf-8") as fin, \
         PROMOTED_PATH.open("w", encoding="utf-8") as fout:
        
        for line in fin:
            line = line.strip()
            if not line: continue
            
            raw_rec = json.loads(line)
            
            # Safely extract the angle whether it's named 'angle_degrees', 'phi', or 'psi'
            angle = raw_rec.get("angle_degrees")
            if angle is None:
                angle = raw_rec.get("phi") if "phi" in raw_rec else raw_rec.get("psi", 0.0)
            
            promoted_rec = {
                "entity_id": str(raw_rec.get("id", uuid.uuid4())),
                "domain": "biology_backbone",
                "volume": 11,
                "lake_id": "b5_pdb_protein",
                "angle_degrees": angle,
                "geometry_payload": {
                    "coordinates": [],
                    "dimensionality": 1,
                    "geometry_type": "dihedral_angle"
                },
                "meta": {
                    "source": "RCSB PDB smaller B5 pull",
                    "ingest_timestamp": now_ts,
                    "sovereign": True
                },
                "_raw_payload": raw_rec
            }
            
            fout.write(json.dumps(promoted_rec, ensure_ascii=False) + "\n")
            count += 1
            
            if count % 250000 == 0:
                print(f"  -> Wrapped {count:,} records...")

    elapsed = time.time() - start_time
    print("-" * 60)
    print(f"SUCCESS: {count:,} records promoted in {elapsed:.1f} seconds.")
    print(f"Ready for scalarization. Run 'python engine/run_pipeline.py' next.")
    print("=" * 60)

if __name__ == "__main__":
    promote()