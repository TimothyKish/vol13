"""
comb_scan.py -- THE MODULUS TEST
================================================================================
Mondy Aurora Kish, 2026-09-13. Pre-register before running on real data.

WHAT THIS MEASURES, AND WHY IT IS THE ONLY WAY TO REACH k_geo
--------------------------------------------------------------------------------
Both engines depend on k_geo and N only through the product N*ln(k_geo). A single
peak therefore cannot separate "register 16 at k_geo = 16/pi" from "register 15
at k_geo = (16/pi)^(16/15)". The degeneracy is exact.

A COMB breaks it. The period engine's register periods are

        Delta_N = N * Delta_0      with     Delta_0 = ln(k_geo) / (24*pi)

so if the excess peaks fall on integer multiples of a common fundamental, that
fundamental determines k_geo:

        k_geo = exp( 24 * pi * Delta_0 )

For k_geo = 16/pi, Delta_0 = 0.0215901.
A 0.54% change in k_geo moves Delta_0 to 0.0216618 -- a 0.33% shift, which a
joint fit over ~20 teeth can see even though no adjacent PAIR is resolvable.

That is the whole point: fitting many teeth jointly beats resolving two.

RESIDUAL AMBIGUITY, STATED BEFORE THE RUN
        A comb at Delta_0 is also a comb at Delta_0/m with alternate teeth
        empty. The fit therefore determines ln(k_geo) up to a rational factor.
        The script reports the whole harmonic family, not a single winner.

METHOD
        Rayleigh resultant  R(Delta) = |mean exp(2 pi i x / Delta)|,  P = n R^2,
        computed exactly via FFT of a finely binned histogram of x = ln(quantity).
        Deterministic edge leakage (P ~ n sinc^2(span/Delta), the term Atlas
        derived) is removed by a running median in log-Delta, not by a surrogate
        -- the log-phase surrogate was proven to destroy signal and leakage
        together and is not used here.

TWO-SIDED VALIDATION IS MANDATORY AND RUNS FIRST
        A. structureless, matched n and span  -> comb score must be unremarkable
        B. planted comb at k_geo = 16/pi      -> Delta_0 must be recovered
        If A fails or B fails, the real run does not happen.

LAKE
        L_emission_nist_logified.jsonl -- single source (NIST ASD Z=1-18),
        continuous, >50k distinct values, no stitching. The L_universal_* and
        L_comprehensive_master lakes are cross-scale composites and are the
        banned construction; do not point this at them.
"""

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

K_GEO = 16 / math.pi
DELTA0_KGEO = math.log(K_GEO) / (24 * math.pi)      # 0.0215901
REGISTERS = list(range(4, 27))

VALUE_NAMES = ("klghs_lnx", "log_x", "ln_x", "lnx", "log_value", "x_log",
               "logified", "value_log", "log_quantity", "s_log")
RAW_NAMES = ("klghs_x", "x", "value", "quantity", "raw_value", "val")


# ---------------------------------------------------------------- loading ---
def load_logvalues(path):
    p = Path(path)
    if not p.exists():
        sys.exit(f"ABORT -- lake not found: {p}")
    vals, keys, n_raw, took_log = [], set(), 0, False
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            n_raw += 1
            keys.update(rec.keys())
            v = None
            for nm in VALUE_NAMES:
                if nm in rec and rec[nm] is not None:
                    v = float(rec[nm]); break
            if v is None:
                for nm in RAW_NAMES:
                    if nm in rec and rec[nm] is not None:
                        raw = float(rec[nm])
                        if raw > 0:
                            v = math.log(raw); took_log = True
                        break
            if v is not None and math.isfinite(v):
                vals.append(v)
    if not vals:
        sys.exit("ABORT -- no usable value field.\n  tried: "
                 + ", ".join(VALUE_NAMES + RAW_NAMES)
                 + "\n  keys present: " + ", ".join(sorted(keys))
                 + "\nNo values were simulated.")
    return np.asarray(vals, dtype=np.float64), n_raw, took_log


def effective_span(x, frac=0.99):
    lo = np.quantile(x, (1 - frac) / 2)
    hi = np.quantile(x, 1 - (1 - frac) / 2)
    return lo, hi


# ------------------------------------------------------------ periodogram ---
def rayleigh_spectrum(x, dmin, dmax, oversample=16, nbins=1 << 21):
    """Exact Rayleigh power on a period grid, via FFT of a binned histogram.

    Returns (deltas, P) sorted by increasing delta.
    """
    x = x - x.min()
    L = float(x.max())
    if L <= 0:
        sys.exit("ABORT -- zero span.")
    h, edges = np.histogram(x, bins=nbins, range=(0.0, L))
    w = L / nbins
    centres_phase = (np.arange(nbins) + 0.5) * w
    # phase-correct the half-bin offset
    npad = nbins * oversample
    F = np.fft.rfft(h.astype(np.float64), n=npad)
    k = np.arange(F.size)
    freq = k / (npad * w)                 # cycles per unit x
    with np.errstate(divide="ignore"):
        delta = np.where(freq > 0, 1.0 / np.maximum(freq, 1e-30), np.inf)
    sel = (delta >= dmin) & (delta <= dmax)
    # half-bin phase correction (does not change |F|, kept for clarity)
    n = h.sum()
    P = (np.abs(F[sel]) ** 2) / n         # = n * R^2
    d = delta[sel]
    order = np.argsort(d)
    return d[order], P[order], L, n


def running_background(d, P, win_frac=0.06):
    """Median + MAD in a sliding window that is uniform in log(delta).
    Removes the deterministic sinc leakage without touching narrow peaks."""
    ld = np.log(d)
    half = win_frac * (ld[-1] - ld[0]) / 2
    bg = np.empty_like(P)
    sd = np.empty_like(P)
    lo = np.searchsorted(ld, ld - half)
    hi = np.searchsorted(ld, ld + half)
    for i in range(P.size):
        seg = P[lo[i]:hi[i]]
        m = np.median(seg)
        bg[i] = m
        sd[i] = 1.4826 * np.median(np.abs(seg - m)) + 1e-30
    return bg, sd


# -------------------------------------------------------------- comb fit ---
def comb_score(d, excess, d0, registers=REGISTERS):
    """Mean excess evaluated at delta = N*d0 for every register N."""
    targets = np.array([N * d0 for N in registers])
    if targets.max() > d.max() or targets.min() < d.min():
        return -np.inf
    idx = np.searchsorted(d, targets)
    idx = np.clip(idx, 1, d.size - 1)
    return float(np.mean(excess[idx]))


def fit_comb(d, excess, d0_lo, d0_hi, steps=20000):
    grid = np.linspace(d0_lo, d0_hi, steps)
    sc = np.array([comb_score(d, excess, g) for g in grid])
    best = int(np.argmax(sc))
    return grid, sc, grid[best], sc[best]


# ----------------------------------------------------------- validation ----
def make_structureless(n, span, seed=42):
    rng = np.random.default_rng(seed)
    return rng.uniform(0.0, span, size=n)


def make_planted(n, span, d0=DELTA0_KGEO, N=16, frac=0.35, seed=7):
    """Structureless background plus a fraction locked onto the N*d0 comb."""
    rng = np.random.default_rng(seed)
    base = rng.uniform(0.0, span, size=n)
    k = int(n * frac)
    D = N * d0
    nodes = np.floor(rng.uniform(0, span / D, size=k)) * D
    base[:k] = nodes + rng.normal(0, D * 0.02, size=k)
    return np.clip(base, 0, span)


# ---------------------------------------------------------------- report ---
def run_one(label, x, args, quiet=False):
    d, P, L, n = rayleigh_spectrum(x, args.dmin, args.dmax,
                                   oversample=args.oversample,
                                   nbins=args.nbins)
    bg, sd = running_background(d, P, args.bgwin)
    exc = (P - bg) / sd
    grid, sc, d0_best, sc_best = fit_comb(d, exc, args.d0lo, args.d0hi,
                                          args.d0steps)
    k_fit = math.exp(24 * math.pi * d0_best)
    sc_kgeo = comb_score(d, exc, DELTA0_KGEO)
    # null distribution of the comb score over the d0 grid
    p_beat = float(np.mean(sc >= sc_kgeo))
    if not quiet:
        print(f"  {label}")
        print(f"    n = {n:,}   log-span = {L:.4f} nat = {L/math.log(10):.2f} decades")
        print(f"    comb score at k_geo=16/pi (d0={DELTA0_KGEO:.7f}) : {sc_kgeo:+.3f}")
        print(f"    best-fit d0                                      : {d0_best:.7f}")
        print(f"    implied k_geo = exp(24 pi d0)                    : {k_fit:.5f}"
              f"   ({(k_fit/K_GEO-1)*100:+.2f}% vs 16/pi)")
        print(f"    best comb score                                  : {sc_best:+.3f}")
        print(f"    fraction of d0 values scoring >= k_geo           : {p_beat*100:.1f}%")
    return dict(n=n, span=L, sc_kgeo=sc_kgeo, d0_best=d0_best, k_fit=k_fit,
                sc_best=sc_best, p_beat=p_beat, d=d, exc=exc, grid=grid, sc=sc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lake", default="./lakes1d_period/logified/"
                                     "L_emission_nist_logified.jsonl")
    ap.add_argument("--trim", type=float, default=0.99,
                    help="effective-span quantile band (Atlas support gate); "
                         "0 disables trimming")
    ap.add_argument("--dmin", type=float, default=0.06)
    ap.add_argument("--dmax", type=float, default=0.62)
    ap.add_argument("--d0lo", type=float, default=0.0190)
    ap.add_argument("--d0hi", type=float, default=0.0245)
    ap.add_argument("--d0steps", type=int, default=20000)
    ap.add_argument("--oversample", type=int, default=16)
    ap.add_argument("--nbins", type=int, default=1 << 21)
    ap.add_argument("--bgwin", type=float, default=0.06)
    ap.add_argument("--skip-validation", action="store_true")
    args = ap.parse_args()

    print("=" * 78)
    print(" COMB SCAN -- the modulus test")
    print(f" Delta_0(16/pi) = {DELTA0_KGEO:.7f}   k_geo = exp(24 pi Delta_0)")
    print(f" scanning Delta in [{args.dmin}, {args.dmax}], "
          f"d0 in [{args.d0lo}, {args.d0hi}]")
    print("=" * 78)

    x, n_raw, took_log = load_logvalues(args.lake)
    print(f"  lake      : {args.lake}")
    print(f"  records   : {n_raw:,} read, {x.size:,} usable"
          f"{'  (log taken here)' if took_log else '  (already logified)'}")
    lo, hi = effective_span(x, args.trim) if args.trim > 0 else (x.min(), x.max())
    raw_span = x.max() - x.min()
    eff_span = hi - lo
    print(f"  raw span  : {raw_span:.4f} nat ({raw_span/math.log(10):.2f} decades)")
    print(f"  eff span  : {eff_span:.4f} nat ({eff_span/math.log(10):.2f} decades)"
          f"   inflation {raw_span/max(eff_span,1e-9):.2f}x")
    xt = x[(x >= lo) & (x <= hi)] if args.trim > 0 else x
    print(f"  scored on : {xt.size:,} records (effective band)")

    # --- support diagnostic: Form E screen, run before anything is scored ---
    u = np.unique(xt)
    gaps = np.diff(u)
    print(f"  distinct  : {u.size:,} values ({u.size/max(xt.size,1)*100:.2f}% of n)")
    if gaps.size:
        print(f"  gap (nat) : median {np.median(gaps):.3e}  "
              f"min {gaps.min():.3e}  max {gaps.max():.3e}")
        # a quantised support shows gaps piling on a common multiple
        ratio = np.median(gaps) / max(gaps.min(), 1e-30)
        if u.size < 0.10 * xt.size:
            print("  [FORM E WARNING] fewer than 10% distinct values -- this "
                  "support may be quantised.")
        if gaps.max() > 0.25 * (hi - lo):
            print(f"  [SEAM WARNING] largest gap is "
                  f"{gaps.max()/(hi-lo)*100:.1f}% of the span -- the support has "
                  "a void. Check this is one population, not a stitch.")
    print()

    if not args.skip_validation:
        print("-" * 78)
        print(" TWO-SIDED VALIDATION -- runs first, gates the real run")
        print("-" * 78)
        a = run_one("A. STRUCTURELESS (matched n and span)",
                    make_structureless(xt.size, eff_span), args)
        print()
        b = run_one("B. PLANTED COMB at k_geo = 16/pi, 35% locked, N=16",
                    make_planted(xt.size, eff_span), args)
        print()
        ok_a = a["p_beat"] > 0.05
        ok_b = abs(b["k_fit"] / K_GEO - 1) < 0.02
        print(f"  A passes (structureless shows no privileged d0): {ok_a}")
        print(f"  B passes (planted comb recovers k_geo to 2%)   : {ok_b}")
        if not (ok_a and ok_b):
            print()
            print("  VALIDATION FAILED -- the real run does NOT proceed.")
            print("  A failing A means the scan manufactures a comb from nothing.")
            print("  A failing B means it cannot see one that is there.")
            sys.exit(1)
        print()

    print("-" * 78)
    print(" REAL DATA")
    print("-" * 78)
    r = run_one("C. " + Path(args.lake).name, xt, args)
    print()
    print("  PER-REGISTER EXCESS at the 16/pi comb:")
    for N in REGISTERS:
        t = N * DELTA0_KGEO
        if t < r["d"][0] or t > r["d"][-1]:
            continue
        i = int(np.searchsorted(r["d"], t))
        i = min(max(i, 0), r["d"].size - 1)
        M = eff_span / t
        flag = "  <- M/N < 1, unresolvable" if M / N < 1 else ""
        print(f"    {N:>2}/pi  Delta={t:.5f}  M={M:6.1f}  M/N={M/N:5.2f}  "
              f"excess={r['exc'][i]:+7.2f}{flag}")
    print()
    print("  HARMONIC-FAMILY AMBIGUITY (stated before the run):")
    for m in (1, 2, 3):
        d0 = r["d0_best"] / m
        print(f"    d0/{m} = {d0:.7f}  ->  k_geo = {math.exp(24*math.pi*d0):.5f}")
    print()
    print("  HOW TO READ THE RESULT")
    print("   * If 'fraction of d0 values scoring >= k_geo' is large (>5%),")
    print("     no fundamental is privileged and the comb test is NULL.")
    print("     That is a real outcome and it means k_geo is not measurable")
    print("     from this data -- NOT that it is wrong.")
    print("   * If the best-fit k_geo sits within the resolution of 16/pi,")
    print("     the constant is confirmed at that precision. State the precision.")
    print("   * If it sits clearly elsewhere, THAT is the empirical result that")
    print("     would justify changing the constant. Nothing short of it does.")
    print("=" * 78)


if __name__ == "__main__":
    main()