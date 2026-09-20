"""
KishLattice Sovereign Lake Fetcher & Merger
Target: s23 Magnetic Susceptibility Expansion
Source: Landolt-Börnstein (SpringerMaterials)
Rule: Strict CGS Molar, Measured Provenance, CRC Priority
"""

import csv
import os
import sys

def merge_landolt():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    raw_dir = os.path.join(script_dir, "..", "lake", "inputs_raw")
    
    crc_path = os.path.join(raw_dir, "crc_molar_susceptibilities.csv")
    landolt_path = os.path.join(raw_dir, "landolt_molar_susceptibilities.csv")
    merged_path = os.path.join(raw_dir, "s23_merged_baseline.csv")
    dropped_log = os.path.join(raw_dir, "dropped_materials_expansion.log")

    if not os.path.exists(crc_path):
        print(f"[ERROR] Baseline CRC file missing. Cannot enforce priority hierarchy.")
        sys.exit(1)
        
    if not os.path.exists(landolt_path):
        print(f"[ERROR] Landolt export missing at {landolt_path}. Cannot expand.")
        sys.exit(1)

    existing_formulas = set()
    records = []
    dropped = []

    # 1. Load the Priority Baseline (CRC)
    with open(crc_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            mat = row.get('material', '').strip()
            form = row.get('formula', '').strip()
            
            # Normalize formula for duplicate checking
            form_key = form.replace(" ", "").upper()
            existing_formulas.add(form_key)
            
            records.append({
                "material": mat,
                "formula": form,
                "type": "molar",
                "chi_value_cgs": row.get('chi_value_cgs', '').strip(),
                "provenance": "measured",
                "source": "CRC"
            })
            
    crc_count = len(records)
    print(f"Loaded {crc_count} baseline records from CRC.")

    # 2. Parse and Merge Landolt
    landolt_added = 0
    with open(landolt_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            mat = row.get('material', '').strip()
            form = row.get('formula', '').strip()
            sType = row.get('type', '').strip().lower()
            val_str = row.get('chi_value_cgs', '').strip()
            prov = row.get('provenance', '').strip().lower()

            form_key = form.replace(" ", "").upper()

            # Rule 1: Type
            if sType != 'molar':
                dropped.append(f"{mat} - REJECTED: Type '{sType}' is not 'molar'.")
                continue
            
            # Rule 2: Provenance
            if prov != 'measured':
                dropped.append(f"{mat} - REJECTED: Provenance '{prov}'.")
                continue

            # Rule 3: Duplicate Hierarchy
            if form_key in existing_formulas:
                dropped.append(f"{mat} - DUPLICATE: Dropped in favor of CRC baseline.")
                continue

            try:
                chi_val = float(val_str)
                if chi_val != 0.0:
                    records.append({
                        "material": mat,
                        "formula": form,
                        "type": "molar",
                        "chi_value_cgs": chi_val,
                        "provenance": "measured",
                        "source": "Landolt"
                    })
                    existing_formulas.add(form_key)
                    landolt_added += 1
            except ValueError:
                dropped.append(f"{mat} - REJECTED: Invalid value '{val_str}'")

    print(f"Added {landolt_added} new measured records from Landolt-Börnstein.")
    print(f"Total merged dataset size: {len(records)}")

    # 3. Write Merged Output
    with open(merged_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["material", "formula", "type", "chi_value_cgs", "provenance", "source"])
        writer.writeheader()
        writer.writerows(records)

    with open(dropped_log, 'w', encoding='utf-8') as f:
        for d in dropped: f.write(d + '\n')

if __name__ == "__main__":
    merge_landolt()