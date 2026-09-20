"""
KishLattice Sovereign Lake Validator
Target: s23 Magnetic Susceptibility (Molar)
Action: Customs Officer - validates schema, domains, and physics before engine run.
"""

import json
import os
import sys

def validate_lake(filepath, expected_domain):
    count = 0
    err_domain = 0
    err_physics = 0

    if not os.path.exists(filepath):
        print(f"[FAIL] Missing file: {os.path.basename(filepath)}")
        return False

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            rec = json.loads(line)
            count += 1
            
            # 1. Domain Match
            if rec.get("domain") != expected_domain: 
                err_domain += 1
            
            # 2. Physics Match (Absolute Susceptibility must be > 0)
            chi = rec.get("klghs_abs_chi")
            if not (isinstance(chi, (int, float)) and chi > 0): 
                err_physics += 1
    
    if err_domain > 0 or err_physics > 0:
        print(f"[FAIL] {os.path.basename(filepath)}: Domains={err_domain}, Physics={err_physics}")
        return False
        
    print(f"[OK] {os.path.basename(filepath)} passed ({count} records).")
    return True

def validate():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    promoted_dir = os.path.join(script_dir, "..", "..", "..", "lakes", "inputs_promoted")
    
    dia_path = os.path.join(promoted_dir, "L_susceptibility_dia.jsonl")
    dia_scr_path = os.path.join(promoted_dir, "L_susceptibility_dia_scramble.jsonl")
    para_path = os.path.join(promoted_dir, "L_susceptibility_para.jsonl")
    para_scr_path = os.path.join(promoted_dir, "L_susceptibility_para_scramble.jsonl")

    lakes_to_test = [
        (dia_path, "electron_dia_susceptibility"),
        (dia_scr_path, "electron_dia_susceptibility_scramble"),
        (para_path, "electron_para_susceptibility"),
        (para_scr_path, "electron_para_susceptibility_scramble")
    ]

    print("Running Customs Officer checks on s23 Susceptibility lakes...\n")
    all_passed = True
    for path, domain in lakes_to_test:
        if not validate_lake(path, domain):
            all_passed = False

    if all_passed:
        print("\n[SUCCESS] S23 SUSCEPTIBILITY FLEET READY FOR ENGINE.")
    else:
        print("\n[ERROR] Validation failed. Check promoted records before running pipeline.")
        sys.exit(1)

if __name__ == "__main__":
    validate()