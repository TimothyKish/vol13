# Vol 12 Integrated Config — Audit Record (rev 2)

**Prepared by:** Atlas (Chief Experimental Architect)
**Status:** Proposal. Not run. One blocking question outstanding (item 1).
**Supersedes:** rev 1. Paths now verified against filesystem tree; field paths verified
against lake schemas by `scripts/inspect_schema.py`.

| | rev 1 | rev 2 |
|---|---|---|
| Lakes in table | 80 | 82 |
| Enabled | 63 | 55 |
| Gated / retired | 17 | 27 |
| Distinct enabled domains | 61 | 53 |
| Ordered pairs | 3,660 | 2,756 |
| Masked as same-object | 0 | 110 |
| **Pinch combinations** | **84,180** | **60,858** |

---

## 1. BLOCKING — the engine may not be reading the configured field

Evidence from the regression run of 2026-08-16:

- `s2_stellar_kinematics` record 1 stores `meta.val_raw_kms = 54.72644642484259`.
- `log(1 + 54.726) / log(k_geo)` = **2.469781**, which equals the lake's stored `meta.scalar_raw` exactly.
- The lake also stores `scalar_klc = 2.670401629977723`, which equals
  `scalar_raw − sector_mean + global_mean` = `2.469781 − 0.892351 + 1.092971`. Exact.
- The regression run reported domain `mean = 1.092971`.
- The lake's metadata stores `meta.global_mean = 1.092971`. **Identical to six decimals.**

Meanwhile `scalarize.json` was asking that domain for `v_perp`, a field that does not
exist in the lake at any nesting depth.

The straightforward reading is that the engine consumed the precomputed, sector-normalized
`scalar_klc` rather than computing from the configured field. This also explains the
negative domain minimum (−0.1935) flagged in rev 1: it is a normalization offset, not a
negative velocity.

**Why it matters.** Three lakes carry `sector_normalized: true` — `s1_gaia_parallax`,
`s2_stellar_kinematics`, `g1_galaxy_kinematics`. If `scalar_klc` is what gets scored, then
the stellar, stellar-kinematic and galactic results were computed on values that had a
per-sector mean shift applied before hypothesis testing. `s2`'s own metadata carries the
note: *"val field was computed before hypothesis testing. PHYSICAL lake preceded mixture
audit per Phoenix audit trail."*

**Required before anything else:** read `engine/scalarize.py` and establish
(a) whether `field` in `scalarize.json` controls the read at all,
(b) whether there is a fallback to `scalar_klc` when the field is absent,
(c) whether dotted paths (`_raw_payload.vdisp`) resolve.

If there is a silent fallback, it must become a hard failure. A domain that reports
`nonzero = n` while reading a different quantity than configured is worse than one that
reports zeros, because zeros are visible and this is not.

---

## 2. Vol 11 defect confirmed — pulsar rotation

`k2_pulsar_periods` carries `p0_ms` (at `_raw_payload.p0_ms` and `meta.p0_ms`).
It does **not** carry `period_days`.

Vol 11 pooled `k1_kepler_rotation` and `k2_pulsar_periods` into one `stellar_rotation`
domain reading `period_days`. K1 has `prot_days`, K2 has `p0_ms`. **Neither lake has the
field Vol 11 asked for.**

Vol 11 `stellar_rotation` results should not be cited until it is established what the
engine actually read. Rev 2 splits the domain: `stellar_rotation_kepler` → `meta.prot_days`,
`stellar_rotation_pulsar` → `_raw_payload.p0_ms`.

*(Note: `_raw_payload.prot_days` is the string `"1.532"`, not a number. `meta.prot_days` is
the float. Config uses the float.)*

---

## 3. Same-object families — 110 pairings masked

The lakes disclose this themselves. `s3_gaia_luminosity` states it covers the same 1.81M
stars as `s1` and `s2`; `s4_gaia_colour` lists `same_object_lakes: [s1, s2, s3]`; `p2` and
`p3` list `[p1]` and `[p1, p2]`.

Rev 1 treated all of these as independent domains. They are not. `s3 × s4` is luminosity
against colour on one stellar population — the Hertzsprung–Russell relation, known since
1911. Inside 3,660 pairings that reads as a cross-domain lock.

Rev 2 adds `same_object_group` to `volumes.json` and a `__pinch_rule__` requiring the pinch
builder to mask within-group pairings. Groups among enabled lakes:

| group | lakes |
|---|---|
| `gaia_dr3_1.81M` | s1, s2, s4 |
| `nasa_exo_pscomppars` | p1, p2, p3, p4, p_ecc, p_incl, p_transit, p1_wrongbox |
| `atnf_pulsars` | k2, k2a, k2b, k2c, k2d, k2_wrongbox |
| `sdss_dr16_galaxies` | g1, g1b, g1c |
| `cms_dimuon` | h1, h1b, h1c, h1d |

**This masking is not yet implemented in the engine.** `build_pinch_table.py` must read
`same_object_group` and skip those pairings, or the mask is decorative.

---

## 4. Path corrections from the filesystem tree

- `p1_wrongbox` → **`lakes/inputs_promoted/p1_wrong_promoted.jsonl`**. The file was never
  missing; rev 1 asked for the wrong name. Not a rebuild.
- `p_eccentricity` → `p_ecc_promoted.jsonl`, `p_inclination` → `p_incl_promoted.jsonl` (confirmed present).
- All other enabled lakes follow `{lake}_promoted.jsonl` and are confirmed on disk.

Present on disk but absent from every prior config, now listed and gated pending a ruling:
`np1_orbital_periods_promoted.jsonl` (a sovereign orbital null — `chaos_null_null_orbital.jsonl`
exists in `synthetic/`, so it has been scored at some point), `b5_pdb_protein_promoted.jsonl`,
and `ligo_coherence_NOISE_CONTROL.jsonl`.

---

## 5. Field resolutions — 15 config fixes, 1 genuine rebuild

Rev 1 reported 18 field failures. After recursive inspection:

**Resolved by repointing (no rebuild):** `frb_chime`, `g1_galaxy_kinematics`,
`k2_pulsar_periods`, `k1_kepler_rotation`, `p1_orbital_periods`, `p2_orbital_radius`,
`p3_planet_mass`, `q3_molecular_vibration`, `q9_c60`, `s1_gaia_parallax`,
`s2_stellar_kinematics`, `s4_gaia_colour`, `t2_planetary`, `t4_cosmological`,
plus the `p1_wrongbox` path fix.

`t2_planetary` and `t4_cosmological` sit **four levels deep**
(`meta.source_row.meta.source_row.raw_payload.*`) from repeated re-promotion.
`scripts/unwrap_t_series.py` already exists and would flatten these — cleaner than a
four-level accessor.

**Genuine rebuild — one lake:** `chemistry`. Its `_raw_payload` is
`{zinc_id, n_atoms, max_radius, scalar_invariant}` — no bond length at any depth, despite
the config describing ZINC/CCCBDB bond lengths. Worse: `scalar_klc` = `scalar_invariant`
= 0.22046264235717844, **bit-identical**. No log transform was ever applied. Whatever the
chemistry domain has reported since Vol 5, it is not a `log(1+x)/log(k_geo)` scalar of a
bond length.

**Deferred, not rebuilds:** `materials` (derived field, formula already documented in the
lake's own RCA note — `bond_length = (volume/nsites)^(1/3)` — needs engine support);
`q2_molecular_geometry` (value present at `_raw_payload.value` but needs a
`measurement_type` filter so bond lengths aren't mixed with other measurement types);
`s3_gaia_luminosity` (candidates present but the `scalarization_formula` string was
truncated in the dump — need the full text).

---

## 6. Lakes gated for producing undefined output

These passed the field check in rev 1 and are still wrong.

| lake | defect | consequence |
|---|---|---|
| `g1a_radius` | min = **−9999** sentinel | `log(1 − 9999)` undefined |
| `b4_pdb_protein` | angles span **[−180, 180]** | undefined below −1, ~half the records |
| `b5_pdb_full_protein` | same | same, 6.8M records |
| `s2_wrongbox` | raw `v_perp` max **3.70 × 10¹⁰ km/s** ≈ 123,000 × c | wrong *data*, not wrong *math* |

A wrongbox exists to apply wrong mathematics to correct data. `s2_wrongbox` fails that
premise and cannot function as a falsification lane in its current state.

**Null family inconsistency:** `n1`, `n2`, `n3` all return `scalar_klc` range **[0, 0]** —
constant zero, which has no variance and is not a null distribution. `n4` returns
[2.32227, 2.60422]. One of these behaviours is wrong. Note `t4_cosmological` record 1 has
`scalar_kls = 2.3222363`, which is the lower bound of the N4 range; worth confirming N4 is
not derived from the real cosmology lake.

---

## 7. `q1_atomic_spectra` — gated, and the rev 1 "disjoint" verdict was invalid

The rev 1 overlap test reported DISJOINT. That result compared 151,839 wavelengths against
an **empty set** — `q1` returned zero records because its field was nested too. Zero
records in, zero overlap out. The verdict was a null result misread as a finding.

Direct inspection now shows both lakes drawing NIST ASD on the **same H I line**:
`q1` has `_raw_payload.wavelength_nm = 91.232366`; `L_emission_nist` covers
`upper_energy_cm1 = 109610.2232`, and 91.232366 nm ↔ 109610.2232 cm⁻¹ are the same
transition.

Separately, `q1`'s own metadata says its scalarization is
`log(upper_energy_cm1 + 1)/log(k_geo)` — and `scalar_kls = 7.128809` back-solves to 109,610,
confirming it. So the config calls this domain *wavelength* while the lake computed
*upper-state energy*. Config and provenance disagree about what the domain contains.

Stays disabled.

---

## 8. Pre-flight sequence

1. **Resolve item 1.** Read `engine/scalarize.py`. Nothing below is meaningful until the
   engine's field-resolution behaviour is known.
2. Implement `same_object_group` masking in `build_pinch_table.py`.
3. Run `scripts/unwrap_t_series.py` on T2/T4 rather than relying on four-level accessors.
4. **Unify only.** Abort if any lake reports `nonzero < n`. Do not proceed to chaos/pinch.
5. Confirm disk and RAM. Regression wrote ~923 bytes/record; a 30M-record master is roughly
   28 GB, and the pinch stage loads the whole file into memory before compressing to
   32-bit arrays.

**Rulings needed from Mondy before the run:** the b4/b5 dihedral formula (item 6); whether
sector-normalized lakes may be scored at all (item 1); the null family inconsistency (item 6);
whether `np1_orbital_periods` enters the table (item 4).
