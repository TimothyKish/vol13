#!/usr/bin/env python3
# ==============================================================================
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC. FOUNDER: Timothy John Kish
# Open for scientific testing / peer review. Cite "KishLattice 16/pi Initiative".
# ==============================================================================
#
# support_profile.py  --  MANDATORY pre-pinch support gate (period engine).
#
# WHY: the resolution criterion M/N > 2.67 is computed on min-to-max log-span.
# A sparse TAIL of outlier records inflates that span without contributing usable
# support, making a domain look resolved when its mass occupies a narrow band.
# Discovered on the NIST anchor first contact: raw span 23.0 (M/N=4.17) but 99.7%
# of mass in the top ~4 units -> effective M/N = 1.23, BACKGROUND-LIMITED.
#
# This stage runs BEFORE the periodogram. It reports raw span, EFFECTIVE span
# (central 99% mass band), tail fraction, and inflation, and writes a JSON gate
# file the pipeline reads. The periodogram scores on EFFECTIVE span.
#
#   raw_span  = max(lnx) - min(lnx)
#   eff_span  = quantile(1-q) - quantile(q)     q = 0.005  (99% band)
#   inflation = raw_span / eff_span
#
# VERDICT (thresholds pre-registered, subject to referee ruling):
#   inflation <  1.5  -> SUPPORT-OK
#   1.5..3.0          -> TAIL-INFLATED       (score on eff_span; raw M/N flagged)
#   >= 3.0            -> SPARSE-TAIL-ARTIFACT (raw M/N void; eff_span is the truth)
# ==============================================================================
import json, math, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
LOGIFIED = ROOT / "lakes1d_period" / "logified"
GATE_OUT = ROOT / "lakes1d_period" / "unified" / "support_gate.json"

Q = 0.005
INFL_OK, INFL_ART = 1.5, 3.0


def profile(lnx, q=Q):
    lnx = np.asarray(lnx, float)
    lnx = lnx[np.isfinite(lnx)]                       # drop any nan/inf defensively
    if len(lnx) < 2 or float(lnx.max() - lnx.min()) <= 0.0:
        # empty, single-valued, or degenerate: no span to profile. Named, not fatal.
        return {"n": int(len(lnx)), "raw_span": 0.0, "eff_span": 0.0,
                "tail_fraction": 0.0, "inflation": float("inf"),
                "verdict": "EMPTY-OR-DEGENERATE",
                "raw_min": float(lnx.min()) if len(lnx) else float("nan"),
                "raw_max": float(lnx.max()) if len(lnx) else float("nan"),
                "eff_lo": float("nan"), "eff_hi": float("nan")}
    lo, hi = np.quantile(lnx, [q, 1 - q])
    raw = float(lnx.max() - lnx.min())
    eff = float(hi - lo)
    tail = float(np.mean((lnx < lo) | (lnx > hi)))
    infl = raw / eff if eff > 0 else float("inf")
    verdict = ("SUPPORT-OK" if infl < INFL_OK else
               "TAIL-INFLATED" if infl < INFL_ART else "SPARSE-TAIL-ARTIFACT")
    return {"n": len(lnx), "raw_span": raw, "eff_span": eff, "tail_fraction": tail,
            "inflation": infl, "verdict": verdict,
            "raw_min": float(lnx.min()), "raw_max": float(lnx.max()),
            "eff_lo": float(lo), "eff_hi": float(hi)}


def histogram(lnx, bins=20):
    h, e = np.histogram(np.asarray(lnx, float), bins)
    return [(float(e[i]), float(e[i + 1]), int(h[i])) for i in range(bins)]


def report(lnx, name="domain", bins=20, out=sys.stdout):
    p = profile(lnx)
    hist = histogram(lnx, bins)
    mx = max((c for _, _, c in hist), default=1)
    print(f"  SUPPORT PROFILE: {name}", file=out)
    print(f"    n = {p['n']:,}", file=out)
    print(f"    raw span {p['raw_min']:.1f}..{p['raw_max']:.1f} = {p['raw_span']:.2f} "
          f"({p['raw_span']/math.log(10):.1f} dec)", file=out)
    print(f"    eff span {p['eff_lo']:.1f}..{p['eff_hi']:.1f} = {p['eff_span']:.2f} "
          f"({p['eff_span']/math.log(10):.1f} dec)", file=out)
    print(f"    tail outside 99% band: {p['tail_fraction']*100:.2f}%", file=out)
    print(f"    inflation raw/eff = {p['inflation']:.2f}  -> {p['verdict']}", file=out)
    if p["verdict"] != "SUPPORT-OK":
        print(f"    *** score on EFFECTIVE span {p['eff_span']:.2f}, not raw {p['raw_span']:.2f} ***", file=out)
    for lo, hi, c in hist:
        bar = "#" * min(50, int(50 * c / mx))
        print(f"    {lo:6.1f}-{hi:6.1f} {c:>9}  {bar}", file=out)
    return p


def run_gate():
    """Profile every logified lake, write the gate file, return the profiles."""
    GATE_OUT.parent.mkdir(parents=True, exist_ok=True)
    profiles = {}
    if not LOGIFIED.exists():
        raise SystemExit(f"[support] no logified dir {LOGIFIED}")
    for src in sorted(LOGIFIED.glob("*_logified.jsonl")):
        lnx = [json.loads(l)["klghs_lnx"] for l in open(src, encoding="utf-8") if l.strip()]
        if not lnx:
            continue
        dom = src.stem.replace("_logified", "")
        p = report(lnx, name=dom)
        profiles[dom] = p
        print(file=sys.stdout)
    with open(GATE_OUT, "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2)
    print(f"  support gate written -> {GATE_OUT}")
    return profiles


if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        lnx = [json.loads(l)["klghs_lnx"] for l in open(path, encoding="utf-8") if l.strip()]
        report(lnx, name=path.stem)
    else:
        run_gate()
