"""
KISH-LATTICE FORWARD KINEMATIC ENGINE -- Amino Acid Harmonic Sweep [CORRECTED]

This is the only one of the four that read real data. Three problems found:

  1. THE FILTER ENFORCED THE ANSWER. The original accepted C-C pairs only in
     1.45-1.60 A. In phase units that window is [0.2283, 0.2887] -- it cannot
     contain a bond more than 0.04 from the 0.25 node. The clustering was
     guaranteed by the selection, not measured. The window is now wide enough
     to span a FULL node cell, so a miss is possible.

  2. NO NULL. Nodes sit at k^(j/24), spaced by k^(1/24) = 7.0% for k = 16/pi.
     Landing within 1.5% of SOME node happens ~43% of the time for any
     constant. The modulus sweep below measures this empirically: it asks
     where 16/pi ranks among all moduli, which is the only question that
     makes 16/pi special rather than merely present.

  3. AROMATIC C-N WAS MIXED WITH SINGLE C-N. His/Trp/Arg ring C-N at
     1.31-1.38 A is a different bond population. Now separated.

  Also note: ~70 C-C measurements are not 70 independent facts. They are one
  chemical constant (the sp3 C-C bond length) sampled repeatedly. Effective
  n is ~1, and the printed per-bond table should not be read as a sample.

  PRECISION WARNING: bond lengths are known to ~0.001 A. The mean C-C
  residual of +0.023 A is ~23x that. If the framework predicts the node
  EXACTLY, this data refutes it. The claim survives only with a stated
  tolerance, and no tolerance has been derived.
"""

import json
import math
import itertools
from pathlib import Path

LAKE = Path("./lakes_kishlattice/inputs_promoted/b3_amino.jsonl")

K_GEO = 16 / math.pi
CONTAINER = 24
TOL = 0.05                 # framework lock tolerance, in node units

# Windows widened to span a full node cell (ratio k^(1/24) = 1.070) with room.
CC_WINDOW = (1.40, 1.75)   # sp3 C-C ~1.52; window now spans > 1 cell
CN_WINDOW = (1.25, 1.60)
AROMATIC_CN_MAX = 1.40     # below this, ring C-N -- separate population


def dist(a, b):
    return math.sqrt((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2
                     + (a["z"] - b["z"]) ** 2)


def rp(d, k):
    """Register position: distance in units of 1/CONTAINER of a log-k cycle."""
    return CONTAINER * math.log(d) / math.log(k)


def node_dist(d, k):
    x = rp(d, k)
    return abs(x - round(x))


def lock_fraction(ds, k, tol=TOL):
    return sum(1 for d in ds if node_dist(d, k) < tol) / len(ds)


def load_bonds():
    if not LAKE.exists():
        raise SystemExit(f"ABORT -- lake not found: {LAKE}\n"
                         "No values simulated. Fix the path and re-run.")
    cc, cn_single, cn_arom = [], [], []
    n_mol = 0
    with open(LAKE, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            mol = json.loads(line)
            atoms = mol.get("coords") or mol.get("atoms")
            if not atoms:
                raise SystemExit(
                    f"ABORT -- record '{mol.get('name','?')}' has no coords.\n"
                    f"Keys present: {sorted(mol.keys())}")
            n_mol += 1
            for a1, a2 in itertools.combinations(atoms, 2):
                pair = tuple(sorted([a1["atom"], a2["atom"]]))
                d = dist(a1, a2)
                if pair == ("C", "C") and CC_WINDOW[0] <= d <= CC_WINDOW[1]:
                    cc.append((mol["name"], d))
                elif pair == ("C", "N") and CN_WINDOW[0] <= d <= CN_WINDOW[1]:
                    (cn_arom if d < AROMATIC_CN_MAX else cn_single).append(
                        (mol["name"], d))
    if not cc:
        raise SystemExit("ABORT -- no C-C bonds found in the widened window.")
    return n_mol, cc, cn_single, cn_arom


def summarise(label, bonds, k):
    if not bonds:
        print(f"  {label:<22}: none found")
        return None
    ds = [d for _, d in bonds]
    node_d = K_GEO ** 0.25
    mean = sum(ds) / len(ds)
    nds = [node_dist(d, k) for d in ds]
    lf = lock_fraction(ds, k)
    span = math.log(max(ds) / min(ds)) / math.log(k) * CONTAINER
    print(f"  {label:<22}: n={len(ds):>4}  mean={mean:.4f} A  "
          f"resid={mean - node_d:+.4f} A  ({(mean/node_d - 1)*100:+.2f}%)")
    print(f"  {'':<22}  mean |dist to node| = {sum(nds)/len(nds):.4f} cells   "
          f"lock@{TOL} = {lf*100:.1f}%")
    print(f"  {'':<22}  data spans {span:.3f} node cells  "
          f"{'<-- DELTA FUNCTION, cannot resolve a period' if span < 1 else ''}")
    return ds


def modulus_sweep(ds, label, n_k=40000, k_lo=1.5, k_hi=20.0):
    """THE NULL. Where does 16/pi rank among all moduli?"""
    obs = lock_fraction(ds, K_GEO)
    obs_nd = sum(node_dist(d, K_GEO) for d in ds) / len(ds)
    better_lock = better_nd = 0
    lo, hi = math.log(k_lo), math.log(k_hi)
    for i in range(n_k):
        k = math.exp(lo + (hi - lo) * i / (n_k - 1))
        if abs(k - K_GEO) < 1e-9:
            continue
        if lock_fraction(ds, k) >= obs:
            better_lock += 1
        if sum(node_dist(d, k) for d in ds) / len(ds) <= obs_nd:
            better_nd += 1
    p_lock = better_lock / n_k
    p_nd = better_nd / n_k
    print()
    print(f"  MODULUS-SWEEP NULL -- {label}")
    print(f"    sweep: {n_k:,} moduli, log-uniform on [{k_lo}, {k_hi}]")
    print(f"    16/pi lock fraction @tol {TOL} : {obs*100:.1f}%")
    print(f"    moduli doing AT LEAST AS WELL   : {p_lock*100:.1f}%   <- p-value")
    print(f"    16/pi mean node distance        : {obs_nd:.4f} cells")
    print(f"    moduli doing AT LEAST AS WELL   : {p_nd*100:.1f}%   <- p-value")
    if p_lock > 0.05:
        print(f"    VERDICT: 16/pi is NOT privileged. A randomly chosen modulus")
        print(f"             matches or beats it {p_lock*100:.0f}% of the time.")
    else:
        print(f"    VERDICT: 16/pi sits in the top {p_lock*100:.1f}% of moduli.")
        print(f"             Worth pursuing -- then check whether the winning")
        print(f"             band is narrow or whether many moduli tie.")
    return p_lock, p_nd


def main():
    node_d = K_GEO ** 0.25
    print("=" * 78)
    print(" KISH-LATTICE AMINO ACID HARMONIC SWEEP  [corrected]")
    print(f" k_geo = {K_GEO:.6f}   container = {CONTAINER}   "
          f"node spacing = {K_GEO**(1/CONTAINER):.4f}x ({(K_GEO**(1/CONTAINER)-1)*100:.1f}%)")
    print(f" 1/4-phase node distance = k_geo^0.25 = {node_d:.5f} A")
    print("=" * 78)

    n_mol, cc, cn_s, cn_a = load_bonds()
    print(f"  molecules read : {n_mol}")
    print(f"  windows        : C-C {CC_WINDOW}  C-N {CN_WINDOW} "
          f"(aromatic < {AROMATIC_CN_MAX})")
    print()
    cc_d = summarise("C-C (sp3)", cc, K_GEO)
    cn_sd = summarise("C-N single", cn_s, K_GEO)
    cn_ad = summarise("C-N aromatic", cn_a, K_GEO)

    print()
    print("  Effective independence: these are repeated measurements of a few")
    print("  chemical constants, not independent samples. n_eff ~ number of")
    print("  distinct bond types, i.e. ~3, not ~150.")

    modulus_sweep(cc_d, "C-C (sp3)")
    if cn_sd:
        modulus_sweep(cn_sd, "C-N single")

    print()
    print("  ANALYTIC CROSS-CHECK: nodes are spaced "
          f"{(K_GEO**(1/CONTAINER)-1)*100:.1f}% apart, so landing within 1.5%")
    print(f"  of SOME node has prior probability ~"
          f"{2*0.015/(K_GEO**(1/CONTAINER)-1)*100:.0f}%. The sweep p-value above")
    print("  should come out near that figure if there is nothing here.")
    print("=" * 78)


if __name__ == "__main__":
    main()
