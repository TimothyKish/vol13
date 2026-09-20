#!/usr/bin/env python3
# ==============================================================================
# build_universal_length.py
# Bridges atomic wavelengths to galactic radii into pure Meters (m).
# ==============================================================================
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IN_DIR = ROOT / "lakes" / "inputs_promoted"
OUT_DIR = ROOT / "lakes1d_period" / "inputs_promoted"
OUT_FILE = OUT_DIR / "L_universal_length_promoted.jsonl"

LENGTH_SOURCES = [
    {"file": "q1_atomic_spectra_promoted.jsonl", "key": "wavelength_nm", "mult": 1e-9, "desc": "Atomic Wavelengths (nm)"},
    {"file": "np1_orbital_periods_promoted.jsonl", "key": "semi_major_au", "mult": 1.495978707e11, "desc": "Exoplanet Orbits (AU)"},
    {"file": "p1_orbital_periods_promoted.jsonl", "key": "semi_major_au", "mult": 1.495978707e11, "desc": "Planet Orbits (AU)"},
    {"file": "s1_gaia_parallax_promoted.jsonl", "key": "dist_pc", "mult": 3.085677581e16, "desc": "Stellar Distance (pc)"},
    {"file": "g1a_radius_promoted.jsonl", "key": "effective_radius_kpc", "mult": 3.085677581e19, "desc": "Galactic Radius (kpc)"}
]

def safe_extract(record, key):
    if key in record: return record[key]
    if "_raw_payload" in record and key in record["_raw_payload"]: return record["_raw_payload"][key]
    if "geometry_payload" in record and key in record["geometry_payload"]: return record["geometry_payload"][key]
    if "meta" in record and key in record["meta"]: return record["meta"][key]
    return None

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    total_records = 0
    length_values = []
    
    with open(OUT_FILE, "w", encoding="utf-8") as out_f:
        for src in LENGTH_SOURCES:
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
                        
                    m_value = val * src["mult"]
                    master_rec = {
                        "entity_id": rec.get("entity_id", rec.get("id", f"len_{total_records}")),
                        "domain": "universal_length",
                        "lake_id": "L_universal_length",
                        "klghs_x": m_value,
                        "meta": {"source_file": src["file"], "extracted_field": src["key"], "raw_value": val}
                    }
                    out_f.write(json.dumps(master_rec) + "\n")
                    length_values.append(m_value)
                    total_records += 1
                    domain_records += 1
            print(f"  -> {src['file']}: {domain_records:,} records ({src['desc']})")

    if length_values:
        span = max([math.log(x) for x in length_values]) - min([math.log(x) for x in length_values])
        print(f"\n[*] SUCCESS: {total_records:,} records. Bounds: {min(length_values):.2e} to {max(length_values):.2e} m")
        print(f"[*] Log-Span: {span:.2f} units ({(span/math.log(10)):.2f} decades)")

if __name__ == "__main__":
    main()