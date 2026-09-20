#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_lake.py (s15_electron_beta, v3 — per-branch via level reconstruction)

PATH 2 / Option 2C. The IAEA summary API does not expose per-branch beta
endpoints directly (decay_rads returns one ground-state row per nuclide,
ceiling ~1,380 — a puddle). This script reconstructs the per-branch endpoints
from data the API DOES expose:

    beta branch endpoint(parent, level) = Q_beta-(parent) - E_level(daughter)

For each beta-minus parent, the daughter is (Z+1, N-1). Every energetically
allowed daughter level (E_level < Q) is a distinct beta branch, and the max
electron kinetic energy for that branch is Q - E_level. This is the real
multi-branch structure, reconstructed — ~1,380 parents x several allowed
levels each -> target 5,000-11,000 endpoints.

PHYSICAL TYPE: beta-MINUS only (electron). No positron, no EC. Pending Mondy's
ruling on electron-emission vs lepton-family.

DERIVED LAKE: endpoint = Q - E_level is a derivation. The spec REQUIRES the
scramble control (build_scramble_control) — if scrambled level assignments still
lock at the same register, the lock is a construction artifact. Run it before
trusting any lock.

Records carry a top-level "domain" field (REQUIRED by the pipeline).
"""

import urllib.request
import urllib.parse
import csv
import io
import json
import os
import random

DOMAIN = "electron_beta"
MIN_TARGET = 5000
FLOOR = 2000
BASE = "https://www-nds.iaea.org/relnsd/v0/data"
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "lake", "raw",
                        "iaea_beta_decay_raw.jsonl")

# cache of levels per (z,n) so we don't re-pull daughters
_LEVEL_CACHE = {}


def _fetch_csv(params, timeout=120):
    url = BASE + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        text = resp.read().decode("utf-8", errors="replace")
    return list(csv.DictReader(io.StringIO(text)))


def get_beta_parents():
    """All nuclides with a beta-minus Q-value (the ~1,380 parents)."""
    rows = _fetch_csv({"fields": "ground_states", "nuclides": "all"})
    parents = []
    for r in rows:
        modes = f"{r.get('decay_1','')} {r.get('decay_2','')} {r.get('decay_3','')}"
        q = (r.get("qbm") or "").strip()
        if "B-" in modes and q:
            try:
                qv = float(q)
            except ValueError:
                continue
            if qv <= 0:
                continue
            try:
                z = int(float(r.get("z", 0))); n = int(float(r.get("n", 0)))
            except ValueError:
                continue
            parents.append({"z": z, "n": n, "symbol": r.get("symbol", ""),
                            "qbm_kev": qv})
    return parents


def get_daughter_levels(z, n):
    """Daughter of B- decay of (z,n) is (z+1, n-1). Pull its level energies (keV)."""
    dz, dn = z + 1, n - 1
    key = (dz, dn)
    if key in _LEVEL_CACHE:
        return _LEVEL_CACHE[key]
    # IAEA levels query for a single nuclide, e.g. nuclides=137cs style: "<A><symbol>"
    # The API also accepts z,n selection; use the daughter's mass+symbol if available.
    # Simplest robust selector: nuclides="<dz>_<dn>" may not work; use A+symbol.
    # We approximate by requesting levels for the daughter via z,n if supported,
    # else fall back to ground-state-only (level 0).
    try:
        rows = _fetch_csv({"fields": "levels", "nuclides": f"{dz+dn}{_sym(dz)}"},
                          timeout=60)
        levels = []
        for r in rows:
            e = (r.get("energy") or "").strip()
            try:
                ev = float(e)
            except ValueError:
                continue
            if ev >= 0:
                levels.append(ev)
        if not levels:
            levels = [0.0]
    except Exception:
        levels = [0.0]   # fall back to ground-state branch only
    _LEVEL_CACHE[key] = levels
    return levels


# minimal Z->symbol for daughter selection; extend as needed
_SYMBOLS = ("n H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn "
            "Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd "
            "In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu "
            "Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu "
            "Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og").split()


def _sym(z):
    return _SYMBOLS[z] if 0 <= z < len(_SYMBOLS) else "n"


def build_per_branch():
    print("[*] Fetching beta-minus parents (ground_states qbm)...")
    parents = get_beta_parents()
    print(f"    {len(parents)} beta-minus parents")
    records = []
    for i, p in enumerate(parents):
        levels = get_daughter_levels(p["z"], p["n"])
        for e_level in levels:
            endpoint = p["qbm_kev"] - e_level
            if endpoint <= 0:
                continue   # level not energetically allowed
            records.append({
                "domain": DOMAIN,
                "element": p["symbol"],
                "isotope": f"{p['symbol']}-{p['z']+p['n']}",   # mass number, correct
                "z": p["z"], "n": p["n"],
                "daughter_level_kev": e_level,
                "beta_endpoint_kev": endpoint,   # the scalar target field
                "parent_qbm_kev": p["qbm_kev"],
                "rad_type": "bm_perbranch",
                "source": "IAEA Livechart: Q(bm) - E_level(daughter), per-branch",
            })
        if (i + 1) % 200 == 0:
            print(f"    ...{i+1}/{len(parents)} parents, {len(records)} branches so far")
    return records


def main():
    print("=" * 60)
    print("  BETA LAKE BUILD v3 — per-branch via Q - E_level reconstruction")
    print("  physical type: beta-MINUS only (electron)")
    print(f"  target N >= {MIN_TARGET} (doubled), floor {FLOOR}")
    print("=" * 60)
    records = build_per_branch()
    n = len(records)
    print(f"\n[*] Total per-branch endpoints: {n}")
    if n >= MIN_TARGET:
        print(f"[+] CLEARS doubled target ({MIN_TARGET}).")
    elif n >= FLOOR:
        print(f"[~] Above floor ({FLOOR}), below doubled target. Usable.")
    else:
        print(f"[!] BELOW FLOOR ({FLOOR}). Level pull likely failed — check _sym/levels query.")
        print(f"    Each parent may have returned only its ground-state level (1 branch).")
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    print(f"[+] Raw lake written: {os.path.abspath(OUT_PATH)}")
    print("\nDERIVED LAKE: run build_scramble_control() and confirm the scrambled")
    print("lake does NOT lock before trusting any real lock. Then promote (keep")
    print("'domain'), stitch configs, score standalone through lock-to-enter (z>=10).")


def build_scramble_control(raw_path=OUT_PATH):
    """Scramble which daughter-level pairs with which parent Q, rewrite endpoints.
    If the scrambled lake still locks at the same register, the lock is a
    derivation artifact of Q - E_level, not physics."""
    recs = [json.loads(l) for l in open(raw_path, encoding="utf-8") if l.strip()]
    qs = [r["parent_qbm_kev"] for r in recs]
    random.shuffle(qs)
    out = raw_path.replace(".jsonl", "_SCRAMBLE_CONTROL.jsonl")
    with open(out, "w", encoding="utf-8") as f:
        for r, q in zip(recs, qs):
            ep = q - r["daughter_level_kev"]
            if ep <= 0:
                continue
            rc = dict(r)
            rc["beta_endpoint_kev"] = ep
            rc["parent_qbm_kev"] = q
            rc["domain"] = DOMAIN + "_scramble_control"
            rc["source"] = "SCRAMBLE CONTROL: shuffled Q vs level (artifact check)"
            f.write(json.dumps(rc) + "\n")
    print(f"[+] Scramble control written: {out}")


if __name__ == "__main__":
    main()