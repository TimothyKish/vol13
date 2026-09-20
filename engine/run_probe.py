# ==============================================================================
# run_probe.py
# KishLattice Star Probe -- Crystalline Terminus Diagnostic Orchestrator
#
# TOOLBELT INSTRUMENT: This script is one instrument in the Vol 12 toolbelt.
# It sits alongside the Vol 11 1D engine (run_pipeline.py) without replacing it.
# Future instruments (2D engine, LIGO probe, materials probe) follow the same
# pattern: a named probe block in harmonic_targets.json, a dedicated run_probe.py
# call with --probe <name>.
#
# ARCHITECTURE:
#   1. Reads the named probe block from configs/harmonic_targets.json
#   2. Filters volumes.json to only probe-tagged lakes
#   3. Runs the standard four-stage pipeline (scalarize -> unify -> chaos -> pinch)
#      using the existing Vol 11 engine scripts without modification
#   4. After pinch completes, reads z_scores_master.json and compares each
#      lake's result against its pre-registered target register
#   5. Writes a probe_diagnostic_report.json and a human-readable
#      probe_diagnostic_report.txt to lakes/reports/
#
# CHAIN OF CUSTODY:
#   - Raw promoted files are never touched. Read-only inputs.
#   - All KLGHS fields are additions (scalar_kls, scalar_klc, klghs_* prefix).
#   - Excluded records written with logged reasons, never silently dropped.
#   - Full engine fingerprint recorded in report for reproducibility.
#   - MD5 checksum of unified_master recorded in report.
#
# USAGE:
#   python engine_lattice_probe1/run_probe.py --probe star_probe
#   python engine_lattice_probe1/run_probe.py --probe star_probe --no-advisory
#   python engine_lattice_probe1/run_probe.py --probe star_probe --from pinch
#   python engine_lattice_probe1/run_probe.py --probe star_probe --dry-run
#
# AUTHORS: Atlas Aurora Kish (Chief Experimental Architect)
#          Timothy John Kish (Lead)
# VOLUME: 12 - Star Probe (Crystalline Terminus)
# PRE-REGISTRATION: DOI 10.5281/zenodo.20370708
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

import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
import os
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PI    = math.pi
K_GEO = 16.0 / PI

# ---------------------------------------------------------------------------
# Paths  (all relative to vol root — parent of engine_lattice_probe1/)
# ---------------------------------------------------------------------------
SCRIPT_DIR   = Path(__file__).resolve().parent
VOL_ROOT     = SCRIPT_DIR.parent
CONFIG_DIR   = VOL_ROOT / "config"
ENGINE_DIR   = SCRIPT_DIR
LAKES_DIR    = VOL_ROOT / "lakes"
UNIFIED_DIR  = LAKES_DIR / "unified"
REPORTS_DIR  = LAKES_DIR / "reports"
LOGS_DIR     = LAKES_DIR / "logs"

HARMONIC_CFG   = CONFIG_DIR / "harmonic_targets.json"
VOLUMES_CFG    = CONFIG_DIR / "volumes.json"
SCALARIZE_CFG  = CONFIG_DIR / "scalarize.json"
Z_SCORES_PATH  = UNIFIED_DIR / "z_scores_master.json"
CHECKSUM_PATH  = UNIFIED_DIR / "unified_master.jsonl.md5"

PIPELINE_STAGES = [
    {
        "name":        "scalarize",
        "script":      ENGINE_DIR / "scalarize.py",
        "description": "Transform promoted lakes into scalar space",
        "produces":    "lakes/unified/*_scalarized.jsonl",
    },
    {
        "name":        "unify",
        "script":      ENGINE_DIR / "unify.py",
        "description": "Stream all scalarized lakes into unified master",
        "produces":    "lakes/unified/unified_master.jsonl",
        "checksum":    True,
    },
    {
        "name":        "chaos",
        "script":      ENGINE_DIR / "build_chaos_nulls.py",
        "description": "Build chaos null distributions per domain",
        "produces":    "lakes/synthetic/chaos_null_*.jsonl",
    },
    {
        "name":        "pinch",
        "script":      ENGINE_DIR / "build_pinch_table.py",
        "description": "Compute z-scores and cross-domain pinch table",
        "produces":    "lakes/unified/pinch_table_cross_domain.json",
    },
]

STAGE_NAMES = [s["name"] for s in PIPELINE_STAGES]

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------
def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

def format_elapsed(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:   return f"{h}h {m}m {s}s"
    elif m > 0: return f"{m}m {s}s"
    else:       return f"{s}s"

def get_engine_version() -> str:
    try:
        sys.path.insert(0, str(ENGINE_DIR))
        from engine_version import compute_engine_version
        return compute_engine_version(base_dir=VOL_ROOT)
    except Exception as e:
        return f"ERROR: {e}"
    finally:
        if str(ENGINE_DIR) in sys.path:
            sys.path.remove(str(ENGINE_DIR))

def read_checksum() -> str:
    """Read the MD5 checksum from the unified master checksum file."""
    try:
        text = CHECKSUM_PATH.read_text(encoding="utf-8")
        return text.split()[0]
    except Exception:
        return "unavailable"

# ---------------------------------------------------------------------------
# Config Loaders
# ---------------------------------------------------------------------------
def load_probe_config(probe_name: str) -> dict:
    """Load and validate the named probe block from harmonic_targets.json."""
    if not HARMONIC_CFG.exists():
        print(f"[ERROR] harmonic_targets.json not found at {HARMONIC_CFG}", file=sys.stderr)
        sys.exit(1)

    with open(HARMONIC_CFG, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    probes = cfg.get("probes", {})
    if probe_name not in probes:
        available = list(probes.keys()) or ["(none defined)"]
        print(f"[ERROR] Probe '{probe_name}' not found in harmonic_targets.json.", file=sys.stderr)
        print(f"  Available probes: {available}", file=sys.stderr)
        sys.exit(1)

    probe_cfg = probes[probe_name]
    print(f"[harmonic_targets.json] Loaded probe: '{probe_name}'")
    print(f"  Description:      {probe_cfg.get('description', 'n/a')}")
    print(f"  Pre-registration: {probe_cfg.get('pre_registration_doi', 'n/a')}")
    print(f"  Targets:          {len(probe_cfg.get('targets', []))}")

    return probe_cfg

def load_probe_volumes(probe_name: str) -> dict:
    """
    Load volumes.json and return only lakes tagged to this probe.
    Chain-of-custody: volumes.json is read-only. No mutation.
    """
    if not VOLUMES_CFG.exists():
        print(f"[ERROR] volumes.json not found at {VOLUMES_CFG}", file=sys.stderr)
        sys.exit(1)

    with open(VOLUMES_CFG, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    all_volumes = cfg.get("volumes", {})
    probe_volumes = {
        name: meta for name, meta in all_volumes.items()
        if meta.get("enabled", False) and meta.get("probe") == probe_name
    }

    if not probe_volumes:
        print(f"[ERROR] No enabled volumes found for probe '{probe_name}' in volumes.json.", file=sys.stderr)
        sys.exit(1)

    print(f"[volumes.json] {len(probe_volumes)} lake(s) enabled for probe '{probe_name}':")
    for name, meta in probe_volumes.items():
        print(f"  {name}  ->  domain={meta.get('domain')}  lake_id={meta.get('lake_id')}")

    return probe_volumes

# ---------------------------------------------------------------------------
# Stage Runner
# ---------------------------------------------------------------------------
def run_stage(stage: dict, log_fh, dry_run: bool = False) -> dict:
    """Run a single pipeline stage as a subprocess. Mirror of run_pipeline.py pattern."""
    name        = stage["name"]
    script_path = stage["script"]
    description = stage["description"]

    print(f"\n{'=' * 60}")
    print(f"[{utc_now()}] STAGE: {name.upper()}")
    print(f"{description}")
    print(f"{'=' * 60}")

    if dry_run:
        print(f"  [DRY RUN] Would execute: python {script_path}")
        log_fh.write(f"[DRY RUN] Stage: {name}\n")
        return {"name": name, "success": True, "elapsed": 0.0}

    log_fh.write(f"\n[{utc_now()}] STAGE: {name.upper()}\n")
    log_fh.flush()

    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(VOL_ROOT),
            capture_output=False,
            text=True,
            encoding="utf-8",
        )
        elapsed = time.time() - start
        success = result.returncode == 0

        status = "COMPLETE" if success else f"FAILED (exit code {result.returncode})"
        msg = f"[{utc_now()}] STAGE {status}: {name} in {format_elapsed(elapsed)}"
        print(msg)
        log_fh.write(msg + "\n")
        log_fh.flush()

        return {"name": name, "success": success, "elapsed": elapsed,
                "returncode": result.returncode}

    except Exception as e:
        elapsed = time.time() - start
        msg = f"[{utc_now()}] STAGE EXCEPTION: {name} — {e}"
        print(msg, file=sys.stderr)
        log_fh.write(msg + "\n")
        return {"name": name, "success": False, "elapsed": elapsed, "error": str(e)}

# ---------------------------------------------------------------------------
# Probe Diagnostic — Core of the Star Probe
# ---------------------------------------------------------------------------
def scalar_at_register(n: int) -> float:
    """Return the scalar value at register N/pi."""
    return n / PI

def modular_residual(scalar: float, n: int) -> float:
    """
    Compute the modular residual of a scalar value relative to register N/pi.
    The residual is the fractional distance from the nearest integer node
    after scaling by log(k_geo).
    """
    target = scalar_at_register(n)
    log_k  = math.log(K_GEO)
    # Map scalar into the modular lattice space
    mod_val = (scalar * log_k) % 1.0
    mod_tgt = (target * log_k) % 1.0
    diff = abs(mod_val - mod_tgt)
    return min(diff, 1.0 - diff)  # wrap-around distance

def build_probe_diagnostic(probe_cfg: dict, lock_threshold: float) -> dict:
    """
    Read z_scores_master.json and build the probe diagnostic report.

    For each pre-registered target in the probe config:
      - Find the domain's z-scores across all registers
      - Extract the z-score at the predicted register
      - Extract the peak z-score and its register
      - Compare peak vs prediction
      - Classify result: CONFIRMED / PARTIAL / NULL / UNEXPECTED_SIGNAL

    Chain-of-custody: z_scores_master.json is read-only. No mutation.
    """
    if not Z_SCORES_PATH.exists():
        return {
            "status": "ERROR",
            "message": f"z_scores_master.json not found at {Z_SCORES_PATH}. "
                       f"Run the full pipeline first."
        }

    with open(Z_SCORES_PATH, "r", encoding="utf-8") as f:
        z_scores = json.load(f)

    targets    = probe_cfg.get("targets", [])
    results    = []
    all_pass   = True
    any_signal = False

    for target in targets:
        domain          = target["domain"]
        predicted_n     = target["register_prediction"]
        secondary_n     = target.get("register_secondary")
        field           = target["field"]
        interpretation  = target.get("physical_interpretation", "")
        note            = target.get("note", "")

        domain_scores = z_scores.get(domain)

        if domain_scores is None:
            result = {
                "domain":            domain,
                "field":             field,
                "register_predicted": predicted_n,
                "status":            "NO_DATA",
                "message":           f"Domain '{domain}' not found in z_scores_master.json. "
                                     f"Check volumes.json and scalarize.json are consistent.",
                "physical_interpretation": interpretation,
            }
            results.append(result)
            all_pass = False
            continue

        # Extract chaos z-scores per register
        # z_scores_master.json structure: {domain: {register_n: {chaos_z: float, ...}}}
        register_zscores = {}
        for reg_key, reg_data in domain_scores.items():
            try:
                n = int(reg_key)
                if isinstance(reg_data, dict):
                    z = float(reg_data.get("chaos_z", reg_data.get("z", 0.0)))
                else:
                    z = float(reg_data)
                register_zscores[n] = z
            except (ValueError, TypeError):
                continue

        if not register_zscores:
            result = {
                "domain":            domain,
                "field":             field,
                "register_predicted": predicted_n,
                "status":            "NO_SCORES",
                "message":           "z_scores_master.json entry exists but contains no register scores.",
                "physical_interpretation": interpretation,
            }
            results.append(result)
            all_pass = False
            continue

        # Find peak register and its z-score
        peak_n = max(register_zscores, key=lambda n: register_zscores[n])
        peak_z = register_zscores[peak_n]

        # z-score at predicted register
        predicted_z = register_zscores.get(predicted_n, 0.0)

        # z-score at secondary register (if defined)
        secondary_z = register_zscores.get(secondary_n, 0.0) if secondary_n else None

        # Classification
        STRONG_THRESHOLD = 5.0   # z > +5 = STRONG signal
        WEAK_THRESHOLD   = 2.5   # z > +2.5 = WEAK signal

        if predicted_z >= STRONG_THRESHOLD:
            if peak_n == predicted_n:
                status  = "CONFIRMED"
                message = (f"STRONG signal at predicted register {predicted_n}/pi "
                           f"(z={predicted_z:.2f}). Peak matches prediction exactly.")
                any_signal = True
            else:
                status  = "PARTIAL"
                message = (f"STRONG signal at predicted register {predicted_n}/pi "
                           f"(z={predicted_z:.2f}) but peak is at {peak_n}/pi "
                           f"(z={peak_z:.2f}). Framework registers signal; peak is offset.")
                any_signal = True

        elif peak_z >= STRONG_THRESHOLD and peak_n != predicted_n:
            status  = "UNEXPECTED_SIGNAL"
            message = (f"STRONG signal at unexpected register {peak_n}/pi "
                       f"(z={peak_z:.2f}). Predicted {predicted_n}/pi shows z={predicted_z:.2f}. "
                       f"Signal is real but our scalarization assumption may need revision.")
            any_signal = True
            all_pass   = False

        elif predicted_z >= WEAK_THRESHOLD:
            status  = "WEAK_SIGNAL"
            message = (f"Weak signal at predicted register {predicted_n}/pi "
                       f"(z={predicted_z:.2f}). Below STRONG threshold ({STRONG_THRESHOLD}). "
                       f"Suggestive but not conclusive.")
            any_signal = True
            all_pass   = False

        else:
            status  = "NULL"
            message = (f"No signal at predicted register {predicted_n}/pi "
                       f"(z={predicted_z:.2f}). Peak register is {peak_n}/pi "
                       f"(z={peak_z:.2f}). "
                       f"Null result constrains the crystalline terminus model.")
            all_pass = False

        # Full register z-score table for Vera's reporting layer
        sorted_registers = sorted(register_zscores.keys())
        register_table   = [
            {"register": n, "scalar": round(scalar_at_register(n), 6),
             "z_score": round(register_zscores[n], 4)}
            for n in sorted_registers
        ]

        result = {
            "domain":                domain,
            "field":                 field,
            "register_predicted":    predicted_n,
            "register_predicted_scalar": round(scalar_at_register(predicted_n), 6),
            "register_secondary":    secondary_n,
            "z_at_predicted":        round(predicted_z, 4),
            "z_at_secondary":        round(secondary_z, 4) if secondary_z is not None else None,
            "peak_register":         peak_n,
            "peak_z":                round(peak_z, 4),
            "peak_scalar":           round(scalar_at_register(peak_n), 6),
            "status":                status,
            "message":               message,
            "physical_interpretation": interpretation,
            "note":                  note,
            "register_table":        register_table,
        }
        results.append(result)

    # Overall probe verdict
    if all_pass and any_signal:
        verdict = "CONFIRMED"
        verdict_message = ("All probe targets show STRONG signal at predicted registers. "
                           "Crystalline terminus hypothesis supported.")
    elif any_signal and not all_pass:
        verdict = "PARTIAL"
        verdict_message = ("Some probe targets show signal. Mixed result. "
                           "Review per-target status for next steps.")
    elif not any_signal:
        verdict = "NULL"
        verdict_message = ("No targets show signal above threshold. "
                           "Null result constrains the crystalline terminus model. "
                           "Consider alternative scalarization formulas.")
    else:
        verdict = "UNKNOWN"
        verdict_message = "Could not determine verdict. Review target results individually."

    return {
        "verdict":         verdict,
        "verdict_message": verdict_message,
        "targets":         results,
        "any_signal":      any_signal,
        "all_confirmed":   all_pass and any_signal,
    }

# ---------------------------------------------------------------------------
# Report Writer
# ---------------------------------------------------------------------------
def write_diagnostic_report(probe_name: str, probe_cfg: dict,
                             diagnostic: dict, engine_version: str,
                             checksum: str, stage_results: list,
                             total_elapsed: float, run_timestamp: str):
    """
    Write the probe diagnostic report in both JSON and human-readable text.
    Chain-of-custody: additive output only. No source files modified.
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # JSON report — machine-readable, for Vera's reporting layer
    json_report = {
        "probe_name":            probe_name,
        "description":           probe_cfg.get("description", ""),
        "pre_registration_doi":  probe_cfg.get("pre_registration_doi", ""),
        "run_timestamp":         run_timestamp,
        "completed_utc":         utc_now(),
        "engine_version":        engine_version,
        "unified_master_md5":    checksum,
        "total_runtime":         format_elapsed(total_elapsed),
        "pipeline_stages":       stage_results,
        "diagnostic":            diagnostic,
    }

    json_path = REPORTS_DIR / f"probe_diagnostic_{probe_name}_{run_timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_report, f, indent=2, ensure_ascii=False)

    # Human-readable text report
    txt_path = REPORTS_DIR / f"probe_diagnostic_{probe_name}_{run_timestamp}.txt"
    lines    = []

    lines.append("=" * 70)
    lines.append(f"  KISHLATTICE STAR PROBE -- DIAGNOSTIC REPORT")
    lines.append(f"  Probe:            {probe_name}")
    lines.append(f"  Description:      {probe_cfg.get('description', '')}")
    lines.append(f"  Pre-registration: {probe_cfg.get('pre_registration_doi', '')}")
    lines.append(f"  Run timestamp:    {run_timestamp}")
    lines.append(f"  Completed UTC:    {utc_now()}")
    lines.append(f"  Total runtime:    {format_elapsed(total_elapsed)}")
    lines.append(f"  Engine version:   {engine_version[:64]}")
    lines.append(f"                    {engine_version[64:128]}")
    lines.append(f"                    {engine_version[128:]}")
    lines.append(f"  Unified master:   {checksum}")
    lines.append("=" * 70)
    lines.append("")

    # Stage summary
    lines.append("PIPELINE STAGES")
    lines.append("-" * 40)
    for s in stage_results:
        icon = "[OK]  " if s["success"] else "[FAIL]"
        lines.append(f"  {icon} {s['name']:<12} {format_elapsed(s['elapsed'])}")
    lines.append("")

    # Overall verdict
    verdict = diagnostic.get("verdict", "UNKNOWN")
    lines.append("=" * 70)
    lines.append(f"  PROBE VERDICT: {verdict}")
    lines.append(f"  {diagnostic.get('verdict_message', '')}")
    lines.append("=" * 70)
    lines.append("")

    # Per-target results
    lines.append("TARGET RESULTS")
    lines.append("-" * 70)

    for target in diagnostic.get("targets", []):
        lines.append(f"")
        lines.append(f"  Domain:      {target['domain']}")
        lines.append(f"  Field:       {target['field']}")
        lines.append(f"  Predicted:   N={target['register_predicted']} "
                     f"(scalar={target.get('register_predicted_scalar', 'n/a')})")
        if target.get("register_secondary"):
            lines.append(f"  Secondary:   N={target['register_secondary']}")
        lines.append(f"  Status:      {target['status']}")
        lines.append(f"  z @ predict: {target.get('z_at_predicted', 'n/a')}")
        if target.get("z_at_secondary") is not None:
            lines.append(f"  z @ second:  {target.get('z_at_secondary')}")
        lines.append(f"  Peak:        N={target.get('peak_register')} "
                     f"(z={target.get('peak_z', 'n/a')}, "
                     f"scalar={target.get('peak_scalar', 'n/a')})")
        lines.append(f"  Message:     {target['message']}")
        lines.append(f"  Physics:     {target.get('physical_interpretation', '')}")
        lines.append("")

        # Register table
        reg_table = target.get("register_table", [])
        if reg_table:
            lines.append(f"  {'N':>4}  {'scalar':>10}  {'z_score':>10}  {'':}")
            lines.append(f"  {'-'*4}  {'-'*10}  {'-'*10}")
            for row in reg_table:
                n    = row["register"]
                sc   = row["scalar"]
                z    = row["z_score"]
                flag = ""
                if n == target.get("register_predicted"):
                    flag = "  <-- PREDICTED"
                elif n == target.get("register_secondary"):
                    flag = "  <-- SECONDARY"
                elif n == target.get("peak_register"):
                    flag = "  <-- PEAK"
                lines.append(f"  {n:>4}  {sc:>10.6f}  {z:>10.4f}{flag}")
        lines.append("")
        lines.append("  " + "-" * 68)

    lines.append("")
    lines.append("NOTE: A null result or wrong-register result is scientific information.")
    lines.append("      Wrong register + strong signal = scalarization assumption needs revision.")
    lines.append("      Null result = framework constrains the crystalline terminus model.")
    lines.append("      The data is the authority. Pre-registration timestamps our current understanding.")
    lines.append("")
    lines.append(f"  JSON report: {json_path}")
    lines.append("=" * 70)

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n  Diagnostic report (JSON): {json_path}")
    print(f"  Diagnostic report (text): {txt_path}")

    return json_path, txt_path

# ---------------------------------------------------------------------------
# Advisory
# ---------------------------------------------------------------------------
ADVISORY = """
==============================================================
         KISHLATTICE STAR PROBE -- RUNTIME ADVISORY
==============================================================
  FRB probe lakes are small (~5000 + ~900 records).
  Expected runtime on commodity hardware:
    scalarize:  < 1 min
    unify:      < 1 min
    chaos:      2-5 min
    pinch:      2-10 min
  Total: approximately 10-20 minutes.

  [MONITORING TIP] In a second terminal, run:
    python engine_lattice_probe1/sidecar.py
  to watch live progress.

  Output:
    lakes/unified/unified_master.jsonl
    lakes/unified/z_scores_master.json
    lakes/reports/probe_diagnostic_star_probe_<timestamp>.json
    lakes/reports/probe_diagnostic_star_probe_<timestamp>.txt

  CANCEL: press Ctrl+C within 10 seconds
==============================================================
"""

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="KishLattice Star Probe -- Crystalline Terminus Diagnostic",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python engine_lattice_probe1/run_probe.py --probe star_probe
  python engine_lattice_probe1/run_probe.py --probe star_probe --no-advisory
  python engine_lattice_probe1/run_probe.py --probe star_probe --from pinch
  python engine_lattice_probe1/run_probe.py --probe star_probe --dry-run
        """
    )
    parser.add_argument("--probe",       required=True, metavar="PROBE_NAME",
                        help="Name of the probe to run (must exist in harmonic_targets.json probes block)")
    parser.add_argument("--from",        dest="from_stage", metavar="STAGE",
                        choices=STAGE_NAMES, default=None,
                        help="Resume from this stage (skips earlier stages)")
    parser.add_argument("--dry-run",     action="store_true",
                        help="Print execution plan without running anything")
    parser.add_argument("--no-advisory", action="store_true",
                        help="Skip the countdown advisory")
    args = parser.parse_args()

    # Change to vol root so relative paths in engine scripts resolve correctly
    os.chdir(VOL_ROOT)

    # ---------------------------------------------------------------------------
    # Load probe and volume configs
    # ---------------------------------------------------------------------------
    print("\nKishLattice Star Probe")
    print("=" * 60)
    print(f"  Probe:    {args.probe}")
    print(f"  Vol root: {VOL_ROOT}")
    print()

    probe_cfg    = load_probe_config(args.probe)
    probe_vols   = load_probe_volumes(args.probe)

    # ---------------------------------------------------------------------------
    # Engine fingerprint
    # ---------------------------------------------------------------------------
    print(f"\n[{utc_now()}] Computing engine fingerprint...")
    engine_version = get_engine_version()
    if engine_version.startswith("ERROR"):
        print(f"  WARNING: Could not compute engine fingerprint: {engine_version}")
    else:
        print(f"  Engine version: {engine_version[:64]}...")
        print(f"                  ...{engine_version[64:128]}...")
        print(f"                  ...{engine_version[128:]}")

    # ---------------------------------------------------------------------------
    # Build stage list
    # ---------------------------------------------------------------------------
    if args.from_stage:
        start_idx     = STAGE_NAMES.index(args.from_stage)
        stages_to_run = PIPELINE_STAGES[start_idx:]
        print(f"\nResuming from stage: {args.from_stage}")
    else:
        stages_to_run = PIPELINE_STAGES

    print(f"\nStages to run: {' -> '.join(s['name'] for s in stages_to_run)}")

    if args.dry_run:
        print("\n[DRY RUN] No scripts will be executed.")
        for stage in stages_to_run:
            print(f"  Would run: python {stage['script']}")
        print("\n[DRY RUN] Probe diagnostic would be generated after pinch stage.")
        return

    # ---------------------------------------------------------------------------
    # Advisory countdown
    # ---------------------------------------------------------------------------
    if not args.no_advisory:
        print(ADVISORY)
        print("Starting in 10 seconds. Press Ctrl+C to cancel.")
        try:
            for i in range(10, 0, -1):
                print(f"  {i}...", end="\r", flush=True)
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\nCancelled.")
            sys.exit(0)
        print()

    # ---------------------------------------------------------------------------
    # Run pipeline stages
    # ---------------------------------------------------------------------------
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    run_timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_path      = LOGS_DIR / f"probe_{args.probe}_{run_timestamp}.log"

    pipeline_start = time.time()
    stage_results  = []
    checksum       = "not_yet_computed"

    with open(log_path, "w", encoding="utf-8") as log_fh:
        log_header = (
            f"KishLattice Star Probe Run Log\n"
            f"{'=' * 60}\n"
            f"probe_name:      {args.probe}\n"
            f"run_timestamp:   {run_timestamp}\n"
            f"vol_root:        {VOL_ROOT}\n"
            f"engine_version:  {engine_version}\n"
            f"stages:          {', '.join(s['name'] for s in stages_to_run)}\n"
            f"started_utc:     {utc_now()}\n"
            f"{'=' * 60}\n\n"
        )
        log_fh.write(log_header)
        log_fh.flush()

        for stage in stages_to_run:
            result = run_stage(stage, log_fh, dry_run=False)
            stage_results.append(result)

            if stage.get("checksum") and result["success"]:
                checksum = read_checksum()

            if not result["success"]:
                msg = (f"\n{'=' * 60}\n"
                       f"[{utc_now()}] PIPELINE HALTED -- {stage['name']} failed.\n"
                       f"  Fix the issue and re-run:\n"
                       f"  python engine_lattice_probe1/run_probe.py "
                       f"--probe {args.probe} --from {stage['name']}\n"
                       f"{'=' * 60}")
                print(msg)
                log_fh.write(msg + "\n")
                break

        total_elapsed = time.time() - pipeline_start

        # ---------------------------------------------------------------------------
        # Probe diagnostic (runs even if pipeline halted — partial data is informative)
        # ---------------------------------------------------------------------------
        print(f"\n{'=' * 60}")
        print(f"[{utc_now()}] STAGE: PROBE DIAGNOSTIC")
        print("Reading z_scores_master.json and evaluating targets...")
        print(f"{'=' * 60}")

        lock_threshold = 0.05
        try:
            with open(HARMONIC_CFG, "r", encoding="utf-8") as f:
                harmonic_cfg = json.load(f)
            lock_threshold = float(harmonic_cfg.get("lock_threshold", 0.05))
        except Exception:
            pass

        diagnostic = build_probe_diagnostic(probe_cfg, lock_threshold)

        # Print verdict to terminal
        print(f"\n  PROBE VERDICT: {diagnostic['verdict']}")
        print(f"  {diagnostic['verdict_message']}")
        print()
        for target in diagnostic.get("targets", []):
            print(f"  [{target['status']:>20}]  {target['domain']}  "
                  f"(predicted N={target['register_predicted']}, "
                  f"z={target.get('z_at_predicted', 'n/a')}, "
                  f"peak N={target.get('peak_register')}, "
                  f"peak z={target.get('peak_z', 'n/a')})")

        # Write full report
        json_path, txt_path = write_diagnostic_report(
            args.probe, probe_cfg, diagnostic, engine_version,
            checksum, stage_results, total_elapsed, run_timestamp
        )

        # Final pipeline summary
        required_ok = all(r["success"] for r in stage_results)
        status      = "COMPLETE" if required_ok else "HALTED"

        summary = (
            f"\n{'=' * 60}\n"
            f"[{utc_now()}] PROBE {status}\n"
            f"  Total runtime: {format_elapsed(total_elapsed)}\n"
            f"  Log file:      {log_path}\n"
            f"  Verdict:       {diagnostic['verdict']}\n"
            f"{'=' * 60}"
        )
        print(summary)
        log_fh.write(summary + "\n")

    sys.exit(0 if required_ok else 1)


if __name__ == "__main__":
    main()