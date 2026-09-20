"""
KISH-LATTICE FORWARD KINEMATIC ENGINE -- Galactic Rotation  [CORRECTED]

WHAT CHANGED (Mondy cross-check, 2026-09-12):
  1. The original script loaded the galactic lake and then DISCARDED it,
     generating every printed value with random.uniform. Its own comment said
     so. That fallback is gone: this version aborts if the data is not there.
  2. a_0 is now DERIVED, not the fitted MOND value. The original hardcoded
     1.2e-10 while its comment claimed derivation from c/(2*pi*T_univ).
     Those differ by 11%. Both are computed and printed side by side, and the
     DERIVED one is the framework's prediction. Using the fitted value would
     be testing MOND against MOND.
  3. The comparison is now against OBSERVED rotation velocity. v_lat vs
     v_Kepler at a random radius is not a test of anything -- v_lat has no
     radius dependence, so its flatness is true by construction.

WHAT THIS NEEDS:
     baryonic (visible) mass  +  observed flat rotation velocity, per galaxy.
     SDSS velocity-dispersion lakes do NOT carry baryonic mass. The standard
     source is SPARC (Lelli, McGaugh & Schombert 2016): 175 galaxies with
     resolved curves and 3.6um stellar masses. If the lake aborts, that is
     the correct outcome and SPARC is what to promote next.
"""

import math
from kish_lake_io import (G, C, M_SUN, KPC, load_jsonl, require,
                          report_provenance)

LAKE = "./lakes_kishlattice/inputs_promoted/g1_galaxy_kinematics_promoted.jsonl"

# PROBE RESULT 2026-09-13 -- this lake CANNOT run the BTFR test, and the abort
# is the correct outcome. g1 carries, per record:
#     _raw_payload.vdisp   (SDSS velocity DISPERSION, km/s -- real, raw)
#     ra, dec, z, sector, kish_bin, weight
# There is no baryonic mass, no radius, and no rotation velocity. A dispersion
# is not a rotation curve.
#
# TWO REAL PATHS FORWARD:
#   (1) SPARC (Lelli, McGaugh & Schombert 2016): 175 galaxies, resolved
#       rotation curves + 3.6um stellar masses. The standard BTFR dataset.
#       This is the right lake to promote next.
#   (2) The dispersion analogue. MOND predicts a baryonic Faber-Jackson
#       relation sigma^4 = G*M_bary*a_0 of the SAME form. g1 already has
#       sigma for 1.84M galaxies -- it needs only M_bary joined in
#       (e.g. SDSS stellar masses from the MPA-JHU or Portsmouth catalogues
#       on the same objID). That would be a far larger test than SPARC.
#
# NOTE: g1's vdisp sits at _raw_payload.vdisp, which is the field Vol 12
# confirmed was always reachable -- g1 never went through the legacy fallback
# and is the one clean control in the kinematic tier. Keep it that way: use
# _raw_payload.vdisp, never meta.scalar_raw or the sector-normalized scalar.
SPEC = {
    "m_bary_sun": ("m_bary_msun", "mass_baryonic_msun", "m_star_msun",
                   "baryonic_mass", "Mbar", "mass_vis_msun", "logMbar"),
    "v_flat_kms": ("v_flat_kms", "vflat", "v_obs_kms", "vrot_kms",
                   "v_circ_kms", "Vflat"),
}

# --- a_0, derived rather than fitted -------------------------------------
# Framework route: a_0 = c / (2*pi*T_univ) with T_univ the Universal Cycle.
# The Atlas defines T_univ = 2*pi/omega_univ but never assigns a value, so
# we anchor it at the Hubble time and report the sensitivity.
H0_KM_S_MPC = 67.4
MPC = 3.0856775814913673e22
H0 = H0_KM_S_MPC * 1000 / MPC
A0_DERIVED = C * H0 / (2 * math.pi)
A0_MOND_FIT = 1.2e-10


def main(show=25):
    print("=" * 78)
    print(" KISH-LATTICE FORWARD ENGINE: GALACTIC ROTATION  [corrected]")
    print(" Harmonic limit:  v^4 = G * M_bary * a_0")
    print("=" * 78)
    print(f"  a_0 DERIVED  = c*H0/(2*pi) = {A0_DERIVED:.4e} m/s^2  "
          f"(H0 = {H0_KM_S_MPC} km/s/Mpc)")
    print(f"  a_0 MOND fit = {A0_MOND_FIT:.4e} m/s^2")
    print(f"  ratio derived/fitted = {A0_DERIVED/A0_MOND_FIT:.4f}  "
          f"({(A0_DERIVED/A0_MOND_FIT-1)*100:+.1f}%)")
    print("  The DERIVED value is the framework's prediction. Scoring with the")
    print("  fitted value would be testing MOND against MOND.")
    print("=" * 78)

    recs = load_jsonl(LAKE, "g1_galaxy_kinematics")
    rows, paths, cov = require(recs, SPEC, "g1_galaxy_kinematics")
    report_provenance("galactic", LAKE, recs, rows, paths, cov)

    out = []
    for row in rows:
        mb = row["m_bary_sun"]
        if mb <= 0:
            continue
        # tolerate log-mass columns
        m_kg = (10 ** mb if mb < 100 else mb) * M_SUN
        v_obs = row["v_flat_kms"] * 1000.0
        if v_obs <= 0:
            continue
        v_der = (G * m_kg * A0_DERIVED) ** 0.25
        v_fit = (G * m_kg * A0_MOND_FIT) ** 0.25
        out.append((m_kg / M_SUN, v_obs / 1000, v_der / 1000, v_fit / 1000))

    if not out:
        raise SystemExit("no rows survived positivity checks")

    out.sort(key=lambda t: t[0])
    print(f"{'M_bary (Msun)':>14} | {'v_obs':>8} | {'v_derived':>10} | "
          f"{'v_fitted':>9} | {'dex resid':>10}")
    print("-" * 78)
    step = max(1, len(out) // show)
    for mb, vo, vd, vf in out[::step][:show]:
        print(f"{mb:>14.3e} | {vo:>8.2f} | {vd:>10.2f} | {vf:>9.2f} | "
              f"{math.log10(vd/vo):>10.4f}")

    def stats(idx):
        res = [math.log10(t[idx] / t[1]) for t in out]
        n = len(res)
        mean = sum(res) / n
        sd = math.sqrt(sum((x - mean) ** 2 for x in res) / n) if n > 1 else 0.0
        return mean, sd

    md, sd_d = stats(2)
    mf, sd_f = stats(3)
    print("-" * 78)
    print(f"  n galaxies : {len(out):,}")
    print(f"  DERIVED a_0 : mean log10(v_pred/v_obs) = {md:+.4f} dex, "
          f"scatter = {sd_d:.4f} dex")
    print(f"  FITTED  a_0 : mean log10(v_pred/v_obs) = {mf:+.4f} dex, "
          f"scatter = {sd_f:.4f} dex")
    print()
    print("  HOW TO READ THIS:")
    print("   * The SCATTER is the test. Observed BTFR scatter is ~0.10 dex.")
    print("     a_0 only sets the zero point -- it cannot change the scatter,")
    print("     so matching scatter tests the v^4 law, not the lattice.")
    print("   * The OFFSET is where the derived a_0 is tested. A derived a_0")
    print("     11% low predicts a mean offset of log10(0.89^0.25) = -0.0128")
    print("     dex. If the observed offset matches that, the derivation is")
    print("     consistent; if it lands at 0.000, the data prefers the fitted")
    print("     value and the c*H0/(2*pi) route is disfavoured.")
    print("   * PRE-REGISTER which of those you expect BEFORE running on the")
    print("     full sample. This one is easy to read after the fact.")
    print("=" * 78)


if __name__ == "__main__":
    main()
