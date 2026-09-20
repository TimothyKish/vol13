#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
anchor_stability_check.py  —  Third-anchor stability diagnostic.

Per Mondy's ruling: the third gate anchor must be (a) z well above +5 on the
CURRENT engine, (b) the SAME register across at least two volumes (stability),
and (c) physically independent of stellar velocity and protein geometry.

Because the Sister Papers engine is checksum-identical to the Vol 11 engine
(engine_version.py fingerprint verified), a candidate domain scored here and
matching its published Vol 11 register is a genuine same-engine reproduction —
the strongest form of the stability criterion.

This script reads the current z_scores_master.json and, for each candidate
domain, reports:
  - peak register and z on the CURRENT engine
  - whether it clears STRONG (z >= 5)
  - whether its peak matches the EXPECTED (published Vol 11) register
  - a PASS/FAIL against all three of Mondy's criteria

It does NOT score lakes itself — it reads what the engine has already scored.
So the workflow is: port + run the candidate lakes through the engine first
(so they appear in z_scores_master.json), THEN run this to read the verdict.

Run from engine dir:  python anchor_stability_check.py
"""

import json
import os

ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIGS_DIR = os.path.join(ENGINE_DIR, "..", "configs")
LEDGER_PATH = os.path.join(ENGINE_DIR, "..", "lakes", "unified", "z_scores_master.json")
STRONG = 5.0

# Candidate third anchors, with their EXPECTED (published Vol 11) register and
# their independence status vs the two locked anchors (stellar velocity, protein).
# expected_N is what the published record says; the check confirms the current
# engine reproduces it.
CANDIDATES = [
    {"domain": "nuclear_binding", "expected_N": 21, "independent": True,
     "note": "q4_nuclear, AME2020 binding energy, prediction P21"},
    {"domain": "galactic",        "expected_N": 21, "independent": True,
     "note": "g1_galaxy_kinematics, SDSS vdisp, sector-normalized (uses stored scalar_kls)"},
]

RESERVED = {"subnuclear"}  # Mondy: reserved as the 2D positive control


def load_registers():
    with open(os.path.join(CONFIGS_DIR, "harmonic_targets.json"), "r", encoding="utf-8") as f:
        return json.load(f)["registers"]


def load_ledger():
    if not os.path.exists(LEDGER_PATH):
        return None
    with open(LEDGER_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def peak(cz, registers):
    i = max(range(len(cz)), key=lambda k: cz[k])
    return registers[i], cz[i]


def z_at(cz, N, registers):
    if N not in registers:
        return None
    i = registers.index(N)
    return cz[i] if i < len(cz) else None


def main():
    print("=" * 70)
    print("   THIRD-ANCHOR STABILITY CHECK  (Mondy's 3 criteria, current engine)")
    print("=" * 70)
    ledger = load_ledger()
    if ledger is None:
        print(f"  [!] Ledger not found: {LEDGER_PATH}")
        return
    registers = load_registers()
    present = list(ledger.keys())
    print(f"  Domains scored in current engine ledger: {present}\n")

    shortlist = []
    for c in CANDIDATES:
        dom, expN = c["domain"], c["expected_N"]
        print(f"[{dom}]  (expected {expN}/pi — {c['note']})")
        if dom in RESERVED:
            print(f"    RESERVED — do not use as gate anchor (Q5 dimensionality control).\n")
            continue
        if dom not in ledger:
            print(f"    NOT IN LEDGER — port this lake and score it on the engine first,")
            print(f"    then re-run this check. Cannot adjudicate an unscored domain.\n")
            continue
        cz = ledger[dom]["chaos_z"]
        pkN, pkZ = peak(cz, registers)
        zexp = z_at(cz, expN, registers)

        crit_a = pkZ >= STRONG                          # strong on current engine
        crit_b = (pkN == expN)                          # reproduces published register
        crit_c = c["independent"]                       # physically independent

        print(f"    current engine peak : {pkN}/pi  z={pkZ:+.2f}")
        print(f"    z at expected {expN}/pi : {zexp:+.2f}" if zexp is not None else "    expected register not in family")
        print(f"    (a) STRONG (z>=5)        : {'PASS' if crit_a else 'FAIL'}")
        print(f"    (b) register stable      : {'PASS' if crit_b else f'FAIL (peak {pkN}/pi != expected {expN}/pi)'}")
        print(f"    (c) independent          : {'PASS' if crit_c else 'FAIL'}")
        verdict = crit_a and crit_b and crit_c
        print(f"    -> {'QUALIFIES as third anchor' if verdict else 'does not qualify'}\n")
        if verdict:
            shortlist.append((dom, pkN, pkZ))

    print("=" * 70)
    print("   SHORTLIST FOR MONDY")
    print("=" * 70)
    if shortlist:
        for dom, N, z in sorted(shortlist, key=lambda t: -t[2]):
            print(f"  {dom:22} {N}/pi  z={z:+.2f}   (STRONG, stable, independent)")
        print(f"\n  Strongest qualifying: {shortlist[0][0]} at {shortlist[0][1]}/pi")
    else:
        print("  No candidate in the current ledger qualifies.")
        print("  Either port + score the candidate lakes (nuclear_binding, galactic vdisp)")
        print("  through the engine first, or consider Mondy's Branch B (two-anchor gate).")

    out = os.path.join(ENGINE_DIR, "anchor_stability_result.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"present": present, "shortlist": shortlist}, f, indent=2)
    print(f"\n  Written: {out}")


if __name__ == "__main__":
    main()