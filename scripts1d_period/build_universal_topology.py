#!/usr/bin/env python3
# ==============================================================================
# build_universal_topology.py
# Bridges molecular chirality, protein folds, and orbital inclinations in Degrees.
# ==============================================================================
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IN_DIR = ROOT / "lakes" / "inputs_promoted"
OUT_DIR = ROOT / "lakes1d_period" / "inputs_promoted"
OUT_FILE = OUT_DIR / "L_universal_topology_promoted.jsonl"

TOPOLOGY_SOURCES = [
    {"file": "b1_chirality_promoted.jsonl", "key": "specific_rotation_deg", "desc": "Molecular Chirality"},
    {"file": "b3_amino_promoted.jsonl", "key": "backbone_angle_deg", "desc": "Amino Backbone Angles"},
    {"file": "b5_pdb_protein_promoted.jsonl", "key": "angle_degrees", "desc": "PDB Protein Folds"},
    {"file": "b5_pdb_full_protein_promoted.jsonl", "key": "angle_degrees", "desc": "PDB Full Protein Folds"},
    {"file": "p_incl_promoted.jsonl", "key": "inclination_deg", "desc": "Planetary Inclination"}
]

def safe_extract(record, key):
    if key in record: return record[key]
    if "_raw_payload" in record and key in record["_raw_payload"]: return record["_raw_payload"][key]
    if "geometry_payload" in record and key in record["geometry_payload"]: return record["geometry_payload"][key]
    return None

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    total_records = 0
    deg_values = []
    
    with open(OUT_FILE, "w", encoding="utf-8") as out_f:
        for src in TOPOLOGY_SOURCES:
            src_path = IN_DIR / src["file"]
            if not src_path.exists(): continue
                
            domain_records = 0
            with open(src_path, "r", encoding="utf-8") as in_f:
                for line in in_f:
                    if not line.strip(): continue
                    try: rec = json.loads(line)
                    except: continue
                        
                    raw_val = safe_extract(rec, src["key"])
                    if raw_val is None: continue
                    try: val = float(raw_val)
                    except: continue
                    val = abs(val) 
                    if val <= 0 or not math.isfinite(val): continue
                        
                    master_rec = {
                        "entity_id": rec.get("entity_id", rec.get("id", f"topo_{total_records}")),
                        "domain": "universal_topology",
                        "lake_id": "L_universal_topology",
                        "klghs_x": val,
                        "meta": {"source_file": src["file"], "extracted_field": src["key"]}
                    }
                    out_f.write(json.dumps(master_rec) + "\n")
                    deg_values.append(val)
                    total_records += 1
                    domain_records += 1
            print(f"  -> {src['file']}: {domain_records:,} records ({src['desc']})")

    if deg_values:
        span = max([math.log(x) for x in deg_values]) - min([math.log(x) for x in deg_values])
        print(f"\n[*] SUCCESS: {total_records:,} records. Bounds: {min(deg_values):.2e} to {max(deg_values):.2e} deg")
        print(f"[*] Log-Span: {span:.2f} units ({(span/math.log(10)):.2f} decades)")

if __name__ == "__main__":
    main()