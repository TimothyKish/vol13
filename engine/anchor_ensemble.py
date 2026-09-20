#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
anchor_ensemble.py  —  Ensemble real-z baseline for the gate anchors.

Runs the pinch stage N times (reseeding the chaos null each run) and aggregates
the per-anchor, per-register chaos z into mean +/- std. This turns the reseed
jitter observed between single runs (Gaia 15<->16, protein 25<->16 trading peaks)
from an alarming anomaly into a measured quantity.

WHY: build_pinch_table's compute_dual_z_scores uses unseeded np.random.uniform,
so each pinch run reseeds the chaos comparison. Scalarize/unify are deterministic,
so we skip them (--from pinch). Figures are wasted here, so we skip them.

Per iteration it runs:
    python run_pipeline.py --from pinch --skip-figures --no-advisory
then reads z_scores_master.json and records the chaos z at each anchor register.

Output: mean, std, min, max of chaos z per anchor register, plus how often each
anchor's register was the PEAK (the co-dominance measure). Writes a JSON artifact.

SAFETY: this rewrites z_scores_master.json each run (that is how the pinch works).
It backs up the current ledger to z_scores_master.json.ensemble_bak before starting
and restores it at the end, so the canonical ledger is preserved.

Usage:  python anchor_ensemble.py --runs 20
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import numpy as np

ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(ENGINE_DIR)
CONFIGS_DIR = os.path.join(ROOT, "configs")
LEDGER = os.path.join(ROOT, "lakes", "unified", "z_scores_master.json")
RUN_PIPELINE = os.path.join(ENGINE_DIR, "run_pipeline.py")

# The Sister Papers: Electron Duality Falsification
# ELECTRON PROBE: the register is NOT pre-specified. The scientific question is
# WHERE each lake peaks and how stably, and whether the two electron lakes peak at
# the SAME register (supports "electron = one thing") or DIFFERENT registers
# (supports "electron = multiple phenomena lumped under one label"). The nominal
# value is only a readout convenience; the peak distribution is the answer.
ANCHORS = {
    "quantum_kinematic": 16,     # L_fermi_velocity  (nominal only; peak measured)
    "quantum_transitional": 25,  # L_emission_nist   (record predicts 25/pi; peak measured)
}
ELECTRON_LAKES = ("quantum_kinematic", "quantum_transitional")


def load_registers():
    with open(os.path.join(CONFIGS_DIR, "harmonic_targets.json"), "r", encoding="utf-8") as f:
        return json.load(f)["registers"]


def read_ledger_z(registers):
    """Return {domain: {'peak_N':N, 'z_at_anchor':z, 'full':[...]}} for the anchors."""
    with open(LEDGER, "r", encoding="utf-8") as f:
        led = json.load(f)
    out = {}
    for dom, anchorN in ANCHORS.items():
        if dom not in led:
            out[dom] = None
            continue
        cz = led[dom]["chaos_z"]
        peak_i = max(range(len(cz)), key=lambda i: cz[i])
        peak_N = registers[peak_i]
        idx = registers.index(anchorN)
        z_at = cz[idx] if idx < len(cz) else None
        out[dom] = {"peak_N": peak_N, "z_at_anchor": z_at}
    return out


def run_pinch_once():
    """Run only the pinch stage, no figures, no advisory. Returns True on success."""
    cmd = [sys.executable, RUN_PIPELINE, "--from", "pinch", "--skip-figures", "--no-advisory"]
    r = subprocess.run(cmd, cwd=ENGINE_DIR, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"    [!] pinch run failed:\n{(r.stderr or r.stdout)[:500]}")
        return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=20, help="number of pinch iterations")
    args = ap.parse_args()

    registers = load_registers()

    # backup the canonical ledger
    backup = LEDGER + ".ensemble_bak"
    if os.path.exists(LEDGER):
        shutil.copy2(LEDGER, backup)
        print(f"Backed up ledger -> {backup}")

    # collectors
    z_at_anchor = {d: [] for d in ANCHORS}
    peak_hits   = {d: {} for d in ANCHORS}   # register -> count of times it was peak

    print(f"\nRunning {args.runs} pinch iterations (reseed each). "
          f"Skipping scalarize/unify/figures.\n")

    completed = 0
    for i in range(args.runs):
        print(f"[run {i+1}/{args.runs}] pinch ...", end=" ", flush=True)
        if not run_pinch_once():
            print("FAILED — stopping ensemble.")
            break
        snap = read_ledger_z(registers)
        line = []
        for dom, info in snap.items():
            if info is None:
                line.append(f"{dom}:MISSING")
                continue
            z_at_anchor[dom].append(info["z_at_anchor"])
            pk = info["peak_N"]
            peak_hits[dom][pk] = peak_hits[dom].get(pk, 0) + 1
            line.append(f"{dom[:12]}@{ANCHORS[dom]}={info['z_at_anchor']:.1f}(pk{pk})")
        completed += 1
        print("  ".join(line))

    # restore canonical ledger
    if os.path.exists(backup):
        shutil.copy2(backup, LEDGER)
        print(f"\nRestored canonical ledger from {backup}")

    # aggregate
    print("\n" + "=" * 72)
    print(f"   ANCHOR ENSEMBLE  ({completed} runs)")
    print("=" * 72)
    results = {}
    for dom, anchorN in ANCHORS.items():
        zs = [z for z in z_at_anchor[dom] if z is not None]
        if not zs:
            print(f"  {dom:20} @ {anchorN}/pi : no data"); continue
        arr = np.array(zs)
        hits = peak_hits[dom]
        total = sum(hits.values())
        peak_frac = {f"{k}/pi": f"{v}/{total}" for k, v in sorted(hits.items(), key=lambda t:-t[1])}
        # fraction of runs where the ANCHOR register was also the peak
        anchor_peak_frac = hits.get(anchorN, 0) / total if total else 0.0
        print(f"\n  {dom} @ {anchorN}/pi")
        print(f"    real chaos-z: mean={arr.mean():.2f}  std={arr.std(ddof=1):.2f}  "
              f"min={arr.min():.2f}  max={arr.max():.2f}")
        # find the register that is MOST OFTEN the peak, and how dominant it is
        top_peak_N = max(hits, key=hits.get) if hits else None
        top_peak_frac = hits.get(top_peak_N, 0) / total if total else 0.0
        print(f"    anchor register {anchorN}/pi was the peak in {anchor_peak_frac*100:.0f}% of runs")
        print(f"    most-frequent peak: {top_peak_N}/pi ({top_peak_frac*100:.0f}% of runs)")
        print(f"    peak distribution: {peak_frac}")
        # ELECTRON PROBE readout: report the dominant peak and its stability.
        # No "misaligned" verdict here -- there is no pre-chosen correct register;
        # the peak IS the measurement.
        strong = (arr.mean() - arr.std(ddof=1) >= 5.0)
        stable_peak = (top_peak_frac >= 0.60)
        if stable_peak and strong:
            print(f"    -> STABLE PEAK at {top_peak_N}/pi ({top_peak_frac*100:.0f}% of runs), stably STRONG.")
        elif stable_peak and not strong:
            print(f"    -> peak at {top_peak_N}/pi is stable but not stably STRONG (mean-1sd<5).")
        elif (not stable_peak) and strong:
            print(f"    -> STRONG but peak UNSTABLE across registers (co-dominant band): {peak_frac}")
        else:
            print(f"    -> weak and unstable -- no clear register for this lake.")
        results[dom] = {
            "anchor_N": anchorN, "mean": float(arr.mean()), "std": float(arr.std(ddof=1)),
            "min": float(arr.min()), "max": float(arr.max()),
            "anchor_peak_fraction": anchor_peak_frac,
            "most_frequent_peak_N": top_peak_N,
            "most_frequent_peak_fraction": top_peak_frac,
            "aligned": bool(top_peak_N == anchorN),
            "peak_distribution": hits,
        }

    # ================= ELECTRON QUESTION: SAME OR DIFFERENT? =================
    ek = [d for d in ELECTRON_LAKES if d in results]
    if len(ek) == 2:
        a, b = ek
        pa, pb = results[a]["most_frequent_peak_N"], results[b]["most_frequent_peak_N"]
        fa, fb = results[a]["most_frequent_peak_fraction"], results[b]["most_frequent_peak_fraction"]
        print("\n" + "=" * 72)
        print("   THE ELECTRON QUESTION: one phenomenon, or several lumped together?")
        print("=" * 72)
        print(f"   L_fermi_velocity (quantum_kinematic)  peaks {pa}/pi  ({fa*100:.0f}% stable)")
        print(f"   L_emission_nist  (quantum_transitional) peaks {pb}/pi  ({fb*100:.0f}% stable)")
        both_stable = (fa >= 0.60) and (fb >= 0.60)
        if pa == pb and both_stable:
            print(f"\n   -> SAME register ({pa}/pi), both stable. Consistent with the electron")
            print(f"      being ONE phenomenon in this coordinate. (Not proof -- Form B still open.)")
        elif pa != pb and both_stable:
            print(f"\n   -> DIFFERENT registers ({pa}/pi vs {pb}/pi), both stable. This is the")
            print(f"      candidate signature that 'electron' LUMPS distinct lattice behaviors.")
            print(f"      A real finding to pre-register and pursue -- NOT yet proof. The register")
            print(f"      difference must be shown robust to the same scrutiny protein's 16-vs-25")
            print(f"      discrepancy is getting: reseed-stable, and not a scalarization artifact.")
        else:
            print(f"\n   -> One or both peaks UNSTABLE across reseeds. No clean same/different")
            print(f"      verdict yet. Report the distributions honestly; do not force a reading.")
        print(f"\n   REMINDER: raw pinch z, not a gate. Form A (transform artifact) is closed by")
        print(f"   theorem; whatever these registers are, they are genuine phase-locks. Whether")
        print(f"   the register DIFFERENCE means distinct physics is a Form-B / interpretation")
        print(f"   question requiring its own pre-registration.")

    out = os.path.join(ENGINE_DIR, "anchor_ensemble_result.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"runs": completed, "anchors": results}, f, indent=2)
    print(f"\n  Written: {out}")
    print("\n  Take mean +/- std per anchor to Mondy as the gate's real-z baseline.")


if __name__ == "__main__":
    main()