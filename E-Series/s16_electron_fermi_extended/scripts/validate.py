#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os

OUT_REAL = os.path.join(os.path.dirname(__file__), "..", "lake", "promoted", "L_fermi_extended_promoted.jsonl")
OUT_SCRAMBLE = os.path.join(os.path.dirname(__file__), "..", "lake", "promoted", "L_fermi_scramble_ctrl_promoted.jsonl")

def check_file(path, expected_domain):
    if not os.path.exists(path):
        return 0, 1
    count = 0
    err = 0
    with open(path, 'r') as f:
        for line in f:
            if not line.strip(): continue
            count += 1
            rec = json.loads(line)
            if "fermi_velocity_ms" not in rec or rec.get("domain") != expected_domain:
                err += 1
    return count, err

def main():
    r_count, r_err = check_file(OUT_REAL, "electron_fermi_extended")
    s_count, s_err = check_file(OUT_SCRAMBLE, "electron_fermi_scramble_ctrl")

    print("=" * 50)
    print(" S16 FERMI EXTENDED VALIDATION")
    print("=" * 50)
    print(f" REAL:      {r_count} records, {r_err} errors")
    print(f" SCRAMBLED: {s_count} records, {s_err} errors")
    
    if r_count < 5000:
        print(f" [FAIL] Density check failed. N={r_count} < 5000 target.")
    elif r_err > 0 or s_err > 0:
        print(" [FAIL] Schema validation failed.")
    else:
        print(" [PASS] Ready for Unification.")

if __name__ == "__main__":
    main()