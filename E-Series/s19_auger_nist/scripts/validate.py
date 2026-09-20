"""
KishLattice Sovereign Lake Validator
Target: s19 Auger Electrons Promoted
Action: Verifies schema, domain constraints, and physics bounds.
"""

import json
import os
import sys

def validate():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    in_path = os.path.join(script_dir, "..", "lake", "inputs_promoted", "s19_auger_electrons_promoted.jsonl")

    if not os.path.exists(in_path):
        print(f"[FAIL] Promoted lake not found: {in_path}")
        sys.exit(1)

    print(f"Validating {in_path}...")

    count = 0
    err_domain = 0
    err_energy = 0
    energies = []

    with open(in_path, 'r', encoding='utf-8') as f:
        for line in f:
            rec = json.loads(line)
            count += 1
            
            # Check domain
            if rec.get("domain") != "electron_auger_kinematic":
                err_domain += 1
                
            # Check energy (must be a positive float)
            energy = rec.get("energy_ev")
            if not isinstance(energy, (int, float)) or energy <= 0:
                err_energy += 1
            else:
                energies.append(energy)

    if err_domain > 0 or err_energy > 0:
        print("\n[FAIL] Validation rejected.")
        print(f"  Missing/Bad Domain: {err_domain}")
        print(f"  Missing/Bad Energy: {err_energy}")
        sys.exit(1)

    print("\n[OK] Validation PASSED.")
    print(f"  Total Records: {count}")
    if energies:
        print(f"  Energy Range:  {min(energies):.2f} eV to {max(energies):.2f} eV")
        print(f"  Mean Energy:   {sum(energies)/len(energies):.2f} eV")
        
    print("\nLAKE IS READY FOR MAIN ENGINE STITCHING.")

if __name__ == "__main__":
    validate()