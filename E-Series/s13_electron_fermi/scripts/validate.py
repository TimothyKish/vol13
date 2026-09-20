import json
import os
import glob

PROMOTED_DIR = "../lake/promoted/"
# Standard Vol 10/11 receipt path for the engine
RECEIPT_PATH = "../../../lakes/logs/series_s13_geometric_electron_receipt.txt"

# Core fields required on EVERY KishLattice record
REQUIRED_COMMON = ["klghs_natural_unit", "klghs_transform", "element", "Z", "source"]

def validate_fermi_record(record, line_num):
    errors = []
    if "fermi_velocity_ms" not in record:
        errors.append("Missing 'fermi_velocity_ms'")
    elif not isinstance(record["fermi_velocity_ms"], (int, float)):
        errors.append("'fermi_velocity_ms' must be a numeric value")

    if record.get("klghs_natural_unit") != "m/s":
        errors.append(f"klghs_natural_unit must be 'm/s', found '{record.get('klghs_natural_unit')}'")

    return errors

def validate_nist_record(record, line_num):
    errors = []
    if "transition_frequency_Hz" not in record:
        errors.append("Missing 'transition_frequency_Hz'")
    elif not isinstance(record["transition_frequency_Hz"], (int, float)):
        errors.append("'transition_frequency_Hz' must be a numeric value")

    if "vertex_class" not in record:
        errors.append("Missing 'vertex_class'")
    else:
        valid_classes = ["2", "4", "8", "EXCLUDE"]
        if str(record["vertex_class"]) not in valid_classes:
            errors.append(f"Invalid vertex_class: {record.get('vertex_class')}. Must be one of {valid_classes}")

    if record.get("klghs_natural_unit") != "Hz":
        errors.append(f"klghs_natural_unit must be 'Hz', found '{record.get('klghs_natural_unit')}'")

    return errors

def validate_file(filepath):
    filename = os.path.basename(filepath)
    print(f"[VALIDATE] Scanning {filename}...")
    errors = 0
    records = 0

    with open(filepath, 'r') as f:
        for line_num, line in enumerate(f, 1):
            try:
                record = json.loads(line.strip())
                records += 1
                line_errors = []

                # 1. Check common fields
                for req in REQUIRED_COMMON:
                    if req not in record:
                        line_errors.append(f"Missing '{req}'")

                if record.get("klghs_transform") != "log_standard":
                    line_errors.append(f"klghs_transform must be 'log_standard', found '{record.get('klghs_transform')}'")

                # 2. Check lake-specific data and schemas
                if "fermi_velocity" in filename.lower():
                    line_errors.extend(validate_fermi_record(record, line_num))
                elif "emission_nist" in filename.lower():
                    line_errors.extend(validate_nist_record(record, line_num))
                else:
                    line_errors.append("Filename does not match known S13 schemas (fermi_velocity or emission_nist)")

                # Print line errors if any
                if line_errors:
                    print(f"  [!] Line {line_num} errors: {', '.join(line_errors)}")
                    errors += 1

            except json.JSONDecodeError:
                print(f"  [!] Line {line_num} error: Invalid JSON syntax")
                errors += 1

    if errors == 0:
        print(f"[PASS] {filename}: {records} records validated perfectly against the S13 Pre-Registration.")
        return True
    else:
        print(f"[FAIL] {filename}: {errors} records contained schema violations.")
        return False

def main():
    print("--- KLGHS S13 VALIDATION SEQUENCE ---")
    promoted_files = glob.glob(os.path.join(PROMOTED_DIR, "*.jsonl"))

    if not promoted_files:
        print(f"[ERROR] No promoted JSONL files found in {PROMOTED_DIR}")
        return

    all_passed = True
    for fpath in promoted_files:
        if not validate_file(fpath):
            all_passed = False

    if all_passed:
        print("\n[SUCCESS] All S13 lakes pass strict schema validation.")
        os.makedirs(os.path.dirname(RECEIPT_PATH), exist_ok=True)
        with open(RECEIPT_PATH, "w") as f:
            f.write("VALIDATED: s13_geometric_electron\n")
            f.write("STATUS: READY FOR UNIFY\n")
        print(f"[RECEIPT] Engine validation receipt written to {RECEIPT_PATH}")
    else:
        print("\n[HALT] Validation failed. Fix schema errors in promote.py before allowing engine ingest.")

if __name__ == "__main__":
    main()