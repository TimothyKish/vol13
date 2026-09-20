#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
promote.py (s16_electron_fermi_extended)
Derives v_F from E_F and generates both the REAL and SCRAMBLED sovereign lakes.
"""

import json
import os
import random
import math

IN_PATH = os.path.join(os.path.dirname(__file__), "..", "lake", "raw", "mp_fermi_raw.jsonl")
OUT_REAL = os.path.join(os.path.dirname(__file__), "..", "lake", "promoted", "L_fermi_extended_promoted.jsonl")
OUT_SCRAMBLE = os.path.join(os.path.dirname(__file__), "..", "lake", "promoted", "L_fermi_scramble_ctrl_promoted.jsonl")

# v_F = sqrt(2 * E_F / m_e)
# 1 eV = 1.60218e-19 J. m_e = 9.10938e-31 kg.
# v_F (m/s) = 593096.9 * sqrt(|E_F|)
V_F_CONSTANT = 593096.9

def main():
    if not os.path.exists(IN_PATH):
        print(f"[!] Raw file not found: {IN_PATH}")
        return

    raw_records = []
    ef_values = []
    
    with open(IN_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            rec = json.loads(line)
            raw_records.append(rec)
            ef_values.append(rec["fermi_energy_ev"])

    # Create the scrambled control list
    ef_scrambled = list(ef_values)
    random.shuffle(ef_scrambled)

    real_out = []
    scramble_out = []

    for i, rec in enumerate(raw_records):
        # REAL
        ef_real = abs(ef_values[i])
        vf_real = V_F_CONSTANT * math.sqrt(ef_real)
        
        real_rec = dict(rec)
        real_rec["fermi_velocity_ms"] = vf_real
        real_rec["klghs_natural_unit"] = "m/s"
        real_rec["klghs_transform"] = "log_standard"
        real_rec["domain"] = "electron_fermi_extended"
        real_out.append(real_rec)

        # SCRAMBLED CONTROL
        ef_scr = abs(ef_scrambled[i])
        vf_scr = V_F_CONSTANT * math.sqrt(ef_scr)
        
        scr_rec = dict(rec)
        scr_rec["fermi_energy_ev"] = ef_scr  # Replaced with scrambled
        scr_rec["fermi_velocity_ms"] = vf_scr
        scr_rec["klghs_natural_unit"] = "m/s"
        scr_rec["klghs_transform"] = "log_standard"
        scr_rec["domain"] = "electron_fermi_scramble_ctrl"
        scramble_out.append(scr_rec)

    # Write files
    os.makedirs(os.path.dirname(OUT_REAL), exist_ok=True)
    with open(OUT_REAL, 'w', encoding='utf-8') as f:
        for rec in real_out: f.write(json.dumps(rec) + "\n")
        
    with open(OUT_SCRAMBLE, 'w', encoding='utf-8') as f:
        for rec in scramble_out: f.write(json.dumps(rec) + "\n")

    print(f"[+] REAL Promoted lake: {len(real_out)} records")
    print(f"[+] SCRAMBLED Control lake: {len(scramble_out)} records")

if __name__ == "__main__":
    main()