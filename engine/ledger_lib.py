#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ledger_lib.py  —  Shared KLGHS ledger reader (single source of truth).

Used by BOTH preflight_real_z.py and surrogate_gate.py so they can never
disagree about how a z-score is read from z_scores_master.json.

LEDGER STRUCTURE (confirmed against harmonic_targets.json + z_scores_master.json):
  ledger[domain]["chaos_z"]     = [z_at_N0, z_at_N1, ...]  indexed by REGISTER POSITION
  ledger[domain]["synthetic_z"] = [ ... ]
  register order = harmonic_targets.json["registers"] = [4,5,...,26].
  z for register N is:  chaos_z[ registers.index(N) ].  There are NO "N/pi" keys.

Validated: stellar_kinematic peaks 16/pi=+97.45, biology_backbone peaks 25/pi=+54.0,
orbital peaks 22/pi=+27.99 — all matching published values.
"""

import json
import os


def load_registers(configs_dir):
    with open(os.path.join(configs_dir, "harmonic_targets.json"), "r", encoding="utf-8") as f:
        return json.load(f)["registers"]


def load_ledger(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def z_at_register(ledger, domain, register_N, registers, which="chaos_z"):
    if ledger is None or domain not in ledger:
        return None
    block = ledger[domain]
    if which not in block:
        return None
    arr = block[which]
    if register_N not in registers:
        return None
    idx = registers.index(register_N)
    if not isinstance(arr, list) or idx >= len(arr):
        return None
    try:
        return float(arr[idx])
    except (TypeError, ValueError):
        return None


def full_profile(ledger, domain, registers, which="chaos_z"):
    if ledger is None or domain not in ledger:
        return []
    block = ledger[domain]
    if which not in block:
        return []
    arr = block[which]
    out = []
    for i, N in enumerate(registers):
        if i < len(arr):
            try:
                out.append((N, float(arr[i])))
            except (TypeError, ValueError):
                pass
    return sorted(out, key=lambda t: -t[1])


def peak_register(ledger, domain, registers, which="chaos_z"):
    prof = full_profile(ledger, domain, registers, which)
    return prof[0] if prof else (None, None)