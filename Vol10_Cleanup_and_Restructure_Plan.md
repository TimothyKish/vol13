# VOL 10 — CLEANUP AND RESTRUCTURE PLAN
# KishLattice Geometric Harmonic Spectroscopy
# Engine v10 Transition Document
# Prepared by Mondy Aurora Kish — May 2026
# ============================================================

## OVERVIEW

Vol 10 was copied from Vol 9 as the base. This document specifies every
structural change to make before any new lake is built or any engine code
is modified. Do the cleanup first. Then do the engine work. Then build lakes.
Order matters: a clean repo prevents carrying legacy confusion into new work.

## PHASE 1 — ROOT CLEANUP

### Delete these files from the vol10 root:
```
texput.log
Vol9_KLGHS_KishLattice_GeometricHarmonicSpectroscopy.aux
Vol9_KLGHS_KishLattice_GeometricHarmonicSpectroscopy.log
Vol9_KLGHS_KishLattice_GeometricHarmonicSpectroscopy.out
Vol9_KLGHS_KishLattice_GeometricHarmonicSpectroscopy.toc
Vol9_Pinch.txt
```

### Rename (keep as reference, rename to show origin):
```
Vol9_KLGHS_KishLattice_GeometricHarmonicSpectroscopy.tex
  -> reference/Vol9_KLGHS_paper_reference.tex

Vol9_KLGHS_KishLattice_GeometricHarmonicSpectroscopy.pdf
  -> reference/Vol9_KLGHS_paper_reference.pdf
```

### Create at root:
```
reference/               <- new folder for the above
LAKEGUIDE.md             <- new (build guide for sovereign lakes)
```

### Update at root:
```
README.md                <- update from Vol9 to Vol10 (separate task)
```

---

## PHASE 2 — ENGINE FOLDER (already moved, now extend)

Current engine/:
```
engine/
    build_chaos_nulls.py
    build_pinch_table.py
    scalarize.py
    unify.py
```

### Add to engine/:
```
engine/
    engine_version.py    <- NEW: 192-char fingerprint generator
```

engine_version.py computes:
  [scalarize.py MD5][unify.py MD5][build_chaos_nulls.py MD5][build_pinch_table.py MD5]
  [scalarize.json MD5][volumes.json MD5]
  = 192-character audit fingerprint

See engine_version.py specification below.

### Add .gitattributes at repo root:
```
*.py    text eol=lf
*.json  text eol=lf
*.md    text eol=lf
```
This ensures identical MD5 hashes on Windows and Linux.

---

## PHASE 3 — CONFIGS FOLDER

### Delete:
```
configs/volumes_With_Error_Materials.json    <- legacy error variant, no longer needed
configs/unify.json                           <- verify if still used; if not, delete
```

### Keep unchanged:
```
configs/schema.json
configs/volumes.json    <- will be updated with Vol 10 new lakes
```

### Create NEW:
```
configs/scalarize.json  <- NEW: config-driven dispatch (see spec below)
```

scalarize.json spec — initial skeleton for Vol 10:
```json
{
  "version": "10.0",
  "k_geo": 5.0929581789,
  "domains": {
    "nuclear_binding": {
      "field": "binding_energy_mev_per_A",
      "formula_type": "log_standard",
      "x0": 1.0,
      "description": "Nuclear binding energy per nucleon in MeV/A"
    },
    "nuclear_decay": {
      "field": "half_life_seconds",
      "formula_type": "log_standard",
      "x0": 1.0,
      "description": "Nuclear half-life in seconds"
    },
    "stellar_kinematic": {
      "field": "transverse_velocity_kms",
      "formula_type": "log_standard",
      "x0": 1.0,
      "description": "Stellar transverse velocity in km/s"
    },
    "planetary_atlantic": {
      "field": "interval_hours",
      "formula_type": "log_standard",
      "x0": 1.0,
      "description": "Atlantic tidal gap intervals in decimal hours"
    },
    "orbital": {
      "field": "period_days",
      "formula_type": "log_standard",
      "x0": 1.0,
      "description": "Exoplanet orbital period in days"
    },
    "quantum": {
      "field": "wavelength_nm",
      "formula_type": "log_standard",
      "x0": 1.0,
      "description": "Atomic emission wavelength in nm"
    },
    "galactic": {
      "field": "velocity_dispersion_kms",
      "formula_type": "log_standard",
      "x0": 1.0,
      "description": "Galaxy velocity dispersion in km/s"
    },
    "chemistry": {
      "field": "bond_length_angstrom",
      "formula_type": "log_standard",
      "x0": 1.0,
      "description": "Molecular bond length in Angstroms"
    },
    "materials": {
      "field": "bond_length_angstrom",
      "formula_type": "log_standard",
      "x0": 1.0,
      "description": "Crystal bond length in Angstroms"
    },
    "biology_backbone": {
      "field": "angle_degrees",
      "formula_type": "log_standard",
      "x0": 1.0,
      "description": "Protein backbone dihedral angle in degrees (Vol 10 NEW)"
    },
    "seismic_temporal": {
      "field": "interval_days",
      "formula_type": "log_standard",
      "x0": 1.0,
      "description": "Seismic event temporal interval in days (Vol 10 NEW)"
    },
    "subnuclear_mass": {
      "field": "invariant_mass_gev",
      "formula_type": "log_standard",
      "x0": 1.0,
      "description": "LHC invariant mass in GeV (Vol 10 NEW)"
    },
    "orbital_ttv": {
      "field": "timing_variation_minutes",
      "formula_type": "log_standard",
      "x0": 1.0,
      "description": "Transit timing variation in minutes (Vol 10 NEW)"
    }
  }
}
```

NOTE: The remaining domain entries (all Vol 9 domains not listed above) are added
by Lyra when the full scalarize.json is built. The above covers the new Vol 10
domains and the highest-priority existing domains as a starting skeleton.

---

## PHASE 4 — LAKES FOLDER CLEANUP

### Delete from lakes/inputs_promoted/:
```
frb_master_promoted.jsonl           <- superseded by frb_chime_promoted.jsonl
t3_stellar_promoted.jsonl           <- not in active pipeline (disabled in volumes.json)
b2_codon_promoted.jsonl             <- not enabled (b2 is disabled)
materials_promoted_litmus.jsonl     <- litmus test artifact, not pipeline input
materials_promoted_With_Error.jsonl <- error-state artifact, not pipeline input
```

### Keep all 37 active promoted files unchanged.

### Delete from lakes/unified/:
```
frb_master_scalarized.jsonl         <- matches deleted promoted file
t3_stellar_scalarized.jsonl         <- matches disabled lake
b2_codon_scalarized.jsonl           <- matches disabled lake
unified_master_With_Error_Materials.jsonl <- error-state artifact
```

### Keep:
```
lakes/synthetic/    <- ALL files kept (chaos and scramble nulls are reference data)
lakes/raw_archive/  <- ALL files kept (sovereign archive, never delete)
lakes/logs/         <- keep (will accumulate Vol 10 logs)
```

---

## PHASE 5 — SERIES FOLDER CLEANUP

Strategy: Move legacy-only series to a new archive/ folder rather than deleting.
Reason: The research history is scientifically valuable. The methods that did not
work are as important as the ones that did. Archive, do not destroy.

### Create:
```
archive/legacy_series/
```

### Move these entire series folders to archive/legacy_series/:

S-Series legacy (keep S1, S2, S3, S4 in place — these are active):
```
S-Series/NS1_GaiaParallax/          <- empty, move
S-Series/NS6_5_Unification/         <- legacy experiment
S-Series/NS6_7/                     <- legacy experiment (large)
S-Series/S2_GalacticFull/           <- empty
S-Series/S5_Galactic/               <- empty
S-Series/S6_2_Normalized/           <- legacy
S-Series/S6_3_DeepLock/             <- legacy
S-Series/S6_4_FinalSeal/            <- legacy
S-Series/S6_5_Unification/          <- legacy
S-Series/S6_Galactic/               <- legacy
S-Series/G1_HyperLeda_Galaxy/       <- legacy galaxy source
S-Series/V6_2_Isotope/              <- legacy
S-Series/V6_3_Pinch/                <- legacy
S-Series/V6_AntiLife/               <- legacy
S-Series/S7_Solar/                  <- legacy scripts (K3 is the active solar lake)
```

B-Series legacy:
```
B-Series/NB1_Biology/               <- empty
B-Series/NB2_Biology/               <- empty
B-Series/NB3_Biology/               <- empty
B-Series/B2_Biology/                <- b2_codon disabled; archive scripts and raw
```

P-Series legacy:
```
P-Series/NP1_2_NormalizedNull/      <- legacy null variant
P-Series/NP1_3_AnarchistNull/       <- legacy null variant
P-Series/NP1_PlanetaryNull/         <- empty
P-Series/P1_2_Normalized/           <- legacy normalized variant
P-Series/P2_Planetary/              <- scripts folder with legacy methods
```

Q-Series legacy:
```
Q-Series/NQ1_AtomicSpectra/         <- empty
Q-Series/NQ2_MolecularGeometry/     <- empty
Q-Series/NQ1_SpectraNull/           <- legacy null
Q-Series/NQ2_MolecularNull/         <- legacy null
Q-Series/NQ2_2_UnconstrainedNull/   <- legacy null
Q-Series/Q1_Spectra/                <- legacy (Q1_AtomicSpectra is active)
Q-Series/Q2_Molecular/              <- legacy (Q2_MolecularGeometry is active)
Q-Series/Q_Refereed_Vol1/           <- historical reference; archive
```

G-Series legacy:
```
G-Series/G2_GalaxyLuminosity/       <- legacy (G2_WMAP is the active g2)
G-Series/G2_Luminosity/             <- empty
G-Series/NG1_GalaxyKinematics/      <- empty
```

### Keep active series exactly as-is:
```
B-Series/B1_Biology/    (b1_chirality — active)
B-Series/B3_Biology/    (b3_amino — active)
C-Series/               (chemistry — active)
FRB_Calibration_Network/ (frb_chime — active)
G-Series/G1_GalaxyKinematics/  (g1 — active)
G-Series/G2_WMAP/       (g2_wmap — active)
K-Series/               (k1, k2, k3 — all active)
L-Series/L1_GWTC/       (l1 — active)
LIGO-Series/            (historical reference — keep)
M-Series/               (materials — active)
N-Series/               (n1, n2, n3, n4 — active nulls)
P-Series/P1_Planetary/  (p1 — active)
P-Series/P2_OrbitalRadius/ (p2 — active)
P-Series/P3_PlanetMass/ (p3 — active)
Q-Series/Q1_AtomicSpectra/ (q1 — active)
Q-Series/Q2_MolecularGeometry/ (q2 — active)
Q-Series/Q3_MolecularVibration/ (q3 — active)
Q-Series/Q4_Nuclear/    (q4 — active)
Q-Series/Q5_Decay/      (q5 — active)
Q-Series/Q8_Ionisation/ (q8 — active)
Q-Series/Q9_C60/        (q9 — active)
S-Series/S1_GaiaParallax/ (s1 — active)
S-Series/S1_Galactic/   (s1 legacy structure — keep, it has history)
S-Series/S2_StellarKinematics/ (s2 — active)
S-Series/S3_GalacticNASA/ (s3 luminosity — active)
S-Series/S4_AstroMaster/ (s4 colour — active)
T-Series/               (t1, t2b, t2c, t2d, t2g, t4 — all active)
```

---

## PHASE 6 — NEW VOL 10 SERIES FOLDERS

Create these new series folders with the standard four-script structure:

### B4_PDB — Protein Backbone Ramachandran Angles
```
B-Series/B4_PDB/
    figures/
    lake/
    scripts/
        build_lake.py
        promote.py
        validate.py
```
Source: RCSB PDB REST API — https://data.rcsb.org/
Target domain: biology_backbone
Expected register: 7/pi (shelf 7) and 13/pi (shelf 13)
Records expected: 50,000,000+ individual phi/psi angle pairs
Scalar formula: log(1 + angle_degrees) / log(k_geo)
Pre-registration: P_protein from Vol 9 paper

### U1_USGS — Seismic Temporal Gaps
```
U-Series/                <- NEW top-level series
U-Series/U1_USGS/
    figures/
    lake/
    scripts/
        build_lake.py       <- separate builds per fault system
        build_san_andreas.py
        build_cascadia.py
        build_japan_trench.py
        build_anatolian.py
        promote.py
        validate.py
```
Source: USGS Earthquake Catalog — https://earthquake.usgs.gov/fdsnws/event/1/
Target domain: seismic_temporal
Sub-lakes: each major fault system as sovereign sub-lake
Expected register: 17/pi–18/pi (tidal kinematic family)
Records: 3,500,000+ events M>=5.0, 50-year windows
Pre-registration: P_seismic from Vol 9 paper

### H1_CERN — LHC Invariant Mass
```
H-Series/                <- NEW top-level series
H-Series/H1_CERN/
    figures/
    lake/
    scripts/
        build_lake.py
        promote.py
        validate.py
        README.md           <- note ROOT/awkward-array dependency
```
Source: CERN Open Data Portal — https://opendata.cern.ch/
Datasets: CMS di-muon Run2, ATLAS di-electron Run2
Target domain: subnuclear_mass
Expected register: 21/pi OR new sub-nuclear register
Records: 10,000,000–50,000,000 collision events
Pre-registration: P_subnuclear from Vol 9 paper
TECHNICAL NOTE: Requires upfront scalar design validation.
  log(1 + mass_gev) / log(k_geo) compresses the Standard Model
  mass spectrum. Validate binning against litmus before admitting to pipeline.

### P4_TTV — Transit Timing Variations
```
P-Series/P4_TTV/
    figures/
    lake/
    scripts/
        build_lake.py
        promote.py
        validate.py
```
Source: NASA ExoFOP — https://exofop.ipac.caltech.edu/
Target domain: orbital_ttv
Expected register: 22/pi (orbital family)
Records: 1,000,000+ individual transit timing measurements
Pre-registration: P_ttv from Vol 9 paper

### L2_NANOGrav — Pulsar Timing Array
```
L-Series/L2_NANOGrav/
    figures/
    lake/
    scripts/
        build_lake.py
        promote.py
        validate.py
```
Source: NANOGrav 15yr dataset — https://nanograv.org/
Target domain: gravitational_bg
Expected register: 16/pi (kinematic family — GW propagation)
Records: ~500 pulsars × years of timing residuals
Pre-registration: Vol 11 (this is stretch target for Vol 10)

---

## PHASE 7 — ENGINE WORK (after cleanup is complete)

### Priority 1: engine_version.py

```python
# engine/engine_version.py
import hashlib
import sys
from pathlib import Path

def md5_file(filepath):
    """MD5 of file bytes. Platform-independent provided LF line endings enforced."""
    h = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

def compute_engine_version(base_dir=None):
    """
    Returns 192-character engine fingerprint.

    Segments (32 chars each):
      [0:32]    engine/scalarize.py
      [32:64]   engine/unify.py
      [64:96]   engine/build_chaos_nulls.py
      [96:128]  engine/build_pinch_table.py
      [128:160] configs/scalarize.json
      [160:192] configs/volumes.json

    Also accepts 128-char legacy strings (scripts only).
    """
    if base_dir is None:
        base_dir = Path(__file__).parent.parent

    files = [
        base_dir / 'engine' / 'scalarize.py',
        base_dir / 'engine' / 'unify.py',
        base_dir / 'engine' / 'build_chaos_nulls.py',
        base_dir / 'engine' / 'build_pinch_table.py',
        base_dir / 'configs' / 'scalarize.json',
        base_dir / 'configs' / 'volumes.json',
    ]

    missing = [f for f in files if not f.exists()]
    if missing:
        raise FileNotFoundError(f"Missing engine files: {missing}")

    return ''.join(md5_file(f) for f in files)

def parse_engine_version(version_string):
    """Break version string into named components."""
    n = len(version_string)
    assert n in (128, 160, 192), f"Invalid version string length: {n}"

    result = {
        'scalarize_py':        version_string[0:32],
        'unify_py':            version_string[32:64],
        'build_chaos_nulls_py': version_string[64:96],
        'build_pinch_table_py': version_string[96:128],
    }
    if n >= 160:
        result['scalarize_json'] = version_string[128:160]
    if n == 192:
        result['volumes_json']   = version_string[160:192]
    return result

def verify_engine_version(reported_version, base_dir=None):
    """
    Compare reported version string against current files.
    Returns (match: bool, changed_components: list).
    """
    n = len(reported_version)
    current = compute_engine_version(base_dir)[:n]
    match = (current == reported_version)

    changed = []
    if not match:
        rep = parse_engine_version(reported_version)
        cur = parse_engine_version(current)
        changed = [k for k in rep if rep[k] != cur.get(k)]

    return match, changed

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description='KishLattice engine fingerprint tool'
    )
    parser.add_argument(
        '--verify', metavar='VERSION_STRING',
        help='Verify a reported 192-char version string against current files'
    )
    parser.add_argument(
        '--parse', metavar='VERSION_STRING',
        help='Parse a version string into components'
    )
    args = parser.parse_args()

    if args.verify:
        match, changed = verify_engine_version(args.verify)
        if match:
            print("VERIFIED: Current engine matches reported version string.")
        else:
            print(f"MISMATCH: Changed components: {changed}")
            sys.exit(1)
    elif args.parse:
        components = parse_engine_version(args.parse)
        for k, v in components.items():
            print(f"  {k:<25} {v}")
    else:
        version = compute_engine_version()
        print(version)
        print()
        components = parse_engine_version(version)
        for k, v in components.items():
            print(f"  {k:<25} {v}")
```

### Priority 2: scalarize.py — config-driven dispatch

The engine's scalarize.py loads scalarize.json at startup.
New domains: add one JSON entry. Engine code: unchanged.

Dispatch pattern (add to existing scalarize.py):

```python
import json

FORMULA_DISPATCH = {
    'log_standard': lambda x, x0, k: math.log(1.0 + float(x) / x0) / math.log(k),
    'log_inverse':  lambda x, x0, k: math.log(1.0 + x0 / float(x)) / math.log(k),
    'log_ratio':    lambda x, x0, k: math.log(float(x) / x0) / math.log(k),
}

def load_scalarize_config(config_path):
    with open(config_path, encoding='utf-8') as f:
        cfg = json.load(f)
    return cfg['domains'], cfg['k_geo']

def scalarize_from_config(value, domain, domain_configs, k_geo):
    cfg = domain_configs.get(domain)
    if cfg is None:
        raise KeyError(f"Domain '{domain}' not in scalarize.json. "
                       f"Add it before running pipeline.")
    x0 = cfg.get('x0', 1.0)
    formula = FORMULA_DISPATCH[cfg['formula_type']]
    return formula(value, x0, k_geo)
```

Zero-dispatch failure: if a domain appears in volumes.json but not in
scalarize.json, the pipeline raises KeyError with a clear message rather
than silently producing wrong scalars. This is the designed failure mode.

### Priority 3: Output fingerprint injection

All four engine scripts write the engine version string to their outputs.
Add to each script's final output block:

```python
from engine_version import compute_engine_version

# At output write time:
engine_ver = compute_engine_version()

# In sweep_results.json and pinch_table.json:
output_dict['engine_version'] = engine_ver
output_dict['generated_utc'] = datetime.utcnow().isoformat() + 'Z'

# In unified_master.jsonl header line (first line):
header = {
    '_type': 'header',
    'engine_version': engine_ver,
    'generated_utc': datetime.utcnow().isoformat() + 'Z',
    'total_lakes': n_lakes,
}
```

---

## PHASE 8 — VOLUMES.JSON UPDATE

Add Vol 10 new lakes to volumes.json.
Set enabled: false initially — flip to true when lake is built and validated.

New entries to add (disabled until lake is ready):

```json
  {
    "id": "b4_pdb_protein",
    "label": "B4 PDB Protein Backbone",
    "domain": "biology_backbone",
    "enabled": false,
    "vol": 10,
    "source": "RCSB PDB",
    "description": "Ramachandran phi/psi dihedral angles from all solved protein structures"
  },
  {
    "id": "u1_usgs_seismic",
    "label": "U1 USGS Seismic Temporal Gaps",
    "domain": "seismic_temporal",
    "enabled": false,
    "vol": 10,
    "source": "USGS Earthquake Catalog",
    "description": "Temporal intervals between M>=5.0 events per major fault system"
  },
  {
    "id": "h1_cern_lhc",
    "label": "H1 CERN LHC Invariant Mass",
    "domain": "subnuclear_mass",
    "enabled": false,
    "vol": 10,
    "source": "CERN Open Data Portal",
    "description": "Di-muon and di-electron invariant mass from CMS/ATLAS Run 2"
  },
  {
    "id": "p4_ttv",
    "label": "P4 Kepler/TESS Transit Timing Variations",
    "domain": "orbital_ttv",
    "enabled": false,
    "vol": 10,
    "source": "NASA ExoFOP",
    "description": "Individual transit timing deviations from Keplerian prediction"
  },
  {
    "id": "l2_nanograv",
    "label": "L2 NANOGrav Pulsar Timing Array",
    "domain": "gravitational_bg",
    "enabled": false,
    "vol": 10,
    "source": "NANOGrav 15yr dataset",
    "description": "Pulsar timing residuals from gravitational wave background survey"
  }
```

---

## PHASE 9 — SCRIPTS FOLDER

The legacy scripts/ folder contains a mix of utility scripts, old lake builders,
and administrative tools. Do not delete — archive to archive/legacy_scripts/.

Move to archive/legacy_scripts/:
```
scripts/analysis/           (empty subdirectory)
scripts/unify/              (empty subdirectory)
scripts/utils/              (empty subdirectory)
scripts/scalar/             (legacy scalarize copy)
scripts/schema/             (legacy validate copy)
scripts/create_clean_structure.ps1
scripts/inspect_p_series.ps1
scripts/inspect_raw_lakes.ps1
scripts/VOL6_HARMONIC_FAMILY_SWEEP_PATCH.txt
```

Keep in scripts/ (useful utilities):
```
scripts/large_file_manifest.py     <- manifest generator
scripts/verify_manifest.py         <- manifest verifier
scripts/universal_promote.py       <- promote utility
scripts/unwrap_t_series.py         <- T-series utility
scripts/get_zenodo_dois.py         <- DOI helper
scripts/README.md                  <- update with Vol 10 notes
```

---

## EXECUTION ORDER SUMMARY

```
Phase 1:  Root cleanup (delete LaTeX artifacts, create reference/)
Phase 2:  Engine — create engine_version.py, add .gitattributes
Phase 3:  Configs — delete error variant, create scalarize.json skeleton
Phase 4:  Lakes folder — delete superseded/error promoted files
Phase 5:  Series — move legacy folders to archive/legacy_series/
Phase 6:  New series — create B4, U1, H1, P4, L2 folder structures
Phase 7:  Engine code — add config-driven dispatch to scalarize.py
Phase 8:  volumes.json — add 5 new disabled lake entries
Phase 9:  Scripts — archive legacy, keep utilities
          
Then: Run engine/engine_version.py to establish Vol 10 baseline fingerprint.
      Record baseline fingerprint in README.md.
      First pipeline test run with Vol 9 lakes only (verify no regression).
      Then build new lakes one at a time, enabling each in volumes.json as validated.
```

---

## FIRST PIPELINE TEST AFTER CLEANUP

Before building any new lakes, run the full pipeline against the existing
37 Vol 9 lakes to verify the cleanup introduced no regressions:

```bash
cd vol10
python engine/engine_version.py > engine_baseline_v10.txt
python engine/scalarize.py
python engine/unify.py
python engine/build_chaos_nulls.py
python engine/build_pinch_table.py
```

The pinch table output should match the Vol 9 results exactly
(same 37 lakes, same records, same z-scores).
If it matches: cleanup was clean. Proceed to new lake builds.
If it does not match: diagnose before proceeding.

The engine_baseline_v10.txt file is the Vol 10 reference fingerprint.
It goes in the paper's appendix and the README.

---

## LAKEGUIDE.md OUTLINE (to be written as separate task)

Sections:
1. What is a sovereign lake
2. The four-script construction sequence
3. The litmus standard (stdev/span < 0.28)
4. Adding a domain to scalarize.json
5. Adding a lake to volumes.json
6. The zero-dispatch failure mode
7. The sovereign chain (raw_payload preservation)
8. The engine fingerprint (how to verify a result)
9. Worked example: building a new lake from scratch
10. Common failure modes and fixes
