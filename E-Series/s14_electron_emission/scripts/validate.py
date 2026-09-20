#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
validate.py — KLGHS S14 Validation
Aligned with Atlas Aurora Kish architecture and the updated promote.py schema.

This validator checks:
- Required KLGHS fields
- Correct natural unit (Hz)
- Correct transform (log_standard)
- Correct predicted_register (25/pi)
- Correct vertex_class (2, 4, 8 only)
- Correct numeric types for derived physics fields
- Presence of raw_row_index for chain-of-custody
"""

import json
import os
import glob

PROMOTED_DIR = "../lake/promoted/"
RECEIPT_PATH = "../../../lakes/logs/series_s14_geometric_electron_receipt.txt"

# Required fields in every promoted record
REQUIRED_FIELDS = [
    "element",
    "Z",
    "raw_row_index",
    "Ei_cm1",
    "Ek_cm1",
    "delta_wavenumber_cm1",
    "klghs_transition_freq_Hz",
    "klghs_transition_energy_eV",
    "klghs_vertex_class",
    "klghs_natural_unit",
    "klghs_transform",
    "klghs_domain",
    "predicted_register"
]

VALID_VERTEX_CLASSES = [2, 4, 8]


def validate_record(record, line_num):
    errors = []

    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in record:
            errors.append(f"Missing '{field}'")

    # Check natural unit
    if record.get("klghs_natural_unit") != "Hz":
        errors.append(f"klghs_natural_unit must be 'Hz', found '{record.get('klghs_natural_unit')}'")

    # Check transform
    if record.get("klghs_transform") != "log_standard":
        errors.append(f"klghs_transform must be 'log_standard'")

    # Check predicted register
    if record.get("predicted_register") != "25/pi":
        errors.append(f"predicted_register must be '25/pi'")

    # Check vertex class
    vc = record.get("klghs_vertex_class")
    if vc not in VALID_VERTEX_CLASSES:
        errors.append(f"Invalid klghs_vertex_class '{vc}', must be one of {VALID_VERTEX_CLASSES}")

    # Check numeric physics fields
    numeric_fields = [
        "Ei_cm1",
        "Ek_cm1",
        "delta_wavenumber_cm1",
        "klghs_transition_freq_Hz",
        "klghs_transition_energy_eV"
    ]

    for nf in numeric_fields:
        val = record.get(nf)
        if not isinstance(val, (int, float)):
            errors.append(f"'{nf}' must be numeric, found '{val}'")

    return errors


def validate_file(filepath):
    filename = os.path.basename(filepath)
    print(f"[VALIDATE] Scanning {filename}...")
    errors = 0
    records = 0

    with open(filepath, "r") as f:
        for line_num, line in enumerate(f, 1):
            try:
                record = json.loads(line.strip())
                records += 1

                line_errors = validate_record(record, line_num)

                if line_errors:
                    print(f"  [!] Line {line_num} errors: {', '.join(line_errors)}")
                    errors += 1

            except json.JSONDecodeError:
                print(f"  [!] Line {line_num}: Invalid JSON syntax")
                errors += 1

    if errors == 0:
        print(f"[PASS] {filename}: {records} records validated perfectly.")
        return True
    else:
        print(f"[FAIL] {filename}: {errors} records contained schema violations.")
        return False


def main():
    print("--- KLGHS S14 VALIDATION SEQUENCE ---")
    promoted_files = glob.glob(os.path.join(PROMOTED_DIR, "*.jsonl"))

    if not promoted_files:
        print(f"[ERROR] No promoted JSONL files found in {PROMOTED_DIR}")
        return

    all_passed = True
    for fpath in promoted_files:
        if not validate_file(fpath):
            all_passed = False

    if all_passed:
        print("\n[SUCCESS] S14 Transitional Channel passes strict schema validation.")
        os.makedirs(os.path.dirname(RECEIPT_PATH), exist_ok=True)
        with open(RECEIPT_PATH, "w") as f:
            f.write("VALIDATED: s14_geometric_electron\n")
            f.write("STATUS: READY FOR UNIFY\n")
        print(f"[RECEIPT] Engine validation receipt written to {RECEIPT_PATH}")
    else:
        print("\n[HALT] Validation failed. Fix schema errors before allowing engine ingest.")


if __name__ == "__main__":
    main()
