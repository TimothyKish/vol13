#!/usr/bin/env python3
# ==============================================================================
# SCRIPT: ensemble_z.py
# TARGET: Ensemble z-scoring with per-pass retention and register occupancy.
#
# Implements the Vol 12 methods ruling (Mondy, 2026-08-22):
#   - single-run z is withdrawn as a citable quantity
#   - N passes retained per register, occupancy reported alongside mean +/- sd
#   - co-dominance decided on the EMPIRICAL spread of the DIFFERENCE,
#     sd(z_A - z_B), measured from the ensemble -- not derived from sd(z)
#   - two-sided self-validation: the loop must be shown able to vary
#     before it is trusted to show stability
#
# EFFICIENCY: compute_dist_lock_internal contains no RNG and the chaos/synthetic
# null lakes are built under a fixed seed, so the cross-domain matrix is already
# deterministic. Only compute_dual_z_scores reseeds. This script loops the
# z-stage alone and never touches the cross-domain matrix.
#
# AUTHORS: Atlas / Timothy John Kish
# AUDIT STATUS: proposed -- awaiting Mondy sign-off
# ==============================================================================

import argparse, json, math, sys, time
from pathlib import Path
import numpy as np

ENGINE_DIR = Path(__file__).resolve().parent
ROOT = ENGINE_DIR.parent
sys.path.insert(0, str(ENGINE_DIR))

from build_pinch_table import (          # noqa: E402
    load_domain_scalars, compute_dual_z_scores,
    HARMONIC_TARGETS, UNIFIED_PATH,
)

OUT_PATH = ROOT / "lakes" / "unified" / "ensemble_z_master.json"

# Pre-registered co-dominance threshold. Fixed before results are examined.
CODOMINANCE_SIGMA = 2.0
# Mondy's tie-break: calls within this margin of the threshold report as
# co-dominant (the conservative direction).
TIEBREAK_MARGIN = 0.25


# ------------------------------------------------------------------ validation
def self_validate(scalars, registers, trials):
    """
    Two-sided. A loop that silently inherits one global seed returns N identical
    passes and reports beautiful 100% occupancy on nothing.

      (a) unseeded passes MUST differ   -> proves the loop can vary
      (b) seeded passes MUST match      -> proves the variation is the RNG,
                                           not uncontrolled state

    Returns True only if both hold.
    """
    print("\n" + "=" * 78)
    print("ENSEMBLE SELF-VALIDATION")
    print("=" * 78)
    hl = registers[len(registers) // 2]

    a = [compute_dual_z_scores(scalars, hl, n_trials=trials)[2] for _ in range(3)]
    varies = len(set(np.round(a, 9))) > 1
    print(f"  (a) unseeded passes differ : {a[0]:.6f}  {a[1]:.6f}  {a[2]:.6f}")
    print(f"      -> {'PASS' if varies else '*** FAIL - passes identical ***'}")

    b = []
    for _ in range(2):
        np.random.seed(42)
        b.append(compute_dual_z_scores(scalars, hl, n_trials=trials)[2])
    reproduces = abs(b[0] - b[1]) < 1e-12
    print(f"  (b) seeded passes match    : {b[0]:.6f}  {b[1]:.6f}")
    print(f"      -> {'PASS' if reproduces else '*** FAIL - seed does not control RNG ***'}")

    ok = varies and reproduces
    print(f"\n  VERDICT: {'validated' if ok else 'NOT VALIDATED - do not read results'}")
    print("=" * 78)
    return ok


# -------------------------------------------------------------------- ensemble
def run_ensemble(domain_scalars, n_passes, trials):
    registers = list(HARMONIC_TARGETS.keys())
    results = {}
    order = sorted(domain_scalars, key=lambda d: len(domain_scalars[d]))
    t_start = time.time()

    for di, dom in enumerate(order, 1):
        scalars = domain_scalars[dom]
        n = len(scalars)
        passes = np.zeros((n_passes, len(registers)), dtype=np.float64)

        print(f"  [{di}/{len(order)}] {dom:<32} n={n:>10,}  ", end="", flush=True)
        t0 = time.time()
        for p in range(n_passes):
            for ri, hl in enumerate(registers):
                passes[p, ri] = compute_dual_z_scores(scalars, hl, n_trials=trials)[2]
        print(f"{time.time()-t0:6.1f}s")

        results[dom] = summarise(dom, passes, registers, n_passes, n)

    print(f"\n  Ensemble complete in {time.time()-t_start:.1f}s")
    return results


def summarise(dom, passes, registers, n_passes, n_records):
    mean_z = passes.mean(axis=0)
    sd_z = passes.std(axis=0, ddof=1) if n_passes > 1 else np.zeros(len(registers))

    # Register occupancy: which register held the peak, per pass.
    peaks = [registers[i] for i in passes.argmax(axis=1)]
    occ = {r: peaks.count(r) / n_passes for r in set(peaks)}
    occ = dict(sorted(occ.items(), key=lambda kv: -kv[1]))
    occ_se = math.sqrt(0.25 / n_passes) * 100      # worst-case binomial, in pp

    ranked = sorted(range(len(registers)), key=lambda i: -mean_z[i])
    iA, iB = ranked[0], ranked[1]

    # THE quantity the co-dominance rule needs, measured not derived.
    delta = passes[:, iA] - passes[:, iB]
    d_mean = float(delta.mean())
    d_sd = float(delta.std(ddof=1)) if n_passes > 1 else 0.0
    d_sem = d_sd / math.sqrt(n_passes) if n_passes > 1 else 0.0
    separation = abs(d_mean) / d_sem if d_sem > 0 else float("inf")

    # Settles the correlation question with no extra cost and no assumption.
    corr = float(np.corrcoef(passes[:, iA], passes[:, iB])[0, 1]) if n_passes > 2 else None
    predicted_indep = math.sqrt(sd_z[iA] ** 2 + sd_z[iB] ** 2)

    if separation < CODOMINANCE_SIGMA - TIEBREAK_MARGIN:
        verdict, band = "CO-DOMINANT", [registers[iA], registers[iB]]
    elif separation < CODOMINANCE_SIGMA + TIEBREAK_MARGIN:
        verdict, band = "MARGINAL -> CO-DOMINANT (tie-break)", [registers[iA], registers[iB]]
    else:
        verdict, band = "SEPARATED", [registers[iA]]

    return {
        "n_records": int(n_records),
        "n_passes": n_passes,
        "mean_z": {r: round(float(m), 4) for r, m in zip(registers, mean_z)},
        "sd_z": {r: round(float(s), 4) for r, s in zip(registers, sd_z)},
        "occupancy": {r: round(v, 3) for r, v in occ.items()},
        "occupancy_se_pp": round(occ_se, 1),
        "top_pair": [registers[iA], registers[iB]],
        "delta_mean": round(d_mean, 4),
        "delta_sd_measured": round(d_sd, 4),
        "delta_sd_if_independent": round(float(predicted_indep), 4),
        "delta_sem": round(d_sem, 4),
        "separation_sigma": round(separation, 3) if math.isfinite(separation) else None,
        "correlation_top_pair": round(corr, 4) if corr is not None else None,
        "verdict": verdict,
        "reported_band": band,
    }


def report(results, n_passes, trials):
    print("\n" + "=" * 100)
    print(f"ENSEMBLE Z REPORT   N={n_passes} passes, T={trials} trials"
          f"   (T_eff = {n_passes*trials:,})")
    print("=" * 100)
    print(f"  {'domain':<28}{'band':<16}{'mean z':>9}{'occ':>7}{'sep':>8}  verdict")
    print("  " + "-" * 96)
    for dom, r in sorted(results.items()):
        band = ",".join(r["reported_band"])
        top = r["reported_band"][0]
        sep = f"{r['separation_sigma']:.2f}" if r["separation_sigma"] is not None else "inf"
        print(f"  {dom:<28}{band:<16}{r['mean_z'][top]:>9.2f}"
              f"{r['occupancy'].get(top,0)*100:>6.0f}%{sep:>8}  {r['verdict']}")

    print("\n  Occupancy precision: +/-{:.0f} pp\n".format(
        list(results.values())[0]["occupancy_se_pp"] if results else 0))

    print("  --- Correlation check (settles whether registers share null draws) ---")
    print(f"  {'domain':<28}{'pair':<16}{'corr':>8}{'sd(D) meas':>12}{'if indep':>10}")
    for dom, r in sorted(results.items()):
        c = r["correlation_top_pair"]
        print(f"  {dom:<28}{','.join(r['top_pair']):<16}"
              f"{(f'{c:+.3f}' if c is not None else 'n/a'):>8}"
              f"{r['delta_sd_measured']:>12.3f}{r['delta_sd_if_independent']:>10.3f}")
    print("\n  Code inspection predicts INDEPENDENT draws per register: each")
    print("  compute_dual_z_scores call makes its own np.random.uniform draw.")
    print("  If so, corr ~ 0 and measured sd(D) ~ the independent prediction.")
    print("  A materially negative corr, or measured sd(D) well below the")
    print("  prediction, falsifies that reading. Report whichever is observed.")
    print("=" * 100)


def main():
    ap = argparse.ArgumentParser(description="Ensemble z-scoring with register occupancy.")
    ap.add_argument("--passes", type=int, default=10, help="N passes (headline anchors: 50)")
    ap.add_argument("--trials", type=int, default=1000, help="T chaos trials per pass")
    ap.add_argument("--domain", action="append", help="restrict to domain(s); repeatable")
    ap.add_argument("--skip-validation", action="store_true",
                    help="NOT for production. Results are not citable.")
    args = ap.parse_args()

    if not UNIFIED_PATH.exists():
        raise SystemExit(f"Unified master not found: {UNIFIED_PATH}")

    print("Loading unified master...")
    domains = load_domain_scalars(UNIFIED_PATH)
    if args.domain:
        domains = {d: v for d, v in domains.items() if d in set(args.domain)}
        if not domains:
            raise SystemExit(f"No matching domains. Available: {sorted(domains)}")
    print(f"  {len(domains)} domains loaded.")

    if not args.skip_validation:
        probe = min(domains, key=lambda d: len(domains[d]))
        if not self_validate(domains[probe], list(HARMONIC_TARGETS.keys()), args.trials):
            raise SystemExit(2)
    else:
        print("\n[WARN] Self-validation skipped. Results are NOT citable.\n")

    print(f"\nRunning {args.passes} passes at T={args.trials}...\n")
    results = run_ensemble(domains, args.passes, args.trials)
    report(results, args.passes, args.trials)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "n_passes": args.passes,
            "n_trials": args.trials,
            "t_effective": args.passes * args.trials,
            "codominance_sigma": CODOMINANCE_SIGMA,
            "tiebreak_margin": TIEBREAK_MARGIN,
            "domains": results,
        }, f, indent=2)
    print(f"\n  Written: {OUT_PATH}\n")


if __name__ == "__main__":
    main()