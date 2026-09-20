#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import numpy as np

P4_FILE = "../lakes/inputs_promoted/p4_ttv_promoted.jsonl"
DATA_KEY = "ttv_absolute_minutes"
K_GEO = 16.0 / np.pi
REGISTERS_N = list(range(5, 27))

def main():
    if not os.path.exists(P4_FILE):
        print(f"[!] Not found: {P4_FILE}")
        return

    vals, bad = [], 0
    with open(P4_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try: rec = json.loads(line)
            except json.JSONDecodeError: bad += 1; continue
            
            v = rec.get(DATA_KEY)
            if v is not None:
                try: vals.append(float(v))
                except: bad += 1

    if not vals:
        print(f"[!] No values under key '{DATA_KEY}'.")
        return

    v = np.asarray(vals, dtype=float)
    s = np.log(1.0 + np.abs(v)) / np.log(K_GEO)

    print("=" * 60)
    print("   TTV FLOOR-SMEAR DIAGNOSTIC  (p4_ttv anchor viability)")
    print("=" * 60)
    print(f"  records loaded         : {len(v):,}  (bad lines: {bad})")
    print(f"  RAW {DATA_KEY}")
    print(f"    min / median / max   : {v.min():.4g} / {np.median(v):.4g} / {v.max():.4g}")
    print(f"    mean / std           : {v.mean():.4g} / {v.std():.4g}")
    
    frac_sub1 = np.mean(v < 1.0)
    print(f"    fraction < 1.0 min   : {frac_sub1:.1%}")

    print("\n  SCALAR  s = log(1+|x|)/log(k_geo)")
    print(f"    scalar span (max-min): {s.max() - s.min():.4f}")

    reg16 = 16 / np.pi
    ratio = s / reg16
    frac = ratio - np.floor(ratio)
    first_cell = np.mean(frac < (1.0 / 24)) 
    print(f"    frac in 1st node cell of 16/pi : {first_cell:.1%}  (uniform would be ~4.2%)\n")

    print("=" * 60)
    floored = frac_sub1 > 0.5 or (s.max() - s.min()) < reg16 or first_cell > 0.25
    marginal = (0.3 < frac_sub1 <= 0.5) or first_cell > 0.10
    
    if floored:
        print("  VERDICT: FLOOR-SMEARED  — p4_ttv is NOT a viable gate anchor.")
        print("  RECOMMEND: escalate to Mondy to substitute a cleaner kinematic anchor.")
    elif marginal:
        print("  VERDICT: MARGINAL — p4_ttv has partial floor contamination.")
    else:
        print("  VERDICT: VIABLE — p4_ttv scalars span the register grid adequately.")
    print("=" * 60)

if __name__ == "__main__":
    main()