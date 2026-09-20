"""
KishLattice Sovereign Lake Validator
Target: s23 Magnetic Susceptibility Extended
Action: Customs Officer - validates schema, domains, provenance, and physics bounds.
"""
import json
import os
import sys

def validate_lake(filename, expected_domain):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(script_dir, "..", "lake", "inputs_promoted", filename)

    if not os.path.exists(filepath):
        print(f"[FAIL] Missing file: {filename}")
        return False

    count = 0
    err_domain = 0
    err_physics = 0
    err_prov = 0

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
                
            # 3. Provenance Law Enforcer
            if rec.get("provenance") != "measured":
                err_prov += 1
    
    if err_domain > 0 or err_physics > 0 or err_prov > 0:
        print(f"[FAIL] {filename}: Domains={err_domain}, Physics={err_physics}, Non-Measured={err_prov}")
        return False
        
    print(f"[PASS] {filename} passed all Customs Officer checks ({count} records).")
    return True

def validate():
    print("--- KLGHS S23 EXTENDED VALIDATION SEQUENCE ---")
    passed_dia = validate_lake("s23_dia_promoted.jsonl", "electron_dia_susceptibility")
    passed_para = validate_lake("s23_para_promoted.jsonl", "electron_para_susceptibility")

    if passed_dia and passed_para:
        print("\n[SUCCESS] S23 Extended Fleet passes strict schema and provenance validation.")
        print("[RECEIPT] Ready for derive_and_scramble.py to push to master ledger.")
    else:
        print("\n[ERROR] Validation failed. Check promoted records before proceeding.")
        sys.exit(1)

if __name__ == "__main__":
    validate()