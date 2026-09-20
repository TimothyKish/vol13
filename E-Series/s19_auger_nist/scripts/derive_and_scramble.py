"""
KishLattice Sovereign Lake Derivation & Scramble
Target: L_auger_electrons
Action: Derives velocity from eV, builds scramble twin, renames to L_ convention.
"""

import json
import os
import random
import math

def process_auger():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    in_path = os.path.join(script_dir, "..", "lake", "inputs_promoted", "s19_auger_electrons_promoted.jsonl")
    
    out_real = os.path.join(script_dir, "..", "..", "..", "lakes", "inputs_promoted", "L_auger_electrons_promoted.jsonl")
    out_scramble = os.path.join(script_dir, "..", "..", "..", "lakes", "inputs_promoted", "L_auger_scramble_ctrl_promoted.jsonl")

    # The Non-Relativistic Electron Velocity Constant from Energy (v = 593096.9 * sqrt(E_ev))
    VELOCITY_CONST = 593096.9

    records = []
    energies = []

    print(f"Reading base lake from {in_path}...")
    with open(in_path, 'r', encoding='utf-8') as f:
        for line in f:
            rec = json.loads(line)
            records.append(rec)
            energies.append(rec["energy_ev"])

    print("Deriving kinematic velocities and building scramble control...")
    
    # Create a scrambled copy of the energies
    scrambled_energies = energies.copy()
    random.shuffle(scrambled_energies)

    with open(out_real, 'w', encoding='utf-8') as f_real, \
         open(out_scramble, 'w', encoding='utf-8') as f_scr:
        
        for i, rec in enumerate(records):
            # 1. Real Record
            real_rec = rec.copy()
            real_rec["domain"] = "electron_auger_kinematic"
            real_rec["velocity_ms"] = VELOCITY_CONST * math.sqrt(real_rec["energy_ev"])
            f_real.write(json.dumps(real_rec) + '\n')

            # 2. Scramble Record (Same element/transition, randomized energy)
            scr_rec = rec.copy()
            scr_rec["domain"] = "electron_auger_scramble_ctrl"
            scr_rec["energy_ev"] = scrambled_energies[i]
            scr_rec["velocity_ms"] = VELOCITY_CONST * math.sqrt(scrambled_energies[i])
            scr_rec["entity_id"] = f"{scr_rec['entity_id']}_scramble"
            f_scr.write(json.dumps(scr_rec) + '\n')

    print(f"[OK] Real lake written to: {out_real}")
    print(f"[OK] Scramble lake written to: {out_scramble}")

if __name__ == "__main__":
    process_auger()