#!/usr/bin/env python3
# ==============================================================================
# trial_2b_sector_bound.py  (v3 -- correct bound)
#
# Pre-registered: Vol 12, Chapter 15. Referee ruling: Mondy, 2026-08-27 (Section E).
# The one test in the programme that can prove the Form C diagnosis (Erratum 4a,
# the withdrawal of stellar_kinematic) WRONG.
#
# FIELDS (confirmed from lake record):
#   raw velocity      : meta.val_raw_kms
#   sector label      : meta.sector           ("NW","NE","SW","SE")
#   normalised scalar : scalar_kls = ln(v_norm)/ln(k_geo)   (the Form C product)
#   normalisation     : v_norm shift = scalar_raw - sector_mean + global_mean
#                       (a per-sector ADDITIVE shift in scalar space)
#
# STATISTIC (period engine, register N/pi):
#   theta_j  = 2*pi * ln(v) / Delta_N ,   Delta_N = N*ln(k_geo)/(24*pi)
#   R        = | mean_j exp(i theta_j) |
#
# THE TWO QUANTITIES, per the ruling:
#
#   (1) FALSIFICATION TEST -- per-sector R_j on RAW velocity.
#       A per-sector additive shift ROTATES each sector's resultant but cannot
#       LENGTHEN it. So if the lock is real, it must already be present within
#       sectors, on raw values, before any shift.
#         PREDICT: every R_j ~ 1/sqrt(n_j)  (chance).
#         IF any R_j >> chance  => real per-sector periodicity exists, the
#         offsets only aligned it => FORM C DIAGNOSIS IS WRONG.
#
#   (2) THE BOUND (correct form) -- an algebraic identity, hence a check on the
#       code, not a hypothesis. Both sides use the SAME (normalised) data:
#         R_total(norm) = | sum_j (n_j/n) R_j(norm) e^{i psi_j} |
#                       <= sum_j (n_j/n) R_j(norm)
#       If the LHS exceeds the RHS, the implementation is wrong.
#
#   (3) THE FORM C MEASUREMENT -- report R on raw (pooled) vs R on normalised.
#       The gap is the amplification the sector shift produces. This is the
#       positive statement of the mechanism, not a pass/fail.
#
# Run from vol13/ :  python scripts/trial_2b_sector_bound.py
# ==============================================================================
import json, glob, math
import numpy as np

K = math.log(16/math.pi)

def get(o, path):
    cur = o
    for k in path.split('.'):
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return None
    return cur

def resultant_complex(lnx, N):
    """Return the COMPLEX mean resultant vector at register N (period engine)."""
    delta = N*K/(24*math.pi)
    return np.mean(np.exp(1j * 2*math.pi*lnx/delta))

def R_of(lnx, N):
    return abs(resultant_complex(lnx, N))

# ------------------------------------------------------------------ load
p = glob.glob('lakes/**/*s2_stellar_kinematics*promoted*.jsonl', recursive=True)[0]
raw, sec, kls = [], [], []
for line in open(p, encoding='utf-8'):
    line = line.strip()
    if not line:
        continue
    o = json.loads(line)
    v = get(o, 'meta.val_raw_kms')
    s = get(o, 'meta.sector')
    z = o.get('scalar_kls')
    if v is not None and v > 0:
        raw.append(float(v))
        sec.append(s if s is not None else '?')
        kls.append(float(z) if z is not None else np.nan)
raw = np.array(raw); sec = np.array(sec); kls = np.array(kls)

lnraw  = np.log(raw)          # ln of raw velocity
lnnorm = kls * K              # scalar_kls = ln(v_norm)/K  ->  ln(v_norm) = kls*K

print("="*72)
print("TRIAL 2b  --  SECTOR BOUND TEST   (Erratum 4a falsification)")
print("="*72)
print(f"  lake: {p}")
print(f"  n = {len(raw):,}   sectors: {sorted(set(sec))}")

N = 16
print(f"\n  register {N}/pi   Delta_N = {N*K/(24*math.pi):.6f}")

# ---- (1) FALSIFICATION TEST: per-sector R_j on RAW velocity ---------------
print(f"\n  (1) FALSIFICATION TEST -- per-sector resultant on RAW velocity")
print(f"  {'sector':>8}{'n_j':>12}{'R_j(raw)':>12}{'1/sqrt(n)':>12}{'ratio':>8}")
flagged = []
n_total = len(raw)
for s in sorted(set(sec)):
    m = sec == s
    if m.sum() < 30:
        continue
    Rj = R_of(lnraw[m], N)
    chance = 1/math.sqrt(m.sum())
    ratio = Rj/chance
    mark = "  <-- REAL PERIODICITY" if ratio > 4 else ""
    if ratio > 4:
        flagged.append((s, ratio))
    print(f"  {str(s):>8}{m.sum():>12,}{Rj:>12.5f}{chance:>12.5f}{ratio:>8.1f}{mark}")

# ---- (2) THE BOUND: both sides on the SAME (normalised) data --------------
valid = ~np.isnan(lnnorm)
R_total_norm = R_of(lnnorm[valid], N)
bound_norm = 0.0
for s in sorted(set(sec)):
    m = (sec == s) & valid
    if m.sum() < 30:
        continue
    bound_norm += (m.sum()/valid.sum()) * R_of(lnnorm[m], N)
print(f"\n  (2) IMPLEMENTATION CHECK -- triangle inequality on NORMALISED data")
print(f"      R_total(norm)              = {R_total_norm:.5f}")
print(f"      sum (n_j/n) R_j(norm)      = {bound_norm:.5f}")
ok = R_total_norm <= bound_norm + 1e-9
print(f"      R_total <= sum             : {'OK' if ok else '*** VIOLATED -> CODE BUG ***'}")

# ---- (3) THE FORM C MEASUREMENT: raw pooled vs normalised -----------------
R_raw_pooled = R_of(lnraw, N)
amp = R_total_norm / R_raw_pooled if R_raw_pooled > 0 else float('inf')
print(f"\n  (3) FORM C MEASUREMENT -- what the sector shift does")
print(f"      R(raw, pooled)             = {R_raw_pooled:.5f}")
print(f"      R(normalised)              = {R_total_norm:.5f}")
print(f"      amplification              = {amp:.1f}x")

# ---- verdict --------------------------------------------------------------
print("\n" + "="*72)
if flagged:
    print(f"  VERDICT: {len(flagged)} sector(s) show real periodicity on RAW velocity.")
    print("  The sector offsets ALIGNED pre-existing structure rather than")
    print("  creating it.  *** FORM C DIAGNOSIS (Erratum 4a) IS WRONG. ***")
    print("  The withdrawal of stellar_kinematic must be revisited. Report to Mondy.")
else:
    print("  VERDICT: every sector sits at chance on RAW velocity (R_j ~ 1/sqrt(n_j)).")
    print("  No sector carries independent periodicity, so no arrangement of")
    print(f"  offsets could align one -- yet the normalised data shows R = {R_total_norm:.3f},")
    print(f"  a {amp:.0f}x amplification produced by the per-sector shift alone.")
    print("  *** FORM C CONFIRMED AND MECHANISM-DEMONSTRATED. Erratum 4a stands. ***")
print("="*72)