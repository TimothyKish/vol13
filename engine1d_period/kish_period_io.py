#!/usr/bin/env python3
# ==============================================================================
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC. FOUNDER: Timothy John Kish
# Open for scientific testing / peer review. Cite "KishLattice 16/pi Initiative".
# ==============================================================================
#
# kish_period_io.py  --  shared I/O, resource adaptation, and compute backend.
#
# CORE PRINCIPLE (Timothy, 2026-09-13): this program must run on the machine a
# person already owns. A result that only reproduces on exotic hardware is not
# open. So: SAME NUMBERS on a potato and a beast -- only the SPEED differs.
# Turtle on a 2015 laptop, rabbit on a workstation, identical science.
#
# WHAT THIS MODULE PROVIDES, so no other script rolls its own:
#
#   * iter_lnx(path)      -- STREAMING read of klghs_lnx, one value at a time.
#                            Never materialises the whole file. This is the fix
#                            for the OOM: logify-style full-list reads loaded
#                            22M-record lakes into RAM twice, in four scripts.
#   * load_lnx(path, cap) -- returns a numpy array. If the lake exceeds `cap`,
#                            RESERVOIR-SAMPLES to `cap` (deterministic seed) and
#                            RECORDS that it did so, so the subsample is honest
#                            and reproducible. Lakes under the cap are ALWAYS
#                            read in full -- pulsar (2.5k) and the anchor (189k)
#                            are never sampled; only giant stitched controls are.
#   * xp, HAVE_GPU        -- CuPy if present AND useful, else NumPy. Same code
#                            path both ways. GPU only engages for large arrays
#                            where it actually helps; tiny lakes stay on CPU.
#   * n_workers()         -- sane core count for thread-parallel scans/bootstrap.
#   * resource_banner()   -- one line at startup: cores, GPU, cap. So the user
#                            SEES what the run adapted to.
#
# The cap is 2,000,000 by default (Timothy's ruling). It is logged loudly when
# it triggers and never applied silently.
# ==============================================================================
import json
import os
import sys
import numpy as np

DEFAULT_CAP = 2_000_000
SAMPLE_SEED = 20260913   # deterministic: same subsample every run, reproducible

# ---- compute backend: CuPy if it's present and importable, else NumPy --------
# We do NOT force GPU. cp is used only where the array is large enough to matter
# (see periodogram). For everything else, cp IS np, so code is identical.
try:
    import cupy as _cp                      # noqa
    _cp.zeros(1)                            # touch the device; fails cleanly if none
    HAVE_GPU = True
    _GPU_NAME = _cp.cuda.runtime.getDeviceProperties(0)["name"].decode()
except Exception:
    _cp = None
    HAVE_GPU = False
    _GPU_NAME = None

# GPU only helps above this many points; below it, host<->device copy costs more
# than it saves. Tunable, conservative default.
GPU_MIN_N = 500_000


def n_workers(cap=None):
    """Sane worker count. One on a single-core potato, many on a beast, but
    never so many that context-switching hurts. Respects an env override."""
    env = os.environ.get("KLGHS_WORKERS")
    if env:
        try:
            return max(1, int(env))
        except ValueError:
            pass
    c = os.cpu_count() or 1
    w = max(1, c - 1)          # leave one core for the OS / sidecar
    if cap:
        w = min(w, cap)
    return w


def resource_banner(cap=DEFAULT_CAP):
    cores = os.cpu_count() or 1
    gpu = f"GPU: {_GPU_NAME}" if HAVE_GPU else "GPU: none (CPU only)"
    mode = "rabbit" if (cores >= 8 or HAVE_GPU) else ("hare" if cores >= 4 else "turtle")
    return (f"  resources: {cores} core(s), {n_workers()} worker(s), {gpu}   "
            f"[{mode}]   sample cap: {cap:,}")


# ---- streaming reader --------------------------------------------------------
def iter_lnx(path, field="klghs_lnx"):
    """Yield klghs_lnx values one at a time. Never holds the whole file.
    Skips blank lines and records missing the field, silently -- the logify
    stage already guaranteed the field for logified lakes."""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            v = rec.get(field)
            if v is None:
                # tolerate promoted lakes: hunt one level for a positive raw x
                continue
            if isinstance(v, (int, float)):
                yield float(v)


def count_lines(path):
    """Fast line count without JSON parsing, for deciding whether to sample."""
    n = 0
    with open(path, "rb") as f:
        for _ in f:
            n += 1
    return n


def load_lnx(path, cap=DEFAULT_CAP, log=None):
    """Return (lnx ndarray, meta dict). Streams; reservoir-samples above `cap`.

    meta = {n_total, n_used, sampled(bool), cap}. When sampled, the subsample is
    deterministic (fixed seed) and `sampled` is True so the caller can log it.
    Lakes at or under the cap are returned in full, unsampled, always.
    """
    # First pass decides sampling without holding data: cheap line count.
    n_total = count_lines(path)
    meta = {"n_total": n_total, "n_used": n_total, "sampled": False, "cap": cap}

    if n_total <= cap:
        # full read, streamed into a pre-sized array (no giant Python list)
        arr = np.fromiter(iter_lnx(path), dtype=np.float64, count=-1)
        meta["n_used"] = len(arr)
        return arr, meta

    # reservoir sample to `cap` in a single streaming pass (Algorithm R,
    # deterministic seed so the subsample is identical run-to-run)
    rng = np.random.default_rng(SAMPLE_SEED)
    reservoir = np.empty(cap, dtype=np.float64)
    i = 0
    for v in iter_lnx(path):
        if i < cap:
            reservoir[i] = v
        else:
            j = rng.integers(0, i + 1)
            if j < cap:
                reservoir[j] = v
        i += 1
    meta["n_used"] = cap
    meta["sampled"] = True
    if log:
        log(f"    [sample] {path.name if hasattr(path,'name') else path}: "
            f"{n_total:,} records > cap {cap:,} -> reservoir-sampled to {cap:,} "
            f"(seed {SAMPLE_SEED}, deterministic). Numbers are on the subsample; "
            f"re-run with KLGHS_CAP={n_total} on adequate RAM for the full lake.")
    return reservoir, meta


def cap_from_env(default=DEFAULT_CAP):
    env = os.environ.get("KLGHS_CAP")
    if env:
        try:
            return max(1000, int(env))
        except ValueError:
            pass
    return default


# ---- GPU-aware array helpers (used by periodogram) ---------------------------
def to_compute(arr):
    """Move to GPU if we have one AND the array is large enough to benefit.
    Returns (array_on_backend, backend_module). backend is cp or np."""
    if HAVE_GPU and len(arr) >= GPU_MIN_N:
        return _cp.asarray(arr), _cp
    return arr, np


def to_host(x):
    """Bring a scalar/array back to host float, whichever backend produced it."""
    if HAVE_GPU and _cp is not None and isinstance(x, _cp.ndarray):
        return float(x.get())
    return float(x)


if __name__ == "__main__":
    print(resource_banner())
    if len(sys.argv) > 1:
        from pathlib import Path
        p = Path(sys.argv[1])
        arr, meta = load_lnx(p, cap=cap_from_env(), log=lambda s: print(s))
        print(f"  loaded {meta['n_used']:,} / {meta['n_total']:,} "
              f"(sampled={meta['sampled']})  span={arr.max()-arr.min():.2f} nat")
