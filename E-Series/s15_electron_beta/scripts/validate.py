#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate.py (s15_electron_beta)
Validates the promoted lake schema and enforces the N >= 2000 density rule.
"""

import json
import os

PROMOTED_PATH = os.path.join(os.path.dirname(__file__), "..", "lake", "promoted", "L_beta_decay_promoted.jsonl")
REQUIRED_KEYS = {"beta_endpoint_kev", "domain", "klghs_transform", "klghs_natural_unit"}
MIN_N_THRESHOLD = 2000

def main():
    if not os.path.exists(PROMOTED_PATH):
        print(f"[FAIL] Promoted file not found: {PROMOTED_PATH}")
        return

    count = 0
    errors = 0
    with open(PROMOTED_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            count += 1
            rec = json.loads(line)
            
            missing = REQUIRED_KEYS - set(rec.keys())
            if missing:
                print(f"[!] Record {count} missing keys: {missing}")
                errors += 1

    print("=" * 50)
    print(" L_beta_decay VALIDATION REPORT")
    print("=" * 50)
    print(f" Total Records : {count}")
    print(f" Schema Errors : {errors}")
    
    if count < MIN_N_THRESHOLD:
        print(f" [FAIL] Density check failed. N={count} is below minimum threshold of {MIN_N_THRESHOLD}.")
    elif errors > 0:
        print(" [FAIL] Schema validation failed.")
    else:
        print(" [PASS] Sovereign lake is valid and ready for Unification.")

if __name__ == "__main__":
    main()