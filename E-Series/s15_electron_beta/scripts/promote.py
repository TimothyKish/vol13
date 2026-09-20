#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
promote.py (s15_electron_beta)
Promotes the raw IAEA beta decay lake into a KLGHS-compliant sovereign lake.
"""

import json
import os

IN_PATH = os.path.join(os.path.dirname(__file__), "..", "lake", "raw", "iaea_beta_decay_raw.jsonl")
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "lake", "promoted", "L_beta_decay_promoted.jsonl")

def main():
    if not os.path.exists(IN_PATH):
        print(f"[!] Raw file not found: {IN_PATH}")
        return

    records = []
    with open(IN_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            rec = json.loads(line)
            
            # Inject KLGHS required Promoted fields
            rec["klghs_natural_unit"] = "keV"
            rec["klghs_transform"] = "log_standard"
            rec["domain"] = "electron_beta"  # <-- The crucial Atlas Rewire
            
            records.append(rec)

    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")

    print(f"[+] Promoted lake written: {os.path.abspath(OUT_PATH)} ({len(records)} records)")

if __name__ == "__main__":
    main()