#!/usr/bin/env python3
# ==============================================================================
# SCRIPT: distinct_value_screen.py
# GATE ITEM 4 — Erratum 4 ruling, Mondy Aurora Kish, 2026-08-23
#
# "Distinct-value count, and the fraction of locked mass carried by the top few
#  distinct values. Any domain where a handful of values carry most of the
#  locked mass is flagged Form E."
#
# FORM E — quantised support. The domain takes a small number of distinct
# values; the lock statistic reduces to whether those specific values land near
# nodes, and the record count inflates z far beyond the information content.
#
# Ruled to run BEFORE anything else in the gate, because it is one pass over the
# unified master and it can change the scope of Erratum 4 before that is drafted.
#
# WHAT THIS DOES NOT DO: it does not rule any domain an artifact. It reports
# n_distinct, the concentration of locked mass, and the effective-sample-size
# inflation. The Form E flag is a screening flag, not a verdict.
#
# Usage:  python scripts/distinct_value_screen.py
#         python scripts/distinct_value_screen.py --quantised-only
# ==============================================================================

import json, math, sys, collections
from pathlib import Path

ROOT   = Path(__file__).resolve().parents[1]
MASTER = ROOT / "lakes" / "unified" / "unified_master.jsonl"
K_GEO  = 16.0 / math.pi
LOG_K  = math.log(K_GEO)
CONTAINER  = 24
THRESHOLD  = 0.05
REGISTERS  = list(range(4, 27))

# Above this many distinct values a domain is continuous for our purposes; we
# stop collecting exact values to keep memory bounded.
DISTINCT_CAP = 50_000
# SCREENING CRITERION v2.
# v1 flagged on n_distinct alone, which is the wrong axis: it swept in a dozen
# small-n domains where every record already carries a unique value (n/n_dist
# = 1.0, e.g. seismic_reference 977/977) while missing orbital_ttv, which has
# n/n_dist = 100.5 -- the same repetition as the Gulf tidal lake -- because its
# 2,891 distinct values cleared the count threshold.
#
# The discriminant is REPETITION x CONCENTRATION, not count:
#   repetition   n / n_distinct     how often values recur
#   concentration  share of locked mass on the top few distinct values
# A domain is examined if repetition is meaningful; it is FLAGGED only if the
# locked mass is also concentrated.
REPETITION_EXAMINE = 5.0     # examine concentration above this
CONCENTRATION_FLAG = 0.80    # top-5 share of locked mass to flag Form E
# Rounding used to decide "distinct". float64 noise should not create values.
ROUND_DP = 9

QUANTISED_ONLY = "--quantised-only" in sys.argv


def target(N):
    return N / math.pi


def locks(s, N):
    rp = (s / target(N)) * CONTAINER
    return abs(rp - max(1, round(rp))) < THRESHOLD


def main():
    if not MASTER.exists():
        raise SystemExit(f"Unified master not found: {MASTER}")

    print("=" * 96)
    print("GATE ITEM 4 — FORM E SCREEN (quantised support)")
    print("=" * 96)
    print(f"  reading {MASTER.name}\n")

    counts   = collections.Counter()             # domain -> n records
    values   = collections.defaultdict(collections.Counter)   # domain -> value -> count
    overflow = set()                             # domains past DISTINCT_CAP

    n = 0
    with MASTER.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            dom = (rec.get("domain") or "").lower()
            s = rec.get("scalar_klc")
            if s is None:
                continue
            try:
                s = float(s)
            except (TypeError, ValueError):
                continue
            n += 1
            counts[dom] += 1
            if dom not in overflow:
                values[dom][round(s, ROUND_DP)] += 1
                if len(values[dom]) > DISTINCT_CAP:
                    overflow.add(dom)
                    values[dom] = collections.Counter()   # release
            if n % 2_000_000 == 0:
                print(f"    ... {n:,} records", flush=True)

    print(f"  {n:,} records across {len(counts)} domains\n")

    # ---------------------------------------------------------------- report
    print(f"  {'domain':<28}{'n':>12}{'n_distinct':>13}{'n/n_dist':>11}"
          f"{'sqrt infl':>11}  flag")
    print("  " + "-" * 92)

    flagged = []
    for dom in sorted(counts, key=lambda d: -counts[d]):
        nrec = counts[dom]
        if dom in overflow:
            if QUANTISED_ONLY:
                continue
            print(f"  {dom:<28}{nrec:>12,}{'>50,000':>13}{'-':>11}{'-':>11}  continuous")
            continue
        nd = len(values[dom])
        ratio = nrec / nd if nd else 0
        infl = math.sqrt(ratio) if ratio else 0
        flag = ""
        if ratio >= REPETITION_EXAMINE:
            flag = "examine"
            flagged.append(dom)
        elif nd <= 50:
            flag = "examine (tiny support)"
            flagged.append(dom)
        if QUANTISED_ONLY and not flag:
            continue
        print(f"  {dom:<28}{nrec:>12,}{nd:>13,}{ratio:>11.1f}{infl:>11.1f}  {flag}")

    # ------------------------------------------- locked-mass concentration
    if not flagged:
        print(f"\n  No domain shows repetition >= {REPETITION_EXAMINE}x. No Form E candidates.")
        return

    print("\n" + "=" * 96)
    print("  LOCKED-MASS CONCENTRATION — flagged domains only")
    print("=" * 96)
    print("  For each domain, the register with the highest lock rate, and how")
    print("  much of that locked mass sits on the top distinct values.\n")

    for dom in flagged:
        vc = values[dom]
        nrec = counts[dom]
        best_N, best_rate, best_locked = None, -1.0, None
        for N in REGISTERS:
            locked = {v: c for v, c in vc.items() if locks(v, N)}
            rate = sum(locked.values()) / nrec
            if rate > best_rate:
                best_N, best_rate, best_locked = N, rate, locked

        print(f"  [{dom}]  n={nrec:,}  n_distinct={len(vc):,}")
        print(f"    peak register {best_N}/pi   lock rate {best_rate:.4f}")
        if not best_locked:
            print("    no distinct value locks at any register\n")
            continue
        tot = sum(best_locked.values())
        top = sorted(best_locked.items(), key=lambda kv: -kv[1])[:5]
        cum = sum(c for _, c in top)
        print(f"    {len(best_locked)} distinct values carry all {tot:,} locked records")
        print(f"    top {len(top)} carry {cum:,} = {100.0*cum/tot:.1f}% of locked mass")
        for v, c in top:
            raw = math.exp(v * LOG_K) - 1
            print(f"      scalar {v:.6f}  (raw {raw:.4f})  {c:>9,} records "
                  f"= {100.0*c/tot:.1f}% of locked")
        share = cum / tot
        verdict = ("*** FORM E ***" if share >= CONCENTRATION_FLAG
                   else "not concentrated - NOT Form E")
        print(f"    z inflation vs independent draws: ~{math.sqrt(nrec/len(vc)):.0f}x")
        print(f"    top-5 share {share*100:.1f}% vs flag threshold "
              f"{CONCENTRATION_FLAG*100:.0f}%  ->  {verdict}\n")

    print("=" * 96)
    print("  Screening flag only. A Form E candidate is not thereby an artifact;")
    print("  it is a domain whose lock claim rests on few distinct values and")
    print("  whose z is inflated relative to its information content.")
    print("=" * 96 + "\n")


if __name__ == "__main__":
    main()