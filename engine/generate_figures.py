# ==============================================================================
# generate_figures.py
# KishLattice Geometric Harmonic Spectroscopy -- Report and Figure Generator
# 
# Vol 11 Visual Suite Executor. Auto-discovers all report_*.py plugins in the
# reports/ directory, builds the context dictionary from post-pinch pipeline
# artifacts, and calls each plugin's generate(context) function in sequence.
# 
# -- COMPATIBILITY LAYER --
# All Vol 10 / Vol 11 report plugins use extract_z_scores_from_log() to source
# z-scores. The Vol 11 vectorized pinch stage changed the log output format,
# breaking all log parsers. This module monkey-patches every loaded plugin's
# extract_z_scores_from_log() to return context["z_scores"] (loaded from
# z_scores_master.json) instead of trying to parse the log. No report files
# need to be modified.
# 
# -- PATH CORRECTION --
# Report plugins calculate the vol root as out_dir.parents[3]. This requires
# the output path to be exactly 4 levels deep inside the vol root:
#   ROOT / lakes / figures / output / run_TIMESTAMP/
#                                     ^ this is out_dir
# 
# -- SIDECAR TELEMETRY --
# Writes lattice_heartbeat.json between every plugin so sidecar.py shows
# live progress during the figures stage.
# 
# -- DOMAIN MANIFEST --
# Auto-generates reports/domain_manifest.json by scanning lakes/inputs_promoted/
# for available promoted files and sampling field names from the first record.
# Reports that depend on the manifest will find it ready.
# 
# Report plugins must implement:
#     def generate(context: dict) -> list[Path]:
#         ...
#         return [list_of_files_created]
# 
# Context dictionary provided to every plugin:
#     context["pinch_table"]          -- dict  (pinch_table_cross_domain.json)
#     context["sweep_results"]        -- dict  (sweep_results.json)
#     context["z_scores"]             -- dict  (z_scores_master.json)
#                                        {domain: [z_4pi..z_26pi]}
#     context["output_dir"]           -- Path  (lakes/figures/output/run_TIMESTAMP/)
#     context["unified_master_path"]  -- Path  (lakes/unified/unified_master.jsonl)
#     context["root_path"]            -- Path  (vol root)
#     context["harmonic_labels"]      -- list  (["4/pi", ..., "26/pi"])
#     context["run_timestamp"]        -- str   (UTC timestamp string)
# ==============================================================================
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC.
# FOUNDER: Timothy John Kish
#
# LICENSE & TERMS OF USE:
# This software, including the 16/pi kinematic framework and scalarization
# engines, is open and available for scientific testing, empirical validation,
# and academic peer review.
#
# ATTRIBUTION REQUIREMENT:
# Any publication, derivative code, dataset generation, or public distribution
# relying on this framework must explicitly cite the "KishLattice 16/pi Initiative"
# and credit Timothy John Kish.
#
# Commercial utilization, proprietary harvesting, or uncredited reproduction
# is strictly prohibited without explicit written permission.
# ==============================================================================
import importlib.util
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT               = Path(__file__).resolve().parents[1]
REPORTS_DIR        = ROOT / "reports"
PINCH_TABLE_PATH   = ROOT / "lakes" / "unified" / "pinch_table_cross_domain.json"
SWEEP_RESULTS_PATH = ROOT / "lakes" / "unified" / "sweep_results.json"
Z_SCORES_PATH      = ROOT / "lakes" / "unified" / "z_scores_master.json"
UNIFIED_PATH       = ROOT / "lakes" / "unified" / "unified_master.jsonl"
FIGURES_BASE_DIR   = ROOT / "lakes" / "figures"
HARMONIC_TARGETS_CFG = ROOT / "configs" / "harmonic_targets.json"
PROMOTED_DIR       = ROOT / "lakes" / "inputs_promoted"
MANIFEST_PATH      = ROOT / "reports" / "domain_manifest.json"
HEARTBEAT_PATH     = ROOT / "lakes" / "unified" / "lattice_heartbeat.json"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def utc_now() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

def load_json_safe(path: Path, label: str) -> dict:
    if not path.exists():
        print(f"  [WARN] {label} not found: {path}")
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  [WARN] Could not load {label}: {e}")
        return {}

def write_heartbeat(pct, elapsed, total, completed, action):
    eta = (elapsed / max(1, completed)) * (total - completed) if completed > 0 else 0
    data = {
        "timestamp_utc":  utc_now(),
        "progress_pct":   min(100.0, max(0.0, round(pct, 2))),
        "completed":      completed,
        "total":          total,
        "eta_seconds":    round(eta, 1),
        "current_action": action,
    }
    try:
        with open(HEARTBEAT_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f)
    except Exception:
        pass

def load_harmonic_labels() -> list:
    if HARMONIC_TARGETS_CFG.exists():
        try:
            with open(HARMONIC_TARGETS_CFG, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            registers = cfg.get("registers", list(range(4, 27)))
            return [f"{n}/pi" for n in registers]
        except Exception:
            pass
    return [f"{n}/pi" for n in range(4, 27)]

def discover_reports(reports_dir: Path) -> list:
    if not reports_dir.exists():
        return []
    return sorted(reports_dir.glob("report_*.py"))

def load_plugin(plugin_path: Path):
    spec   = importlib.util.spec_from_file_location(plugin_path.stem, plugin_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# ---------------------------------------------------------------------------
# Monkey-patch: replace extract_z_scores_from_log on every loaded module.
#
# All Vol 10/11 reports contain this function and call it with a root_path
# argument. The Vol 11 vectorized pinch stage changed the z-score output
# format in the log, so all existing parsers return {}.
#
# This replacement ignores root_path entirely and returns context["z_scores"]
# which is loaded directly from z_scores_master.json -- the definitive source.
# ---------------------------------------------------------------------------
def patch_module_z_scores(module, z_scores: dict):
    """
    If the module defines extract_z_scores_from_log(), replace it with a
    lambda that returns the pre-loaded z_scores dict from context.
    The replacement accepts any positional/keyword arguments so the call
    site in the report script continues to work without modification.
    """
    if hasattr(module, 'extract_z_scores_from_log') and callable(
            module.extract_z_scores_from_log):
        module.extract_z_scores_from_log = lambda *a, **kw: z_scores
        return True
    return False

# ---------------------------------------------------------------------------
# Domain manifest auto-generation.
#
# Reports 01, 02_universal_histograms, and 09 look for
#   reports/domain_manifest.json
# which maps domain names to their promoted file, measurement field,
# axis label, and chart title.
#
# Strategy:
#   1. Scan lakes/inputs_promoted/ for *_promoted.jsonl files.
#   2. For each file, read the first record and extract field names.
#   3. Infer the best numeric measurement field using a priority list
#      and fallback to the first numeric field found.
#   4. Build a manifest entry and write the file if it does not yet exist.
#
# The manifest is NOT overwritten if it already exists (preserve manual edits).
# ---------------------------------------------------------------------------

# Priority field names per domain substring (longest match wins).
# These cover the known lake designs as of Vol 11.
FIELD_HINTS = {
    "stellar_kinematic":  ("transverse_velocity_km_s", "Transverse Velocity (km/s)"),
    "stellar_colour":     ("bp_rp",                    "Gaia BP-RP Colour Index"),
    "stellar_luminosity": ("phot_g_mean_mag",           "Gaia G-band Magnitude"),
    "stellar_rotation":   ("period_days",               "Rotation Period (days)"),
    "stellar_cycle":      ("cycle_years",               "Cycle Length (years)"),
    "stellar":            ("parallax",                  "Gaia Parallax (mas)"),
    "biology_backbone":   ("phi",                       "Ramachandran Phi (deg)"),
    "biology_amino":      ("residue_mass_da",           "Residue Mass (Da)"),
    "biology_chirality":  ("optical_rotation",          "Optical Rotation"),
    "orbital_ttv":        ("ttv_minutes",               "Transit Timing Variation (min)"),
    "orbital_radius":     ("pl_orbsmax",                "Semi-Major Axis (AU)"),
    "orbital_mass":       ("pl_bmassj",                 "Planet Mass (Mjup)"),
    "orbital":            ("pl_orbper",                 "Orbital Period (days)"),
    "galactic":           ("sigma_km_s",                "Velocity Dispersion (km/s)"),
    "subnuclear_mass":    ("mass_mev",                  "Particle Mass (MeV)"),
    "quantum":            ("wavelength_nm",             "Wavelength (nm)"),
    "seismic_temporal":   ("inter_event_days",          "Inter-Event Time (days)"),
    "planetary_atlantic": ("tidal_range_m",             "Tidal Range (m)"),
    "planetary_gulf":     ("tidal_range_m",             "Tidal Range (m)"),
    "planetary_pacific":  ("tidal_range_m",             "Tidal Range (m)"),
    "planetary_indian":   ("tidal_range_m",             "Tidal Range (m)"),
    "planetary":          ("tidal_range_m",             "Tidal Range (m)"),
    "chemistry":          ("molecular_weight",          "Molecular Weight (Da)"),
    "materials":          ("band_gap_ev",               "Band Gap (eV)"),
    "nuclear_binding":    ("binding_energy_mev",        "Binding Energy (MeV)"),
    "nuclear_decay":      ("half_life_s",               "Half Life (s)"),
    "frb":                ("fluence_jy_ms",             "Fluence (Jy ms)"),
    "gravitational_wave": ("mass_solar",                "Chirp Mass (Msun)"),
    "cmb_anisotropy":     ("multipole_l",               "Multipole Moment l"),
    "cosmology":          ("redshift",                  "Redshift z"),
}

def _pick_field_from_record(rec: dict, domain: str) -> tuple:
    """
    Pick (field_name, x_label) for a domain.
    First tries FIELD_HINTS (longest matching key), then falls back to the
    first float-valued field in the record that isn't an ID/flag.
    """
    # Try hint lookup (longest domain substring match first)
    dom_lower = domain.lower()
    best_key, best_hint = None, None
    for hint_key, (field, label) in FIELD_HINTS.items():
        if hint_key in dom_lower:
            if best_key is None or len(hint_key) > len(best_key):
                best_key, best_hint = hint_key, (field, label)
    if best_hint:
        field_name, x_label = best_hint
        # Verify the field exists in the actual record
        val = (rec.get(field_name)
               or rec.get("payload", {}).get(field_name)
               or rec.get("_raw_payload", {}).get(field_name))
        if val is not None:
            return field_name, x_label

    # Fallback: first numeric field that looks like a measurement
    skip = {"id", "uid", "flag", "index", "type", "name", "label",
            "source_id", "lake_id", "domain", "volume"}
    for k, v in rec.items():
        if any(s in k.lower() for s in skip):
            continue
        try:
            float(v)
            return k, k.replace("_", " ").title()
        except (TypeError, ValueError):
            continue
    return None, None

def build_domain_manifest(z_scores: dict) -> dict:
    """
    Scan lakes/inputs_promoted/ and build domain_manifest.json.
    Returns the manifest dict (also writes it to disk if not yet present).
    """
    if not PROMOTED_DIR.exists():
        return {}

    manifest = {}
    # Match promoted files to domains using z_scores domain names
    promoted_files = {f.stem.replace("_promoted", ""): f
                      for f in PROMOTED_DIR.glob("*_promoted.jsonl")}

    for domain in sorted(z_scores.keys()):
        # Try exact match first, then substring match
        matched_file = None
        for lake_id, fpath in promoted_files.items():
            if lake_id == domain or lake_id.endswith(f"_{domain}") \
                    or domain.startswith(lake_id.lstrip("s1234567890_")):
                matched_file = fpath
                break
        if matched_file is None:
            # Broader search: any promoted file whose stem contains the domain
            for lake_id, fpath in promoted_files.items():
                if domain in lake_id or lake_id in domain:
                    matched_file = fpath
                    break
        if matched_file is None:
            continue

        # Read first record to sample fields
        first_rec = {}
        try:
            with matched_file.open("r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        first_rec = json.loads(line)
                        break
        except Exception:
            continue

        field_name, x_label = _pick_field_from_record(first_rec, domain)
        if field_name is None:
            continue

        manifest[domain] = {
            "file":    matched_file.name,
            "field":   field_name,
            "x_label": x_label,
            "title":   domain.replace("_", " ").title(),
        }

    return manifest

def ensure_domain_manifest(z_scores: dict) -> dict:
    """
    Return the domain manifest, generating it if not already present.
    Existing manifest is kept intact (preserves manual edits).
    """
    if MANIFEST_PATH.exists():
        try:
            with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            print(f"  Manifest: loaded existing ({len(manifest)} domains) "
                  f"-- {MANIFEST_PATH.name}")
            return manifest
        except Exception as e:
            print(f"  Manifest: could not read existing file ({e}), rebuilding.")

    print(f"  Manifest: generating from promoted files in {PROMOTED_DIR.name}/...")
    manifest = build_domain_manifest(z_scores)

    if manifest:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        print(f"  Manifest: wrote {len(manifest)} domain entries "
              f"-> {MANIFEST_PATH}")
    else:
        print(f"  Manifest: no promoted files found in {PROMOTED_DIR} "
              f"-- reports 01/02h/09 will skip gracefully.")

    return manifest

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    # Force UTF-8 on Windows subprocess pipe capture
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

    run_timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    pipeline_start = time.time()

    print(f"\n[{utc_now()}] FIGURES: Auto-discovering report plugins")
    print(f"  Reports directory: {REPORTS_DIR}")

    # ------------------------------------------------------------------
    # Discover plugins
    # ------------------------------------------------------------------
    plugin_paths = discover_reports(REPORTS_DIR)
    if not plugin_paths:
        print(f"\n  [INFO] No report plugins found in {REPORTS_DIR}")
        print(f"         Create reports/report_XX_myname.py to add a plugin.")
        sys.exit(0)

    print(f"  Found {len(plugin_paths)} plugin(s):")
    for p in plugin_paths:
        print(f"    - {p.name}")

    # ------------------------------------------------------------------
    # Load pipeline artifacts
    # ------------------------------------------------------------------
    print(f"\n[{utc_now()}] Loading pipeline artifacts...")
    pinch_table   = load_json_safe(PINCH_TABLE_PATH,   "pinch_table_cross_domain.json")
    sweep_results = load_json_safe(SWEEP_RESULTS_PATH, "sweep_results.json")
    z_scores      = load_json_safe(Z_SCORES_PATH,      "z_scores_master.json")

    if not pinch_table:
        print("\n  [ERROR] pinch_table_cross_domain.json is required but missing.")
        sys.exit(1)

    if not z_scores:
        print("\n  [WARN] z_scores_master.json not found -- z-score reports will skip.")

    harmonic_labels = load_harmonic_labels()
    print(f"  Pinch table:  {len(pinch_table)} domain rows")
    print(f"  Sweep results:{len(sweep_results)} domain entries")
    print(f"  Z-scores:     {len(z_scores)} domains x {len(harmonic_labels)} registers")
    print(f"  Harmonics:    {harmonic_labels[0]} ... {harmonic_labels[-1]}")

    # ------------------------------------------------------------------
    # Ensure domain manifest exists (for reports 01, 02h, 09)
    # ------------------------------------------------------------------
    ensure_domain_manifest(z_scores)

    # ------------------------------------------------------------------
    # Create output directory.
    # NOTE: 4 levels deep inside ROOT so that out_dir.parents[3] == ROOT,
    # matching the path calculation used by all existing report plugins:
    #   ROOT/lakes/figures/output/run_TIMESTAMP/
    # ------------------------------------------------------------------
    output_dir = FIGURES_BASE_DIR / "output" / f"run_{run_timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n  Output directory: {output_dir}")

    # ------------------------------------------------------------------
    # Build context
    # ------------------------------------------------------------------
    context = {
        "pinch_table":         pinch_table,
        "sweep_results":       sweep_results,
        "z_scores":            z_scores,
        "output_dir":          output_dir,
        "unified_master_path": UNIFIED_PATH,
        "root_path":           ROOT,
        "harmonic_labels":     harmonic_labels,
        "run_timestamp":       run_timestamp,
    }

    # ------------------------------------------------------------------
    # Run plugins
    # ------------------------------------------------------------------
    total_plugins = len(plugin_paths)
    write_heartbeat(0, 0, total_plugins, 0,
                    f"[FIGURES] Starting {total_plugins} plugins...")

    print(f"\n[{utc_now()}] Running {total_plugins} report plugin(s)...\n")

    results    = []
    all_files  = []
    any_error  = False
    patched    = 0

    for idx, plugin_path in enumerate(plugin_paths):
        plugin_name = plugin_path.stem
        elapsed_so_far = time.time() - pipeline_start

        write_heartbeat(
            (idx / total_plugins) * 100,
            elapsed_so_far, total_plugins, idx,
            f"[FIGURES] {idx+1}/{total_plugins}: {plugin_name}"
        )

        print(f"  [{plugin_name}]")
        t0 = time.time()

        try:
            module = load_plugin(plugin_path)

            if not hasattr(module, 'generate') or not callable(module.generate):
                print(f"    [SKIP] No callable generate() function found.")
                results.append({"plugin": plugin_name, "status": "skipped",
                                 "files": [], "elapsed": 0.0})
                continue

            # ----------------------------------------------------------
            # COMPATIBILITY PATCH: replace the log-based z-score parser
            # with a direct reference to context["z_scores"].
            # ----------------------------------------------------------
            if patch_module_z_scores(module, z_scores):
                patched += 1

            generated = module.generate(context)
            elapsed   = time.time() - t0

            if generated is None:
                generated = []

            file_list = [str(f) for f in generated]
            all_files.extend(file_list)

            if file_list:
                print(f"    [OK] {len(file_list)} file(s) in {elapsed:.1f}s")
                for fp in file_list:
                    print(f"         {fp}")
            else:
                print(f"    [OK] 0 files in {elapsed:.1f}s "
                      f"(plugin ran, nothing saved)")

            results.append({"plugin": plugin_name, "status": "ok",
                             "files": file_list, "elapsed": elapsed})

        except Exception as e:
            elapsed = time.time() - t0
            print(f"    [FAIL] {plugin_name}: {e}")
            import traceback
            traceback.print_exc()
            results.append({"plugin": plugin_name, "status": "error",
                             "error": str(e), "files": [], "elapsed": elapsed})
            any_error = True

    total_elapsed = time.time() - pipeline_start

    write_heartbeat(100, total_elapsed, total_plugins, total_plugins,
                    f"[FIGURES] Complete -- {len(all_files)} files generated")

    # ------------------------------------------------------------------
    # Write index
    # ------------------------------------------------------------------
    index_path = output_dir / "figures_index.json"
    index = {
        "run_timestamp":   run_timestamp,
        "generated_utc":   utc_now(),
        "total_files":     len(all_files),
        "total_elapsed_s": round(total_elapsed, 2),
        "z_score_patches": patched,
        "plugins":         results,
        "files":           all_files,
    }
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    ok_count   = sum(1 for r in results if r["status"] == "ok")
    err_count  = sum(1 for r in results if r["status"] == "error")
    skip_count = sum(1 for r in results if r["status"] == "skipped")

    print(f"\n[{utc_now()}] FIGURES COMPLETE")
    print(f"  Plugins:  {ok_count} OK  |  {err_count} FAILED  |  {skip_count} SKIPPED")
    print(f"  Files:    {len(all_files)} generated")
    print(f"  Patched:  {patched} plugin(s) upgraded to z_scores_master.json")
    print(f"  Runtime:  {total_elapsed:.1f}s")
    print(f"  Index:    {index_path}")
    print(f"  Output:   {output_dir}")

    sys.exit(1 if any_error else 0)

if __name__ == "__main__":
    main()