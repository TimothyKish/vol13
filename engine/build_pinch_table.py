# ==============================================================================
# SCRIPT: build_pinch_table.py
# VOLUME: 11 - Full Harmonic Sweep + Ceiling Bracket + Rosetta Sub-Lattice
# TARGET: Compute cross-domain harmonic residuals and build the pinch table
#         across the complete N/pi harmonic family (N = 4 to 26).
#
# UPGRADES: Parallel Processing, Checkpointing, Dynamic Routing,
#           Memory-Safe IPC (Numpy 32-bit), Sidecar Telemetry, ASCII-Safe.
#           Live Telemetry injected into Master Lake, Chaos, & Z-Score loops.
#           Harmonic register family loaded from configs/harmonic_targets.json.
#           z_scores_master.json exported after per-domain z-score computation.
#
# PERF (Vol 11): Vectorized lock_rate and chaos_z_score using NumPy batch ops.
#           Replaces Python for-loops with array operations. Z-score stage
#           reduced from ~8 hours to ~5-15 minutes on Vol 10 lake set.
#           Batch sizing auto-scales to available RAM for B5 and beyond.
#
# FIX (Vol 11): Worker processes suppress config-load print to prevent
#           repeated [harmonic_targets.json] spam during parallel stage.
#
# FIX (Vol 11): Stage 2/2 heartbeat reset at z-score start so sidecar
#           does not show 100% Complete while z-scores are still running.
#
# FIX (Vol 11): Informative per-domain z-score progress: domain name,
#           record count, elapsed time per domain, live ETA.
#
# FIX (Vol 11): UTF-8 encoding enforced on all file I/O and on
#           sys.stdout/sys.stderr. Prevents UnicodeDecodeError when
#           run_pipeline.py captures subprocess stdout on Windows
#           (cp1252 default) and decodes as utf-8.
#
# VOL 11 UPGRADE: 3rd Null Integration (Synthetic Matched Distribution).
#           Ingests synthetic_null lakes, computes synthetic_lock and synthetic_delta
#           in cross-domain matrix. Upgraded the NumPy batch loop to compute both
#           Chaos (Uniform) and Synthetic (Gaussian Matched) Z-Scores simultaneously.
#           z_scores_master.json now structured to hold both Z-Score vectors.
#           FIX: Replaced __name__ check with MainProcess check to support run_pipeline.py
# ==============================================================================
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC.
# FOUNDER: Timothy John Kish
#
# LICENSE & TERMS OF USE:
# This software, including the 16/pi kinematic framework and scalarization
# engines, is open and available for scientific testing, empirical validation,
# and academic peer review.
# ==============================================================================
import json
import math
import multiprocessing
import os
import sys
import time
from pathlib import Path
import numpy as np
import concurrent.futures

# --------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------
PI    = math.pi
K_GEO = 16.0 / PI    

N_CHAOS_TRIALS = 100  

# ==============================================================================
# VOL 12 — COMMON-SUPPORT CORRECTION  (Mondy ruling, 2026-08-23, Erratum 4)
#
# Form D: the chaos null is uniform over the empirical range and does not
# reproduce the data's below-floor mass. `nearest = max(1, round(r_p))` makes
# every record with r_p < 0.5 mechanically non-lockable, and the two arms of the
# comparison put different amounts of mass there. Measured on
# s2_stellar_kinematics: 27.5% of the data below the 16/pi floor against 2.5% of
# the uniform null, which alone reproduced the entire 23-register profile at
# 1.23% mean error with NO harmonic structure assumed.
#
# Remedy (ruled): exclude r_p < 0.5 from BOTH arms at every register and report
# the excluded fraction. The cut sits at the anti-node, maximally distant from
# any lock window, so it neither adds nor removes locked records preferentially.
#
# Validated two-sided before adoption (scripts/validate_common_support.py):
#   right-skewed structureless, 27.5% below floor, n=1.8M
#       median z  -132.5 (uncorrected)  ->  -4.92 (corrected)
#   planted lock at 19/pi in the same data still recovered at z = +182
# Residual: |z| up to ~10 remains on structureless data; the shape mismatch
# above the floor is not removed by this correction. Hence the baseline below.
# ==============================================================================
SUPPORT_FLOOR = 0.5

# Offset-sweep baseline. The residual is NOT monotonic and can carry local
# structure, so a scalar per-domain baseline is insufficient; it is measured per
# register. The uniform null's lock rate is invariant to grid phase, so the null
# is computed once and only the real rate is swept -- the sweep is nearly free.
# Discriminant becomes PEAK MINUS MEDIAN, not peak versus zero.
OFFSET_SWEEP_N = 24

# Vol 11.1 labelled "STRONG signal" at z > 3.0 while the pre-registered
# threshold is z >= 5.0. Two domains in run_20260823_011734 were printed STRONG
# without meeting it: null_cosmology_null (+4.1, a designated NULL) and
# biology_chirality (+3.3). Threshold restored and printed at run start.
STRONG_Z   = 5.0
MODERATE_Z = 3.0

CHAOS_BATCH_BYTES = 512 * 1024 * 1024

# --------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------
ROOT                 = Path(__file__).resolve().parents[1]
UNIFIED_PATH         = ROOT / "lakes" / "unified" / "unified_master.jsonl"
PINCH_TABLE_PATH     = ROOT / "lakes" / "unified" / "pinch_table_cross_domain.json"
STATE_FILE_PATH      = ROOT / "lakes" / "unified" / "pinch_state.json"
HEARTBEAT_PATH       = ROOT / "lakes" / "unified" / "lattice_heartbeat.json"
Z_SCORES_PATH        = ROOT / "lakes" / "unified" / "z_scores_master.json"
SYNTHETIC_DIR        = ROOT / "lakes" / "synthetic"
VOLUMES_CFG_PATH     = ROOT / "configs" / "volumes.json"
HARMONIC_TARGETS_CFG = ROOT / "configs" / "harmonic_targets.json"

# --------------------------------------------------------------------
# Harmonic Configuration Loader
# --------------------------------------------------------------------
def load_harmonic_config():
    is_main = multiprocessing.current_process().name == 'MainProcess'

    if HARMONIC_TARGETS_CFG.exists():
        with open(HARMONIC_TARGETS_CFG, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        registers      = cfg.get("registers", list(range(4, 27)))
        container      = int(cfg.get("container", 24))
        lock_threshold = float(cfg.get("lock_threshold", 0.05))
        if is_main:
            print(f"[harmonic_targets.json] Loaded {len(registers)} registers "
                  f"(N={registers[0]} to N={registers[-1]}), "
                  f"container={container}, threshold={lock_threshold}")
    else:
        registers      = list(range(4, 27))
        container      = 24
        lock_threshold = 0.05
        if is_main:
            print(f"[WARN] harmonic_targets.json not found at {HARMONIC_TARGETS_CFG}")
            print(f"       Using defaults: N=4..26, container=24, threshold=0.05")

    harmonic_targets = {f"{n}/pi": float(n) / PI for n in registers}
    return harmonic_targets, container, lock_threshold

HARMONIC_TARGETS, CONTAINER, LOCK_THRESHOLD = load_harmonic_config()

# --------------------------------------------------------------------
# Heartbeat Telemetry System
# --------------------------------------------------------------------
def write_heartbeat(pct, elapsed, total_tasks, completed_tasks, current_action):
    eta = (elapsed / max(1, completed_tasks)) * (total_tasks - completed_tasks) \
          if completed_tasks > 0 else 0
    data = {
        "timestamp_utc":  time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
        "progress_pct":   min(100.0, max(0.0, round(pct, 2))),
        "completed":      completed_tasks,
        "total":          total_tasks,
        "eta_seconds":    round(eta, 1),
        "current_action": current_action,
    }
    try:
        with open(HEARTBEAT_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f)
    except Exception:
        pass

# --------------------------------------------------------------------
# Dynamic Configuration Loader
# --------------------------------------------------------------------
CONFIG_PINCH_SLOTS = {}

def load_dynamic_configs():
    global CONFIG_PINCH_SLOTS
    if VOLUMES_CFG_PATH.exists():
        with open(VOLUMES_CFG_PATH, "r", encoding="utf-8") as f:
            vols = json.load(f).get("volumes", {})
        for lake_id, meta in vols.items():
            if "__pinch_slot__" in meta:
                CONFIG_PINCH_SLOTS[lake_id.lower()] = meta["__pinch_slot__"]

# --------------------------------------------------------------------
# Worker Globals (Memory Safe IPC)
# --------------------------------------------------------------------
_worker_active    = {}
_worker_chaos     = {}
_worker_synthetic = {}

def init_worker(active_data, chaos_data, synthetic_data):
    global _worker_active, _worker_chaos, _worker_synthetic
    _worker_active    = active_data
    _worker_chaos     = chaos_data
    _worker_synthetic = synthetic_data

# --------------------------------------------------------------------
# Domain scalar loader
# --------------------------------------------------------------------
def load_domain_scalars(unified_path):
    load_dynamic_configs()
    raw_domains      = {}
    lines_processed  = 0
    total_bytes      = unified_path.stat().st_size if unified_path.exists() else 0
    bytes_processed  = 0
    start_time       = time.time()
    last_save        = time.time()

    print("  Loading records into memory. Please wait...")
    write_heartbeat(0, 0, 100, 0, "Loading Master Lake into RAM...")

    with unified_path.open("r", encoding="utf-8") as f:
        for line in f:
            bytes_processed += len(line.encode('utf-8'))
            line = line.strip()
            if not line: continue

            lines_processed += 1
            entry   = json.loads(line)
            domain  = (entry.get("domain") or "").lower()
            lake_id = (entry.get("lake_id") or entry.get("_volume_name") or entry.get("volume_name") or "").lower()
            scalar  = entry.get("scalar_klc")
            if scalar is None: continue
            try:
                s = float(scalar)
            except (TypeError, ValueError):
                continue

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
            raw_domains.setdefault(label, []).append(s)

            if time.time() - last_save > 2.0:
                pct = (bytes_processed / total_bytes) * 100 if total_bytes > 0 else 0
                write_heartbeat(pct, time.time() - start_time, 100, int(pct), f"Loading to RAM ({lines_processed:,} recs)")
                print(f"    -> Parsed {lines_processed:,} records...", end='\r', flush=True)
                last_save = time.time()

    print(f"\n  Finished loading {lines_processed:,} total records.")
    write_heartbeat(100, time.time() - start_time, 100, 100, "Compressing Numpy Arrays...")
    print("  Compressing to 32-bit Numpy Arrays for Memory-Safe IPC...")

    compressed_domains = {}
    for dom, vals in raw_domains.items():
        if vals:
            nonz = [v for v in vals if v != 0.0]
            if nonz:
                compressed_domains[dom] = np.array(nonz, dtype=np.float32)

    del raw_domains
    return compressed_domains

# --------------------------------------------------------------------
# Chaos & Synthetic Null Loaders
# --------------------------------------------------------------------
def load_all_chaos_nulls(domains):
    chaos_dict = {}
    print("\n  Loading Chaos Nulls into memory...")
    for dom in domains:
        path = SYNTHETIC_DIR / f"chaos_null_{dom}.jsonl"
        if not path.exists():
            chaos_dict[dom] = None
            continue
        scalars = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try: scalars.append(float(json.loads(line).get("scalar_klc", 0.0)))
                    except: pass
        chaos_dict[dom] = np.array(scalars, dtype=np.float32) if scalars else None
    print("  Finished loading Chaos Nulls.")
    return chaos_dict

def load_all_synthetic_nulls(domains):
    synth_dict = {}
    print("  Loading Synthetic Nulls into memory...")
    for dom in domains:
        path = SYNTHETIC_DIR / f"synthetic_null_{dom}.jsonl"
        if not path.exists():
            synth_dict[dom] = None
            continue
        scalars = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try: scalars.append(float(json.loads(line).get("scalar_klc", 0.0)))
                    except: pass
        synth_dict[dom] = np.array(scalars, dtype=np.float32) if scalars else None
    print("  Finished loading Synthetic Nulls.")
    return synth_dict

# --------------------------------------------------------------------
# VECTORIZED Metric Functions
# --------------------------------------------------------------------
FIXED_SUPPORT_CHECK = True


def compute_dist_lock_internal(scalars_a, scalars_b, target):
    def sorted_residuals(sc):
        rp      = (sc / target) * CONTAINER
        nearest = np.maximum(1, np.round(rp))
        return np.sort(np.abs(rp - nearest))

    ra = sorted_residuals(scalars_a)
    rb = sorted_residuals(scalars_b)
    if len(ra) == 0 or len(rb) == 0:
        return 0.0, float("inf")

    n  = max(len(ra), len(rb))
    xa = np.linspace(0.0, 1.0, len(ra))
    xb = np.linspace(0.0, 1.0, len(rb))
    xc = np.linspace(0.0, 1.0, n)
    ia = np.interp(xc, xa, ra)
    ib = np.interp(xc, xb, rb)

    rms  = float(np.sqrt(np.mean((ia - ib) ** 2)))
    lock = 1.0 / (1.0 + rms) if math.isfinite(rms) else 0.0
    return lock, rms

def compute_dual_z_scores(scalars, harmonic_label, n_trials=N_CHAOS_TRIALS,
                          support_mask=None):
    if len(scalars) == 0:
        return 0.0, 0.0, 0.0, 0.0, 0.0

    lo, hi    = float(np.min(scalars)), float(np.max(scalars))
    mean, std = float(np.mean(scalars)), float(np.std(scalars))
    n         = len(scalars)
    target    = HARMONIC_TARGETS[harmonic_label]

    rp_real = (scalars / target) * CONTAINER

    # --- VOL 12: common-support restriction ---
    keep_real = rp_real >= SUPPORT_FLOOR if support_mask is None else support_mask
    n_keep    = int(np.count_nonzero(keep_real))
    kept_frac = (n_keep / n) if n else 0.0
    if n_keep == 0:
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

    base    = rp_real[keep_real].astype(np.float64)
    real_lr = float(np.count_nonzero(np.abs(base - np.round(base)) < LOCK_THRESHOLD)) / n_keep

    max_per_batch = max(1, CHAOS_BATCH_BYTES // (n * 4 * 2))
    batch_size    = min(n_trials, max_per_batch)

    chaos_locked = []
    synth_locked = []
    trials_done  = 0

    while trials_done < n_trials:
        batch = min(batch_size, n_trials - trials_done)
        
        c_samples = np.random.uniform(lo, hi, size=(batch, n)).astype(np.float32)
        c_rp      = (c_samples / target) * CONTAINER
        c_keep    = c_rp >= SUPPORT_FLOOR
        c_hit     = (np.abs(c_rp - np.round(c_rp)) < LOCK_THRESHOLD) & c_keep
        chaos_locked.append(c_hit.sum(axis=1) / np.maximum(1, c_keep.sum(axis=1)))

        s_samples = np.random.normal(mean, std, size=(batch, n)).astype(np.float32)
        s_samples = np.clip(s_samples, lo, hi)
        s_rp      = (s_samples / target) * CONTAINER
        s_keep    = s_rp >= SUPPORT_FLOOR
        s_hit     = (np.abs(s_rp - np.round(s_rp)) < LOCK_THRESHOLD) & s_keep
        synth_locked.append(s_hit.sum(axis=1) / np.maximum(1, s_keep.sum(axis=1)))

        trials_done += batch

    c_arr  = np.concatenate(chaos_locked).astype(np.float64)
    c_mean = float(np.mean(c_arr))
    c_std  = float(np.std(c_arr))
    cz     = (real_lr - c_mean) / c_std if c_std > 0 else 0.0

    s_arr  = np.concatenate(synth_locked).astype(np.float64)
    s_mean = float(np.mean(s_arr))
    s_std  = float(np.std(s_arr))
    sz     = (real_lr - s_mean) / s_std if s_std > 0 else 0.0

    # --- VOL 12: offset-sweep baseline ---
    # Support is fixed by the physical floor and held constant across offsets;
    # only the grid phase moves. The uniform null is phase-invariant, so c_mean
    # and c_std are reused rather than recomputed.
    if c_std > 0:
        sweep = np.empty(OFFSET_SWEEP_N)
        for i in range(OFFSET_SWEEP_N):
            sh = base + (i / OFFSET_SWEEP_N)
            sweep[i] = np.count_nonzero(np.abs(sh - np.round(sh)) < LOCK_THRESHOLD) / n_keep
        baseline_cz = float(np.median((sweep - c_mean) / c_std))
    else:
        baseline_cz = 0.0
    signal_cz = cz - baseline_cz

    return real_lr, c_mean, cz, s_mean, sz, kept_frac, baseline_cz, signal_cz

# --------------------------------------------------------------------
# Worker Task Execution
# --------------------------------------------------------------------
def worker_compute_cell(dom_a, dom_b, harmonic_label):
    global _worker_active, _worker_chaos, _worker_synthetic
    target = HARMONIC_TARGETS[harmonic_label]

    dist_lock, dist_rms = compute_dist_lock_internal(
        _worker_active[dom_a], _worker_active[dom_b], target
    )

    chaos_b     = _worker_chaos.get(dom_b)
    chaos_lock  = None
    chaos_delta = None
    if chaos_b is not None:
        cl, _ = compute_dist_lock_internal(_worker_active[dom_a], chaos_b, target)
        chaos_lock  = round(cl, 4)
        chaos_delta = round(dist_lock - cl, 4)

    synth_b     = _worker_synthetic.get(dom_b)
    synth_lock  = None
    synth_delta = None
    if synth_b is not None:
        sl, _ = compute_dist_lock_internal(_worker_active[dom_a], synth_b, target)
        synth_lock  = round(sl, 4)
        synth_delta = round(dist_lock - sl, 4)

    return (dom_a, dom_b, harmonic_label,
            round(dist_lock, 4), round(dist_rms, 4),
            chaos_lock, chaos_delta, synth_lock, synth_delta)

# --------------------------------------------------------------------
# Main Execution Loop
# --------------------------------------------------------------------
def build_pinch_table_parallel(domain_scalars):
    active     = {d: v for d, v in domain_scalars.items() if len(v) > 0}
    domains    = sorted(active.keys())
    
    chaos_dict = load_all_chaos_nulls(domains)
    synth_dict = load_all_synthetic_nulls(domains)

    state = {}
    if STATE_FILE_PATH.exists():
        print(f"Resuming from checkpoint: {STATE_FILE_PATH}")
        try:
            with open(STATE_FILE_PATH, 'r', encoding='utf-8') as f:
                state = json.load(f)
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            print(f"[WARN] State file unreadable ({e}) -- starting fresh")
            state = {}

    tasks = []
    for dom_a in domains:
        if dom_a not in state: state[dom_a] = {}
        for dom_b in domains:
            if dom_a == dom_b: continue
            if dom_b not in state[dom_a]: state[dom_a][dom_b] = {}
            for h in HARMONIC_TARGETS:
                if h not in state[dom_a][dom_b]:
                    tasks.append((dom_a, dom_b, h))

    total_tasks = len(tasks) + sum(len(h) for d in state.values() for h in d.values())
    completed = total_tasks - len(tasks)

    print(f"Total Combinations: {total_tasks:,} | Remaining: {len(tasks):,}")

    if not tasks: return state, active

    cores      = max(1, os.cpu_count() - 1)
    start_time = time.time()
    last_save  = time.time()

    write_heartbeat(0, 0, total_tasks, completed, f"[STAGE 1/2] Parallel pinch starting ({cores} workers)...")

    with concurrent.futures.ProcessPoolExecutor(
        max_workers=cores,
        initializer=init_worker,
        initargs=(active, chaos_dict, synth_dict)
    ) as executor:
        future_to_task = {
            executor.submit(worker_compute_cell, a, b, h): (a, b, h)
            for a, b, h in tasks
        }

        for future in concurrent.futures.as_completed(future_to_task):
            a, b, h = future_to_task[future]
            try:
                a_res, b_res, h_res, d_lock, d_rms, c_lock, c_delta, s_lock, s_delta = future.result()
                state[a_res][b_res][h_res] = {
                    "dist_lock":       d_lock,
                    "dist_rms":        d_rms,
                    "chaos_lock":      c_lock,
                    "chaos_delta":     c_delta,
                    "synthetic_lock":  s_lock,
                    "synthetic_delta": s_delta,
                }
                completed += 1

                if time.time() - last_save > 2.0:
                    with open(STATE_FILE_PATH, 'w', encoding='utf-8') as f:
                        json.dump(state, f)
                    write_heartbeat((completed / total_tasks) * 100, time.time() - start_time, total_tasks, completed, f"[STAGE 1/2] {a_res} vs {b_res}")
                    last_save = time.time()

            except Exception as exc:
                print(f"Task {a}x{b} generated an exception: {exc}")

    with open(STATE_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(state, f)
    write_heartbeat(100, time.time() - start_time, total_tasks, total_tasks, "[STAGE 1/2] Parallel pinch complete")
    return state, active

def _fmt_eta(seconds):
    if seconds < 0 or not math.isfinite(seconds): return "estimating..."
    h, m = divmod(int(seconds), 3600)
    m, s = divmod(m, 60)
    if h > 0: return f"{h}h {m:02d}m"
    elif m > 0: return f"{m}m {s:02d}s"
    return f"{s}s"

def display_table(pinch_table, active_domains):
    domains = sorted(active_domains.keys())
    col_w   = 36

    print()
    print("=" * 115)
    print("CROSS-DOMAIN PINCH TABLE".center(115))
    family_str = "  ".join(f"{k}={v:.4f}" for k, v in HARMONIC_TARGETS.items())
    print(f"Moduli: {family_str}".center(130))
    print("dist_lock (1=perfect) | Winner + best chaos_delta per pairing".center(130))
    print("=" * 115)

    header = f"{'Domain':<24}"
    for d in domains: header += f"{d[:col_w]:^{col_w}}"
    print(header)
    print("-" * (24 + col_w * len(domains)))

    for dom_a in domains:
        row = f"{dom_a:<24}"
        for dom_b in domains:
            if dom_a == dom_b:
                row += f"{'-':^{col_w}}"
                continue
            cell = pinch_table.get(dom_a, {}).get(dom_b, {})
            if not cell:
                row += f"{'-':^{col_w}}"
            else:
                scores = tuple(cell[h]["dist_lock"] for h in HARMONIC_TARGETS)
                deltas = [cell[h]["chaos_delta"] for h in HARMONIC_TARGETS]
                s_str  = f"({scores[0]:.3f},{scores[1]:.3f},{scores[2]:.3f})"
                valid  = [d for d in deltas if d is not None]
                if valid: s_str += f" d{max(valid):+.3f}"
                row += f"{s_str:^{col_w}}"
        print(row)

    print()
    print("--- WINNER PER PAIRING ---")
    reported = set()
    for dom_a in domains:
        for dom_b in domains:
            pair = tuple(sorted([dom_a, dom_b]))
            if pair in reported or dom_a == dom_b: continue
            reported.add(pair)
            cell = pinch_table.get(dom_a, {}).get(dom_b, {})
            if not cell: continue
            scores = {h: cell[h]["dist_lock"]  for h in HARMONIC_TARGETS}
            deltas = {h: cell[h]["chaos_delta"] for h in HARMONIC_TARGETS}
            winner = max(scores, key=scores.get)
            d_str  = f"  chaos_delta={deltas[winner]:+.4f}" if deltas[winner] is not None else ""
            sig    = "  *** SIGNAL ***" if deltas[winner] and deltas[winner] > 0.01 else ""
            print(f"  {dom_a} x {dom_b}: {winner}  score={scores[winner]:.4f}{d_str}{sig}")

    print()
    print("--- PER-DOMAIN DUAL Z-SCORES (Chaos | Synthetic) ---")
    hl_list  = list(HARMONIC_TARGETS.keys())
    hdr_cols = " ".join(f"{h:>10}" for h in hl_list)
    print(f"  {'Domain':<26} {hdr_cols}   Best   Interpretation")
    print(f"  {'-'*26} {' '.join(['-'*10]*len(hl_list))}  ------  {'-'*20}")

    z_scores_master = {}
    total_z_tasks   = len(active_domains)
    z_completed     = 0
    start_z_time    = time.time()
    domain_times    = []

    write_heartbeat(0, 0, total_z_tasks, 0, f"[STAGE 2/2] Dual Z-Scores starting ({total_z_tasks} domains)...")

    domain_order = sorted(active_domains.keys(), key=lambda d: len(active_domains[d]))

    for dom in domain_order:
        scalars = active_domains[dom]
        n       = len(scalars)

        eta_str = _fmt_eta((sum(domain_times) / len(domain_times)) * (total_z_tasks - z_completed)) if domain_times else "estimating..."

        print(f"  {z_completed+1:>4}  {dom:<30} {n:>10,}  computing...  ETA: {eta_str}", end='', flush=True)

        t0 = time.time()
        zs_chaos, zs_synth = [], []
        zs_kept, zs_base, zs_signal = [], [], []

        for hl in hl_list:
            (_, _, cz, _, sz, kept, base_z,
             sig_z) = compute_dual_z_scores(scalars, hl, n_trials=N_CHAOS_TRIALS)
            zs_chaos.append(cz); zs_synth.append(sz)
            zs_kept.append(kept); zs_base.append(base_z); zs_signal.append(sig_z)

        # --- VOL 12: fixed-support cross-check (Mondy §D condition) ---
        # The correction discards a register-dependent fraction, so the profile
        # above is computed on different subsets at different registers. Re-score
        # every register against the support surviving at the HIGHEST register,
        # so all registers use one common subset. If the profile holds under
        # both, the register assignment is robust to the cut.
        zs_fixed = []
        if FIXED_SUPPORT_CHECK and len(scalars):
            t_hi  = HARMONIC_TARGETS[hl_list[-1]]
            mask  = ((scalars / t_hi) * CONTAINER) >= SUPPORT_FLOOR
            for hl in hl_list:
                zs_fixed.append(compute_dual_z_scores(
                    scalars, hl, n_trials=N_CHAOS_TRIALS, support_mask=mask)[2])

        elapsed_dom = time.time() - t0
        domain_times.append(elapsed_dom)

        z_scores_master[dom] = {
            "chaos_z": zs_chaos,
            "synthetic_z": zs_synth,
            "kept_fraction": zs_kept,
            "baseline_z": zs_base,
            "signal_z": zs_signal,
            "fixed_support_z": zs_fixed,
            "statistic": "common_support_v12",
            "support_floor": SUPPORT_FLOOR,
        }

        # Discriminant is PEAK MINUS BASELINE, not peak versus zero.
        best_z = max(zs_signal) if zs_signal else 0.0
        best_h = hl_list[zs_signal.index(best_z)] if zs_signal else hl_list[0]
        interp = ("STRONG signal" if best_z >= STRONG_Z
                  else "moderate" if best_z >= MODERATE_Z else "noise floor")
        if zs_kept and min(zs_kept) < 0.5:
            interp += f"  [OUT-OF-RANGE: {min(zs_kept)*100:.0f}% kept]"

        print(f"\r  {z_completed+1:>4}  {dom:<22} {n:>8,} | ", end="")
        z_cols = " ".join(f"{s:>5.1f}" for s in zs_signal)
        kmin, kmax = (min(zs_kept), max(zs_kept)) if zs_kept else (0.0, 0.0)
        print(f"{z_cols}  {best_h:<6} kept {kmin*100:>3.0f}-{kmax*100:<3.0f}%  {interp}")

        z_completed += 1
        avg_t  = sum(domain_times) / len(domain_times)
        z_pct  = (z_completed / max(1, total_z_tasks)) * 100
        remain = _fmt_eta(avg_t * (total_z_tasks - z_completed))
        write_heartbeat(z_pct, time.time() - start_z_time, total_z_tasks, z_completed, f"[STAGE 2/2] {dom} ({z_completed}/{total_z_tasks})  ETA: {remain}")

    total_z_elapsed = time.time() - start_z_time
    write_heartbeat(100, total_z_elapsed, total_z_tasks, total_z_tasks, "[STAGE 2/2] Z-Scores COMPLETE")

    print()
    print(f"  Z-score stage complete: {_fmt_eta(total_z_elapsed)} total  | avg {total_z_elapsed/total_z_tasks:.2f}s per domain  | {total_z_elapsed:.1f}s wall time")

    with open(Z_SCORES_PATH, "w", encoding="utf-8") as f:
        json.dump(z_scores_master, f, indent=2)

    print()
    print(f"  [z_scores_master.json written -> {Z_SCORES_PATH}]")

# --------------------------------------------------------------------
# Entry Point
# --------------------------------------------------------------------
# FIX: The current_process().name check protects Windows parallel workers
# from fork bombing, while ensuring run_pipeline.py can execute the logic
# regardless of whether it uses subprocess, runpy, or exec().
if multiprocessing.current_process().name == 'MainProcess':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

    if not UNIFIED_PATH.exists():
        raise SystemExit(f"Unified master not found: {UNIFIED_PATH}")

    print("\n" + "=" * 60)
    print("  [MONITORING TIP] Open a new terminal and run:")
    print("  python engine/sidecar.py")
    print("  to view the live parallel crunching dashboard.")
    print("=" * 60 + "\n")

    print(f"Loading unified master: {UNIFIED_PATH}")
    domain_scalars = load_domain_scalars(UNIFIED_PATH)

    print("\nBuilding pinch table in PARALLEL mode...")
    pinch_table, active = build_pinch_table_parallel(domain_scalars)

    with PINCH_TABLE_PATH.open("w", encoding="utf-8") as f:
        json.dump(pinch_table, f, indent=2)
    print(f"\nSaved: {PINCH_TABLE_PATH}")

    display_table(pinch_table, active)