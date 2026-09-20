#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scalar_field_probe.py  —  What does each promoted lake actually contain?

Before the gate can scramble a lake, we must know whether the promoted file
stores a pre-computed scalar (scalar-space path) or only a raw physical value
(raw-space path). This probe reads the first record of each anchor lake and
reports which fields are present, so the gate config uses the right injection
mode per lake instead of assuming.

Run from engine dir: python scalar_field_probe.py
"""

import json
import os

ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))

LAKES = {
    "s2_stellar_kinematics": "../lakes/inputs_promoted/s2_stellar_kinematics_promoted.jsonl",
    "b5_pdb_protein":        "../lakes/inputs_promoted/b5_pdb_protein_promoted.jsonl",
    "p1_orbital_periods":    "../lakes/inputs_promoted/p1_orbital_periods_promoted.jsonl",
}

SCALAR_FIELDS = ("scalar_kls", "scalar_klc")

def probe(path):
    full = os.path.join(ENGINE_DIR, path)
    if not os.path.exists(full):
        return None, f"FILE NOT FOUND: {full}"
    with open(full, "r", encoding="utf-8") as f:
        first = f.readline().strip()
    if not first:
        return None, "empty file"
    rec = json.loads(first)
    return rec, None

def main():
    print("=" * 64)
    print("   SCALAR FIELD PROBE  (per-lake injection mode)")
    print("=" * 64)
    for lake, path in LAKES.items():
        rec, err = probe(path)
        print(f"\n[{lake}]")
        if err:
            print(f"    {err}"); continue
        top_keys = list(rec.keys())
        has_scalar = [f for f in SCALAR_FIELDS if f in rec]
        # also check nested meta
        meta = rec.get("meta", {})
        meta_scalar = [f for f in SCALAR_FIELDS if isinstance(meta, dict) and f in meta]
        print(f"    top-level keys : {top_keys}")
        if has_scalar:
            print(f"    -> HAS pre-computed scalar {has_scalar} at ROOT  => SCALAR-SPACE path OK")
        elif meta_scalar:
            print(f"    -> scalar {meta_scalar} only under meta => needs path adjust")
        else:
            print(f"    -> NO pre-computed scalar field => MUST use RAW-SPACE path")
            # identify the likely raw field
            for candidate in ("angle_degrees","period_days_raw","val_raw_kms","ttv_absolute_minutes"):
                if candidate in rec:
                    print(f"       raw field present: '{candidate}'")
                m = rec.get("meta",{})
                if isinstance(m,dict) and candidate in m:
                    print(f"       raw field present under meta: '{candidate}'")
    print("\n" + "=" * 64)
    print("  Use SCALAR-SPACE only where a root scalar_kls exists (sector-normalized s2).")
    print("  Use RAW-SPACE (scramble->invert->inject raw field) for all others.")

if __name__ == "__main__":
    main()