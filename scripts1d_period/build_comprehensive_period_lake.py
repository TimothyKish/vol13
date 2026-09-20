#!/usr/bin/env python3
# ==============================================================================
# build_comprehensive_period_lake.py
# Aggregates all available promoted domain lakes into a master multi-domain 
# period lake for harmonic spectrum mapping across the entire container.
# ==============================================================================
import os
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IN_DIR = ROOT / "lakes" / "inputs_promoted"
OUT_DIR = ROOT / "lakes1d_period" / "inputs_promoted"
OUT_FILE = OUT_DIR / "L_comprehensive_master_promoted.jsonl"

def extract_scalar(record):
    """Hunt for any valid numerical scalar in the record payload or meta."""
    for key in ["klghs_x", "scalar_kls", "value", "frequency", "period", "mass", "radius"]:
        if key in record and isinstance(record[key], (int, float)):
            val = float(record[key])
            if val > 0 and math.isfinite(val):
                return val, key
    
    # Check nested meta or raw payload
    for container_key in ["meta", "_raw_payload"]:
        sub = record.get(container_key)
        if isinstance(sub, dict):
            for sub_k, sub_v in sub.items():
                if isinstance(sub_v, (int, float)):
                    val = float(sub_v)
                    if val > 0 and math.isfinite(val):
                        return val, f"{container_key}.{sub_k}"
                        
    return None, None

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not IN_DIR.exists():
        print(f"[!] Promoted inputs directory not found: {IN_DIR}")
        return

    promoted_files = list(IN_DIR.glob("*_promoted.jsonl"))
    print(f"[*] Found {len(promoted_files)} promoted domain lakes. Harvesting scalars...")

    total_records = 0
    domain_counts = {}

    with open(OUT_FILE, "w", encoding="utf-8") as out_f:
        for src_path in promoted_files:
            domain_name = src_path.stem.replace("_promoted", "")
            domain_records = 0
            
            with open(src_path, "r", encoding="utf-8") as in_f:
                for line in in_f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                        
                    x, source_field = extract_scalar(rec)
                    if x is None:
                        continue
                        
                    master_rec = {
                        "entity_id": rec.get("entity_id", f"{domain_name}_{total_records}"),
                        "domain": "comprehensive_master",  # Unified for the logifier
                        "lake_id": "L_comprehensive_master",
                        "klghs_x": x,
                        "meta": {
                            "original_domain": domain_name,
                            "source_file": src_path.name,
                            "extracted_field": source_field
                        }
                    }
                    
                    out_f.write(json.dumps(master_rec) + "\n")
                    total_records += 1
                    domain_records += 1
                    
            domain_counts[domain_name] = domain_records
            print(f"  -> {domain_name}: {domain_records:,} records extracted")

    print(f"\n[*] SUCCESS: Compiled {total_records:,} total records across {len(domain_counts)} domains.")
    print(f"[*] Master lake saved to: {OUT_FILE}")

if __name__ == "__main__":
    main()