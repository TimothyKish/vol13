#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
surrogate_gate.py  —  KLGHS Phase-Scramble Gate (Question 0)

Reads z_scores_master.json via the shared ledger_lib (array-indexed by register),
identical to preflight_real_z.py. Runs 100 phase-scramble surrogates per anchor
through the production pipeline in an ISOLATED scratch workspace (real ledger never
touched), and reports honest verdicts:

  OPEN         : all anchors real-STRONG and surrogates stay < 3.0 (null band)
  CLOSED       : a surrogate locked >= 5.0 (shape-artifact supported) — real result
  ESCALATE     : a surrogate in the 3.0-5.0 ambiguous band — referee call
  INCONCLUSIVE : an anchor did not run (missing z, mismatch unresolved, pipeline fail)

MISMATCH GUARD: if an anchor's configured register is not where it actually peaks,
the gate REFUSES to run that anchor and marks it MISMATCH_HALT — the register to
test is a referee decision, not a silent script default. Run the preflight first
and get Mondy's ruling on any mismatch before the gate will execute that anchor.

Config note: set each anchor's register_N only after the preflight + Mondy ruling.
"""

import json
import os
import shutil
import subprocess
import tempfile
import numpy as np
import ledger_lib as L

NUM_SURROGATES = 100
K_GEO = 16.0 / np.pi
RNG = np.random.default_rng()

ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIGS_DIR = os.path.join(ENGINE_DIR, "..", "configs")
LEDGER_PATH = os.path.join(ENGINE_DIR, "..", "lakes", "unified", "z_scores_master.json")

# register_N here is the register the gate will TEST. It must match where the anchor
# actually locks (preflight confirms) OR carry an explicit Mondy ruling for a mismatch.
ANCHORS = {
    "s2_stellar_kinematics": {
        "file": "../lakes/inputs_promoted/s2_stellar_kinematics_promoted.jsonl",
        "domain": "stellar_kinematic",
        "injection_mode": "scalar",          # promoted file stores scalar_kls (sector-normalized)
        "scalar_key": "scalar_kls",
        "register_N": 16,
        "real_z_threshold": 5.0,
        "mismatch_ruling": None,
    },
    "b5_pdb_protein": {
        "file": "../lakes/inputs_promoted/b5_pdb_protein_promoted.jsonl",
        "domain": "biology_backbone",
        "injection_mode": "raw",             # promoted file has NO scalar; only angle_degrees
        "data_field": "angle_degrees",
        "register_N": 25,
        "real_z_threshold": 5.0,
        "mismatch_ruling": None,
    },
    "p1_orbital_periods": {
        "file": "../lakes/inputs_promoted/p1_orbital_periods_promoted.jsonl",
        "domain": "orbital",
        "injection_mode": "raw",             # promoted file stores period_days_raw, no scalar
        "data_field": "period_days_raw",
        "register_N": 15,                    # MISMATCH: peak is 22 -> needs ruling
        "real_z_threshold": 5.0,
        "mismatch_ruling": None,
    },
}


def get_from_path(d, path):
    if isinstance(path, str):
        path = [path]
    for key in path:
        if isinstance(d, dict) and key in d:
            d = d[key]
        else:
            return None
    return d


def set_to_path(d, path, value):
    if isinstance(path, str):
        path = [path]
    t = d
    for k in path[:-1]:
        t = t.setdefault(k, {})
    t[path[-1]] = value


def scalarize_log_standard(values):
    v = np.asarray(values, dtype=float)
    return np.log(1.0 + np.abs(v)) / np.log(K_GEO)


def load_anchor(config):
    """Returns (scalars, templates, msg). For scalar mode reads the stored scalar;
    for raw mode reads the raw field and scalarizes it so the scramble operates in
    scalar space consistently."""
    path = os.path.join(ENGINE_DIR, config["file"])
    if not os.path.exists(path):
        return None, None, f"FILE NOT FOUND: {path}"
    mode = config["injection_mode"]
    field = config["scalar_key"] if mode == "scalar" else config["data_field"]
    vals, templates, bad = [], [], 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                bad += 1
                continue
            val = get_from_path(rec, field)
            if val is not None:
                try:
                    vals.append(float(val))
                    templates.append(rec)
                except (TypeError, ValueError):
                    bad += 1
            else:
                bad += 1
    if not vals:
        return None, None, f"No '{field}' found (mode={mode}, bad={bad})"
    arr = np.asarray(vals, dtype=float)
    if mode == "raw":
        arr = scalarize_log_standard(arr)   # bring raw values into scalar space
    return arr, templates, f"loaded {len(arr)} records via {mode}-mode field '{field}' (bad={bad})"


def phase_scramble_scalar(real_scalars, register_N):
    s = np.asarray(real_scalars, dtype=float)
    register = register_N / np.pi
    ratio = s / register
    node_index = np.floor(ratio)
    new_frac = RNG.uniform(0.0, 1.0, len(s))
    return (node_index + new_frac) * register


def _prepare_scratch(scratch_root):
    """Build a scratch tree mirroring what the pipeline reads/writes. Because the
    pipeline resolves ROOT = Path(__file__).parents[1], copying the scripts into
    scratch/engine makes ROOT = scratch_root, so ALL its I/O lands in scratch."""
    scratch_engine = os.path.join(scratch_root, "engine")
    os.makedirs(scratch_engine, exist_ok=True)
    # copy every engine script the pipeline might import or call
    for fn in ("build_chaos_nulls.py", "build_pinch_table.py", "scalarize.py",
               "unify.py", "engine_version.py", "ledger_lib.py", "sidecar.py"):
        s = os.path.join(ENGINE_DIR, fn)
        if os.path.exists(s):
            shutil.copy2(s, os.path.join(scratch_engine, fn))
    # copy configs (harmonic_targets.json, volumes.json, scalarize.json, schema.json)
    real_configs = os.path.join(ENGINE_DIR, "..", "configs")
    if os.path.isdir(real_configs):
        shutil.copytree(real_configs, os.path.join(scratch_root, "configs"), dirs_exist_ok=True)
    # create the lake dirs the pipeline writes into
    os.makedirs(os.path.join(scratch_root, "lakes", "synthetic"), exist_ok=True)
    os.makedirs(os.path.join(scratch_root, "lakes", "unified"), exist_ok=True)
    os.makedirs(os.path.join(scratch_root, "lakes", "logs"), exist_ok=True)


def pipeline_z_isolated(surrogate_records, domain, register_N, registers, scratch_root):
    """Returns (z, error_text). z is None on failure and error_text explains why."""
    scratch_unified = os.path.join(scratch_root, "lakes", "unified")
    master = os.path.join(scratch_unified, "unified_master.jsonl")
    with open(master, "w", encoding="utf-8") as f:
        for rec in surrogate_records:
            f.write(json.dumps(rec) + "\n")
    scratch_engine = os.path.join(scratch_root, "engine")
    for script in ("build_chaos_nulls.py", "build_pinch_table.py"):
        scratch_script = os.path.join(scratch_engine, script)
        if not os.path.exists(scratch_script):
            return None, f"scratch copy missing: {scratch_script} (check _prepare_scratch)"
        try:
            # invoke the SCRATCH COPY so Path(__file__).parents[1] resolves to the
            # scratch root, redirecting ALL pipeline I/O away from the real ledger.
            subprocess.run(["python", scratch_script],
                           check=True, capture_output=True, text=True, cwd=scratch_engine)
        except subprocess.CalledProcessError as e:
            return None, f"{script} failed:\nSTDERR: {(e.stderr or '')[:600]}\nSTDOUT: {(e.stdout or '')[:300]}"
    scratch_ledger = os.path.join(scratch_unified, "z_scores_master.json")
    ledger = L.load_ledger(scratch_ledger)
    if ledger is None:
        return None, f"pipeline ran but no z_scores_master.json at {scratch_ledger}"
    z = L.z_at_register(ledger, domain, register_N, registers)
    if z is None:
        return None, f"pipeline ran but no z for {domain}@{register_N}/pi in scratch ledger (keys: {list(ledger.keys())[:8]})"
    return z, None


def run_phase_scramble_gate():
    print("=" * 64)
    print("   KLGHS PHASE-SCRAMBLE GATE  (Question 0 / Pre-Registered)")
    print("=" * 64, "\n")

    ledger = L.load_ledger(LEDGER_PATH)
    if ledger is None:
        print("  [INCONCLUSIVE] Real ledger not found — gate did not run.")
        return
    registers = L.load_registers(CONFIGS_DIR)

    # SAFETY SENTINEL: record the real ledger's mtime. If any surrogate run changes
    # it, the isolation has failed and we HALT before corrupting the canonical ledger.
    real_ledger_mtime = os.path.getmtime(LEDGER_PATH)

    def _assert_ledger_untouched():
        now = os.path.getmtime(LEDGER_PATH)
        if now != real_ledger_mtime:
            print("\n  [FATAL] Real z_scores_master.json was modified during a surrogate run.")
            print("  Isolation FAILED. Halting to protect your canonical ledger.")
            print("  Restore from z_scores_master.json.bak and do not run the gate until")
            print("  the pipeline can be pointed at an explicit output dir.")
            raise SystemExit(1)

    results = {}
    print(f"ADVISORY: up to {NUM_SURROGATES} pipeline passes per anchor. May take 1-3 hrs.\n")

    for anchor_id, cfg in ANCHORS.items():
        print(f"--> Anchor: {anchor_id.upper()}")
        dom, testN = cfg["domain"], cfg["register_N"]

        # MISMATCH GUARD: refuse to run if configured register isn't the real peak
        peakN, peakZ = L.peak_register(ledger, dom, registers)
        if peakN is not None and peakN != testN and not cfg.get("mismatch_ruling"):
            print(f"    [!] MISMATCH: configured {testN}/pi but peak is {peakN}/pi (z={peakZ:+.2f}).")
            print(f"    [!] Refusing to run — needs a referee ruling (set mismatch_ruling).")
            results[anchor_id] = {"status": "MISMATCH_HALT",
                                  "configured_N": testN, "peak_N": peakN, "peak_z": peakZ}
            print("-" * 58); continue

        real_z = L.z_at_register(ledger, dom, testN, registers)
        if real_z is None:
            print(f"    [!] Real z not found for {dom}@{testN}/pi — INCONCLUSIVE.")
            results[anchor_id] = {"status": "INCONCLUSIVE"}
            print("-" * 58); continue

        print(f"    [+] Real chaos-Z at {testN}/pi: {real_z:.2f}  (need >= {cfg['real_z_threshold']})")
        if cfg.get("mismatch_ruling"):
            print(f"    [i] mismatch authorized by ruling: {cfg['mismatch_ruling']}")
        if real_z < cfg["real_z_threshold"]:
            print("    [!] Real anchor not STRONG — cannot serve as positive control.")
            results[anchor_id] = {"status": "REAL_NOT_STRONG", "real_z": float(real_z)}
            print("-" * 58); continue

        real_scalars, templates, msg = load_anchor(cfg)
        print(f"    [+] {msg}")
        if real_scalars is None:
            results[anchor_id] = {"status": "LOAD_FAILED"}
            print("-" * 58); continue

        surr_z = []
        print(f"    [>] {NUM_SURROGATES} surrogates: ", end="", flush=True)
        with tempfile.TemporaryDirectory(prefix=f"gate_{anchor_id}_") as scratch:
            _prepare_scratch(scratch)
            mode = cfg["injection_mode"]
            for i in range(NUM_SURROGATES):
                s_scr = phase_scramble_scalar(real_scalars, testN)
                surro = []
                if mode == "scalar":
                    for scal, rec in zip(s_scr, templates):
                        r = dict(rec)
                        r["scalar_kls"] = float(scal)
                        r["scalar_klc"] = float(scal)
                        surro.append(r)
                else:  # raw mode: invert scrambled scalar back to a raw value, inject raw field
                    raw_scr = (K_GEO ** s_scr) - 1.0
                    field = cfg["data_field"]
                    for raw, rec in zip(raw_scr, templates):
                        r = dict(rec)
                        set_to_path(r, field, float(raw))
                        surro.append(r)
                z, err = pipeline_z_isolated(surro, dom, testN, registers, scratch)
                _assert_ledger_untouched()   # halt if real ledger was written
                if z is None:
                    print(f"\n    [!] Surrogate {i} pipeline failed. First error:\n{err}")
                    break
                surr_z.append(z)
                print(".", end="", flush=True)
        print()

        if len(surr_z) != NUM_SURROGATES:
            results[anchor_id] = {"status": "INCONCLUSIVE", "real_z": float(real_z)}
            print("-" * 58); continue

        surr_z = np.array(surr_z)
        mean_z, std_z, max_z = surr_z.mean(), surr_z.std(ddof=1), surr_z.max()
        print(f"    [+] Surrogate Z: mean={mean_z:.2f} std={std_z:.2f} MAX={max_z:.2f}")
        if max_z >= 5.0:
            status = "FAILED"
        elif max_z >= 3.0:
            status = "ESCALATE"
        else:
            status = "PASSED"
        print(f"    [*] STATUS: {status}")
        results[anchor_id] = {"real_z": float(real_z), "test_N": testN,
                              "surr_mean_z": float(mean_z), "surr_std_z": float(std_z),
                              "surr_max_z": float(max_z), "status": status}
        print("-" * 58)

    print("\n" + "=" * 64)
    print("   GATE VERDICT")
    print("=" * 64)
    for name, r in results.items():
        s = r["status"]
        if s in ("PASSED", "FAILED", "ESCALATE"):
            print(f"  {name:<25} {s:<14} (real={r['real_z']:.2f} surrMax={r['surr_max_z']:.2f})")
        elif s == "MISMATCH_HALT":
            print(f"  {name:<25} MISMATCH_HALT  (cfg {r['configured_N']}/pi, peak {r['peak_N']}/pi)")
        else:
            print(f"  {name:<25} {s}")

    ran = [r for r in results.values() if r["status"] in ("PASSED", "FAILED", "ESCALATE")]
    all_ran = len(ran) == 3
    all_passed = all_ran and all(r["status"] == "PASSED" for r in ran)
    any_failed = any(r["status"] == "FAILED" for r in ran)
    any_escalate = any(r["status"] == "ESCALATE" for r in ran)

    print()
    if not all_ran:
        print("  [VERDICT: INCONCLUSIVE] One or more anchors did not run (see statuses).")
        print("  This is NOT a falsification. Resolve flagged anchors (mismatch rulings,")
        print("  missing z) and re-run. CLOSED is only valid when all three ran surrogates.")
    elif all_passed:
        print("  [VERDICT: OPEN] All three anchors: real STRONG, surrogates in null band")
        print("  (<3.0). Shape-artifact objection closed for the anchor domains.")
    elif any_failed:
        print("  [VERDICT: CLOSED] A surrogate locked (>=5.0). Shape-artifact supported.")
        print("  Real result. Escalate to Mondy for the foundational re-examination.")
    elif any_escalate:
        print("  [VERDICT: ESCALATE TO MONDY] Ambiguous band (3.0-5.0). Not a pass.")

    out = os.path.join(ENGINE_DIR, "phase_scramble_gate_result.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Result written: {out}")


if __name__ == "__main__":
    run_phase_scramble_gate()