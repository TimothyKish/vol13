"""
KISH-LATTICE FORWARD KINEMATIC ENGINE -- Planetary Strain Sweep  [CORRECTED]

WHAT CHANGED (Mondy cross-check, 2026-09-12):
  1. The random.uniform fallback is REMOVED. Missing fields abort the run.
  2. V_Kepler is printed BESIDE V_Lattice, because they are the same number.

     ALGEBRAIC IDENTITY -- stated up front so no reader mistakes it for a
     prediction:
         v_lat = c*sqrt((16/pi) * eps)  with  eps = (pi/32)(r_s/r)
               = c*sqrt(r_s/(2r)) = c*sqrt(GM/(c^2 r)) = sqrt(GM/r) = v_Kepler
     The two factors cancel exactly. The weak-field agreement is DEFINITIONAL,
     not derived: eps was defined by matching the Newtonian potential.
     The ratio column exists to prove the identity numerically, not to
     demonstrate a match.
  3. The real content is the STRAIN COLUMN and the O(eps^2) deviation, which
     is the only place the lattice can differ from Newton in this regime.
  4. "Bypassing the yield falsifier" removed -- a test with no power in a
     regime is not a pass in that regime.
"""

import math
from kish_lake_io import (G, C, M_SUN, AU, load_jsonl, require,
                          report_provenance)

LAKE = "./lakes_kishlattice/inputs_promoted/p2_orbital_radius_promoted.jsonl"

# PROBE RESULT 2026-09-13 -- read this before running.
#   pl_orbsmax IS present, but buried at
#       meta.source_row._raw_payload.pl_orbsmax
#   (three levels deep; the resolver is now recursive to reach it).
#   st_mass IS NOT PRESENT ANYWHERE. The promoted payload carries only
#       pl_name, hostname, pl_orbsmax, pl_orbsmaxerr1/2, sy_dist, disc_facility
#   so this engine WILL ABORT on m_star_sun, and that is the correct outcome.
#
# TO RUN IT, one of:
#   (a) re-pull p2 from NASA pscomppars including st_mass (one column), or
#   (b) join p1_orbital_periods on entity_id and derive M from Kepler's third
#       law, M = 4*pi^2 a^3 / (G P^2). Legitimate for the STRAIN column, but
#       do NOT then compare v_lat to v_Kepler -- that would be circular on top
#       of an identity that is already circular.
SPEC = {
    "r_au":       ("pl_orbsmax", "orbsmax", "semi_major_axis_au", "a_au",
                   "orbital_radius_au", "sma_au"),
    "m_star_sun": ("st_mass", "stellar_mass_sun", "host_mass_msun",
                   "m_star_solar", "st_mass_msun"),
}

# Candidate yield strains. eps_y is NOT derived -- it is the open parameter.
EPS_Y_SCENARIOS = {"A (0.1)": 0.1, "B (0.01)": 0.01, "C (0.001)": 0.001}


def main(show=25):
    print("=" * 78)
    print(" KISH-LATTICE FORWARD ENGINE: PLANETARY STRAIN SWEEP  [corrected]")
    print(" eps(r) = (pi/32)(r_s/r)      v_lat == v_Kepler identically")
    print("=" * 78)

    recs = load_jsonl(LAKE, "p2_orbital_radius")
    rows, paths, cov = require(recs, SPEC, "p2_orbital_radius")
    report_provenance("planetary", LAKE, recs, rows, paths, cov)

    out = []
    for row in rows:
        r = row["r_au"] * AU
        m = row["m_star_sun"] * M_SUN
        if r <= 0 or m <= 0:
            continue
        r_s = 2 * G * m / C**2
        eps = (math.pi / 32) * (r_s / r)
        v_lat = C * math.sqrt((16 / math.pi) * eps)
        v_kep = math.sqrt(G * m / r)
        out.append((row["r_au"], row["m_star_sun"], eps,
                    v_lat / 1000, v_kep / 1000))

    if not out:
        raise SystemExit("no rows survived positivity checks")

    out.sort(key=lambda t: t[0])
    print(f"{'r (AU)':>10} | {'M* (Msun)':>9} | {'eps(r)':>12} | "
          f"{'v_lat km/s':>11} | {'v_Kep km/s':>11} | {'ratio-1':>10}")
    print("-" * 78)
    step = max(1, len(out) // show)
    for r_au, m_s, eps, vl, vk in out[::step][:show]:
        print(f"{r_au:>10.4f} | {m_s:>9.3f} | {eps:>12.4e} | "
              f"{vl:>11.3f} | {vk:>11.3f} | {vl/vk - 1:>10.2e}")

    eps_all = [t[2] for t in out]
    eps_max, eps_min = max(eps_all), min(eps_all)
    resid = max(abs(t[3] / t[4] - 1) for t in out)

    print("-" * 78)
    print(f"  n scored            : {len(out):,}")
    print(f"  strain range        : {eps_min:.3e}  ..  {eps_max:.3e}")
    print(f"  max |v_lat/v_Kep-1| : {resid:.3e}   "
          f"(floating-point only -- the two are the same expression)")
    print()
    print("  O(eps^2) DEVIATION -- the only lattice-vs-Newton difference here.")
    print("  Assuming the elastic nonlinearity becomes O(1) at yield "
          "(kappa ~ 1/eps_y):")
    print(f"  {'scenario':<12} | {'max frac. deviation':>20} | "
          f"{'vs |beta-1| < 1e-4':>20}")
    print("  " + "-" * 60)
    for name, ey in EPS_Y_SCENARIOS.items():
        dev = eps_max / ey
        verdict = "below PPN bound" if dev < 1e-4 else "PPN-VISIBLE"
        print(f"  {name:<12} | {dev:>20.3e} | {verdict:>20}")
    print()
    print("  READ THIS CORRECTLY: solar-system strains are ~1e-9, so a")
    print("  quadratic term cannot show here for any plausible eps_y. This")
    print("  regime has NO POWER to discriminate. It is not a pass.")
    print("  The discriminating regime is eps >~ 1e-7: binary pulsars,")
    print("  the S2 orbit around Sgr A*, and GWTC ringdowns.")
    print("=" * 78)


if __name__ == "__main__":
    main()
