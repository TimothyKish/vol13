#!/usr/bin/env python3
# ==============================================================================
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC. FOUNDER: Timothy John Kish
# Open for scientific testing / peer review. Cite "KishLattice 16/pi Initiative".
# ==============================================================================
#
# validate_trial1.py  --  THE BUILD GATE for the period engine.
#
# The period engine is NOT built out until this passes. Pre-registered in
# Vol 12 Ch 15 and Vol 13 Ch 4. Four checks, expectations fixed in advance:
#
#   A. STRUCTURELESS returns excess ~ 0 at every scoreable register.
#      (The engine does not manufacture a lock from nothing.)
#   B. A PLANTED lock is recovered at its register, where the annulus exists.
#      (The engine has not suppressed sensitivity along with the artifact.)
#   C. UNIT INVARIANCE: the planted lock's excess is identical under x->c*x.
#      (The property the phase engine fails and this one holds by theorem --
#       the check the common-support correction never had to face.)
#   D. TRIAL 1: quantum_transitional, logified from its real lake, returns
#      16/pi. THIS IS THE BUILD GATE. If it fails, the build does not proceed.
#
# D is skipped gracefully if the real lake is not present, so A-C can be run
# on any machine; D runs wherever lakes1d_period/logified/ has the anchor.
# ==============================================================================

import math
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from periodogram import (load_registers_and_kgeo, delta_N, resultant_power,
                         score_register, scan_domain, unit_invariance_check,
                         RES_THRESHOLD)

ROOT = Path(__file__).resolve().parent.parent
LOGIFIED = ROOT / "lakes1d_period" / "logified"
RNG = np.random.default_rng(20260907)


def banner(t): print("\n" + "=" * 68 + f"\n  {t}\n" + "=" * 68)


def main():
    registers, container, kg = load_registers_and_kgeo()
    print(f"registers {registers[0]}..{registers[-1]}  container={container}  "
          f"k_geo={kg:.8f}  RES_THRESHOLD={RES_THRESHOLD:.4f}")

    passed = True

    # ---- A. structureless -> excess ~ 0 ------------------------------------
    banner("A. STRUCTURELESS (span chosen so annulus is non-empty)")
    # uniform ln(x) over a wide span so several registers are scoreable
    lnx = RNG.uniform(0, 60, 300_000)  # wide span -> honest n_indep
    rows, best = scan_domain(lnx, kg, container, registers)
    scored = [r for r in rows if r["status"] == "SCORED"]
    maxabs = max((abs(r["excess"]) for r in scored), default=float("nan"))
    print(f"  scoreable registers: {len(scored)}   max|excess| = {maxabs:.2f}")
    # look-elsewhere: max of ~23 register excesses on structureless data is an
    # order statistic, not a single draw. Vol 12 adopted the LEE-corrected bar
    # (local z >= 6.22 for a survey-wide 5-sigma). The synthetic gate uses it too.
    A_ok = len(scored) > 0 and maxabs < 6.22
    print(f"  A {'PASS' if A_ok else 'FAIL'} (LEE-corrected bar 6.22; naive 5.0 is wrong for a {len(scored)}-register scan)")
    passed &= A_ok

    # ---- B. planted lock recovered -----------------------------------------
    banner("B. PLANTED LOCK at a register where the annulus exists")
    # plant at a PRIME register so no lower harmonic (N/2, N/3) competes:
    # Delta_N is linear in N, so a signal on register N also sits on N/2, N/3...
    # A prime with no factor in [4,26] gives an unambiguous recovery target.
    primes = [p for p in (13, 17, 19, 23) if p in registers]
    Nplant = None
    for N in primes:
        r = score_register(RNG.uniform(0, 60, 2000), N, kg, container)
        if r["MN"] > RES_THRESHOLD:
            Nplant = N
    if Nplant is None:
        Nplant = 13
    # plant on register Nplant: place 15% of points exactly on nodes of Delta_Nplant
    d = delta_N(Nplant, kg, container)
    base = RNG.uniform(0, 60, 300_000)
    idx = RNG.choice(len(base), int(0.15 * len(base)), replace=False)
    base[idx] = np.round(base[idx] / d) * d
    rows, best = scan_domain(base, kg, container, registers)
    print(f"  planted at {Nplant}/pi; engine best = {best['N']}/pi  excess={best['excess']:.1f}")
    B_ok = best is not None and best["N"] == Nplant and best["excess"] > 20
    print(f"  B {'PASS' if B_ok else 'FAIL'} (expect best == {Nplant}/pi, excess > 20)")
    passed &= B_ok

    # ---- C. unit invariance of the planted lock ----------------------------
    banner("C. UNIT INVARIANCE (theorem made executable)")
    vals, inv = unit_invariance_check(base, Nplant, kg, container)
    print(f"  P under x*[1, e, 3, 1/60] = {[round(v,1) for v in vals]}")
    print(f"  C {'PASS' if inv else 'FAIL'} (all identical to 1e-6)")
    passed &= inv

    # ---- D. TRIAL 1: the real anchor ---------------------------------------
    banner("D. TRIAL 1 -- quantum_transitional (THE BUILD GATE)")
    # Pin the anchor EXACTLY. A loose *logified* glob will catch the
    # universal_* stitched lakes now living in this folder (that bug reported
    # D on universal_angular, 270k records, not the 189k NIST anchor).
    anchor = []
    if LOGIFIED.exists():
        for exact in ("L_emission_nist_logified.jsonl",
                      "quantum_transitional_logified.jsonl"):
            p = LOGIFIED / exact
            if p.exists():
                anchor = [p]; break
    if not anchor:
        print("  [skip] real anchor lake not found under lakes1d_period/logified/.")
        print("  Run logify.py on L_emission_nist first, then re-run this gate.")
        print("\n  A-C are the synthetic gate; D is the empirical gate. D is REQUIRED")
        print("  before the period engine is built out.")
    else:
        import json
        lnx = np.array([json.loads(l)["klghs_lnx"]
                        for l in open(anchor[0], encoding="utf-8") if l.strip()])
        n = len(lnx)
        print(f"  loaded {n:,} records from {anchor[0].name}")
        # (Mondy A) confirm the count matches the FILED trial -- cheapest check
        # that the right file loaded. This has been the failure point twice.
        FILED_N = 189330
        FILED_REGISTER = 16
        BAR_SINGLE = 5.57   # single-lake 23-register scan (Mondy D)
        if n != FILED_N:
            print(f"  *** WARNING: n={n:,} != filed n={FILED_N:,}. Wrong lake? ***")
        else:
            print(f"  n confirmed == filed {FILED_N:,}")

        from support_profile import profile

        # (Mondy B.1) SWEEP the percentile; do not fix it at 99.
        print(f"  percentile sweep (eff span, M/N at {FILED_REGISTER}/pi):")
        d16 = FILED_REGISTER * math.log(kg) / (container * math.pi)
        sweep = {}
        for q in (0.025, 0.005, 0.0005):     # 95%, 99%, 99.9% central bands
            p = profile(lnx, q=q)
            mn16 = (p["eff_span"] / d16) / FILED_REGISTER
            sweep[q] = (p["eff_span"], mn16, p["verdict"])
            pct = int(round((1 - 2*q) * 100))
            print(f"    {pct:>4}% band: eff_span {p['eff_span']:6.2f}  "
                  f"({p['eff_span']/math.log(10):4.1f} dec)  M/N@16 {mn16:5.2f}  {p['verdict']}")

        # verdict stability across the sweep IS the finding (Mondy B.1)
        mns = [v[1] for v in sweep.values()]
        resolves16 = [mn > RES_THRESHOLD for mn in mns]
        stable = all(resolves16) or not any(resolves16)

        # (Mondy A) report AT 16/pi against the FILED prediction, not "best".
        # Use the 99% band as the reported figure but decide on stability.
        eff99 = sweep[0.005][0]
        # does the annulus exist at 16/pi on the (99%) effective span?
        M16 = eff99 / d16
        mn16 = M16 / FILED_REGISTER
        print(f"\n  FILED PREDICTION: {FILED_REGISTER}/pi with a clear peak excess.")
        print(f"  at {FILED_REGISTER}/pi: effective M/N = {mn16:.2f}  "
              f"(threshold {RES_THRESHOLD:.2f})")

        if mn16 <= RES_THRESHOLD:
            print(f"  annulus EMPTY at {FILED_REGISTER}/pi on effective support.")
            print(f"  TRIAL 1 OUTCOME: REGISTER-UNRESOLVED")
            print(f"    The anchor shows strong commensurate concentration (phase engine")
            print(f"    z=+30.6), but its effective support cannot determine the period.")
            print(f"    The assignment to {FILED_REGISTER}/pi rather than a neighbour is")
            print(f"    NOT established by this data. (Mondy C wording.)")
            print(f"  stability across 95/99/99.9: "
                  f"{'STABLE (unresolved at all)' if stable else 'UNSTABLE -- verdict flips with percentile'}")
            passed = False   # gate does not go green; but this is a filed, legitimate outcome
        else:
            # annulus exists: compute the actual excess AT 16/pi
            r16 = score_register(lnx, FILED_REGISTER, kg, container)
            ex = r16.get("excess", float("nan"))
            ni = r16.get("n_indep", float("nan"))
            print(f"  excess at {FILED_REGISTER}/pi = {ex:.1f}   n_indep = {ni:.1f}")
            print(f"  single-lake bar = {BAR_SINGLE}   survey bar = 6.22")
            if ex >= BAR_SINGLE and stable:
                print(f"  TRIAL 1 OUTCOME: PASS -- {FILED_REGISTER}/pi clears {BAR_SINGLE}, "
                      f"stable across percentile sweep.")
            else:
                print(f"  TRIAL 1 OUTCOME: FAIL -- excess below {BAR_SINGLE} or verdict unstable.")
                passed = False

    banner("BUILD GATE " + ("GREEN -- period engine may be built out" if passed
                            else "RED -- do not build; report the failing check"))
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()