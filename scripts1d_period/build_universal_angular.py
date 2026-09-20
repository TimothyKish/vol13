#!/usr/bin/env python3
# ==============================================================================
# build_universal_angular.py
# Stitches quantum and macro rotational/frequency domains into a single 
# scale-invariant lake measured strictly in Hertz (cycles per second).
# ==============================================================================
import json
import math
from pathlib import Path

ROOT = Path(r"C:\Users\timot\Downloads\Science\src\Unification\vol13")
IN_DIR = ROOT / "lakes" / "inputs_promoted"
OUT_DIR = ROOT / "lakes1d_period" / "inputs_promoted"
OUT_FILE = OUT_DIR / "L_universal_angular_promoted.jsonl"

def safe_get(d, keys):
    for k in keys:
        if isinstance(d, dict) and k in d: d = d[k]
        else: return None
    return d

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    
    sources = [
        {
            "file": "L_emission_nist_promoted.jsonl",
            "domain": "quantum_transitional",
            "hz_extractor": lambda r: safe_get(r, ["klghs_transition_freq_Hz"])
        },
        {
            "file": "k2_pulsar_periods_promoted.jsonl",
            "domain": "stellar_rotation_pulsar",
            "hz_extractor": lambda r: 1000.0 / safe_get(r, ["_raw_payload", "p0_ms"]) if safe_get(r, ["_raw_payload", "p0_ms"]) else None
        },
        {
            "file": "k1_kepler_rotation_promoted.jsonl",
            "domain": "stellar_rotation_kepler",
            "hz_extractor": lambda r: 1.0 / (safe_get(r, ["meta", "prot_days"]) * 86400.0) if safe_get(r, ["meta", "prot_days"]) else None
        },
        {
            "file": "p1_orbital_periods_promoted.jsonl",
            "domain": "orbital",
            "hz_extractor": lambda r: 1.0 / (safe_get(r, ["_raw_payload", "period_days"]) * 86400.0) if safe_get(r, ["_raw_payload", "period_days"]) else None
        }
    ]

    total_records = 0
    hz_values = []
    
    with open(OUT_FILE, "w", encoding="utf-8") as out_f:
        for src in sources:
            in_path = IN_DIR / src["file"]
            if not in_path.exists():
                print(f"[!] Warning: {src['file']} not found. Skipping.")
                continue
                
            count = 0
            with open(in_path, "r", encoding="utf-8") as in_f:
                for line in in_f:
                    if not line.strip(): continue
                    rec = json.loads(line)
                    
                    try:
                        hz = src["hz_extractor"](rec)
                        if hz is None or hz <= 0 or not math.isfinite(hz): continue
                    except Exception:
                        continue
                        
                    # Create the new stitched record
                    new_rec = {
                        "entity_id": rec.get("entity_id", f"stitched_{total_records}"),
                        "domain": "universal_angular",
                        "lake_id": "L_universal_angular",
                        "universal_hz": hz,
                        "meta": {
                            "original_domain": src["domain"],
                            "source_file": src["file"],
                            "stitched": True
                        }
                    }
                    
                    out_f.write(json.dumps(new_rec) + "\n")
                    hz_values.append(hz)
                    count += 1
                    total_records += 1
                    
            print(f"  Processed {count:,} valid records from {src['domain']}")

    if hz_values:
        log_hz = [math.log(x) for x in hz_values]
        span = max(log_hz) - min(log_hz)
        print(f"\n[*] SUCCESS: Stitched {total_records:,} records into Universal Angular Lake.")
        print(f"[*] Raw Hertz bounds: {min(hz_values):.2e} Hz to {max(hz_values):.2e} Hz")
        print(f"[*] Log-Span: {span:.2f} units ({(span/math.log(10)):.2f} decades)")
        print(f"[*] Saved to: {OUT_FILE}")

if __name__ == "__main__":
    main()