#!/usr/bin/env python3
# ==============================================================================
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC. FOUNDER: Timothy John Kish
# Open for scientific testing / peer review. Cite "KishLattice 16/pi Initiative".
# ==============================================================================
#
# histogram_view.py  --  standard support-shape viewer for logified lakes.
#
# WHY THIS IS A STANDARD RUN: the support gate (support_profile.py) reports
# effective span, tail fraction and inflation as NUMBERS. But numbers alone hid
# the truth twice -- the NIST anchor's "10 decades" and the half-life's "46
# effective decades" both looked fine as summary stats and were sparse tails or
# single spikes once you SAW the distribution. The histogram is the check the
# summary statistic cannot replace: it shows whether the mass is FILLED across
# the span or CLUMPED into bands with gaps (the Form-E / cross-scale hazard).
#
# It reads logified lakes (klghs_lnx) OR promoted lakes (any positive field via
# --field). It prints, per lake:
#   - n, raw span, effective span at 95/99/99.9 (from support_profile)
#   - a 25-bin ln(x) histogram with bars
#   - the fraction of mass in the single densest bin (spike detector)
#   - the number of empty interior bins (gap detector)
# and a one-line SHAPE verdict: FILLED / TAILED / CLUMPED / SPIKED.
#
# It scores NOTHING and claims NOTHING about registers. It is a data-shape
# instrument, run alongside the census so every lake carries its picture.
#
# Usage:
#   python engine1d_period/histogram_view.py                 # all logified lakes
#   python engine1d_period/histogram_view.py <file.jsonl>    # one lake
#   python engine1d_period/histogram_view.py <promoted.jsonl> --field half_life_seconds
# ==============================================================================
import json, math, sys, argparse
from pathlib import Path
import numpy as np

_here = Path(__file__).resolve().parent
sys.path.insert(0, str(_here))
from support_profile import profile

ROOT = _here.parent
LOGIFIED = ROOT / "lakes1d_period" / "logified"


def extract_lnx(path, field=None):
    """Return ln(x) array. logified lakes carry klghs_lnx; promoted lakes need
    a positive field (top-level, _raw_payload, or meta)."""
    out = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        if field is None and "klghs_lnx" in rec:
            v = rec["klghs_lnx"]
            if isinstance(v, (int, float)) and math.isfinite(v):
                out.append(float(v))
            continue
        # promoted-lake path: hunt for the field
        val = None
        keys = [field] if field else ("klghs_x", "universal_hz", "value")
        for k in keys:
            if k and k in rec:
                val = rec[k]; break
            for cont in ("_raw_payload", "meta"):
                sub = rec.get(cont, {})
                if isinstance(sub, dict) and k in sub:
                    val = sub[k]; break
            if val is not None:
                break
        try:
            v = float(val)
            if v > 0 and math.isfinite(v):
                out.append(math.log(v))
        except (TypeError, ValueError):
            pass
    return np.array(out)


def shape_verdict(counts, densest_frac, empty_interior, tail_frac, inflation):
    # order matters: the most disqualifying shape wins.
    if densest_frac >= 0.25:
        return "SPIKED", "one bin holds >=25% of mass -- likely a single value or placeholder"
    if empty_interior >= 3:
        return "CLUMPED", f"{empty_interior} empty interior bins -- banded support with gaps (Form-E hazard)"
    # inflation is the decisive tail signal: raw span >> effective span means the
    # min-max is stretched by sparse records the 99% band already trims.
    if inflation >= 3.0:
        return "TAILED", f"inflation {inflation:.1f}x -- span dominated by sparse tail, not mass"
    if inflation >= 1.5 or tail_frac >= 0.05:
        return "TAIL-INFLATED", f"inflation {inflation:.1f}x -- effective span notably below raw"
    return "FILLED", "mass spread across the span -- honest support"


def view(path, field=None, bins=25):
    lnx = extract_lnx(path, field)
    if len(lnx) < 20:
        print(f"  {path.name}: only {len(lnx)} usable records (field ok?) -- skipped")
        return
    p = profile(lnx)
    print("\n" + "="*72)
    print(f"  {path.name}   n={len(lnx):,}")
    print("="*72)
    for q, pct in ((0.025,95),(0.005,99),(0.0005,99.9)):
        pp = profile(lnx, q=q)
        print(f"    {pct:>5}% band: eff {pp['eff_span']:7.2f} nat "
              f"({pp['eff_span']/math.log(10):5.1f} dec)")
    print(f"    raw span   : {p['raw_span']:7.2f} nat "
          f"({p['raw_span']/math.log(10):5.1f} dec)   inflation {p['inflation']:.2f}")

    h, e = np.histogram(lnx, bins)
    hmax = max(1, h.max())
    densest_frac = h.max() / len(lnx)
    empty_interior = int(np.sum(h[1:-1] == 0))
    print()
    for i in range(bins):
        bar = "#" * int(50 * h[i] / hmax)
        print(f"    {e[i]:8.1f}..{e[i+1]:8.1f} {h[i]:>8}  {bar}")
    verdict, why = shape_verdict(h, densest_frac, empty_interior, p["tail_fraction"], p["inflation"])
    print(f"\n    densest bin: {densest_frac*100:.1f}% of mass   "
          f"empty interior bins: {empty_interior}   tail: {p['tail_fraction']*100:.1f}%")
    print(f"    SHAPE: {verdict} -- {why}")


def main():
    ap = argparse.ArgumentParser(description="support-shape histogram viewer")
    ap.add_argument("path", nargs="?", help="one lake file; omit to scan all logified")
    ap.add_argument("--field", help="positive field to log() (for promoted lakes)")
    ap.add_argument("--bins", type=int, default=25)
    a = ap.parse_args()

    if a.path:
        view(Path(a.path), a.field, a.bins)
    else:
        files = sorted(LOGIFIED.glob("*_logified.jsonl"))
        if not files:
            print("no logified lakes found"); sys.exit(1)
        print(f"scanning {len(files)} logified lakes for support shape...")
        for f in files:
            view(f, None, a.bins)


if __name__ == "__main__":
    main()