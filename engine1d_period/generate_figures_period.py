#!/usr/bin/env python3
# ==============================================================================
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC. FOUNDER: Timothy John Kish
# Open for scientific testing / peer review. Cite "KishLattice 16/pi Initiative".
# ==============================================================================
#
# generate_figures_period.py  --  Period-engine report/figure executor (Vera).
#
# Same design as the phase engine's generate_figures.py: auto-discovers every
# report_*.py plugin in reports1d_period/, builds a context dict from the period
# engine's own artifacts, calls each plugin's generate(context) in sequence, and
# writes a sidecar heartbeat between plugins so the run shows progress.
#
# It is a NO-OP if reports1d_period/ has no report_*.py plugins yet -- the
# pipeline calls it optionally, so an empty reports folder is fine. When Vera
# adds plugins, they run automatically on the next pipeline figures stage.
#
# CONTEXT provided to every plugin (period-engine flavour -- NOT phase z-scores):
#   context["portrait"]        dict   period_portrait.json (per-lake support,
#                                      shape, resolvable registers, sampled flag)
#   context["logified_dir"]    Path   lakes1d_period/logified/  (raw ln x per lake)
#   context["output_dir"]      Path   reports1d_period/output/run_TIMESTAMP/
#   context["root_path"]       Path   vol root
#   context["registers"]       list   [4..26]
#   context["harmonic_labels"] list   ["4/pi", ..., "26/pi"]
#   context["kg"], ["container"]      the modulus and container (test-time only)
#   context["run_timestamp"]   str    UTC stamp
#   context["load_lnx"]        func   streaming loader (cap-aware) for big lakes
#
# A plugin implements:
#     def generate(context: dict) -> list[Path]:
#         ...returns the files it created.
# ==============================================================================
import importlib.util
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ENGINE = Path(__file__).resolve().parent
ROOT   = ENGINE.parent
REPORTS_DIR   = ROOT / "reports1d_period"
UNIFIED       = ROOT / "lakes1d_period" / "unified"
LOGIFIED      = ROOT / "lakes1d_period" / "logified"
PORTRAIT_PATH = UNIFIED / "period_portrait.json"
HEARTBEAT     = UNIFIED / "period_heartbeat.json"

sys.path.insert(0, str(ENGINE))
from periodogram import load_registers_and_kgeo
from kish_period_io import load_lnx, cap_from_env


def utc(): return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def heartbeat(pct, done, total, action):
    try:
        UNIFIED.mkdir(parents=True, exist_ok=True)
        HEARTBEAT.write_text(json.dumps({
            "timestamp_utc": utc(), "progress_pct": round(pct, 1),
            "completed": done, "total": total,
            "current_action": action, "eta_seconds": 0}))
    except Exception:
        pass


def discover_plugins():
    if not REPORTS_DIR.exists():
        return []
    return sorted(p for p in REPORTS_DIR.glob("report_*.py")
                 if p.parent.name == "reports1d_period")


def load_plugin(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "generate"):
        raise AttributeError(f"{path.name} has no generate(context) function")
    return mod


def build_context(output_dir):
    registers, container, kg = load_registers_and_kgeo()
    portrait = {}
    if PORTRAIT_PATH.exists():
        try:
            portrait = json.loads(PORTRAIT_PATH.read_text())
        except Exception:
            portrait = {}
    return {
        "portrait": portrait,
        "logified_dir": LOGIFIED,
        "output_dir": output_dir,
        "root_path": ROOT,
        "registers": registers,
        "harmonic_labels": [f"{N}/pi" for N in registers],
        "kg": kg, "container": container,
        "run_timestamp": datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"),
        "load_lnx": lambda p: load_lnx(Path(p), cap=cap_from_env())[0],
    }


def main():
    plugins = discover_plugins()
    if not plugins:
        print("  [figures] no report_*.py plugins in reports1d_period/ -- nothing to do.")
        print("            (Vera adds plugins here; they run automatically next time.)")
        return

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = REPORTS_DIR / "output" / f"run_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    ctx = build_context(out_dir)

    print(f"  [figures] {len(plugins)} plugin(s) -> {out_dir}")
    created = []
    index = {}
    for i, path in enumerate(plugins):
        heartbeat(100*i/len(plugins), i, len(plugins), f"figure: {path.stem}")
        try:
            mod = load_plugin(path)
            files = mod.generate(ctx) or []
            files = [str(Path(f)) for f in files]
            created += files
            index[path.stem] = files
            print(f"    [{path.stem}] {len(files)} file(s)")
        except Exception as e:
            print(f"    [{path.stem}] FAILED: {e}")
            index[path.stem] = {"error": str(e)}
    heartbeat(100, len(plugins), len(plugins), "figures done")

    (out_dir / "figures_index.json").write_text(json.dumps(index, indent=2))
    print(f"  [figures] {len(created)} file(s) total; index -> {out_dir/'figures_index.json'}")


if __name__ == "__main__":
    main()
