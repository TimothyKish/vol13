#!/usr/bin/env python3
# ==============================================================================
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC. FOUNDER: Timothy John Kish
# Open for scientific testing / peer review. Cite "KishLattice 16/pi Initiative".
# ==============================================================================
#
# register_stability.py  --  the period engine's pre-registration discipline.
#
# TIMOTHY'S INSIGHT (2026-09-10): in the period engine, the winning register is
# downstream of where the sample's support mass happens to sit, so a different
# random draw could shift the modal register to a neighbour. Therefore guessing
# a register tests the wrong thing. THE CLAIM IS INVARIANCE, NOT LOCATION:
#
#   A real geometric lock survives resampling. A binning artifact wanders.
#
# This test resamples the lake (split-half + bootstrap), finds the winning
# resolvable register in each resample, and reports:
#   * the modal register and how often it wins (stability fraction)
#   * whether the winner's EXCESS clears the look-elsewhere bar, on the full lake
#   * VERDICT: STABLE-AND-LOCKED / STABLE-BELOW-BAR / WANDERS
#
# It does NOT pre-name a register. Whatever register the data chooses is a
# measurement; the pre-registered prediction is only that it holds under
# resampling and clears the bar. Both outcomes are reportable.
#
# Run:  python engine1d_period/register_stability.py <logified.jsonl> [--boot 200]
# ==============================================================================
import json, math, sys, argparse
from pathlib import Path
from collections import Counter
import numpy as np

_here = Path(__file__).resolve().parent
sys.path.insert(0, str(_here))
from periodogram import load_registers_and_kgeo, delta_N, score_register, RES_THRESHOLD
from support_profile import profile
from kish_period_io import load_lnx, cap_from_env

BAR_SINGLE = 5.57   # single-lake 23-register look-elsewhere bar (Mondy)
BOOT_SUBSAMPLE = 200_000   # per-resample cap: stability is about the register,
#                            not every record; a large lake need not rescore
#                            millions 400x. Deterministic via the run seed.

def best_resolvable(lnx, registers, kg, container, eff_span):
    """Winning resolvable register (excess), scored on effective-span gate."""
    best = None
    for N in registers:
        d = delta_N(N, kg, container)
        if (eff_span / d) / N <= RES_THRESHOLD:
            continue   # not resolvable on effective support
        r = score_register(lnx, N, kg, container)
        ex = r.get("excess")
        if ex is not None and (best is None or ex > best[1]):
            best = (N, ex, r.get("n_indep"))
    return best

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--boot", type=int, default=200)
    ap.add_argument("--seed", type=int, default=20260910)
    a = ap.parse_args()

    registers, container, kg = load_registers_and_kgeo()
    lnx, _meta = load_lnx(Path(a.path), cap=cap_from_env())
    n = len(lnx)
    if n < 20:
        print(f"  SKIPPED -- only {n} usable klghs_lnx values in {a.path}. "
              f"Check the logify field mapping for this lake.")
        return
    rng = np.random.default_rng(a.seed)

    print("="*72)
    print(f"  REGISTER STABILITY  --  {Path(a.path).name}")
    print(f"  claim: INVARIANCE, not location (register filed UNKNOWN)")
    print("="*72)
    print(f"  n = {n:,}")

    # full-lake support + shape gate
    p = profile(lnx)
    eff = p["eff_span"] if p["verdict"] != "SUPPORT-OK" else p["raw_span"]
    print(f"  eff span 99%: {p['eff_span']:.2f} nat ({p['eff_span']/math.log(10):.1f} dec)  "
          f"inflation {p['inflation']:.2f}  verdict {p['verdict']}")

    full = best_resolvable(lnx, registers, kg, container, eff)
    if full is None:
        print("\n  no resolvable register on effective support -- nothing to test.")
        print("  VERDICT: UNRESOLVED (dynamic range too small on honest support)")
        return
    fullN, fullEx, fullNi = full
    print(f"  full-lake winner: {fullN}/pi  excess {fullEx:.1f}  n_indep {fullNi:.1f}")

    # For very large lakes, work from a fixed subsample so 400 resamples stay
    # tractable on commodity hardware. The register verdict is unchanged; only
    # runtime is bounded. Small lakes (pulsar, anchor) use every record.
    if n > BOOT_SUBSAMPLE:
        work = lnx[rng.choice(n, BOOT_SUBSAMPLE, replace=False)]
        print(f"  [subsample] n={n:,} > {BOOT_SUBSAMPLE:,}; bootstrapping on "
              f"{BOOT_SUBSAMPLE:,} (register verdict unchanged, runtime bounded)")
    else:
        work = lnx
    wn = len(work)

    # split-half (disjoint) x repeated, and bootstrap, with heartbeat
    winners = Counter()
    print(f"\n  resampling: {a.boot} bootstraps + {a.boot} split-halves ...")
    _hb_path = Path("lakes1d_period/unified/period_heartbeat.json")
    def _beat(msg):
        try:
            import json as _j, time as _t
            _hb_path.parent.mkdir(parents=True, exist_ok=True)
            _hb_path.write_text(_j.dumps({"timestamp_utc": _t.strftime("%Y-%m-%dT%H:%M:%SZ", _t.gmtime()),
                "progress_pct": 0, "completed": 0, "total": 0, "current_action": msg, "eta_seconds": 0}))
        except Exception: pass
    for _bi in range(a.boot):
        if _bi % 20 == 0: _beat(f"bootstrap {_bi}/{a.boot}")
        bs = work[rng.integers(0, wn, wn)]
        pe = profile(bs); effb = pe["eff_span"] if pe["verdict"]!="SUPPORT-OK" else pe["raw_span"]
        b = best_resolvable(bs, registers, kg, container, effb)
        if b: winners[b[0]] += 1
    for _si in range(a.boot):
        if _si % 20 == 0: _beat(f"split-half {_si}/{a.boot}")
        idx = rng.permutation(wn)[: wn // 2]
        half = work[idx]
        ph = profile(half); effh = ph["eff_span"] if ph["verdict"]!="SUPPORT-OK" else ph["raw_span"]
        b = best_resolvable(half, registers, kg, container, effh)
        if b: winners[b[0]] += 1

    total = sum(winners.values())
    modalN, modalCount = winners.most_common(1)[0]
    stability = modalCount / total if total else 0.0
    print(f"\n  winning register across {total} resamples:")
    for N, c in winners.most_common(6):
        print(f"    {N}/pi : {c:>4} ({100*c/total:.0f}%)")
    print(f"\n  modal register {modalN}/pi, stability {stability*100:.0f}%")

    # verdict
    print("\n" + "="*72)
    stable = stability >= 0.60 and modalN == fullN
    locked = fullEx >= BAR_SINGLE
    if stable and locked:
        print(f"  VERDICT: STABLE-AND-LOCKED at {fullN}/pi")
        print(f"    register survives resampling ({stability*100:.0f}%) AND clears the "
              f"bar (excess {fullEx:.1f} >= {BAR_SINGLE}).")
        print(f"    This is a real, pre-registered register result at the register")
        print(f"    the DATA chose. Report to Mondy for independent confirmation.")
    elif stable and not locked:
        print(f"  VERDICT: STABLE-BELOW-BAR at {fullN}/pi")
        print(f"    register is stable under resampling ({stability*100:.0f}%) but excess "
              f"{fullEx:.1f} is below the bar {BAR_SINGLE}.")
        print(f"    Consistent commensurate structure that does not clear noise. Honest null-ish.")
    else:
        print(f"  VERDICT: WANDERS")
        print(f"    winning register is not stable under resampling "
              f"(modal {modalN}/pi only {stability*100:.0f}%; full-lake {fullN}/pi).")
        print(f"    The 'winner' is a binning property of the draw, not a lock.")
        print(f"    Exactly the outcome Timothy predicted the period engine can produce.")
    print("="*72)

if __name__ == "__main__":
    main()