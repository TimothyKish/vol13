# ==============================================================================
# SCRIPT: unify.py  (STREAMING REWRITE — memory-safe)
# PURPOSE: Merge all enabled scalarized lakes into unified_master.jsonl
#
# FIX:
#   Streaming approach — one record at a time, never holds full lake in RAM.
#   UPGRADE: Added Sidecar Heartbeat Telemetry & Monitoring Tip.
#
# OUTPUT FILES:
#   lakes/unified/unified_master.jsonl      — all records merged
#   lakes/unified/unified_master.jsonl.md5  — sovereign cryptographic receipt
#   lakes/unified/sweep_results.json        — per-domain scalar statistics
#   lakes/unified/pinch_table.json          — domain summary table
#
# AUTHORS: Timothy John Kish & Mondy
# AUDIT STATUS: mondy_verified_2026-05-14 (streaming rewrite + checksum + telemetry)
# ==============================================================================

import json
import math
import os
import sys
import time
import hashlib
from datetime import datetime
from pathlib import Path

# --------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------
SCRIPT_DIR   = Path(__file__).resolve().parent
VOL5_ROOT    = SCRIPT_DIR.parent
CONFIG_PATH  = VOL5_ROOT / "configs" / "volumes.json"
UNIFIED_DIR  = VOL5_ROOT / "lakes" / "unified"
MASTER_PATH  = UNIFIED_DIR / "unified_master.jsonl"
SWEEP_PATH   = UNIFIED_DIR / "sweep_results.json"
PINCH_PATH   = UNIFIED_DIR / "pinch_table.json"
HEARTBEAT_PATH = UNIFIED_DIR / "lattice_heartbeat.json"

UNIFIED_DIR.mkdir(parents=True, exist_ok=True)

HEARTBEAT_INTERVAL = 250_000  # records

# --------------------------------------------------------------------
# Heartbeat Telemetry
# --------------------------------------------------------------------
def write_heartbeat(pct, elapsed, total_tasks, completed_tasks, current_action):
    eta = (elapsed / max(1, completed_tasks)) * (total_tasks - completed_tasks) if completed_tasks > 0 else 0
    data = {
        "timestamp_utc": time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
        "progress_pct": min(100.0, max(0.0, round(pct, 2))),
        "completed": completed_tasks,
        "total": total_tasks,
        "eta_seconds": round(eta, 1),
        "current_action": current_action
    }
    try:
        with open(HEARTBEAT_PATH, 'w') as f:
            json.dump(data, f)
    except Exception:
        pass

# --------------------------------------------------------------------
# Load volumes config
# --------------------------------------------------------------------
def load_volumes():
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg.get("volumes", {})

# --------------------------------------------------------------------
# Locate scalarized file for a given lake name
# --------------------------------------------------------------------
def find_scalarized(name):
    candidates = [
        UNIFIED_DIR / f"{name}_scalarized.jsonl",
        UNIFIED_DIR / f"{name}.jsonl",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None

# --------------------------------------------------------------------
# Streaming unify — core function
# --------------------------------------------------------------------
def unify_streaming(volumes):
    domain_stats = {}
    total_written = 0
    lakes_processed = 0
    master_hash = hashlib.md5()
    
    run_start = time.time()
    start_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    print(f"[{start_time}] Pipeline run started.\n")

    enabled_lakes = [n for n, c in volumes.items() if c.get("enabled", False)]
    total_lakes = len(enabled_lakes)
    
    write_heartbeat(0, 0, total_lakes, 0, "Initializing Unify Phase...")

    with MASTER_PATH.open("w", encoding="utf-8") as fout:
        for lake_name, cfg in volumes.items():
            if not cfg.get("enabled", False):
                continue

            scalarized = find_scalarized(lake_name)
            if scalarized is None:
                print(f"  [SKIP] {lake_name} — scalarized file not found")
                lakes_processed += 1
                continue

            domain = cfg.get("domain", lake_name)
            lake_count = 0
            heartbeat_last = time.time()

            with scalarized.open("r", encoding="utf-8") as fin:
                for line in fin:
                    line = line.strip()
                    if not line:
                        continue

                    rec = json.loads(line)
                    scalar = (rec.get("scalar_klc")
                              or rec.get("scalar_kls")
                              or rec.get("scalar_invariant")
                              or 0.0)
                    try:
                        scalar = float(scalar)
                    except (TypeError, ValueError):
                        scalar = 0.0
                    if not math.isfinite(scalar):
                        scalar = 0.0

                    rec["domain"] = domain
                    line_str = json.dumps(rec, ensure_ascii=False) + "\n"
                    line_bytes = line_str.encode('utf-8')
                    fout.write(line_str)
                    master_hash.update(line_bytes)

                    if domain not in domain_stats:
                        domain_stats[domain] = {
                            "n": 0, "nonzero": 0,
                            "sum": 0.0, "sum_sq": 0.0,
                            "min": float("inf"), "max": float("-inf"),
                            "lake_ids": set(),
                        }
                    ds = domain_stats[domain]
                    ds["n"]        += 1
                    ds["lake_ids"].add(lake_name)
                    if scalar != 0.0:
                        ds["nonzero"] += 1
                        ds["sum"]     += scalar
                        ds["sum_sq"]  += scalar * scalar
                        ds["min"]      = min(ds["min"], scalar)
                        ds["max"]      = max(ds["max"], scalar)

                    lake_count    += 1
                    total_written += 1

                    # Telemetry updates
                    if time.time() - heartbeat_last > 2.0:
                        pct = (lakes_processed / total_lakes) * 100
                        write_heartbeat(pct, time.time() - run_start, total_lakes, lakes_processed, f"Unifying {lake_name} ({lake_count:,} recs)")
                        heartbeat_last = time.time()

                    if lake_count % HEARTBEAT_INTERVAL == 0:
                        now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
                        print(f"    [{now}] {lake_count:,} records streamed from {lake_name}...", flush=True)

            lakes_processed += 1
            pct = (lakes_processed / total_lakes) * 100
            write_heartbeat(pct, time.time() - run_start, total_lakes, lakes_processed, f"Finished {lake_name}")
            
            nonzero = domain_stats.get(domain, {}).get("nonzero", 0)
            print(f"  [{lake_name}] domain={domain}  n={lake_count:,}  nonzero={nonzero:,}")

    master_checksum = master_hash.hexdigest()
    end_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    
    write_heartbeat(100, time.time() - run_start, total_lakes, total_lakes, "Writing Checksums...")

    checksum_path = MASTER_PATH.with_suffix('.jsonl.md5')
    with open(checksum_path, 'w') as f:
        f.write(f"{master_checksum}  unified_master.jsonl\n")
        f.write(f"records: {total_written}\n")
        f.write(f"generated_utc: {end_time}\n")

    total_elapsed = time.time() - run_start
    hours = int(total_elapsed // 3600)
    minutes = int((total_elapsed % 3600) // 60)
    seconds = int(total_elapsed % 60)

    print(f"\n[{end_time}] Run complete.")
    print(f"  Total runtime:   {hours}h {minutes}m {seconds}s")
    print(f"  Total records:   {total_written:,}")
    print(f"  Lakes processed: {lakes_processed}")
    print(f"  Throughput:      {total_written / total_elapsed:,.0f} records/sec (average)")
    print(f"  Master checksum: {master_checksum}")
    print(f"  Checksum saved:  {checksum_path}")
    
    return domain_stats

def build_sweep_results(domain_stats):
    sweep = {}
    for domain, ds in domain_stats.items():
        n       = ds["n"]
        nonzero = ds["nonzero"]
        if nonzero > 0:
            mean = ds["sum"] / nonzero
            var  = (ds["sum_sq"] / nonzero) - (mean * mean)
            std  = math.sqrt(max(0.0, var))
            dmin = ds["min"]
            dmax = ds["max"]
        else:
            mean = std = dmin = dmax = 0.0

        sweep[domain] = {
            "domain":  domain,
            "n":       n,
            "nonzero": nonzero,
            "mean":    round(mean, 6),
            "std":     round(std, 6),
            "min":     round(dmin, 6),
            "max":     round(dmax, 6),
            "lakes":   sorted(ds["lake_ids"]),
        }
    return sweep

def build_pinch_table(sweep_results):
    rows = []
    for domain, stats in sorted(sweep_results.items()):
        rows.append({
            "domain":  domain,
            "n":       stats["n"],
            "nonzero": stats["nonzero"],
            "mean":    stats["mean"],
            "std":     stats["std"],
            "min":     stats["min"],
            "max":     stats["max"],
        })
    return {"domains": rows}

def main():
    print("\n" + "=" * 60)
    print("  [MONITORING TIP] Open a new terminal and run:")
    print("  python engine/sidecar.py")
    print("  to view the live unified streaming dashboard.")
    print("=" * 60 + "\n")

    volumes = load_volumes()
    enabled  = [(n, c) for n, c in volumes.items() if c.get("enabled", False)]
    disabled = [(n, c) for n, c in volumes.items() if not c.get("enabled", False)]
    print(f"Volumes: {len(volumes)} total, {len(enabled)} enabled, {len(disabled)} disabled\n")

    domain_stats = unify_streaming(volumes)

    sweep = build_sweep_results(domain_stats)
    with SWEEP_PATH.open("w", encoding="utf-8") as f:
        json.dump(sweep, f, indent=2)

    pinch = build_pinch_table(sweep)
    with PINCH_PATH.open("w", encoding="utf-8") as f:
        json.dump(pinch, f, indent=2)

    print(f"\nUnified master written: {MASTER_PATH}")
    print(f"Sweep results written:  {SWEEP_PATH}")
    print(f"Pinch table written:    {PINCH_PATH}\n")

    print("Domain summary:")
    print(f"  {'Domain':<22} {'n':>10} {'nonzero':>10} {'mean':>8} {'range'}")
    print("  " + "-" * 65)
    for domain, stats in sorted(sweep.items()):
        n    = stats["n"]
        nz   = stats["nonzero"]
        mean = stats["mean"]
        dmin = stats["min"]
        dmax = stats["max"]
        if nz > 0:
            print(f"  {domain:<22} {n:>10,} {nz:>10,} {mean:>8.4f} [{dmin:.4f}, {dmax:.4f}]")
        else:
            print(f"  {domain:<22} {n:>10,} {'(all zeros)':>20}")

if __name__ == "__main__":
    main()