#!/usr/bin/env python3
# ==============================================================================
# build_universal_mass.py
# Bridges cosmological and stellar mass measurements into pure Kilograms (kg).
# ==============================================================================
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IN_DIR = ROOT / "lakes" / "inputs_promoted"
OUT_DIR = ROOT / "lakes1d_period" / "inputs_promoted"
OUT_FILE = OUT_DIR / "L_universal_mass_promoted.jsonl"

SOLAR_MASS_KG = 1.98847e30

MASS_SOURCES = [
    {"file": "g1c_mass_promoted.jsonl", "key": "stellar_mass_solar", "mult": SOLAR_MASS_KG, "desc": "Stellar Mass"},
    {"file": "l1_gwtc_promoted.jsonl", "key": "chirp_mass_solar", "mult": SOLAR_MASS_KG, "desc": "Black Hole Chirp Mass"},
    {"file": "l1_gwtc_promoted.jsonl", "key": "final_mass_solar", "mult": SOLAR_MASS_KG, "desc": "Black Hole Final Mass"}
]

def safe_extract(record, key):
    if key in record: return record[key]
    if "_raw_payload" in record and key in record["_raw_payload"]: return record["_raw_payload"][key]
    if "geometry_payload" in record and key in record["geometry_payload"]: return record["geometry_payload"][key]
    return None

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    total_records = 0
    mass_values = []
    
    with open(OUT_FILE, "w", encoding="utf-8") as out_f:
        for src in MASS_SOURCES:
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
                    if val <= 0 or not math.isfinite(val): continue
                        
                    kg_value = val * src["mult"]
                    master_rec = {
                        "entity_id": rec.get("entity_id", rec.get("id", f"mass_{total_records}")),
                        "domain": "universal_mass",
                        "lake_id": "L_universal_mass",
                        "klghs_x": kg_value,
                        "meta": {"source_file": src["file"], "extracted_field": src["key"], "raw_value": val}
                    }
                    out_f.write(json.dumps(master_rec) + "\n")
                    mass_values.append(kg_value)
                    total_records += 1
                    domain_records += 1
            print(f"  -> {src['file']}: {domain_records:,} records ({src['desc']})")

    if mass_values:
        span = max([math.log(x) for x in mass_values]) - min([math.log(x) for x in mass_values])
        print(f"\n[*] SUCCESS: {total_records:,} records. Bounds: {min(mass_values):.2e} to {max(mass_values):.2e} kg")
        print(f"[*] Log-Span: {span:.2f} units ({(span/math.log(10)):.2f} decades)")

if __name__ == "__main__":
    main()