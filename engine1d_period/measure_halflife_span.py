#!/usr/bin/env python3
# ==============================================================================
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC. FOUNDER: Timothy John Kish
# Open for scientific testing / peer review. Cite "KishLattice 16/pi Initiative".
# ==============================================================================
#
# measure_halflife_span.py  --  Mondy Item 8, the highest-value measurement left.
#
# QUESTION: is nuclear half-life the ONE physical observable that carries the
# 6.41 EFFECTIVE decades needed to resolve 16/pi -- or does its bulk cluster
# by decay mode into a span as narrow as every other domain?
#
# Half-life physically spans ~10^-23 s to ~10^24 s (min-max ~47 decades). But
# min-max is exactly the tail-inflation trap the anchor fell into. This script
# measures the EFFECTIVE span (central mass) at the 95/99/99.9 bands Mondy
# ruled, and reports the register each band can resolve.
#
# It does NOT score for a lock. It answers one question: how many EFFECTIVE
# decades does this observable actually carry, and therefore what is the
# HIGHEST register it could ever resolve on honest support.
#
# Reads q5_decay (the promoted half-life lake). Field: half_life_seconds
# (or _raw_payload variants). Positive values only; ln at test time.
#
# Run:  python engine1d_period/measure_halflife_span.py [path_to_lake.jsonl]
# ==============================================================================
import json, math, sys
from pathlib import Path
import numpy as np

K = math.log(16/math.pi)
def decades_required(N): return N*N*0.025036   # Mondy's effective-decades law

def find_lake():
    here = Path(__file__).resolve().parent.parent
    for pat in ("*q5_decay*promoted*.jsonl", "*q5_decay*logified*.jsonl",
                "*half*life*promoted*.jsonl", "*decay*promoted*.jsonl"):
        for base in (here/"lakes"/"inputs_promoted",
                     here/"lakes1d_period"/"inputs_promoted",
                     here/"lakes1d_period"/"logified"):
            hits = list(base.glob(pat)) if base.exists() else []
            if hits: return hits[0]
    return None

def extract(rec):
    for k in ("half_life_seconds","klghs_x","klghs_lnx","half_life_s","t_half_s","value"):
        if k in rec:
            try:
                v = float(rec[k])
                return math.log(v) if (k != "klghs_lnx" and v > 0) else (v if k=="klghs_lnx" else None)
            except (ValueError, TypeError):
                pass
    for cont in ("_raw_payload","meta"):
        sub = rec.get(cont, {})
        if isinstance(sub, dict):
            for k in ("half_life_seconds","half_life_s","t_half_s","value"):
                if k in sub:
                    try:
                        v = float(sub[k])
                        if v > 0: return math.log(v)
                    except (ValueError, TypeError):
                        pass
    return None

def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else find_lake()
    if not path or not path.exists():
        print("[!] half-life lake not found. Pass the path explicitly:")
        print("    python engine1d_period/measure_halflife_span.py <lake.jsonl>")
        sys.exit(2)

    lnx = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line: continue
        v = extract(json.loads(line))
        if v is not None and math.isfinite(v):
            lnx.append(v)
    lnx = np.array(lnx)
    if len(lnx) < 100:
        print(f"[!] only {len(lnx)} usable records from {path.name}; check the field name.")
        sys.exit(2)

    print("="*70)
    print("  NUCLEAR HALF-LIFE -- EFFECTIVE SPAN  (Mondy Item 8)")
    print("="*70)
    print(f"  lake: {path.name}")
    print(f"  n = {len(lnx):,}")
    raw = float(lnx.max() - lnx.min())
    print(f"  RAW min-max span: {raw:.2f} nat  ({raw/math.log(10):.1f} decades)")
    print(f"  raw bounds: {math.exp(lnx.min()):.2e} s .. {math.exp(lnx.max()):.2e} s\n")

    print(f"  {'band':>6}{'eff span':>11}{'eff dec':>9}{'highest N resolvable':>22}")
    highest_any = 0
    for q, pct in ((0.025,95),(0.005,99),(0.0005,99.9)):
        lo, hi = np.quantile(lnx, [q, 1-q])
        eff = float(hi - lo); dec = eff/math.log(10)
        # highest register whose effective-decade requirement this span meets
        hiN = 0
        for N in range(4,27):
            if dec >= decades_required(N): hiN = N
        highest_any = max(highest_any, hiN)
        tag = f"{hiN}/pi" if hiN else "none (<4/pi)"
        print(f"  {pct:>5}%{eff:>11.2f}{dec:>9.1f}{tag:>22}")

    print("\n  decades required by register (Mondy's law, effective):")
    for N in (10,12,13,14,15,16):
        print(f"    {N}/pi needs {decades_required(N):.1f} eff decades")

    print("\n" + "="*70)
    if highest_any >= 16:
        print("  VERDICT: half-life carries >= 6.41 EFFECTIVE decades in its BULK.")
        print("  This is the ONE observable that could resolve 16/pi on honest")
        print("  support. It becomes the priority lake for the register programme.")
    elif highest_any >= 13:
        print(f"  VERDICT: half-life resolves up to {highest_any}/pi on effective")
        print("  support -- the widest in the survey, but SHORT of 16/pi. The")
        print("  register programme is testable at mid registers, not at 16/pi.")
    elif highest_any >= 4:
        print(f"  VERDICT: even half-life's BULK resolves only to {highest_any}/pi.")
        print("  Its 47-decade range is tail; the mass clusters by decay mode.")
        print("  Item 8 answer: NO single-population observable reaches 16/pi.")
        print("  The register programme cannot be tested at 16/pi by any data.")
    else:
        print("  VERDICT: half-life bulk resolves nothing -- extreme mode clustering.")
    print("="*70)
    print("\n  NOTE: this measures dynamic range only. It is NOT a lock test and")
    print("  makes no claim about whether half-life locks at any register.")

if __name__ == "__main__":
    main()