#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
build_lake.py — Faithful NIST ASD transcription (RAW lake)
Atlas Aurora Kish architecture: raw-stays-raw, no computed physics.

This script:
- Parses NIST CSV bulk files (neutral atoms, I stage)
- Maps columns by header name (safe against NIST column-order changes)
- Preserves all physical fields exactly as NIST provides them
- Adds raw_row_index for chain-of-custody
- Writes JSONL records with no derived fields
"""

import os
import json

BULK_DIR = "../nist_bulk"
RAW_OUT_PATH = "../lake/raw/nist_asd_emission_Z1_to_Z18.jsonl"

# Neutral atoms only (I stage)
ELEMENTS = [
    ("H I", 1), ("He I", 2), ("Li I", 3), ("Be I", 4), ("B I", 5), ("C I", 6),
    ("N I", 7), ("O I", 8), ("F I", 9), ("Ne I", 10), ("Na I", 11), ("Mg I", 12),
    ("Al I", 13), ("Si I", 14), ("P I", 15), ("S I", 16), ("Cl I", 17), ("Ar I", 18)
]


def parse_bulk_csv(spec, z):
    filename = f"{spec.replace(' ', '_')}_lines.ascii"
    path = os.path.join(BULK_DIR, filename)

    if not os.path.exists(path):
        print(f"[!] Missing file: {filename}")
        return []

    records = []
    header_map = None
    row_index = 0

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            parts = [p.strip().strip('"') for p in line.split(",")]

            # Detect header row
            if header_map is None:
                header_map = {name: idx for idx, name in enumerate(parts)}
                continue

            row_index += 1

            # Build raw record using header names
            rec = {
                "element": spec,
                "Z": z,
                "raw_row_index": row_index,
                "source": "NIST ASD Bulk CSV",
                "source_access_date": "2026-07-04"
            }

            # Copy all NIST columns exactly as provided
            for col_name, idx in header_map.items():
                if idx < len(parts):
                    rec[col_name] = parts[idx]

            records.append(rec)

    return records


def build_raw_lake():
    print("[BUILD] Generating RAW NIST ASD lake (neutral atoms)...\n")

    os.makedirs(os.path.dirname(RAW_OUT_PATH), exist_ok=True)

    total = 0

    with open(RAW_OUT_PATH, "w", encoding="utf-8") as out:
        for spec, z in ELEMENTS:
            print(f"  -> Transcribing {spec} ...")
            recs = parse_bulk_csv(spec, z)

            for r in recs:
                out.write(json.dumps(r) + "\n")
                total += 1

    print(f"\n[BUILD] Complete. {total} raw records written.\n")


if __name__ == "__main__":
    build_raw_lake()
