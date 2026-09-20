#!/usr/bin/env python3
# ==============================================================================
# sweep_comprehensive_master.py  --  Full-Spectrum Period Engine Sweep
# Scans the 22.3M-record comprehensive master lake across all pre-registered 
# harmonic registers ($4/\pi$ to $26/\pi$).
# ==============================================================================
import json
import math
from pathlib import Path
import numpy as np
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "engine1d_period"))
from periodogram import load_registers_and_kgeo, scan_domain

LOGIFIED_DIR = ROOT / "lakes1d_period" / "logified"
MASTER_LOGIFIED = LOGIFIED_DIR / "L_comprehensive_master_logified.jsonl"

def main():
    if not MASTER_LOGIFIED.exists():
        print(f"[!] Master logified lake not found at {MASTER_LOGIFIED}. Run logify.py first.")
        sys.exit(1)

    print(f"[*] Loading logified master records from {MASTER_LOGIFIED.name}...")
    lnx_list = []
    with open(MASTER_LOGIFIED, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if "klghs_lnx" in rec:
                    lnx_list.append(float(rec["klghs_lnx"]))
            except Exception:
                continue

    lnx = np.array(lnx_list)
    span = float(lnx.max() - lnx.min())
    print(f"[*] Loaded {len(lnx):,} valid natural log values.")
    print(f"[*] Log-span: {span:.2f} units (~{span/math.log(10):.2f} decades across 81 domains).")

    registers, container, kg = load_registers_and_kgeo()
    print(f"[*] Scanning {len(registers)} registers from {registers[0]}/pi to {registers[-1]}/pi...\n")

    rows, best = scan_domain(lnx, kg, container, registers)

    print("=" * 72)
    print(f" {'REGISTER':<10} | {'STATUS':<20} | {'M/N':<8} | {'EXCESS':<10} | {'N_INDEP'}")
    print("-" * 72)
    for r in rows:
        reg_str = f"{r['N']}/pi"
        status = r['status']
        mn = f"{r['MN']:.2f}" if 'MN' in r else "N/A"
        exc = f"{r['excess']:.2f}" if 'excess' in r and not math.isnan(r['excess']) else "N/A"
        nind = f"{r['n_indep']:.1f}" if 'n_indep' in r else "N/A"
        print(f" {reg_str:<10} | {status:<20} | {mn:<8} | {exc:<10} | {nind}")
    print("=" * 72)

    if best:
        print(f"\n[+] PEAK WINNER: Register {best['N']}/pi with Excess = {best['excess']:.2f} (M/N = {best['MN']:.2f})")
    else:
        print("\n[!] No scoreable register found.")

if __name__ == "__main__":
    main()