#!/usr/bin/env python3
# ==============================================================================
# build_universal_time.py
# 
# THEORETICAL CONTEXT:
# Constructs the "Universal Time Lake", bridging quantum temporal randomness 
# (isotope decay half-lives) with macro determinism (orbital periods) and 
# stochastic planetary systems (geological fault slips, solar cycles, ocean tides).
#
# Everything is normalized to a strict, scale-invariant axis: Seconds.
# ==============================================================================
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IN_DIR = ROOT / "lakes" / "inputs_promoted"
OUT_DIR = ROOT / "lakes1d_period" / "inputs_promoted"
OUT_FILE = OUT_DIR / "L_universal_time_promoted.jsonl"

TIME_SOURCES = [
    # --- QUANTUM / SUBATOMIC (Multiplier: 1.0 - Already in Seconds) ---
    {"file": "q5_decay_promoted.jsonl", "key": "half_life_seconds", "mult": 1.0, "desc": "Isotope Half-lives"},
    
    # --- ORBITAL (Multiplier: 86,400 - Days to Seconds) ---
    {"file": "np1_orbital_periods_promoted.jsonl", "key": "period_days", "mult": 86400.0, "desc": "Exoplanet Orbital Periods"},
    {"file": "p1_orbital_periods_promoted.jsonl", "key": "period_days", "mult": 86400.0, "desc": "Planetary Orbital Periods"},
    
    # --- GEOLOGICAL & SOLAR (Multiplier: 86,400 - Days to Seconds) ---
    {"file": "u1_usgs_san_andreas_promoted.jsonl", "key": "interval_days", "mult": 86400.0, "desc": "San Andreas Quake Intervals"},
    {"file": "u2_usgs_cascadia_promoted.jsonl", "key": "interval_days", "mult": 86400.0, "desc": "Cascadia Quake Intervals"},
    {"file": "u3_usgs_japan_trench_promoted.jsonl", "key": "interval_days", "mult": 86400.0, "desc": "Japan Trench Quake Intervals"},
    {"file": "u4_usgs_anatolian_promoted.jsonl", "key": "interval_days", "mult": 86400.0, "desc": "Anatolian Quake Intervals"},
    {"file": "k3_solar_cycle_promoted.jsonl", "key": "interval_days", "mult": 86400.0, "desc": "Solar Cycle Intervals"},
    
    # --- OCEANIC TIDES (Multiplier: 3600 - Hours to Seconds) ---
    {"file": "t2b_atlantic_promoted.jsonl", "key": "interval_hours", "mult": 3600.0, "desc": "Atlantic Tide Intervals"},
    {"file": "t2c_gulf_promoted.jsonl", "key": "interval_hours", "mult": 3600.0, "desc": "Gulf Tide Intervals"},
    {"file": "t2d_pacific_promoted.jsonl", "key": "interval_hours", "mult": 3600.0, "desc": "Pacific Tide Intervals"},
    {"file": "t2g_indian_promoted.jsonl", "key": "interval_hours", "mult": 3600.0, "desc": "Indian Ocean Tide Intervals"},
    
    # --- TRANSIT TIMING (Multiplier: 60 - Minutes to Seconds) ---
    {"file": "p4_ttv_promoted.jsonl", "key": "ttv_absolute_minutes", "mult": 60.0, "desc": "Exoplanet Transit Timing Variations"}
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
    print(" BUILDING UNIVERSAL TIME LAKE (Seconds)")
    print("================================================================")
    
    total_records = 0
    time_values = []
    
    with open(OUT_FILE, "w", encoding="utf-8") as out_f:
        for src in TIME_SOURCES:
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
                        
                    # Apply multiplier to convert to pure seconds
                    s_value = val * src["mult"]
                    
                    master_rec = {
                        "entity_id": rec.get("entity_id", rec.get("id", f"time_{total_records}")),
                        "domain": "universal_time",
                        "lake_id": "L_universal_time",
                        "klghs_x": s_value,
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
                    time_values.append(s_value)
                    total_records += 1
                    domain_records += 1
                    
            print(f"  -> {original_domain}: {domain_records:,} records ({src['desc']})")

    if time_values:
        log_time = [math.log(x) for x in time_values]
        span = max(log_time) - min(log_time)
        
        print("\n================================================================")
        print(f"[*] SUCCESS: Compiled {total_records:,} records into Universal Time Lake.")
        print(f"[*] Time Bounds: {min(time_values):.4e} s to {max(time_values):.4e} s")
        print(f"[*] Log-Span: {span:.2f} units ({(span/math.log(10)):.2f} decades)")
        print(f"[*] Saved to: {OUT_FILE}")
        print("================================================================\n")

if __name__ == "__main__":
    main()