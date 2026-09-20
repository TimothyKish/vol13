#!/usr/bin/env python3
"""
KishLattice Vol 12 — config pre-flight audit.

Answers three questions WITHOUT running the pipeline:

  [A] MD5 sweep      -- which promoted lakes are byte-identical duplicates
  [B] Field presence -- does every enabled lake actually carry the field
                        scalarize.json asks it for  (catches silent zero-fill)
  [C] Overlap test   -- are q1_atomic_spectra and L_emission_nist the same
                        NIST source seen through wavelength vs frequency

Usage (from vol12 root):
    python scripts/preflight_audit.py
    python scripts/preflight_audit.py --full        # exact nonzero counts, slower

Requires volumes.json / scalarize.json in ./configs/
"""

import json, hashlib, os, sys, collections

# Step up one level from /scripts to the volume root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VOL_ROOT   = os.path.dirname(SCRIPT_DIR)

# Corrected to target 'configs' instead of 'config'
VOLUMES    = os.path.join(VOL_ROOT, "configs", "volumes.json")
SCALARIZE  = os.path.join(VOL_ROOT, "configs", "scalarize.json")
SAMPLE_N   = 2000          # lines sampled for field presence in fast mode
FULL       = "--full" in sys.argv
C_LIGHT    = 299792458.0   # m/s


def md5_of(path, chunk=1 << 20):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(chunk), b""):
            h.update(blk)
    return h.hexdigest()


def resolve(entry, lake):
    p = entry.get("path") or f"lakes/inputs_promoted/{lake}_promoted.jsonl"
    return os.path.join(VOL_ROOT, p.replace("\\", "/"))


def scan(path, field, full=False):
    """Return (n_lines, field_present, n_nonnull, vmin, vmax, keys)."""
    n = nn = 0
    vmin, vmax = None, None
    keys, present = set(), False
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f):
            if not line.strip():
                continue
            n += 1
            if i < SAMPLE_N or full:
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                if i < SAMPLE_N:
                    keys |= set(r.keys())
                if field in r:
                    present = True
                    v = r[field]
                    if isinstance(v, (int, float)) and not isinstance(v, bool):
                        nn += 1
                        vmin = v if vmin is None else min(vmin, v)
                        vmax = v if vmax is None else max(vmax, v)
            elif not full:
                pass
    return n, present, nn, vmin, vmax, keys


def main():
    vols = json.load(open(VOLUMES))["volumes"]
    doms = json.load(open(SCALARIZE))["domains"]

    enabled = {k: v for k, v in vols.items() if v.get("enabled")}
    print(f"\n{'='*78}\nVol 12 PRE-FLIGHT AUDIT   ({len(enabled)} enabled lakes)\n{'='*78}")

    # ---------- [A] MD5 sweep -------------------------------------------
    print(f"\n[A] MD5 SWEEP — byte-identical lakes are the same pull\n{'-'*78}")
    hashes = collections.defaultdict(list)
    sizes = {}
    for lake, e in sorted(vols.items()):
        p = resolve(e, lake)
        if not os.path.exists(p):
            if e.get("enabled"):
                print(f"  MISSING FILE   {lake:34s} -> {p}")
            continue
        h = md5_of(p)
        hashes[h].append(lake)
        sizes[lake] = os.path.getsize(p)
        print(f"  {h}  {sizes[lake]:>14,}  {lake}")

    dupes = {h: ls for h, ls in hashes.items() if len(ls) > 1}
    print(f"\n  DUPLICATE GROUPS: {len(dupes) if dupes else 'none'}")
    for h, ls in dupes.items():
        print(f"    IDENTICAL -> {', '.join(ls)}")

    # ---------- [B] Field presence --------------------------------------
    print(f"\n[B] FIELD PRESENCE — config asks for a field; does the lake have it?"
          f"\n{'-'*78}")
    print(f"  {'lake':<32}{'field asked':<28}{'lines':>12}  verdict")
    fails, checked = [], {}
    for lake, e in sorted(enabled.items()):
        p = resolve(e, lake)
        if not os.path.exists(p):
            continue
        field = doms.get(e["domain"], {}).get("field")
        if field is None:
            print(f"  {lake:<32}{'(no scalarize entry)':<28}{'':>12}  *** NO MAPPING ***")
            fails.append(lake)
            continue
        n, present, nn, vmin, vmax, keys = scan(p, field, FULL)
        checked[lake] = (n, present, nn, vmin, vmax, keys, field)
        if not present:
            near = [k for k in keys if field.lower().strip("_") in k.lower()
                    or k.lower() in field.lower()]
            print(f"  {lake:<32}{field:<28}{n:>12,}  *** FIELD ABSENT ***")
            print(f"      keys present: {sorted(keys)[:12]}")
            if near:
                print(f"      did you mean: {near}")
            fails.append(lake)
        else:
            rng = f"[{vmin:.6g}, {vmax:.6g}]" if vmin is not None else "(non-numeric)"
            flag = "  <-- NEGATIVE VALUES" if (vmin is not None and vmin < 0) else ""
            print(f"  {lake:<32}{field:<28}{n:>12,}  ok  {rng}{flag}")

    print(f"\n  LAKES FAILING FIELD CHECK: {len(fails)}")
    for lk in fails:
        print(f"    FAIL -> {lk}")
    if not fails:
        print("    none — every enabled lake resolves its configured field")

    # ---------- [C] q1 vs L_emission_nist overlap -----------------------
    print(f"\n[C] OVERLAP TEST — q1_atomic_spectra vs L_emission_nist\n{'-'*78}")
    q1p = resolve(vols.get("q1_atomic_spectra", {}), "q1_atomic_spectra")
    lep = resolve(vols.get("L_emission_nist", {}), "L_emission_nist")
    if not (os.path.exists(q1p) and os.path.exists(lep)):
        print("  one or both lakes not on disk — skipped")
    else:
        def pull(path, field, xform):
            out = set()
            tot = 0
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        r = json.loads(line)
                    except Exception:
                        continue
                    v = r.get(field)
                    if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0:
                        tot += 1
                        out.add(round(xform(v), 4))   # 4 dp in nm
            return out, tot

        wl_q1, n_q1 = pull(q1p, "wavelength_nm", lambda x: x)
        wl_le, n_le = pull(lep, "klghs_transition_freq_Hz",
                           lambda f_: (C_LIGHT / f_) * 1e9)

        inter = wl_q1 & wl_le
        denom = min(len(wl_q1), len(wl_le)) or 1
        frac = len(inter) / denom
        print(f"  q1_atomic_spectra   records={n_q1:,}  distinct wavelengths={len(wl_q1):,}")
        print(f"  L_emission_nist     records={n_le:,}  distinct wavelengths={len(wl_le):,}"
              f"   (converted c/f)")
        print(f"  shared wavelength values: {len(inter):,}"
              f"  ({frac*100:.1f}% of the smaller set)")
        if frac > 0.50:
            print("\n  VERDICT: SAME SOURCE. Cross-pinch between 'quantum' and")
            print("             'quantum_transitional' would be self-correlation.")
            print("             Keep q1_atomic_spectra DISABLED; L_emission_nist supersedes.")
        elif frac < 0.05:
            print("\n  VERDICT: DISJOINT. q1_atomic_spectra may be re-enabled.")
        else:
            print("\n  VERDICT: PARTIAL OVERLAP — needs a ruling, not an automatic call.")
            print("             Report the fraction to Mondy before re-enabling.")

    print(f"\n{'='*78}")
    print("GATE: do not proceed to chaos/pinch while any lake FAILS the field check.")
    print(f"{'='*78}\n")


if __name__ == "__main__":
    main()