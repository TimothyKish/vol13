import json, os, sys

def validate_lake(filepath, expected_domain):
    count, err_domain, err_physics = 0, 0, 0
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            rec = json.loads(line)
            count += 1
            if rec.get("domain") != expected_domain: err_domain += 1
            if not (isinstance(rec.get("velocity_ms"), (int, float)) and rec.get("velocity_ms") > 0): err_physics += 1
    
    if err_domain > 0 or err_physics > 0:
        print(f"[FAIL] {os.path.basename(filepath)}: Domains={err_domain}, Physics={err_physics}")
        return False
    print(f"[OK] {os.path.basename(filepath)} passed ({count} records).")
    return True

def validate():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    real_path = os.path.join(script_dir, "..", "..", "..", "lakes", "inputs_promoted", "L_arpes_electrons_promoted.jsonl")
    scramble_path = os.path.join(script_dir, "..", "..", "..", "lakes", "inputs_promoted", "L_arpes_scramble_ctrl_promoted.jsonl")
    if validate_lake(real_path, "electron_arpes_kinematic") and validate_lake(scramble_path, "electron_arpes_scramble_ctrl"):
        print("\n[SUCCESS] ARPES READY FOR ENGINE.")

if __name__ == "__main__":
    validate()