import json
import os
import glob

PROMOTED_DIR = "../lake/promoted/"
RECEIPT_PATH = "../../../lakes/logs/series_s12_geomagnetic_probe_receipt.txt"

REQUIRED_COMMON = ["klghs_natural_unit", "klghs_transform", "source"]

def validate_igrf_record(record, line_num):
    errors = []
    if "amplitude_nT" not in record:
        errors.append("Missing 'amplitude_nT'")
    elif not isinstance(record["amplitude_nT"], (int, float)):
        errors.append("'amplitude_nT' must be numeric")
    elif record["amplitude_nT"] < 0:
        errors.append("'amplitude_nT' must be absolute (positive)")

    if record.get("klghs_natural_unit") != "nT":
        errors.append(f"klghs_natural_unit must be 'nT', found '{record.get('klghs_natural_unit')}'")

    return errors

def validate_file(filepath):
    filename = os.path.basename(filepath)
    print(f"[VALIDATE] Scanning {filename}...")
    errors, records = 0, 0

    with open(filepath, 'r') as f:
        for line_num, line in enumerate(f, 1):
            try:
                record = json.loads(line.strip())
                records += 1
                line_errors = []

                for req in REQUIRED_COMMON:
                    if req not in record:
                        line_errors.append(f"Missing '{req}'")

                if record.get("klghs_transform") != "log_standard":
                    line_errors.append(f"klghs_transform must be 'log_standard'")

                line_errors.extend(validate_igrf_record(record, line_num))

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
    print("--- KLGHS S12 VALIDATION SEQUENCE ---")
    promoted_files = glob.glob(os.path.join(PROMOTED_DIR, "*.jsonl"))

    if not promoted_files:
        print(f"[ERROR] No promoted files found in {PROMOTED_DIR}")
        return

    all_passed = True
    for fpath in promoted_files:
        if not validate_file(fpath):
            all_passed = False

    if all_passed:
        print("\n[SUCCESS] S12 Geomagnetic Probe passes strict schema validation.")
        os.makedirs(os.path.dirname(RECEIPT_PATH), exist_ok=True)
        with open(RECEIPT_PATH, "w") as f:
            f.write("VALIDATED: s12_geomagnetic_probe\n")
            f.write("STATUS: READY FOR UNIFY\n")
        print(f"[RECEIPT] Engine validation receipt written to {RECEIPT_PATH}")
    else:
        print("\n[HALT] Validation failed. Fix schema errors before engine ingest.")

if __name__ == "__main__":
    main()