import json
import os
import random
import math

def process_conversion():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    in_path = os.path.join(script_dir, "..", "lake", "inputs_promoted", "s22_conversion_electrons_promoted.jsonl")
    
    # Writing directly to the main engine lakes folder
    out_real = os.path.join(script_dir, "..", "..", "..", "lakes", "inputs_promoted", "L_conversion_electrons_promoted.jsonl")
    out_scramble = os.path.join(script_dir, "..", "..", "..", "lakes", "inputs_promoted", "L_conversion_scramble_ctrl_promoted.jsonl")

    VELOCITY_CONST = 593096.9

    records, energies = [], []
    with open(in_path, 'r', encoding='utf-8') as f:
        for line in f:
            rec = json.loads(line)
            records.append(rec)
            energies.append(rec["energy_ev"])

    scrambled_energies = energies.copy()
    random.shuffle(scrambled_energies)

    with open(out_real, 'w', encoding='utf-8') as f_real, \
         open(out_scramble, 'w', encoding='utf-8') as f_scr:
        
        for i, rec in enumerate(records):
            # Real Record
            real_rec = rec.copy()
            real_rec["velocity_ms"] = VELOCITY_CONST * math.sqrt(real_rec["energy_ev"])
            f_real.write(json.dumps(real_rec) + '\n')

            # Scramble Record
            scr_rec = rec.copy()
            scr_rec["domain"] = "electron_conversion_scramble_ctrl"
            scr_rec["energy_ev"] = scrambled_energies[i]
            scr_rec["velocity_ms"] = VELOCITY_CONST * math.sqrt(scrambled_energies[i])
            scr_rec["entity_id"] = f"{scr_rec['entity_id']}_scramble"
            f_scr.write(json.dumps(scr_rec) + '\n')

    print(f"[OK] Real lake written to: {out_real}")
    print(f"[OK] Scramble lake written to: {out_scramble}")

if __name__ == "__main__":
    process_conversion()