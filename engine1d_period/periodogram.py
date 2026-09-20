#!/usr/bin/env python3
# ==============================================================================
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC.  FOUNDER: Timothy John Kish
# Open for scientific testing / peer review. Cite "KishLattice 16/pi Initiative"
# and credit Timothy John Kish. No commercial or uncredited use without permission.
# ==============================================================================
#
# periodogram.py  --  PERIOD ENGINE statistic (1D), resource-adaptive.
#
#   theta_j = 2*pi * ln(x_j) / Delta_N ,   Delta_N = N * ln(k_geo) / (24*pi)
#   R       = | mean_j exp(i theta_j) | ,   P = n R^2
#
# k_geo enters HERE, at test time, as the scanned register -- never in the lake.
# Registers come from harmonic_targets.json (NOT hardcoded).
#
# RESOURCE ADAPTATION (Timothy's core principle: same numbers, potato to beast):
#   * The resultant sum runs on GPU (CuPy) when the array is large and a GPU is
#     present, else NumPy. IDENTICAL math both ways -- GPU only changes speed.
#   * The 23-register scan and the 121-point annulus are parallelised across CPU
#     workers when there is more than one core. A single-core machine runs them
#     serially and gets the same answer.
#   * An optional heartbeat callback fires inside the annulus loop so the sidecar
#     never goes dark during a big lake.
#
# THREE things, all pre-registered (Vol 12 Ch 11-12, Mondy rulings 2026-08-27):
#   (1) RESOLUTION GATE  M/N = span / (N^2 * 0.0215902); <=2.67 -> no excess.
#   (2) ANNULAR BACKGROUND  inner=1.6/M outer=0.60/N, 121 pts, excess in MAD.
#   (3) UNIT-INVARIANCE SELF-CHECK  P identical under x->c*x (the theorem).
# ==============================================================================
import json
import math
import sys
from pathlib import Path
import numpy as np

_here = Path(__file__).resolve().parent
sys.path.insert(0, str(_here))
from kish_period_io import to_compute, to_host, HAVE_GPU, n_workers

ROOT = _here.parent
TARGETS_PATH = ROOT / "configs" / "harmonic_targets.json"
TARGETS_ALT  = ROOT / "configs1d_period" / "harmonic_targets.json"

ANNULUS_INNER = 1.6
ANNULUS_OUTER = 0.60
ANNULUS_NPTS  = 121
RES_THRESHOLD = ANNULUS_INNER / ANNULUS_OUTER   # 2.6667, derived


def load_registers_and_kgeo():
    path = TARGETS_PATH if TARGETS_PATH.exists() else TARGETS_ALT
    with open(path, "r", encoding="utf-8") as f:
        t = json.load(f)
    registers = t["registers"]
    container = t.get("container", 24)
    kg = 16.0 / math.pi
    sc = ROOT / "configs" / "scalarize.json"
    if sc.exists():
        try:
            kg = json.load(open(sc, encoding="utf-8")).get("k_geo", kg)
        except Exception:
            pass
    return registers, container, float(kg)


def delta_N(N, kg, container):
    return N * math.log(kg) / (container * math.pi)


# ---- the hot inner kernel, backend-agnostic ---------------------------------
def _resultant_power_backend(lnx_b, xp, delta):
    """Resultant power on whichever backend lnx_b lives (cp or np)."""
    th = (2.0 * math.pi / delta) * lnx_b
    z = xp.mean(xp.exp(1j * th))
    R = abs(z)
    return len(lnx_b) * R * R, R


def resultant_power(lnx, delta):
    """Public entry. Moves to GPU when worthwhile, returns host floats.
    IDENTICAL result to a pure-NumPy call -- only speed differs."""
    lnx_b, xp = to_compute(np.asarray(lnx, dtype=np.float64))
    P, R = _resultant_power_backend(lnx_b, xp, delta)
    return to_host(P), to_host(R)


def score_register(lnx, N, kg, container, heartbeat=None):
    """M/N gate, and (if resolvable) the annular-background excess."""
    lnx = np.asarray(lnx, dtype=np.float64)
    span = float(lnx.max() - lnx.min())
    d = delta_N(N, kg, container)
    M = span / d
    mn = M / N
    out = {"N": N, "log_span": span, "M": M, "MN": mn}

    if mn < 1.0:
        out["status"] = "RESOLUTION-LIMITED"; return out
    if mn <= RES_THRESHOLD:
        out["status"] = "BACKGROUND-LIMITED"; return out

    inner = ANNULUS_INNER / M
    outer = ANNULUS_OUTER / N
    offs = np.concatenate([
        np.linspace(-outer, -inner, ANNULUS_NPTS // 2),
        np.linspace(inner, outer, ANNULUS_NPTS // 2),
    ])
    # move the lake to the compute backend ONCE, reuse across all 121 offsets
    lnx_b, xp = to_compute(lnx)
    bg = np.empty(len(offs), dtype=np.float64)
    for k, t in enumerate(offs):
        P, _ = _resultant_power_backend(lnx_b, xp, d * (1.0 + t))
        bg[k] = to_host(P)
        if heartbeat and (k % 20 == 0):
            heartbeat(f"N={N}/pi bg {k}/{len(offs)}")
    P, R = _resultant_power_backend(lnx_b, xp, d)
    P, R = to_host(P), to_host(R)
    med = float(np.median(bg))
    mad = float(np.median(np.abs(bg - med))) * 1.4826
    excess = (P - med) / mad if mad > 0 else float("nan")
    out.update({"status": "SCORED", "P": P, "R": R, "background": med,
                "excess": float(excess),
                "n_indep": 2.0 * (ANNULUS_OUTER * mn - ANNULUS_INNER)})
    return out


def scan_domain(lnx, kg, container, registers, heartbeat=None, parallel=True):
    """Scan all registers. Parallel across CPU workers when >1 core and no GPU
    (with a GPU the per-register work is already offloaded; threads would just
    contend for the device). Serial otherwise. Same result either way."""
    lnx = np.asarray(lnx, dtype=np.float64)
    workers = n_workers()

    if parallel and workers > 1 and not HAVE_GPU and len(lnx) < 5_000_000:
        from concurrent.futures import ThreadPoolExecutor
        rows = [None] * len(registers)
        done = [0]
        def work(i_N):
            i, N = i_N
            r = score_register(lnx, N, kg, container)
            done[0] += 1
            if heartbeat:
                heartbeat(f"scan {done[0]}/{len(registers)} registers")
            return i, r
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for i, r in ex.map(work, list(enumerate(registers))):
                rows[i] = r
    else:
        rows = []
        for i, N in enumerate(registers):
            rows.append(score_register(lnx, N, kg, container, heartbeat=heartbeat))
            if heartbeat:
                heartbeat(f"scan {i+1}/{len(registers)} registers")

    scored = [r for r in rows if r["status"] == "SCORED"]
    best = max(scored, key=lambda r: r["excess"]) if scored else None
    return rows, best


def unit_invariance_check(lnx, N, kg, container, factors=(1.0, math.e, 3.0, 1/60.0)):
    d = delta_N(N, kg, container)
    lnx = np.asarray(lnx, dtype=np.float64)
    vals = [resultant_power(lnx + math.log(c), d)[0] for c in factors]
    return vals, (max(vals) - min(vals)) < 1e-6 * max(vals)


if __name__ == "__main__":
    registers, container, kg = load_registers_and_kgeo()
    from kish_period_io import resource_banner
    print(resource_banner())
    print(f"registers={registers}\ncontainer={container}  k_geo={kg:.10f}")
    print(f"RES_THRESHOLD = {RES_THRESHOLD:.4f}   GPU={HAVE_GPU}")
