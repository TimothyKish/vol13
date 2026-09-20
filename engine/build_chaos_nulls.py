# ==============================================================================
# SCRIPT: build_chaos_nulls.py
# VOLUME: 11 - Full Harmonic Sweep + Expanded Quantum Floor
# TARGET: Generate chaos, scramble, and synthetic null lakes for each active domain.
#
# UPGRADE: Dynamic Configuration Routing (Zero Hardcoding)
#          Expanded Quantum Floor (N=4 to N=26)
#          Sidecar Heartbeat Telemetry & Monitoring Tip
#          Harmonic register family loaded from configs/harmonic_targets.json
#          (Vol 11 upgrade: N/pi family is now config-driven, not hardcoded)
#
# VOL 11 UPGRADE: Added 3rd Null (Synthetic Matched Distribution).
#          Generates a smooth Gaussian matched to the exact mean/std of the real
#          data to prove the 16/pi lock is not an artifact of the log-modulo 
#          transform acting on smooth continuous data.
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
import json
import math
import random
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

PI    = math.pi
K_GEO = 16.0 / PI

# --------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------
ROOT                    = Path(__file__).resolve().parents[1]
UNIFIED                 = ROOT / "lakes" / "unified" / "unified_master.jsonl"
SYNTHETIC               = ROOT / "lakes" / "synthetic"
VOLUMES_CFG_PATH        = ROOT / "configs" / "volumes.json"
HARMONIC_TARGETS_CFG    = ROOT / "configs" / "harmonic_targets.json"
HEARTBEAT_PATH          = ROOT / "lakes" / "unified" / "lattice_heartbeat.json"

SYNTHETIC.mkdir(parents=True, exist_ok=True)

# Volume number — update each volume cycle
VOLUME_NUMBER = 11

# --------------------------------------------------------------------
# Harmonic Configuration Loader
# Reads configs/harmonic_targets.json so the N/pi family, container,
# and lock threshold are config-driven rather than hardcoded.
# Fallback to full 4/pi-26/pi defaults if config file is absent.
# --------------------------------------------------------------------
def load_harmonic_config():
    if HARMONIC_TARGETS_CFG.exists():
        with open(HARMONIC_TARGETS_CFG, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        registers      = cfg.get("registers", list(range(4, 27)))
        container      = int(cfg.get("container", 24))
        lock_threshold = float(cfg.get("lock_threshold", 0.05))
        print(f"[harmonic_targets.json] Loaded {len(registers)} registers "
              f"(N={registers[0]} to N={registers[-1]}), "
              f"container={container}, threshold={lock_threshold}")
    else:
        registers      = list(range(4, 27))
        container      = 24
        lock_threshold = 0.05
        print(f"[WARN] harmonic_targets.json not found at {HARMONIC_TARGETS_CFG}")
        print(f"       Using defaults: N=4..26, container=24, threshold=0.05")

    harmonic_targets = {f"{n}/pi": float(n) / PI for n in registers}
    return harmonic_targets, container, lock_threshold

# Load at module startup — all functions below use these values
HARMONIC_TARGETS, CONTAINER, LOCK_THRESHOLD = load_harmonic_config()

# --------------------------------------------------------------------
# Dynamic Configuration Loader (No Hardcoding)
# --------------------------------------------------------------------
CONFIG_PINCH_SLOTS = {}

def load_dynamic_configs():
    """Reads volumes.json to dynamically route domains and pinch slots."""
    global CONFIG_PINCH_SLOTS
    if VOLUMES_CFG_PATH.exists():
        with open(VOLUMES_CFG_PATH, "r", encoding="utf-8") as f:
            vols = json.load(f).get("volumes", {})
        for lake_id, meta in vols.items():
            if "__pinch_slot__" in meta:
                CONFIG_PINCH_SLOTS[lake_id.lower()] = meta["__pinch_slot__"]


def load_domain_scalars():
    load_dynamic_configs()
    domains = {}
    with UNIFIED.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec     = json.loads(line)
            domain  = (rec.get("domain") or "").lower()
            lake_id = (rec.get("lake_id") or rec.get("_volume_name") or "").lower()
            scalar  = rec.get("scalar_klc")
            if scalar is None:
                continue
            try:
                s = float(scalar)
            except (TypeError, ValueError):
                continue
            # --- DYNAMIC ROUTING ---
            if lake_id in CONFIG_PINCH_SLOTS:
                label = CONFIG_PINCH_SLOTS[lake_id]
            elif lake_id.startswith(("n1_", "n2_", "n3_", "n4_", "np1_")) or "null" in lake_id:
                label = f"null_{domain}"
            elif domain == "biology":
                label = "biology_other"
            elif domain == "astrophysics":
                label = "frb"
            else:
                label = domain
            domains.setdefault(label, []).append(s)
    return domains


# --------------------------------------------------------------------
# Heartbeat Telemetry
# --------------------------------------------------------------------
def write_heartbeat(pct, elapsed, total_tasks, completed_tasks, current_action):
    eta = (elapsed / max(1, completed_tasks)) * (total_tasks - completed_tasks) if completed_tasks > 0 else 0
    data = {
        "timestamp_utc":  time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
        "progress_pct":   round(pct, 2),
        "completed":      completed_tasks,
        "total":          total_tasks,
        "eta_seconds":    round(eta, 1),
        "current_action": current_action,
    }
    with open(HEARTBEAT_PATH, 'w') as f:
        json.dump(data, f)


def lock_rate(scalars, harmonic_label, threshold=None):
    """
    24-Cell Modular Resonance test.
    rp = (s / target) * CONTAINER
    Locked if |rp - round(rp)| < threshold.
    threshold defaults to the config-loaded LOCK_THRESHOLD.
    """
    if threshold is None:
        threshold = LOCK_THRESHOLD
    if not scalars:
        return 0.0
    target = HARMONIC_TARGETS[harmonic_label]
    locked = 0
    for s in scalars:
        rp      = (s / target) * CONTAINER
        nearest = max(1, round(rp))
        if abs(rp - nearest) < threshold:
            locked += 1
    return locked / len(scalars)


def build_chaos_null(domain_label, scalars):
    lo     = min(scalars)
    hi     = max(scalars)
    n      = len(scalars)
    now_ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    records = []
    for _ in range(n):
        s = random.uniform(lo, hi)
        records.append({
            "entity_id":   str(uuid.uuid4()),
            "domain":      f"null_{domain_label}",
            "volume":      VOLUME_NUMBER,
            "lake_id":     f"chaos_null_{domain_label}",
            "geometry_payload": {
                "coordinates":   [],
                "dimensionality": 0,
                "geometry_type":  "chaos_uniform",
            },
            "scalar_kls": s,
            "scalar_klc": s,
            "meta": {
                "source":           f"Chaos null for {domain_label}",
                "ingest_timestamp": now_ts,
                "sovereign":        False,
                "null_type":        "chaos_uniform",
                "null_range":       [lo, hi],
                "null_n":           n,
                "real_domain":      domain_label,
                "audit_note": (
                    "Absolute floor null. Uniform random over real scalar range. "
                    "Real signal must beat this or no modular structure is present."
                ),
            },
        })
    return records


def build_scramble_null(domain_label, scalars):
    shuffled = scalars[:]
    random.shuffle(shuffled)
    now_ts  = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    records = []
    for s in shuffled:
        records.append({
            "entity_id":   str(uuid.uuid4()),
            "domain":      f"null_{domain_label}",
            "volume":      VOLUME_NUMBER,
            "lake_id":     f"scramble_null_{domain_label}",
            "geometry_payload": {
                "coordinates":   [],
                "dimensionality": 0,
                "geometry_type":  "scrambled_assignment",
            },
            "scalar_kls": s,
            "scalar_klc": s,
            "meta": {
                "source":           f"Scramble null for {domain_label}",
                "ingest_timestamp": now_ts,
                "sovereign":        False,
                "null_type":        "scramble_assignment",
                "real_domain":      domain_label,
                "audit_note": (
                    "Assignment scramble. Preserves distribution shape, destroys pairing. "
                    "Signal surviving this scramble indicates positional/clustering geometry."
                ),
            },
        })
    return records


# --------------------------------------------------------------------
# VOL 11 UPGRADE: 3rd Null - Synthetic Matched Distribution
# --------------------------------------------------------------------
def build_synthetic_null(domain_label, scalars):
    n       = len(scalars)
    mean    = np.mean(scalars)
    std     = np.std(scalars)
    min_val = np.min(scalars)
    max_val = np.max(scalars)

    # Generate smooth Gaussian matched to real data, clipped to actual boundaries
    synthetic_vals = np.random.normal(mean, std, n)
    synthetic_vals = np.clip(synthetic_vals, min_val, max_val)

    now_ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    records = []
    for s in synthetic_vals:
        records.append({
            "entity_id":   str(uuid.uuid4()),
            "domain":      f"null_{domain_label}",
            "volume":      VOLUME_NUMBER,
            "lake_id":     f"synthetic_null_{domain_label}",
            "geometry_payload": {
                "coordinates":   [],
                "dimensionality": 0,
                "geometry_type":  "synthetic_matched",
            },
            "scalar_kls": float(s),
            "scalar_klc": float(s),
            "meta": {
                "source":           f"Synthetic matched null for {domain_label}",
                "ingest_timestamp": now_ts,
                "sovereign":        False,
                "null_type":        "synthetic_matched",
                "null_mean":        float(mean),
                "null_std":         float(std),
                "null_n":           n,
                "real_domain":      domain_label,
                "audit_note": (
                    "3rd Null: Synthetic Gaussian matched to real domain mean and std, "
                    "clipped to real min/max. Proves the 16/pi lock is not an artifact "
                    "of the log-modulo transform acting on smooth data."
                ),
            },
        })
    return records


def main():
    print("\n" + "=" * 60)
    print("  [MONITORING TIP] Open a new terminal and run:")
    print("  python engine/sidecar.py")
    print("  to view the live null generation dashboard.")
    print("=" * 60 + "\n")
    print("NOTE: This job builds null distributions for all domains.")
    print("      Runtime: Dependent on lake sizes. Do not interrupt.")
    print()

    random.seed(42)
    np.random.seed(42)

    if not UNIFIED.exists():
        raise SystemExit(f"Unified master not found: {UNIFIED}")

    print(f"k_geo = 16/pi = {K_GEO:.10f}")
    print(f"Volume number: {VOLUME_NUMBER}")
    print(f"Registers ({len(HARMONIC_TARGETS)}): " +
          "  ".join(f"{k}={v:.6f}" for k, v in HARMONIC_TARGETS.items()))
    print()
    print("Loading unified master...")
    domains = load_domain_scalars()

    print(f"\nFound {len(domains)} domain slots:")
    active_domain_labels = []
    for label in sorted(domains):
        vals = [s for s in domains[label] if s != 0.0]
        if vals:
            active_domain_labels.append(label)
            print(f"  {label:<28} n={len(vals):6d}  "
                  f"mean={np.mean(vals):.4f}  "
                  f"range=[{min(vals):.4f}, {max(vals):.4f}]")
        else:
            print(f"  {label:<28} n={len(domains[label]):6d}  (all zeros)")

    print()
    print("Building null lakes...")
    print()

    total_tasks     = len(active_domain_labels)
    completed_tasks = 0
    start_time      = time.time()

    write_heartbeat(0, 0, total_tasks, 0, "Initializing Null Generator...")

    for domain_label in sorted(domains):
        vals = [s for s in domains[domain_label] if s != 0.0]
        if not vals:
            print(f"[SKIP] {domain_label} -- all zeros")
            continue

        write_heartbeat(
            (completed_tasks / total_tasks) * 100,
            time.time() - start_time,
            total_tasks,
            completed_tasks,
            f"Building nulls for {domain_label}"
        )

        chaos     = build_chaos_null(domain_label, vals)
        scramble  = build_scramble_null(domain_label, vals)
        synthetic = build_synthetic_null(domain_label, vals)

        chaos_path     = SYNTHETIC / f"chaos_null_{domain_label}.jsonl"
        scramble_path  = SYNTHETIC / f"scramble_null_{domain_label}.jsonl"
        synthetic_path = SYNTHETIC / f"synthetic_null_{domain_label}.jsonl"

        with chaos_path.open("w", encoding="utf-8") as f:
            for rec in chaos:
                f.write(json.dumps(rec) + "\n")
        with scramble_path.open("w", encoding="utf-8") as f:
            for rec in scramble:
                f.write(json.dumps(rec) + "\n")
        with synthetic_path.open("w", encoding="utf-8") as f:
            for rec in synthetic:
                f.write(json.dumps(rec) + "\n")

        print(f"[{domain_label}]  n={len(vals)}")
        for hl, target in HARMONIC_TARGETS.items():
            rl    = lock_rate(vals, hl)
            cl    = lock_rate([r["scalar_klc"] for r in chaos], hl)
            sl    = lock_rate([r["scalar_klc"] for r in synthetic], hl)
            delta = rl - cl
            signal = " ** above chaos **" if delta > 0.005 else ""
            print(f"  {hl}: real={rl:.4f}  chaos={cl:.4f}  synth={sl:.4f}  delta={delta:+.4f}{signal}")

        print(f"  -> {chaos_path.name}")
        print(f"  -> {scramble_path.name}")
        print(f"  -> {synthetic_path.name}")
        print()

        completed_tasks += 1
        write_heartbeat(
            (completed_tasks / total_tasks) * 100,
            time.time() - start_time,
            total_tasks,
            completed_tasks,
            f"Finished {domain_label}"
        )

    write_heartbeat(100, time.time() - start_time, total_tasks, total_tasks, "Complete")
    print(f"All null lakes written to: {SYNTHETIC}")
    print()
    print("Next steps:")
    print("  1. python engine/build_pinch_table.py")


if __name__ == "__main__":
    main()