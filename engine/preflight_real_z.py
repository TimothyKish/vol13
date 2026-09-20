#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
preflight_real_z.py  —  Anchor viability audit for the phase-scramble gate.

Reads z_scores_master.json via the shared ledger_lib (array-indexed by register),
and for each candidate anchor reports:
  - the z at its CONFIGURED register
  - the register where it ACTUALLY peaks
  - a MISMATCH flag if those differ
  - a STRONG/MODERATE/NULL verdict at the configured register

This is the falsifiable audit artifact. It makes no anchor decisions — it prints
the evidence so the decision goes to Mondy with the terminal output in hand.

Run from the engine dir:  python preflight_real_z.py
Writes: preflight_real_z_result.json  (for the audit trail / git)
"""

import json
import os
import ledger_lib as L

ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIGS_DIR = os.path.join(ENGINE_DIR, "..", "configs")
LEDGER_PATH = os.path.join(ENGINE_DIR, "..", "lakes", "unified", "z_scores_master.json")
STRONG, MODERATE = 5.0, 3.0

# Candidate anchors and the register each is EXPECTED to lock at.
# These expectations come from the pre-registration / Mondy's ruling; the script
# checks them against reality rather than trusting them.
CANDIDATES = [
    {"domain": "stellar_kinematic", "expected_N": 16, "role": "confirmed anchor 1"},
    {"domain": "biology_backbone",  "expected_N": 25, "role": "confirmed anchor 2"},
    {"domain": "orbital",           "expected_N": 15, "role": "third anchor (Mondy: 15/pi)"},
]


def verdict(z):
    if z is None:
        return "NOT FOUND"
    if z >= STRONG:
        return f"STRONG (z={z:.2f})"
    if z >= MODERATE:
        return f"MODERATE (z={z:.2f}) — below {STRONG}"
    return f"NULL/weak (z={z:.2f})"


def main():
    print("=" * 64)
    print("   PRE-FLIGHT ANCHOR AUDIT  (ledger-indexed, falsifiable)")
    print("=" * 64)

    ledger = L.load_ledger(LEDGER_PATH)
    if ledger is None:
        print(f"  [!] Ledger not found: {LEDGER_PATH}")
        return
    registers = L.load_registers(CONFIGS_DIR)
    print(f"  register order: {registers}")
    print(f"  domains in ledger: {list(ledger.keys())}\n")

    results = {}
    for c in CANDIDATES:
        dom, expN = c["domain"], c["expected_N"]
        z_at_expected = L.z_at_register(ledger, dom, expN, registers)
        peakN, peakZ = L.peak_register(ledger, dom, registers)
        profile = L.full_profile(ledger, dom, registers)
        top6 = ", ".join(f"{N}/pi:{z:+.1f}" for N, z in profile[:6])

        mismatch = (peakN != expN) and (peakN is not None)

        print(f"[{dom}]  ({c['role']})")
        print(f"    configured register : {expN}/pi -> {verdict(z_at_expected)}")
        print(f"    ACTUAL peak         : {peakN}/pi (z={peakZ:+.2f})" if peakN else "    ACTUAL peak: none")
        if mismatch:
            print(f"    ***  MISMATCH: peak is {peakN}/pi, not the configured {expN}/pi  ***")
        print(f"    top registers       : {top6}")
        print()

        results[dom] = {
            "configured_N": expN,
            "z_at_configured": z_at_expected,
            "peak_N": peakN,
            "peak_z": peakZ,
            "mismatch": mismatch,
            "strong_at_configured": (z_at_expected is not None and z_at_expected >= STRONG),
            "strong_at_peak": (peakZ is not None and peakZ >= STRONG),
        }

    # Summary for the escalation
    print("=" * 64)
    print("   AUDIT SUMMARY  (take this to Mondy)")
    print("=" * 64)
    for dom, r in results.items():
        line = f"  {dom:20} cfg {r['configured_N']}/pi z={r['z_at_configured']:.2f}" \
               if r["z_at_configured"] is not None else f"  {dom:20} cfg {r['configured_N']}/pi z=NONE"
        line += f" | peak {r['peak_N']}/pi z={r['peak_z']:.2f}"
        if r["mismatch"]:
            line += "  <-- MISMATCH"
        print(line)

    print()
    n_clean = sum(1 for r in results.values() if r["strong_at_configured"] and not r["mismatch"])
    print(f"  anchors STRONG at configured register with no mismatch: {n_clean}/3")
    any_mismatch = any(r["mismatch"] for r in results.values())
    if any_mismatch:
        print("  >> At least one anchor peaks at a different register than configured.")
        print("     This is a REFEREE decision: test at configured register, at the")
        print("     true peak, or substitute the anchor. Do not resolve in script.")

    out = os.path.join(ENGINE_DIR, "preflight_real_z_result.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Audit artifact written: {out}")


if __name__ == "__main__":
    main()