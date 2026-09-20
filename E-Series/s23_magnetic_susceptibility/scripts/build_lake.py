"""
KishLattice Sovereign Lake Builder
Target: s23 Magnetic Susceptibility (Molar)
Source: CRC Handbook of Chemistry and Physics compilations
"""

import csv
import json
import os
import sys

FLOOR_TARGET = 2000

def build_lake():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    raw_dir = os.path.join(script_dir, "..", "lake", "inputs_raw")
    in_csv = os.path.join(raw_dir, "crc_molar_susceptibilities.csv")
    out_path = os.path.join(raw_dir, "s23_susceptibility_raw.jsonl")
    dropped_log = os.path.join(raw_dir, "dropped_materials.log")

    os.makedirs(raw_dir, exist_ok=True)

    if not os.path.exists(in_csv):
        print(f"[ERROR] Raw data not found at {in_csv}.")
        print("Please provide the compiled CRC CSV with headers: [material, formula, type, chi_value_cgs]")
        sys.exit(1)

    records = []
    dropped = []

    with open(in_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            mat = row.get('material', '').strip()
            form = row.get('formula', '').strip()
            sType = row.get('type', '').strip().lower()
            val_str = row.get('chi_value_cgs', '').strip()

            # Pre-pull rule: STRICTLY Molar only. No conversions.
            if sType != 'molar':
                dropped.append(f"{mat} ({form}) - REJECTED: Type '{sType}' is not 'molar'.")
                continue

            try:
                chi_val = float(val_str)
                # Filter out pure zeros
                if chi_val != 0.0:
                    records.append({
                        "material": mat,
                        "formula": form,
                        "chi_molar_cgs": chi_val,
                        "source": "CRC_Handbook_Compilation"
                    })
            except ValueError:
                dropped.append(f"{mat} - REJECTED: Invalid value '{val_str}'")

    n = len(records)
    print(f"Extracted {n} valid Molar Susceptibility records.")

    if n < FLOOR_TARGET:
        print(f"[PUDDLE WARNING] Dataset N={n} is below the {FLOOR_TARGET} minimum floor.")
        print("This is a known constraint for CRC inorganic tables. Will be reported as a PUDDLE.")
    else:
        print(f"[SUCCESS] Density clears the {FLOOR_TARGET} floor.")

    with open(out_path, 'w', encoding='utf-8') as f:
        for rec in records:
            f.write(json.dumps(rec) + '\n')

    with open(dropped_log, 'w', encoding='utf-8') as f:
        for d in dropped:
            f.write(d + '\n')

    print(f"[OK] Raw lake written to {out_path}")
    print(f"[OK] Dropped log written to {dropped_log}")

if __name__ == "__main__":
    build_lake()