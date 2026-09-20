#!/usr/bin/env python3
# ==============================================================================
# SCRIPT: validate_common_support.py
# GATE ITEM 3 — Erratum 4 ruling, Mondy Aurora Kish, 2026-08-23
#
# "The corrected statistic must be demonstrated to return z ~ 0 on a synthetic
#  right-skewed structureless distribution that currently returns z ~ -84. A fix
#  that has not been shown to fix the known artifact is not permitted to certify
#  anything."
#
# Standalone. Touches no lake and no config. Run before the correction is
# adopted into the engine.
#
# THE CORRECTION (ruled):
#   Exclude all records with r_p < 0.5 from BOTH arms at every register, and
#   report the excluded fraction per domain per register. The cut sits at the
#   anti-node, maximally distant from any lock window, so it neither adds nor
#   removes locked records preferentially.
#
# FOUR TESTS, all pre-registered here before execution:
#   T1  right-skewed, NO structure  -> current: strongly negative. corrected: ~0
#   T2  right-skewed, PLANTED lock  -> corrected must STILL DETECT it
#   T3  uniform, no structure       -> both ~0 (no regression)
#   T4  uniform, PLANTED lock       -> both detect (no regression)
#
# T2 is the half that matters most. A "fix" that suppresses the artifact by
# suppressing all sensitivity is not a fix.
# ==============================================================================

import math
import numpy as np

K_GEO = 16.0 / math.pi
LOG_K = math.log(K_GEO)
CONTAINER = 24
THRESHOLD = 0.05
N_TRIALS = 200
N_REC = 200_000
PLANT_REGISTER = 19          # deliberately NOT 16/pi
PLANT_FRACTION = 0.15
RNG = np.random.default_rng(20260823)


def target(N):
    return N / math.pi


def floor_scalar(N):
    return 0.5 * target(N) / CONTAINER


# ---------------------------------------------------------------- statistics
def lock_rate_current(s, N):
    """Vol 11.1 statistic: clamp to 1, no support restriction."""
    rp = (s / target(N)) * CONTAINER
    nearest = np.maximum(1, np.round(rp))
    return float(np.mean(np.abs(rp - nearest) < THRESHOLD))


def lock_rate_corrected(s, N):
    """Common-support: drop r_p < 0.5 before scoring. Returns (rate, kept_frac)."""
    rp = (s / target(N)) * CONTAINER
    keep = rp >= 0.5
    if keep.sum() == 0:
        return 0.0, 0.0
    rpk = rp[keep]
    nearest = np.round(rpk)
    return float(np.mean(np.abs(rpk - nearest) < THRESHOLD)), float(keep.mean())


def z_score(s, N, corrected):
    lo, hi = float(s.min()), float(s.max())
    n = len(s)
    if corrected:
        real, kept = lock_rate_corrected(s, N)
    else:
        real, kept = lock_rate_current(s, N), 1.0
    null = np.empty(N_TRIALS)
    for t in range(N_TRIALS):
        c = RNG.uniform(lo, hi, n)
        null[t] = lock_rate_corrected(c, N)[0] if corrected else lock_rate_current(c, N)
    m, sd = float(null.mean()), float(null.std())
    return ((real - m) / sd if sd > 0 else 0.0), real, m, kept


# ------------------------------------------------------------------ datasets
def skewed_no_structure(n):
    """Right-skewed, structureless. Tuned so ~27% falls below the 16/pi floor,
    matching the measured s2_stellar_kinematics profile."""
    v = RNG.lognormal(mean=0.35, sigma=1.6, size=n)
    return np.log1p(v) / LOG_K


def plant(s, N, frac):
    """Move `frac` of records onto exact nodes of register N."""
    s = s.copy()
    idx = RNG.choice(len(s), size=int(frac * len(s)), replace=False)
    per = target(N) / CONTAINER
    s[idx] = np.round(s[idx] / per) * per
    return s


def uniform_no_structure(n):
    return RNG.uniform(0.0, 4.25, n)


# ---------------------------------------------------------------------- main
def run(label, s, expect_current, expect_corrected, detect_at=None):
    print(f"\n{'='*82}\n{label}\n{'='*82}")
    fb = float(np.mean(s < floor_scalar(16)))
    print(f"  n={len(s):,}   below 16/pi floor: {fb*100:.2f}%   "
          f"range [{s.min():.4f}, {s.max():.4f}]")
    print(f"\n  {'reg':>6}{'z CURRENT':>12}{'z CORRECTED':>14}{'kept':>9}")
    print("  " + "-" * 43)
    zc, zk = {}, {}
    for N in range(4, 27):
        z0, *_ = z_score(s, N, corrected=False)
        z1, _, _, kept = z_score(s, N, corrected=True)
        zc[N], zk[N] = z0, z1
        mark = "  <== planted" if detect_at == N else ""
        print(f"  {f'{N}/pi':>6}{z0:>12.2f}{z1:>14.2f}{kept*100:>8.1f}%{mark}")

    med0 = float(np.median(list(zc.values())))
    med1 = float(np.median(list(zk.values())))
    print(f"\n  median z  current={med0:+.2f}   corrected={med1:+.2f}")
    print(f"  EXPECTED  current={expect_current}   corrected={expect_corrected}")

    if detect_at is not None:
        ok = zk[detect_at] > 5 and zk[detect_at] == max(zk.values())
        print(f"  planted register {detect_at}/pi under correction: z={zk[detect_at]:+.2f}"
              f"  peak={max(zk, key=zk.get)}/pi  -> {'DETECTED' if ok else '*** LOST ***'}")
        return ok
    ok = abs(med1) < 5.0
    print(f"  -> {'PASS' if ok else '*** FAIL ***'}  (|median corrected z| < 5)")
    return ok


def main():
    print("=" * 82)
    print("GATE ITEM 3 — TWO-SIDED VALIDATION OF THE COMMON-SUPPORT CORRECTION")
    print("=" * 82)
    print("  Pre-registered expectations, fixed before this run:")
    print("    T1 skewed / no structure : current strongly NEGATIVE, corrected ~0")
    print("    T2 skewed / planted lock : corrected must STILL DETECT the plant")
    print("    T3 uniform / no structure: both ~0")
    print("    T4 uniform / planted lock: both detect")
    print("  A fix that passes T1 but fails T2 has removed sensitivity, not artifact.")

    r = {}
    s1 = skewed_no_structure(N_REC)
    r["T1"] = run("T1 — RIGHT-SKEWED, NO STRUCTURE (the known artifact)",
                  s1, "strongly negative", "~0")
    r["T2"] = run(f"T2 — RIGHT-SKEWED, PLANTED LOCK AT {PLANT_REGISTER}/pi",
                  plant(s1, PLANT_REGISTER, PLANT_FRACTION), "masked by artifact",
                  "detects plant", detect_at=PLANT_REGISTER)
    s3 = uniform_no_structure(N_REC)
    r["T3"] = run("T3 — UNIFORM, NO STRUCTURE (regression check)", s3, "~0", "~0")
    r["T4"] = run(f"T4 — UNIFORM, PLANTED LOCK AT {PLANT_REGISTER}/pi (regression check)",
                  plant(s3, PLANT_REGISTER, PLANT_FRACTION), "detects", "detects",
                  detect_at=PLANT_REGISTER)

    print("\n" + "=" * 82)
    print("  VERDICT")
    print("=" * 82)
    for k, v in r.items():
        print(f"    {k}: {'PASS' if v else 'FAIL'}")
    if all(r.values()):
        print("\n  CORRECTION VALIDATED. It removes the known artifact without")
        print("  removing sensitivity to planted structure. Cleared for adoption.")
    else:
        print("\n  NOT VALIDATED. Do not adopt. Do not certify any result with it.")
    print("=" * 82 + "\n")


if __name__ == "__main__":
    main()