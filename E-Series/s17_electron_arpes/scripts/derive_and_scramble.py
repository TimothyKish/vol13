import json, os, random

def process_arpes():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    in_path = os.path.join(script_dir, "..", "lake", "inputs_promoted", "s17_arpes_bi2se3_promoted.jsonl")
    out_real = os.path.join(script_dir, "..", "..", "..", "lakes", "inputs_promoted", "L_arpes_electrons_promoted.jsonl")
    out_scramble = os.path.join(script_dir, "..", "..", "..", "lakes", "inputs_promoted", "L_arpes_scramble_ctrl_promoted.jsonl")

    # Velocity = (hbar * k) / m_e. 
    # Conversion constant for k (1/Angstrom) to velocity (m/s) is roughly 1.157e5
    VELOCITY_CONST = 115767.0
    
    records, momenta = [], []
    with open(in_path, 'r', encoding='utf-8') as f:
        for line in f:
            rec = json.loads(line)
            records.append(rec)
            momenta.append(rec["momentum_k_inv_angstrom"])

    scrambled_momenta = momenta.copy()
    random.shuffle(scrambled_momenta)

    with open(out_real, 'w', encoding='utf-8') as f_real, open(out_scramble, 'w', encoding='utf-8') as f_scr:
        for i, rec in enumerate(records):
            # Real
            real_rec = rec.copy()
            real_rec["velocity_ms"] = VELOCITY_CONST * real_rec["momentum_k_inv_angstrom"]
            f_real.write(json.dumps(real_rec) + '\n')

            # Scramble Control
            scr_rec = rec.copy()
            scr_rec["domain"] = "electron_arpes_scramble_ctrl"
            scr_rec["momentum_k_inv_angstrom"] = scrambled_momenta[i]
            scr_rec["velocity_ms"] = VELOCITY_CONST * scrambled_momenta[i]
            scr_rec["entity_id"] = f"{scr_rec['entity_id']}_scramble"
            f_scr.write(json.dumps(scr_rec) + '\n')

    print("[OK] Real and Scramble ARPES lakes written to master inputs_promoted folder.")

if __name__ == "__main__":
    process_arpes()