# ==============================================================================
# run_pipeline.py
# KishLattice Geometric Harmonic Spectroscopy -- Pipeline Wrapper
#
# Runs the complete four-script pipeline in the correct sequence.
# Stateless execution designed for commodity hardware.
# ASCII-Safe version for Windows cp1252 encoding.
# Intelligent Checkpoint Management (Auto-wipes stale pinch states).
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
import subprocess
import sys
import time
import os
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PIPELINE_STAGES = [
    {
        'name':        'scalarize',
        'script':      'engine/scalarize.py',
        'description': 'Transform promoted lakes into scalar space',
        'produces':    'lakes/unified/*_scalarized.jsonl',
    },
    {
        'name':        'unify',
        'script':      'engine/unify.py',
        'description': 'Stream all scalarized lakes into unified master',
        'produces':    'lakes/unified/unified_master.jsonl',
        'checksum':    True,
    },
    {
        'name':        'chaos',
        'script':      'engine/build_chaos_nulls.py',
        'description': 'Build chaos null distributions per domain',
        'produces':    'lakes/synthetic/chaos_null_*.jsonl',
    },
    {
        'name':        'pinch',
        'script':      'engine/build_pinch_table.py',
        'description': 'Compute z-scores and cross-domain pinch table',
        'produces':    'lakes/unified/pinch_table_cross_domain.json',
    },
    {
        'name':        'figures',
        'script':      'engine/generate_figures.py',
        'description': 'Run report plugins and generate analysis figures',
        'produces':    'lakes/figures/run_TIMESTAMP/',
        'optional':    True,   # pipeline still COMPLETE if figures fail/skip
    },
]

STAGE_NAMES         = [s['name'] for s in PIPELINE_STAGES]
UNIFIED_MASTER_PATH = Path('lakes/unified/unified_master.jsonl')
CHECKSUM_PATH       = Path('lakes/unified/unified_master.jsonl.md5')
LOGS_DIR            = Path('lakes/logs')
STATE_FILE_PATH     = Path('lakes/unified/pinch_state.json')

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------
def utc_now() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

def format_elapsed(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:   return f"{h}h {m}m {s}s"
    elif m > 0: return f"{m}m {s}s"
    else:       return f"{s}s"

def md5_file_streaming(filepath: Path) -> tuple:
    h = hashlib.md5()
    total_bytes = 0
    chunk_size = 8 * 1024 * 1024
    report_interval = 500 * 1024 * 1024
    last_report = 0
    file_size = filepath.stat().st_size
    start = time.time()
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
            total_bytes += len(chunk)
            if total_bytes - last_report >= report_interval:
                pct = 100 * total_bytes / file_size if file_size else 0
                elapsed = time.time() - start
                rate_mb = (total_bytes / elapsed / 1024 / 1024) if elapsed > 0 else 0
                print(f"    [{utc_now()}] Checksum progress: "
                      f"{total_bytes / 1024 / 1024:.0f} MB / "
                      f"{file_size / 1024 / 1024:.0f} MB "
                      f"({pct:.1f}%) at {rate_mb:.0f} MB/s",
                      flush=True)
                last_report = total_bytes
    return h.hexdigest(), total_bytes

def get_engine_version() -> str:
    try:
        engine_dir = Path(__file__).parent / 'engine'
        sys.path.insert(0, str(engine_dir))
        from engine_version import compute_engine_version
        return compute_engine_version()
    except Exception as e:
        return f"ERROR: {e}"
    finally:
        sys.path.pop(0)

def write_run_receipt(log_path: Path, engine_version: str, stage_results: list,
                      master_checksum, total_elapsed: float):
    receipt_path = log_path.with_suffix('.receipt.txt')
    with open(receipt_path, 'w', encoding='utf-8') as f:
        f.write("KishLattice Pipeline Run Receipt\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"engine_version:  {engine_version}\n")
        f.write(f"total_runtime:   {format_elapsed(total_elapsed)}\n")
        f.write(f"completed_utc:   {utc_now()}\n\n")
        f.write("Stages:\n")
        for r in stage_results:
            status = "[OK]" if r['success'] else "[FAIL]"
            f.write(f"  {status} {r['name']:<12} {format_elapsed(r['elapsed'])}\n")
        if master_checksum:
            f.write(f"\nunified_master MD5: {master_checksum}\n")
            f.write(f"checksum_file:      {CHECKSUM_PATH}\n")
    print(f"\n  Receipt written: {receipt_path}")

# ---------------------------------------------------------------------------
# Advisory
# ---------------------------------------------------------------------------
OS_ADVISORY = """
==============================================================
           KISHLATTICE PIPELINE -- RUNTIME ADVISORY
==============================================================
  This pipeline run will take approximately 2-4 hours on
  current hardware (vectorized engine, Vol 11 lake set).
  Full 44-lake configuration with Gaia, SDSS, and PDB:
    scalarize:  ~3 min
    unify:      ~3 min
    chaos:      ~7 min
    pinch:      ~2h (parallel pairings + vectorized z-scores)
    figures:    ~5-10 min (adaptive reports)
  Do NOT interrupt or reboot during pinch stage.
  The pipeline is stateless -- a reboot means starting over.
  BEFORE STARTING -- disable automatic restarts:
  Windows:
    Settings > Windows Update > Advanced > Active Hours
    Or (Admin PowerShell):
      reg add HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\
        WindowsUpdate\\AU /v NoAutoRebootWithLoggedOnUsers
        /t REG_DWORD /d 1 /f
    Disable sleep:
      powercfg /change standby-timeout-ac 0
  Linux:
    sudo systemctl mask sleep.target suspend.target
    sudo systemctl mask hibernate.target hybrid-sleep.target
  LARGE LAKE SILENCE IS NORMAL:
    s1, s2, s3, s4 (Gaia, 2M records each): 1-3h each
    g1 (SDSS galaxies, 1.8M records): 2-4h
    Heartbeat printed every 500k records with timestamp.
    If no output for 30+ min on large lakes: still running.
  OUTPUT: run log written to lakes/logs/run_TIMESTAMP.log
  FIGURES: written to lakes/figures/run_TIMESTAMP/
  CANCEL: press Ctrl+C within 10 seconds to abort safely
==============================================================
"""

def print_advisory(skip: bool = False):
    if skip:
        print("[Advisory skipped via --no-advisory]")
        return
    print(OS_ADVISORY)
    print("Starting pipeline in 10 seconds. Press Ctrl+C to cancel.\n")
    try:
        for i in range(10, 0, -1):
            print(f"  {i}...", end='\r', flush=True)
            time.sleep(1)
        print("  Starting now.          \n")
    except KeyboardInterrupt:
        print("\n\nCancelled by operator. No pipeline stages were run.")
        sys.exit(0)

# ---------------------------------------------------------------------------
# Stage runner
# ---------------------------------------------------------------------------
def run_stage(stage: dict, log_fh, dry_run: bool = False) -> dict:
    name   = stage['name']
    script = stage['script']
    desc   = stage['description']

    header = (f"\n{'=' * 60}\n"
              f"[{utc_now()}] STAGE: {name.upper()}\n"
              f"{desc}\n"
              f"{'=' * 60}")
    print(header, flush=True)
    log_fh.write(header + '\n')
    log_fh.flush()

    if dry_run:
        msg = f"  [DRY RUN] Would execute: python {script}"
        print(msg)
        log_fh.write(msg + '\n')
        return {'name': name, 'success': True, 'elapsed': 0.0}

    if not Path(script).exists():
        msg = f"  ERROR: Script not found: {script}"
        print(msg, flush=True)
        log_fh.write(msg + '\n')
        return {'name': name, 'success': False, 'elapsed': 0.0,
                'error': f"Script not found: {script}"}

    start = time.time()
    try:
        # ------------------------------------------------------------------
        # ENCODING FIX: encoding='utf-8' ensures child process stdout is
        # captured correctly on Windows (default cp1252 would crash on any
        # non-ASCII byte printed by an engine script).
        # errors='replace' prevents a child-side encoding failure from
        # propagating up and killing the pipeline wrapper.
        # ------------------------------------------------------------------
        process = subprocess.Popen(
            [sys.executable, script],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1
        )
        for line in process.stdout:
            print(line, end='', flush=True)
            log_fh.write(line)
            log_fh.flush()
        process.wait()
        elapsed = time.time() - start

        if process.returncode != 0:
            msg = (f"\n[{utc_now()}] STAGE FAILED: {name} "
                   f"(exit code {process.returncode}) after {format_elapsed(elapsed)}")
            print(msg, flush=True)
            log_fh.write(msg + '\n')
            return {'name': name, 'success': False, 'elapsed': elapsed,
                    'error': f"Exit code {process.returncode}"}

        summary = f"\n[{utc_now()}] STAGE COMPLETE: {name} in {format_elapsed(elapsed)}"
        print(summary, flush=True)
        log_fh.write(summary + '\n')
        return {'name': name, 'success': True, 'elapsed': elapsed}

    except Exception as e:
        elapsed = time.time() - start
        msg = f"\n[{utc_now()}] STAGE EXCEPTION: {name} -- {e}"
        print(msg, flush=True)
        log_fh.write(msg + '\n')
        return {'name': name, 'success': False, 'elapsed': elapsed, 'error': str(e)}

# ---------------------------------------------------------------------------
# Checksum
# ---------------------------------------------------------------------------
def compute_and_write_checksum(engine_version: str, log_fh):
    header = f"\n[{utc_now()}] CHECKSUM: computing MD5 of unified_master.jsonl"
    print(header, flush=True)
    log_fh.write(header + '\n')

    if not UNIFIED_MASTER_PATH.exists():
        msg = f"  ERROR: unified_master.jsonl not found at {UNIFIED_MASTER_PATH}"
        print(msg, flush=True)
        log_fh.write(msg + '\n')
        return None

    file_size_mb = UNIFIED_MASTER_PATH.stat().st_size / 1024 / 1024
    print(f"  File size: {file_size_mb:.1f} MB -- streaming checksum...", flush=True)
    start = time.time()
    checksum, byte_count = md5_file_streaming(UNIFIED_MASTER_PATH)
    elapsed = time.time() - start
    generated = utc_now()

    with open(CHECKSUM_PATH, 'w', encoding='utf-8') as f:
        f.write(f"{checksum}  unified_master.jsonl\n")
        f.write(f"bytes:          {byte_count:,}\n")
        f.write(f"size_mb:        {byte_count / 1024 / 1024:.2f}\n")
        f.write(f"generated_utc:  {generated}\n")
        f.write(f"engine_version: {engine_version}\n")

    summary = (f"  Checksum:      {checksum}\n"
               f"  Bytes:         {byte_count:,}\n"
               f"  Computed in:   {format_elapsed(elapsed)}\n"
               f"  Written to:    {CHECKSUM_PATH}")
    print(summary, flush=True)
    log_fh.write(summary + '\n')
    return checksum

# ---------------------------------------------------------------------------
# Verify mode
# ---------------------------------------------------------------------------
def verify_checksum() -> bool:
    print(f"\n[{utc_now()}] VERIFY: checking unified_master.jsonl integrity")
    if not CHECKSUM_PATH.exists():
        print(f"  ERROR: No checksum file found at {CHECKSUM_PATH}")
        print("  Run the full pipeline first to generate a checksum.")
        return False
    with open(CHECKSUM_PATH, 'r', encoding='utf-8') as f:
        first_line = f.readline().strip()
    expected = first_line.split()[0]
    print(f"  Expected MD5: {expected}")
    print(f"  Computing current MD5 of {UNIFIED_MASTER_PATH}...")
    if not UNIFIED_MASTER_PATH.exists():
        print("  ERROR: unified_master.jsonl not found.")
        return False
    actual, byte_count = md5_file_streaming(UNIFIED_MASTER_PATH)
    print(f"  Actual MD5:   {actual}")
    if actual == expected:
        print(f"\n  VERIFIED: unified_master.jsonl is intact.")
        print(f"  Size: {byte_count:,} bytes")
        return True
    else:
        print(f"\n  MISMATCH: unified_master.jsonl has been modified or corrupted.")
        print(f"  The file does not match the published checksum.")
        return False

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description='KishLattice pipeline wrapper -- five stages in sequence.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_pipeline.py                    Full pipeline from scratch
  python run_pipeline.py --no-advisory      Skip the 10-second countdown
  python run_pipeline.py --from unify       Start from unify (skip scalarize)
  python run_pipeline.py --from figures     Re-run figures only (pinch done)
  python run_pipeline.py --skip-figures     Run pipeline, skip figure generation
  python run_pipeline.py --dry-run          Print plan without executing
  python run_pipeline.py --verify           Verify unified_master checksum
        """
    )
    parser.add_argument('--from', dest='from_stage', metavar='STAGE',
                        choices=STAGE_NAMES, default=None)
    parser.add_argument('--dry-run',      action='store_true')
    parser.add_argument('--no-advisory',  action='store_true')
    parser.add_argument('--verify',       action='store_true')
    parser.add_argument('--skip-figures', action='store_true',
                        help='Run pipeline but skip the figures stage')
    args = parser.parse_args()

    vol_root = Path(__file__).resolve().parent.parent
    os.chdir(vol_root)

    if args.verify:
        ok = verify_checksum()
        sys.exit(0 if ok else 1)

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    run_timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    log_path = LOGS_DIR / f"run_{run_timestamp}.log"

    # Build stage list
    if args.from_stage:
        start_idx = STAGE_NAMES.index(args.from_stage)
        stages_to_run = PIPELINE_STAGES[start_idx:]
        print(f"Resuming from stage: {args.from_stage}")
    else:
        stages_to_run = PIPELINE_STAGES

    # Filter out figures if --skip-figures requested
    if args.skip_figures:
        stages_to_run = [s for s in stages_to_run if s['name'] != 'figures']

    print("\nKishLattice Pipeline Wrapper")
    print("=" * 60)
    print(f"  Vol root:   {vol_root}")
    print(f"  Log file:   {log_path}")
    print(f"  Stages:     {' -> '.join(s['name'] for s in stages_to_run)}")
    print(f"  Dry run:    {'YES' if args.dry_run else 'no'}")
    if args.skip_figures:
        print(f"  Figures:    SKIPPED (--skip-figures)")

    # --- INTELLIGENT CHECKPOINT MANAGEMENT ---
    if STATE_FILE_PATH.exists():
        if args.from_stage == 'pinch':
            print(f"  Checkpoint: KEEPING {STATE_FILE_PATH.name} (Resume mode)")
        else:
            print(f"  Checkpoint: WIPING {STATE_FILE_PATH.name} (Fresh run)")
            if not args.dry_run:
                try:
                    STATE_FILE_PATH.unlink()
                except Exception as e:
                    print(f"  [WARNING] Could not delete checkpoint: {e}")
    print()

    print(f"[{utc_now()}] Computing engine fingerprint...")
    engine_version = get_engine_version()
    if engine_version.startswith("ERROR"):
        print(f"  WARNING: Could not compute engine fingerprint: {engine_version}")
    else:
        print(f"  Engine version: {engine_version[:64]}...")
        print(f"                  ...{engine_version[64:128]}...")
        print(f"                  ...{engine_version[128:]}")

    if not args.dry_run:
        print_advisory(skip=args.no_advisory)

    pipeline_start  = time.time()
    stage_results   = []
    master_checksum = None

    with open(log_path, 'w', encoding='utf-8') as log_fh:
        log_header = (
            f"KishLattice Pipeline Run Log\n"
            f"{'=' * 60}\n"
            f"run_timestamp:   {run_timestamp}\n"
            f"vol_root:        {vol_root}\n"
            f"engine_version:  {engine_version}\n"
            f"stages:          {', '.join(s['name'] for s in stages_to_run)}\n"
            f"started_utc:     {utc_now()}\n"
            f"{'=' * 60}\n\n"
        )
        log_fh.write(log_header)
        log_fh.flush()

        for stage in stages_to_run:
            is_optional = stage.get('optional', False)

            result = run_stage(stage, log_fh, dry_run=args.dry_run)
            stage_results.append(result)

            # Post-stage checksum (unify only)
            if result['success'] and stage.get('checksum') and not args.dry_run:
                master_checksum = compute_and_write_checksum(engine_version, log_fh)

            if not result['success']:
                if is_optional:
                    # Optional stages (figures) warn but do not halt the pipeline
                    msg = (f"\n[{utc_now()}] STAGE WARNING: {stage['name']} failed "
                           f"(optional stage -- pipeline continues).\n"
                           f"  Error: {result.get('error', 'unknown')}\n"
                           f"  Re-run figures with: "
                           f"python run_pipeline.py --from figures")
                    print(msg, flush=True)
                    log_fh.write(msg + '\n')
                    # Mark as non-fatal: flip success for summary purposes only
                    result['optional_failure'] = True
                else:
                    # Required stages halt the pipeline
                    msg = (f"\n{'=' * 60}\n"
                           f"[{utc_now()}] PIPELINE HALTED -- {stage['name']} failed.\n"
                           f"  Error: {result.get('error', 'unknown')}\n"
                           f"  Fix the issue and re-run from: "
                           f"python run_pipeline.py --from {stage['name']}\n"
                           f"{'=' * 60}")
                    print(msg, flush=True)
                    log_fh.write(msg + '\n')
                    break

        total_elapsed = time.time() - pipeline_start

        # Pipeline is COMPLETE if all required stages passed.
        # Optional stage failures count as warnings, not failures.
        required_ok = all(
            r['success'] or r.get('optional_failure', False)
            for r in stage_results
        )
        all_ok = all(r['success'] for r in stage_results)
        status = "COMPLETE" if required_ok else "FAILED"

        summary_lines = [
            f"\n{'=' * 60}",
            f"[{utc_now()}] PIPELINE {status}",
            f"  Total runtime: {format_elapsed(total_elapsed)}",
            f"  Log file:      {log_path}",
            "",
            "  Stage summary:",
        ]
        for r in stage_results:
            if r['success']:
                icon = "[OK]  "
            elif r.get('optional_failure'):
                icon = "[WARN]"
            else:
                icon = "[FAIL]"
            summary_lines.append(
                f"    {icon} {r['name']:<12} {format_elapsed(r['elapsed'])}")

        if master_checksum:
            summary_lines += [
                "",
                f"  unified_master MD5: {master_checksum}",
                f"  Checksum file:      {CHECKSUM_PATH}",
            ]

        if not args.dry_run:
            summary_lines += [
                "",
                f"  Engine fingerprint: {engine_version[:64]}",
                f"                      {engine_version[64:128]}",
                f"                      {engine_version[128:]}",
            ]
        summary_lines.append("=" * 60)
        summary = '\n'.join(summary_lines)
        print(summary, flush=True)
        log_fh.write(summary + '\n')

        if not args.dry_run:
            write_run_receipt(log_path, engine_version, stage_results,
                              master_checksum, total_elapsed)

    sys.exit(0 if required_ok else 1)

if __name__ == '__main__':
    main()