#!/usr/bin/env python3
# ==============================================================================
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC. FOUNDER: Timothy John Kish
# Open for scientific testing / peer review. Cite "KishLattice 16/pi Initiative".
# ==============================================================================
#
# register_census.py  --  REPLACES tally_moduli.py ("leaderboard of wins").
#
# WHY tally_moduli.py is withdrawn: it counted, per cross-domain pairing, which
# register scored highest, and ranked registers by win-count. That has no null
# and no threshold, so PURE NOISE produces the same low-register-dominated
# leaderboard (demonstrated: 500 structureless lakes top out at 19-24/pi). Low
# registers "win" because they are CHEAP to resolve (4/pi needs 0.4 decades,
# 16/pi needs 6.4), not because they carry signal. A leaderboard of wins is the
# resolution census inverted, not a measurement.
#
# WHAT THIS DOES INSTEAD, per domain (never per pairing):
#   1. SUPPORT GATE: effective span, swept at 95/99/99.9 (Mondy B.1).
#   2. RESOLUTION GATE: for each register, is M/N > 2.67 on effective span?
#      Registers that fail are RESOLUTION-LIMITED and cannot be claimed.
#   3. EXCESS: only for resolvable registers, the periodogram excess with the
#      annular background and n_indep.
#   4. VERDICT per (domain, register): only registers that clear BOTH the
#      resolution gate AND the look-elsewhere bar (6.22 survey / 5.57 single)
#      count as a signal. Everything else is reported as its limiting reason.
#
# The output is NOT a leaderboard. It is a census: for each domain, the registers
# it could resolve, and of those, the ones that actually lock. A register only
# "appears" in the survey if some domain resolves AND locks it above the bar.
# On current data that set may be EMPTY, and if so the census says exactly that.
#
# Run:  python engine1d_period/register_census.py
# ==============================================================================
import json, math, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from periodogram import (load_registers_and_kgeo, delta_N, score_register,
                         RES_THRESHOLD)
from support_profile import profile
from kish_period_io import load_lnx, cap_from_env, resource_banner

ROOT = Path(__file__).resolve().parent.parent
LOGIFIED = ROOT / "lakes1d_period" / "logified"
BAR_SURVEY = 6.22
BAR_SINGLE = 5.57
N_INDEP_MIN = 2.0   # Mondy D.4


def census_domain(lnx, registers, kg, container):
    # support, swept
    sweep = {q: profile(lnx, q=q) for q in (0.025, 0.005, 0.0005)}
    eff99 = sweep[0.005]["eff_span"]
    infl  = sweep[0.005]["inflation"]
    # effective span used for the resolution gate (honest support)
    eff = eff99 if sweep[0.005]["verdict"] != "SUPPORT-OK" else sweep[0.005]["raw_span"]

    rows = []
    for N in registers:
        d = delta_N(N, kg, container)
        mn_eff = (eff / d) / N
        row = {"N": N, "MN_eff": mn_eff}
        if mn_eff <= RES_THRESHOLD:
            row["status"] = "RESOLUTION-LIMITED" if mn_eff < 1 else "BACKGROUND-LIMITED"
            row["excess"] = None
        else:
            r = score_register(lnx, N, kg, container)
            row["excess"] = r.get("excess")
            row["n_indep"] = r.get("n_indep")
            row["status"] = "SCORED"
        rows.append(row)

    # stability of the resolution verdict across the percentile sweep
    stable_res = {}
    for N in registers:
        d = delta_N(N, kg, container)
        verdicts = []
        for q in (0.025, 0.005, 0.0005):
            e = sweep[q]["eff_span"]
            verdicts.append((e / d) / N > RES_THRESHOLD)
        stable_res[N] = all(verdicts) or not any(verdicts)

    return rows, sweep, infl, stable_res


def main():
    registers, container, kg = load_registers_and_kgeo()
    files = sorted(LOGIFIED.glob("*_logified.jsonl"))
    if not files:
        print("no logified lakes found"); sys.exit(1)

    print(resource_banner(cap_from_env()))
    print("="*78)
    print("  REGISTER CENSUS  (replaces the 'leaderboard of wins')")
    print("  A register counts ONLY where a domain RESOLVES it (M/N>2.67, stable)")
    print("  AND locks it above the look-elsewhere bar. No null, no signal.")
    print("="*78)

    survey_signals = []   # (domain, N, excess) that clear BOTH gates
    for f in files:
        dom = f.stem.replace("_logified", "")
        lnx, _meta = load_lnx(f, cap=cap_from_env())
        if len(lnx) < 20:
            print(f"\n  {dom}  (n={len(lnx)})  SKIPPED -- too few usable values")
            continue
        rows, sweep, infl, stable_res = census_domain(lnx, registers, kg, container)

        resolvable = [r for r in rows if r["status"] == "SCORED"]
        signals = [r for r in resolvable
                   if r["excess"] is not None and r["excess"] >= BAR_SINGLE
                   and r.get("n_indep", 0) >= N_INDEP_MIN and stable_res[r["N"]]]

        eff99 = sweep[0.005]["eff_span"]
        print(f"\n  {dom}  (n={len(lnx):,})")
        print(f"    eff span 99%: {eff99:.2f} nat ({eff99/math.log(10):.1f} dec)  "
              f"inflation {infl:.2f}")
        print(f"    registers resolvable on effective support: "
              f"{[r['N'] for r in resolvable] or 'NONE'}")
        if signals:
            for r in signals:
                print(f"    *** SIGNAL: {r['N']}/pi excess {r['excess']:.1f} "
                      f"n_indep {r['n_indep']:.1f} (stable) ***")
                survey_signals.append((dom, r["N"], r["excess"]))
        else:
            # report the best resolvable register and why it fell short
            if resolvable:
                b = max(resolvable, key=lambda r: (r["excess"] or -9))
                why = ("below bar" if (b["excess"] or 0) < BAR_SINGLE
                       else "unstable across percentile sweep")
                print(f"    no signal: best resolvable {b['N']}/pi "
                      f"excess {b['excess']:.1f} -- {why}")
            else:
                print(f"    no signal: no register resolvable on effective support")

    print("\n" + "="*78)
    print("  SURVEY-WIDE RESULT")
    print("="*78)
    if survey_signals:
        print(f"  Registers that some domain both RESOLVES and LOCKS above {BAR_SINGLE}:")
        from collections import Counter
        byreg = Counter(N for _, N, _ in survey_signals)
        for N, c in sorted(byreg.items()):
            doms = [d for d, n, _ in survey_signals if n == N]
            print(f"    {N}/pi : {c} domain(s) -- {', '.join(doms)}")
    else:
        print("  NO register is both resolved and locked above the bar by ANY domain")
        print("  on effective support in this run. The survey, measured honestly,")
        print("  does not currently demonstrate a register at all.")
        print()
        print("  This is not a null result about the framework -- it is a")
        print("  measurement of the instrument's reach: no available observable")
        print("  carries the effective dynamic range to resolve its register")
        print("  above the noise floor. (Mondy Item 8.)")
    print("="*78)


if __name__ == "__main__":
    main()