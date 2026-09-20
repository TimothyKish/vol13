#!/usr/bin/env python3
# ==============================================================================
# build_universal_velocity.py
# 
# THEORETICAL CONTEXT:
# Constructs the "Universal Velocity Lake", bridging quantum kinematics 
# (electron emission and Fermi velocities) to macro/cosmological kinematics 
# (stellar velocity dispersions and galactic movements).
#
# Everything is normalized to a strict, scale-invariant axis: Meters per Second (m/s).
# ==============================================================================
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IN_DIR = ROOT / "lakes" / "inputs_promoted"
OUT_DIR = ROOT / "lakes1d_period" / "inputs_promoted"
OUT_FILE = OUT_DIR / "L_universal_velocity_promoted.jsonl"

VELOCITY_SOURCES = [
    # --- QUANTUM KINEMATICS (Already in m/s, Mult: 1.0) ---
    {"file": "L_fermi_velocity_promoted.jsonl", "key": "fermi_velocity_ms", "mult": 1.0, "desc": "Fermi Velocity"},
    {"file": "L_arpes_electrons_promoted.jsonl", "key": "velocity_ms", "mult": 1.0, "desc": "ARPES Electron Velocity"},
    {"file": "L_auger_electrons_promoted.jsonl", "key": "velocity_ms", "mult": 1.0, "desc": "Auger Electron Velocity"},
    {"file": "L_compton_electrons_promoted.jsonl", "key": "velocity_ms", "mult": 1.0, "desc": "Compton Electron Velocity"},
    {"file": "L_conversion_electrons_promoted.jsonl", "key": "velocity_ms", "mult": 1.0, "desc": "Conversion Electron Velocity"},

    # --- MACRO KINEMATICS (In km/s, Mult: 1000.0) ---
    {"file": "s2_stellar_kinematics_promoted.jsonl", "key": "val_raw_kms", "mult": 1000.0, "desc": "Gaia Stellar Kinematics"},
    {"file": "g1_galaxy_kinematics_promoted.jsonl", "key": "vdisp", "mult": 1000.0, "desc": "SDSS Galactic Velocity Dispersion"}
]

def safe_extract(record, key):
    if key in record: return record[key]
    if "_raw_payload" in record and key in record["_raw_payload"]: return record["_raw_payload"][key]
    if "geometry_payload" in record and key in record["geometry_payload"]: return record["geometry_payload"][key]
    if "meta" in record and key in record["meta"]: return record["meta"][key]
    return None

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not IN_DIR.exists():
        print(f"[!] Promoted inputs directory not found: {IN_DIR}")
        return

    print("================================================================")
    print(" BUILDING UNIVERSAL VELOCITY LAKE (m/s)")
    print("================================================================")
    
    total_records = 0
    velocity_values = []
    
    with open(OUT_FILE, "w", encoding="utf-8") as out_f:
        for src in VELOCITY_SOURCES:
            src_path = IN_DIR / src["file"]
            if not src_path.exists():
                print(f"[!] Skipping {src['file']} - not found.")
                continue
                
            domain_records = 0
            original_domain = src["file"].replace("_promoted.jsonl", "")
            
            with open(src_path, "r", encoding="utf-8") as in_f:
                for line in in_f:
                    line = line.strip()
                    if not line: continue
                    
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                        
                    raw_val = safe_extract(rec, src["key"])
                    if raw_val is None: continue
                        
                    try:
                        val = float(raw_val)
                    except (ValueError, TypeError):
                        continue
                        
                    if val <= 0 or not math.isfinite(val): continue
                        
                    # Apply multiplier to convert to pure m/s
                    ms_value = val * src["mult"]
                    
                    master_rec = {
                        "entity_id": rec.get("entity_id", rec.get("id", f"vel_{total_records}")),
                        "domain": "universal_velocity",
                        "lake_id": "L_universal_velocity",
                        "klghs_x": ms_value,
                        "meta": {
                            "original_domain": original_domain,
                            "source_file": src["file"],
                            "extracted_field": src["key"],
                            "raw_value": val,
                            "multiplier": src["mult"],
                            "description": src["desc"]
                        }
                    }
                    
                    out_f.write(json.dumps(master_rec) + "\n")
                    velocity_values.append(ms_value)
                    total_records += 1
                    domain_records += 1
                    
            print(f"  -> {original_domain}: {domain_records:,} records ({src['desc']})")

    if velocity_values:
        log_vel = [math.log(x) for x in velocity_values]
        span = max(log_vel) - min(log_vel)
        
        print("\n================================================================")
        print(f"[*] SUCCESS: Compiled {total_records:,} records into Universal Velocity Lake.")
        print(f"[*] Velocity Bounds: {min(velocity_values):.4e} m/s to {max(velocity_values):.4e} m/s")
        print(f"[*] Log-Span: {span:.2f} units ({(span/math.log(10)):.2f} decades)")
        print(f"[*] Saved to: {OUT_FILE}")
        print("================================================================\n")

if __name__ == "__main__":
    main()