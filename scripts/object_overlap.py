#!/usr/bin/env python3
# ==============================================================================
# SCRIPT: object_overlap.py
# P_unit_permutation prerequisite (§3) — settle the family definition by
# MEASUREMENT rather than by assumption.
#
# The question: do `cosmology` (t4_cosmological, SDSS DR16 redshift) and
# `galactic` (g1_galaxy_kinematics, SDSS DR16 velocity dispersions) describe the
# same objects? If they do they collapse into one family for the permutation
# test. If they do not, they are two independent draws.
#
# Collapsing a whole domain on suspicion discards real information. This script
# measures the overlap so the decision is made on a number, and — if the overlap
# is partial — identifies the specific records to drop rather than the domain.
#
# Reports three things, because object overlap is not the only route to
# dependence:
#   1. SKY OVERLAP     — same objects, matched on ra/dec
#   2. REDSHIFT OVERLAP— same population range, which permits selection-induced
#                        correlation (Malmquist) even with zero object overlap
#   3. VERDICT         — independent / partial (with a drop-list) / collapse
#
# Usage:  python scripts/object_overlap.py
#         python scripts/object_overlap.py --tol-arcsec 2.0
#         python scripts/object_overlap.py --pair s1_gaia_parallax g1_galaxy_kinematics
# ==============================================================================

import json, math, sys, argparse, collections
from pathlib import Path

ROOT   = Path(__file__).resolve().parents[1]
PROMO  = ROOT / "lakes" / "inputs_promoted"
OUTDIR = ROOT / "lakes" / "unified"

DEFAULT_PAIR = ("t4_cosmological", "g1_galaxy_kinematics")
# Partial-overlap band. Below LOW -> independent. Above HIGH -> collapse.
LOW, HIGH = 0.01, 0.50


def find_key(rec, key, depth=0):
    """Locate `key` at any depth, shallowest wins. Lakes nest to four levels."""
    if depth > 6 or not isinstance(rec, dict):
        return None
    if key in rec and not isinstance(rec[key], (dict, list)):
        return rec[key]
    for v in rec.values():
        if isinstance(v, dict):
            r = find_key(v, key, depth + 1)
            if r is not None:
                return r
    return None


def load(lake):
    p = PROMO / f"{lake}_promoted.jsonl"
    if not p.exists():
        raise SystemExit(f"not found: {p}")
    out = []
    with p.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            ra, dec, z = find_key(r, "ra"), find_key(r, "dec"), find_key(r, "z")
            eid = r.get("entity_id")
            try:
                ra = float(ra) if ra is not None else None
                dec = float(dec) if dec is not None else None
                z = float(z) if z is not None else None
            except (TypeError, ValueError):
                ra = dec = z = None
            out.append((eid, ra, dec, z))
    return out


def angsep(ra1, d1, ra2, d2):
    """Angular separation in arcsec (small-angle, adequate below a degree)."""
    dd = d1 - d2
    dr = (ra1 - ra2) * math.cos(math.radians((d1 + d2) / 2.0))
    return math.hypot(dr, dd) * 3600.0


def sky_overlap(A, B, tol_arcsec):
    cell = max(tol_arcsec / 3600.0, 1e-9)
    idx = collections.defaultdict(list)
    for i, (_, ra, dec, _) in enumerate(B):
        if ra is None or dec is None:
            continue
        idx[(int(ra / cell), int(dec / cell))].append(i)

    matched_a, matched_b = [], set()
    for j, (eid, ra, dec, _) in enumerate(A):
        if ra is None or dec is None:
            continue
        ci, cj = int(ra / cell), int(dec / cell)
        best = None
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for i in idx.get((ci + di, cj + dj), ()):
                    _, rb, db, _ = B[i]
                    s = angsep(ra, dec, rb, db)
                    if s <= tol_arcsec and (best is None or s < best[1]):
                        best = (i, s)
        if best is not None:
            matched_a.append((j, eid, best[1]))
            matched_b.add(best[0])
    return matched_a, matched_b


def quantiles(vals, qs=(0.0, 0.05, 0.5, 0.95, 1.0)):
    v = sorted(x for x in vals if x is not None)
    if not v:
        return None
    return [v[min(len(v) - 1, int(q * (len(v) - 1)))] for q in qs]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", nargs=2, default=list(DEFAULT_PAIR))
    ap.add_argument("--tol-arcsec", type=float, default=1.0)
    args = ap.parse_args()
    la, lb = args.pair

    print("=" * 84)
    print("OBJECT OVERLAP — P_unit_permutation family definition (§3)")
    print("=" * 84)
    print(f"  A: {la}\n  B: {lb}\n  match tolerance: {args.tol_arcsec} arcsec\n")

    A, B = load(la), load(lb)
    ca = sum(1 for r in A if r[1] is not None)
    cb = sum(1 for r in B if r[1] is not None)
    print(f"  {la:<26} {len(A):>10,} records, {ca:>10,} with coordinates")
    print(f"  {lb:<26} {len(B):>10,} records, {cb:>10,} with coordinates")

    if ca == 0 or cb == 0:
        print("\n  One lake carries no sky coordinates. Sky overlap cannot be")
        print("  measured; fall back to the redshift-population comparison below.")
        ma, mb = [], set()
    else:
        print("\n  matching...", flush=True)
        ma, mb = sky_overlap(A, B, args.tol_arcsec)

    fa = len(ma) / ca if ca else 0.0
    fb = len(mb) / cb if cb else 0.0

    print("\n" + "-" * 84)
    print("  1. SKY OVERLAP")
    print("-" * 84)
    print(f"    matched pairs                : {len(ma):,}")
    print(f"    fraction of {la:<20}: {fa*100:.3f}%")
    print(f"    fraction of {lb:<20}: {fb*100:.3f}%")

    print("\n" + "-" * 84)
    print("  2. REDSHIFT POPULATION")
    print("-" * 84)
    print("    Zero object overlap does not imply independence. Two disjoint")
    print("    samples drawn from the same flux-limited survey over the same")
    print("    redshift range are correlated through selection (Malmquist).")
    qa, qb = quantiles([r[3] for r in A]), quantiles([r[3] for r in B])
    lbl = ("min", "5%", "median", "95%", "max")
    if qa and qb:
        print(f"\n    {'':<10}" + "".join(f"{k:>12}" for k in lbl))
        print(f"    {la[:9]:<10}" + "".join(f"{v:>12.5f}" for v in qa))
        print(f"    {lb[:9]:<10}" + "".join(f"{v:>12.5f}" for v in qb))
        lo, hi = max(qa[0], qb[0]), min(qa[4], qb[4])
        span_a, span_b = qa[4] - qa[0], qb[4] - qb[0]
        ov = max(0.0, hi - lo)
        print(f"\n    z-range overlap: [{lo:.5f}, {hi:.5f}]  "
              f"= {100*ov/span_a if span_a else 0:.1f}% of A, "
              f"{100*ov/span_b if span_b else 0:.1f}% of B")
    else:
        print("\n    redshift not available in one or both lakes")

    print("\n" + "=" * 84)
    print("  3. VERDICT")
    print("=" * 84)
    f = max(fa, fb)
    if f < LOW:
        print(f"    Sky overlap {f*100:.3f}% < {LOW*100:.0f}%  ->  INDEPENDENT on objects.")
        print("    Enter as two separate families in the permutation test.")
        print("    CAVEAT: check section 2. Shared survey and shared redshift range")
        print("    permit selection-induced correlation with no shared objects.")
    elif f > HIGH:
        print(f"    Sky overlap {f*100:.1f}% > {HIGH*100:.0f}%  ->  COLLAPSE into one family.")
        print("    These are substantially the same objects.")
    else:
        print(f"    Sky overlap {f*100:.1f}%  ->  PARTIAL.")
        print("    Do NOT discard either domain. Drop the intersecting records")
        print("    from ONE side, pre-registering which side and why, then enter")
        print("    the two reduced domains as independent.")
        out = OUTDIR / f"overlap_{la}_{lb}.json"
        OUTDIR.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as fh:
            json.dump({"lake_a": la, "lake_b": lb,
                       "tol_arcsec": args.tol_arcsec,
                       "matched_entity_ids_a": [m[1] for m in ma]}, fh, indent=2)
        print(f"\n    drop-list written: {out}")
        print(f"    ({len(ma):,} entity_ids from {la})")
    print("=" * 84 + "\n")


if __name__ == "__main__":
    main()