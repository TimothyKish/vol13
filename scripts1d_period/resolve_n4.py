#!/usr/bin/env python3
# ==============================================================================
# resolve_n4.py  --  Erratum 5 diagnostic
#
# Question: does n4_cosmological (the DESIGNATED NULL for the cosmology domain)
# carry the same scalar distribution as the real cosmology domain (t4)?
# If yes, the null IS the signal and both must be rebuilt/withdrawn before
# either enters the period engine.
#
# Run from vol13/ :  python scripts/resolve_n4.py
# ==============================================================================
import json, glob, math, os
import numpy as np

K = math.log(16/math.pi)

# ADDED 'scalar_kls' to the primary key search
def load_scalars(pattern, keys=('scalar_kls','klghs_scalar','scalar','scalar_raw','s','value','x','d_proxy','val_raw','invariant')):
    cands = glob.glob(pattern, recursive=True)
    if not cands:
        return None, None
    p = cands[0]
    
    if os.path.getsize(p) == 0:
        return p, np.array([])

    def find(o):
        if isinstance(o, dict):
            for k in keys:
                if k in o:
                    try:
                        return float(o[k])
                    except (ValueError, TypeError):
                        pass
            for v in o.values():
                r = find(v)
                if r is not None:
                    return r
        return None
        
    vals = []
    for line in open(p, encoding='utf-8'):
        line = line.strip()
        if not line:
            continue
        v = find(json.loads(line))
        if v is not None:
            vals.append(v)
    return p, np.array(vals)

print("="*66)
print("ERRATUM 5 DIAGNOSTIC  --  does the cosmology null reproduce its domain?")
print("="*66)

# scalarized lakes preferred; fall back to promoted + on-the-fly scalarize
pt, t4 = load_scalars('lakes/**/*t4_cosmological*scalarized*.jsonl')
pn, n4 = load_scalars('lakes/**/*n4_cosmological*scalarized*.jsonl')

if t4 is None or len(t4) == 0 or n4 is None or len(n4) == 0:
    print("  [!] Scalarized lakes empty or missing expected JSON keys.")
    print("  [!] Falling back to promoted lakes + raw log1p scalarize...")
    
    # Strictly search for raw values here so we don't double-math the scalars
    pt_r, t4r = load_scalars('lakes/**/*t4_cosmological*promoted*.jsonl',
                           keys=('d_proxy','val_raw','value','x'))
    pn_r, n4r = load_scalars('lakes/**/*n4_cosmological*promoted*.jsonl',
                           keys=('d_proxy','val_raw','value','x'))
    
    if t4r is None or n4r is None:
        print("  [X] PROMOTED LAKES NOT FOUND. Check directory tree.")
        raise SystemExit
        
    if len(t4r) > 0 and len(n4r) > 0:
        pt = pt_r
        pn = pn_r
        t4 = np.log1p(t4r)/K
        n4 = np.log1p(n4r)/K

print(f"\n  t4_cosmological : {pt}")
if len(t4) > 0:
    print(f"                    n={len(t4):,}  scalar range [{t4.min():.5f}, {t4.max():.5f}]")
else:
    print(f"                    n=0  [LAKE EMPTY OR SCALARIZATION FAILED]")

print(f"  n4_cosmological : {pn}")
if len(n4) > 0:
    print(f"                    n={len(n4):,}  scalar range [{n4.min():.5f}, {n4.max():.5f}]")
else:
    print(f"                    n=0  [LAKE EMPTY OR SCALARIZATION FAILED]")

if len(t4) == 0 or len(n4) == 0:
    print("\n" + "="*66)
    print("  VERDICT: CANNOT COMPARE. DATA EXTRACTION FAILED.")
    print("  The JSON payload does not match the expected field names.")
    print("="*66)
    raise SystemExit

lo_gap = abs(t4.min() - n4.min())
hi_gap = abs(t4.max() - n4.max())
print(f"\n  range endpoint agreement: |dmin|={lo_gap:.2e}  |dmax|={hi_gap:.2e}")

qs = np.linspace(0, 1, 21)
qt = np.quantile(t4, qs); qn = np.quantile(n4, qs)
max_q = np.abs(qt - qn).max()
print(f"  max quantile difference (21 pts): {max_q:.4e}")

print("\n" + "="*66)
if lo_gap < 1e-3 and hi_gap < 1e-3 and max_q < 1e-2:
    print("  VERDICT: NULL REPRODUCES THE DOMAIN.  Erratum 5 CONFIRMED.")
    print("  n4 is not an independent null. Both t4 and n4 must be rebuilt or")
    print("  withdrawn before either enters the period engine. null_cosmology")
    print("  STRONG at 15/pi is the null locking because the null is the data.")
else:
    print("  VERDICT: distributions DIFFER. n4 is a genuine null after all.")
    print("  The 15/pi STRONG needs a different explanation -- report to Atlas.")
print("="*66)