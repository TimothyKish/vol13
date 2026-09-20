#!/usr/bin/env python3
# ==============================================================================
# SCRIPT: floor_fraction_s2.py
# GATE ITEM 1 — Erratum 4 ruling, Mondy Aurora Kish, 2026-08-23
#
# Measures ONE thing: how much of s2_stellar_kinematics sits at or below the
# lock floor in raw form.
#
# This script deliberately does NOT compute sector offsets, does not touch the
# P_sector_shift_artifact prediction, and does not evaluate any register
# alignment. Per the ruling, the floor fraction is reported on its own so that
# it cannot be accused of having been steered by the mechanism it would support.
#
# PRE-REGISTERED KILL CONDITION (filed in the ruling, before this run):
#   If the fraction of records at or below the 16/pi floor is < 0.5%, the
#   Form C preprocessing-concentration mechanism is DEAD and the sector
#   arithmetic is not to be run.
#
# Reads the PROMOTED lake directly (meta.val_raw_kms), not pipeline output, so
# the measurement is independent of scalarize.py.
#
# Usage:  python scripts/floor_fraction_s2.py
# ==============================================================================

import json, math, collections
from pathlib import Path

ROOT  = Path(__file__).resolve().parents[1]
LAKE  = ROOT / "lakes" / "inputs_promoted" / "s2_stellar_kinematics_promoted.jsonl"
K_GEO = 16.0 / math.pi
LOG_K = math.log(K_GEO)
CONTAINER  = 24
REGISTERS  = list(range(4, 27))
KILL_THRESHOLD_PCT = 0.5


def scalar(v):
    return math.log(1.0 + v) / LOG_K


def floor_scalar(N):
    """Smallest scalar whose r_p reaches 0.5. Below this, nearest clamps to 1
    and the record cannot satisfy |r_p - nearest| < 0.05 at any value."""
    return 0.5 * (N / math.pi) / CONTAINER


def floor_velocity(N):
    return math.exp(floor_scalar(N) * LOG_K) - 1.0


def main():
    if not LAKE.exists():
        raise SystemExit(f"Lake not found: {LAKE}")

    print("=" * 78)
    print("GATE ITEM 1 — FLOOR FRACTION, s2_stellar_kinematics")
    print("=" * 78)
    print(f"  lake: {LAKE.name}")
    print(f"  field: meta.val_raw_kms (raw transverse velocity, km/s)")
    print(f"  k_geo = 16/pi = {K_GEO:.10f}\n")

    n = n_missing = 0
    n_zero = n_negative = 0
    below = collections.Counter()
    v_min = None
    low_bins = collections.Counter()      # velocity bins below 1 km/s
    f16 = floor_velocity(16)

    with LAKE.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            n += 1
            v = (rec.get("meta") or {}).get("val_raw_kms")
            if v is None:
                v = (rec.get("_raw_payload") or {}).get("val")
            if v is None:
                n_missing += 1
                continue
            try:
                v = float(v)
            except (TypeError, ValueError):
                n_missing += 1
                continue

            v_min = v if v_min is None else min(v_min, v)
            if v == 0.0:
                n_zero += 1
            if v < 0.0:
                n_negative += 1

            for N in REGISTERS:
                if v <= floor_velocity(N):
                    below[N] += 1

            if v < 1.0:
                low_bins[round(v, 2)] += 1

            if n % 500_000 == 0:
                print(f"    ... {n:,} records read", flush=True)

    usable = n - n_missing
    print(f"\n  records read          : {n:,}")
    print(f"  field missing         : {n_missing:,}")
    print(f"  usable                : {usable:,}")
    print(f"  minimum raw velocity  : {v_min}")
    print(f"  exactly v = 0.0       : {n_zero:,}  ({100.0*n_zero/usable:.4f}%)")
    print(f"  negative velocities   : {n_negative:,}")

    print(f"\n  {'register':>10}{'floor (km/s)':>16}{'records <= floor':>20}{'fraction':>12}")
    print("  " + "-" * 58)
    for N in REGISTERS:
        c = below[N]
        print(f"  {f'{N}/pi':>10}{floor_velocity(N):>16.6f}{c:>20,}{100.0*c/usable:>11.4f}%")

    print(f"\n  Velocity distribution below 1 km/s (0.01 km/s bins, top 12):")
    for v, c in low_bins.most_common(12):
        print(f"    v = {v:>5.2f} km/s : {c:>10,}  ({100.0*c/usable:.4f}%)")

    pct16 = 100.0 * below[16] / usable
    print("\n" + "=" * 78)
    print("  PRE-REGISTERED VERDICT (threshold filed before this run)")
    print("=" * 78)
    print(f"  16/pi floor            : {f16:.6f} km/s  (scalar {floor_scalar(16):.5f})")
    print(f"  records at/below floor : {below[16]:,}  = {pct16:.4f}%")
    print(f"  kill threshold         : {KILL_THRESHOLD_PCT}%\n")
    if pct16 < KILL_THRESHOLD_PCT:
        print("  VERDICT: MECHANISM DEAD.")
        print("  Insufficient mass at the lock floor to support Form C")
        print("  preprocessing-concentration. Do NOT run the sector arithmetic.")
        print("  The s2 collapse still stands as a finding; its cause is unexplained.")
    else:
        print("  VERDICT: MECHANISM SURVIVES THIS TEST.")
        print("  Sufficient mass at the lock floor for a sector shift to act on.")
        print("  This does NOT confirm Form C. It clears the prerequisite only.")
        print("  P_sector_shift_artifact must be filed at Zenodo before the")
        print("  sector arithmetic is run (gate item 2).")
    print("=" * 78 + "\n")


if __name__ == "__main__":
    main()