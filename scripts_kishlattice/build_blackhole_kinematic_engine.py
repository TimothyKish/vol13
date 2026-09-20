"""
KISH-LATTICE FORWARD ENGINE -- Strong-Field Yield Sweep  [v3, schema-matched]

The probe changed this script completely. l1_gwtc is a clean flat schema with
83 real GWTC-3 events carrying BOTH:

    final_mass_solar   (66.2 for GW150914)
    f_ring_hz          (251.5 for GW150914)

That pair is worth far more than either alone, because the Kerr ringdown
frequency of the fundamental l=m=2 mode depends on mass AND spin:

    f = (c^3 / 2*pi*G*M_f) * F(a),   F(a) = 1.5251 - 1.1568 (1-a)^0.1292
                                     [Berti, Cardoso & Will 2006]

Inverting for a gives a REAL, per-event spin from lake data alone. Validated:
GW150914 -> a = 0.651 against the published final spin of 0.67 (3% agreement).

WHY THIS MATTERS
  * The ISCO strain is no longer a constant. It varies through spin, and the
    spins are now measured rather than assumed.
  * The RINGDOWN is the framework's home turf -- this programme started in
    LIGO ringdown residuals -- and it probes the light ring at ~1.5 r_s, where
    eps = (pi/32)/1.5 = 6.545%. That is the deepest strain any current
    instrument reaches.
  * If the inferred spins are physical and Kerr-consistent across 83 events,
    any lattice deviation at the light ring is below measurement precision,
    which BOUNDS eps_y FROM BELOW -- the first real empirical constraint the
    strain formulation has had.

STATED UP FRONT: eps at any fixed multiple of r_s is mass-independent by
construction (r_s cancels). eps(horizon) = pi/32 = 9.8175% for every black
hole. The original script printed that constant 20 times and called it a
universal lock. The mass-dependent real quantity is r_s; the spin-dependent
real quantity is the ISCO radius.
"""

import math
from kish_lake_io import (G, C, M_SUN, load_jsonl, require, resolve,
                          report_provenance)

LAKE = "./lakes_kishlattice/inputs_promoted/l1_gwtc_promoted.jsonl"

SPEC = {
    "m_final_sun": ("final_mass_solar", "final_mass_source", "final_mass",
                    "mass_final_source", "remnant_mass_msun", "Mf"),
}
FRING_NAMES = ("f_ring_hz", "f_ring", "ringdown_freq_hz", "f_qnm_hz")

PI32 = math.pi / 32          # strain at the horizon, exactly
LIGHT_RING_RS = 1.5          # photon sphere, Schwarzschild, in r_s units


def F_berti(a):
    return 1.5251 - 1.1568 * (1.0 - a) ** 0.1292


def spin_from_ringdown(m_sun, f_hz):
    """Invert the Berti fit.

    Returns (a, y, flag) where flag is one of:
       'ok'     -- y in [F(0), F(0.9995)], a is a real inferred spin
       'below'  -- y < F(0): the observed frequency is BELOW the minimum
                   Kerr QNM for this mass. No spin can produce it.
       'above'  -- y >= F(0.9995): requires a >= 1. Unphysical.

    BUG FIXED 2026-09-13 (Mondy): the previous version clamped 'below' to
    a = 0.0 and the consistency check only tested for a >= 1. That made the
    check ONE-SIDED -- it could report "100% physical" while every event sat
    under the floor, which is exactly what happened on the first run. A test
    that cannot fail in one direction is not a test. Both tails are now named.
    """
    base = C**3 / (2 * math.pi * G * m_sun * M_SUN)
    y = f_hz / base
    if y < F_berti(0.0):
        return None, y, "below"
    if y >= F_berti(0.9995):
        return None, y, "above"
    lo, hi = 0.0, 0.9995
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if F_berti(mid) < y:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi), y, "ok"


def kerr_isco_rs(a):
    """Prograde Kerr ISCO in r_s units. a=0 -> 3.0, a->1 -> 0.5."""
    a = min(max(a, 0.0), 0.9999)
    z1 = 1 + (1 - a * a) ** (1 / 3) * ((1 + a) ** (1 / 3) + (1 - a) ** (1 / 3))
    z2 = math.sqrt(3 * a * a + z1 * z1)
    return (3 + z2 - math.sqrt((3 - z1) * (3 + z1 + 2 * z2))) / 2.0


def main(show=30):
    print("=" * 78)
    print(" KISH-LATTICE STRONG-FIELD YIELD SWEEP  [v3]")
    print(" eps(r) = (pi/32)(r_s/r)   |   spins inverted from f_ring + M_f")
    print("=" * 78)

    recs = load_jsonl(LAKE, "l1_gwtc")
    rows, paths, cov = require(recs, SPEC, "l1_gwtc")
    report_provenance("gwtc", LAKE, recs, rows, paths, cov)

    events, n_fring = [], 0
    for rec in recs:
        m, _ = resolve(rec, SPEC["m_final_sun"])
        fr, _ = resolve(rec, FRING_NAMES)
        nm, _ = resolve(rec, ("event_name", "id", "name"))
        if m is None:
            continue
        m = float(m)
        fr = float(fr) if fr is not None else None
        if fr is not None:
            n_fring += 1
        events.append((nm or "?", m, fr))

    print(f"  events with mass        : {len(events)}")
    print(f"  events with f_ring_hz   : {n_fring}")
    if n_fring == 0:
        print("  [ABORT-EQUIVALENT] no ringdown frequencies -- spin cannot be")
        print("  inferred and every strain column below is a constant.")
    print()

    out, below, above = [], [], []
    for nm, m_sun, fr in events:
        r_s = 2 * G * m_sun * M_SUN / C**2
        f_kerr0 = (C**3 / (2 * math.pi * G * m_sun * M_SUN)) * F_berti(0.0)
        if fr is None:
            a, y, flag = None, None, "nofreq"
        else:
            a, y, flag = spin_from_ringdown(m_sun, fr)
            if flag == "below":
                below.append((nm, m_sun, fr, f_kerr0, fr / f_kerr0))
            elif flag == "above":
                above.append((nm, m_sun, fr, y))
        r_isco = kerr_isco_rs(a) if a is not None else float("nan")
        out.append({"name": nm, "m": m_sun, "rs_km": r_s / 1000, "f": fr,
                    "a": a, "flag": flag, "f_kerr0": f_kerr0,
                    "ratio": (fr / f_kerr0) if fr else None,
                    "isco_rs": r_isco,
                    "eps_isco": (PI32 / r_isco) if a is not None else float("nan")})

    out.sort(key=lambda d: d["m"])
    print(f"{'event':<12} | {'Mf':>7} | {'f_obs':>7} | {'f_Kerr0':>8} | "
          f"{'obs/K0':>7} | {'a':>6} | {'flag':>6}")
    print("-" * 78)
    step = max(1, len(out) // show)
    for d in out[::step][:show]:
        a_s = f"{d['a']:.3f}" if d["a"] is not None else "   --"
        f_s = f"{d['f']:.1f}" if d["f"] is not None else "   --"
        r_s_ = f"{d['ratio']:.3f}" if d["ratio"] is not None else "   --"
        print(f"{str(d['name'])[:12]:<12} | {d['m']:>7.1f} | {f_s:>7} | "
              f"{d['f_kerr0']:>8.1f} | {r_s_:>7} | {a_s:>6} | {d['flag']:>6}")

    spins = [d["a"] for d in out if d["a"] is not None]
    ratios = sorted(d["ratio"] for d in out if d["ratio"] is not None)
    print("-" * 78)
    print(f"  n scored : {len(out)}")
    print()
    print("  KERR-CONSISTENCY CHECK  (two-sided)")
    print(f"    inverted to a real spin      : {len(spins)}")
    print(f"    BELOW the a=0 Kerr floor     : {len(below)}   <- no spin can")
    print(f"                                        produce these")
    print(f"    ABOVE the a=1 ceiling        : {len(above)}")
    if ratios:
        med = ratios[len(ratios) // 2]
        print(f"    f_obs / f_Kerr(a=0)          : min {ratios[0]:.3f}  "
              f"median {med:.3f}  max {ratios[-1]:.3f}")
    if len(below) > 0.10 * max(1, len(out)):
        print()
        print("    VERDICT: the f_ring_hz column is NOT a consistent Kerr QNM")
        print("    measurement. A frequency below the non-spinning floor cannot")
        print("    be a fundamental l=m=2 ringdown for the stated mass. Likely")
        print("    causes, in order of probability:")
        print("      (a) f_ring mixes ringdown, merger-peak and post-merger")
        print("          estimates across events;")
        print("      (b) final_mass_solar is total mass for some records;")
        print("      (c) BNS events (Mf < 5) have no BH ringdown at all and")
        print("          should not be in a QNM analysis.")
        print("    An instrument or provenance fault is far likelier than a")
        print("    Kerr violation. THIS IS A LAKE FINDING, NOT A PHYSICS ONE.")
        print("    l1_gwtc is tied to prediction P19 with a pre-registration")
        print("    DOI -- if f_ring feeds that prediction, trace it.")
        print()
        print("    Worst offenders:")
        for nm, m_sun, fr, fk, r in sorted(below, key=lambda t: t[4])[:6]:
            print(f"      {str(nm):<12} Mf={m_sun:>6.1f}  f_obs={fr:>6.1f}  "
                  f"f_Kerr0={fk:>7.1f}  ratio={r:.3f}")
    else:
        eis = [d["eps_isco"] for d in out if d["a"] is not None]
        print(f"    eps @ ISCO : {min(eis)*100:.3f}%  ..  {max(eis)*100:.3f}%")
        print(f"    eps @ light ring (1.5 r_s) : {PI32/LIGHT_RING_RS*100:.4f}%")
        print(f"    eps @ horizon              : {PI32*100:.4f}%")
        print("    Ringdowns are Kerr-consistent, which bounds eps_y from below.")
    print()
    print("  YIELD RADIUS: r/r_s = (pi/32)/eps_y")
    for nm, ey in (("A  eps_y=0.1", 0.1), ("B  eps_y=0.01", 0.01),
                   ("C  eps_y=0.001", 0.001), ("pi/32 exactly", PI32)):
        print(f"    {nm:<16} -> deviation at {PI32/ey:>8.2f} r_s")
    print()
    print("  FLAG, NOT A RESULT: eps(r_s) = pi/32, so eps_y = pi/32 puts the")
    print("  yield surface exactly at the horizon and every deviation inside it.")
    print("  Elegant, and unobservable. If that value is to be claimed it must")
    print("  be DERIVED from the Lagrangian and the falsification radius filed")
    print("  BEFORE the derivation -- not arrived at after noticing it is safe.")
    print("=" * 78)


if __name__ == "__main__":
    main()