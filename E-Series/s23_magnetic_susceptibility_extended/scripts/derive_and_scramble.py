"""
KishLattice Sovereign Lake Derivation & Scramble
Target: s23 Magnetic Susceptibility Extended
Action: Generates Scramble twins and pushes all four files to the master engine inbox.
"""
import json
import os
import random

def process_sublake(in_name, out_real_name, out_scr_name, base_domain):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    in_path = os.path.join(script_dir, "..", "lake", "inputs_promoted", in_name)
    
    # Path to master KishLattice inputs_promoted
    master_promoted_dir = os.path.join(script_dir, "..", "..", "..", "lakes", "inputs_promoted")
    
    out_real = os.path.join(master_promoted_dir, out_real_name)
    out_scramble = os.path.join(master_promoted_dir, out_scr_name)

    records, chis = [], []
    if not os.path.exists(in_path): return

    with open(in_path, 'r', encoding='utf-8') as f:
        for line in f:
            rec = json.loads(line)
            records.append(rec)
            chis.append(rec["klghs_abs_chi"])

    scrambled_chis = chis.copy()
    random.shuffle(scrambled_chis)

    with open(out_real, 'w', encoding='utf-8') as f_real, open(out_scramble, 'w', encoding='utf-8') as f_scr:
        for i, rec in enumerate(records):
            # Real
            f_real.write(json.dumps(rec) + '\n')

            # Scramble
            scr_rec = rec.copy()
            scr_rec["domain"] = f"{base_domain}_scramble"
            scr_rec["klghs_abs_chi"] = scrambled_chis[i]
            scr_rec["entity_id"] = f"{scr_rec['entity_id']}_scramble"
            f_scr.write(json.dumps(scr_rec) + '\n')

def run_all():
    print("Deriving scramble controls and pushing to master ledger...")
    # NOTE: Enforcing the _promoted.jsonl suffix on the output!
    process_sublake("s23_dia_promoted.jsonl", "L_susceptibility_dia_promoted.jsonl", "L_susceptibility_dia_scramble_promoted.jsonl", "electron_dia_susceptibility")
    process_sublake("s23_para_promoted.jsonl", "L_susceptibility_para_promoted.jsonl", "L_susceptibility_para_scramble_promoted.jsonl", "electron_para_susceptibility")
    print("[OK] Real and Scramble Susceptibility lakes pushed to master inputs_promoted.")

if __name__ == "__main__":
    run_all()