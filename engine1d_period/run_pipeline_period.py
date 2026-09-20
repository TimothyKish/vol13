#!/usr/bin/env python3
# ==============================================================================
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC. FOUNDER: Timothy John Kish
# Open for scientific testing / peer review. Cite "KishLattice 16/pi Initiative".
# ==============================================================================
#
# run_pipeline_period.py  --  PERIOD ENGINE orchestrator (1D), full logging.
#
# Familiar to anyone trained on the phase engine: named stages, --from resume,
# a heartbeat for the sidecar, and now a full RUN LOG + RECEIPT written to
# lakes1d_period/logs/ in the same style as the phase engine's lakes/logs/.
#
# STAGES (a run produces the whole picture, not four hand-run scripts):
#   logify     raw promoted lake -> ln(x) lake
#   support    mandatory support-profile gate (effective span, shape verdict)
#   scan       periodogram excess per register, resolution-gated
#   census     survey-wide register census (resolve AND lock above the bar)
#   figures    optional (Vera)
#
# RESOURCE-ADAPTIVE: streams large lakes, reservoir-samples above the cap,
# uses GPU + threads when present, runs on a single core otherwise. Same
# numbers on a potato and a beast (Timothy's core principle).
# ==============================================================================
import argparse, json, math, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

ENGINE = Path(__file__).resolve().parent
ROOT   = ENGINE.parent
LOGIFIED = ROOT / "lakes1d_period" / "logified"
UNIFIED  = ROOT / "lakes1d_period" / "unified"
LOGS     = ROOT / "lakes1d_period" / "logs"
HEARTBEAT = UNIFIED / "period_heartbeat.json"

sys.path.insert(0, str(ENGINE))
from periodogram import load_registers_and_kgeo, scan_domain, delta_N, score_register, RES_THRESHOLD
from support_profile import profile
from kish_period_io import load_lnx, cap_from_env, resource_banner, n_workers

STAGES = ["logify", "support", "scan", "census", "figures"]
BAR_SINGLE = 5.57
BAR_SURVEY = 6.22
N_INDEP_MIN = 2.0   # Mondy D.4: excess from <2 bg samples is not a measurement


# ---- a tee: everything printed also lands in the run log --------------------
class Tee:
    def __init__(self, logpath):
        self.log = open(logpath, "w", encoding="utf-8")
        self.stdout = sys.stdout
    def write(self, s):
        self.stdout.write(s); self.log.write(s)
    def flush(self):
        self.stdout.flush(); self.log.flush()
    def close(self):
        self.log.close()


def utc(): return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def heartbeat_reset(t0):
    """Write a fresh zeroed beat at run start so the sidecar clears the PRIOR
    run's final state immediately, instead of showing stale content until the
    first real beat lands."""
    UNIFIED.mkdir(parents=True, exist_ok=True)
    try:
        HEARTBEAT.write_text(json.dumps({
            "timestamp_utc": utc(), "progress_pct": 0.0,
            "completed": 0, "total": 0,
            "current_action": "starting new run...", "eta_seconds": 0,
        }))
    except Exception:
        pass

def heartbeat(pct, done, total, action, t0):
    UNIFIED.mkdir(parents=True, exist_ok=True)
    try:
        HEARTBEAT.write_text(json.dumps({
            "timestamp_utc": utc(), "progress_pct": round(pct, 1),
            "completed": done, "total": total, "current_action": action,
            "eta_seconds": int((time.time()-t0)/max(pct,1e-9)*(100-pct)) if pct>0 else 0,
        }))
    except Exception:
        pass

def fingerprint():
    try:
        r = subprocess.run([sys.executable, str(ENGINE/"engine_version_period.py")],
                           capture_output=True, text=True)
        return r.stdout.strip().split("\n")[0]
    except Exception:
        return "unavailable"


def stage_logify():
    r = subprocess.run([sys.executable, str(ENGINE/"logify.py")],
                       capture_output=True, text=True)
    print(r.stdout, end="")
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr); return False
    return True


def stage_support_scan_census(cap, skip_scan, skip_census):
    registers, container, kg = load_registers_and_kgeo()
    files = sorted(LOGIFIED.glob("*_logified.jsonl"))
    if not files:
        print("  [support] no logified lakes found"); return False, {}
    results, survey_signals = {}, []
    t0 = time.time()
    nlakes = len(files)

    for i, f in enumerate(files):
        dom = f.stem.replace("_logified", "")
        base_pct = 100.0 * i / nlakes
        heartbeat(base_pct, i, nlakes, f"loading {dom}", t0)

        # STREAMING load with cap + sampling; lakes under cap are full
        lnx, meta = load_lnx(f, cap=cap, log=lambda s: print(s))
        tag = f" [sampled {meta['n_used']:,}/{meta['n_total']:,}]" if meta["sampled"] else ""

        # GUARD: a lake with too few usable values is a NAMED SKIP, never a crash.
        if meta["n_used"] < 20:
            print(f"\n  [{dom}] SKIPPED -- only {meta['n_used']} usable klghs_lnx "
                  f"values (of {meta['n_total']:,} lines). Check the logify field "
                  f"mapping for this lake; nothing scored.")
            results[dom] = {"skipped": True, "n_used": meta["n_used"],
                            "n_total": meta["n_total"]}
            continue

        # ---- SUPPORT (swept) + SHAPE ----
        sweep = {q: profile(lnx, q=q) for q in (0.025, 0.005, 0.0005)}
        if sweep[0.005]["verdict"] == "EMPTY-OR-DEGENERATE":
            print(f"\n  [{dom}] SKIPPED -- support degenerate (zero span or "
                  f"single value). n_used={meta['n_used']:,}. Nothing to score.")
            results[dom] = {"skipped": True, "degenerate": True,
                            "n_used": meta["n_used"]}
            continue
        p = sweep[0.005]
        eff = p["eff_span"] if p["verdict"] != "SUPPORT-OK" else p["raw_span"]
        print(f"\n  [{dom}] n={meta['n_used']:,}{tag}")
        print(f"    support: raw {p['raw_span']:.2f} eff {p['eff_span']:.2f} "
              f"infl {p['inflation']:.2f} -> {p['verdict']}")
        try:
            from histogram_view import shape_verdict
            h, edges = np.histogram(lnx, 25)
            sv, why = shape_verdict(h, h.max()/len(lnx), int(np.sum(h[1:-1]==0)),
                                    p["tail_fraction"], p["inflation"])
            print(f"    shape:   {sv} -- {why}")
            # print the distribution itself -- the histogram is the EVIDENCE, the
            # verdict is only its summary. A reader must see what SPIKED means.
            hmax = max(1, int(h.max()))
            print(f"    distribution (ln x, 25 bins, densest={h.max()/len(lnx)*100:.0f}% of mass):")
            for bi in range(25):
                bar = "#" * int(40 * h[bi] / hmax)
                print(f"      {edges[bi]:8.1f}..{edges[bi+1]:8.1f} {int(h[bi]):>9}  {bar}")
        except Exception as e:
            sv = "unavailable"; print(f"    shape:   (unavailable: {e})")

        rec = {"support": p, "shape": sv, "sampled": meta["sampled"],
               "n_used": meta["n_used"], "n_total": meta["n_total"]}

        if not skip_scan:
            def hb(msg): heartbeat(base_pct, i, nlakes, f"{dom}: {msg}", t0)
            rows, _ = scan_domain(lnx, kg, container, registers, heartbeat=hb)
            # resolution verdict on EFFECTIVE span + stability across sweep
            resolvable = []
            for row in rows:
                d = delta_N(row["N"], kg, container)
                mn_eff = (eff / d) / row["N"]
                row["MN_eff"] = mn_eff
                if row["status"] == "SCORED" and mn_eff <= RES_THRESHOLD:
                    row["status"] = "BACKGROUND-LIMITED-EFFECTIVE"
                if row["status"] == "SCORED":
                    resolvable.append(row)
            # percentile-stability of the resolution verdict
            stable = {}
            for row in rows:
                d = delta_N(row["N"], kg, container)
                vs = [ (sweep[q]["eff_span"]/d)/row["N"] > RES_THRESHOLD
                       for q in (0.025,0.005,0.0005) ]
                stable[row["N"]] = all(vs) or not any(vs)
            signals = [r for r in resolvable
                       if r.get("excess") is not None and r["excess"] >= BAR_SINGLE
                       and r.get("n_indep", 0) >= N_INDEP_MIN
                       and stable[r["N"]]]
            rec["rows"] = rows
            rec["resolvable"] = [r["N"] for r in resolvable]
            if signals:
                for r in signals:
                    print(f"    *** SIGNAL {r['N']}/pi excess {r['excess']:.1f} "
                          f"n_indep {r['n_indep']:.1f} (stable) ***")
                    survey_signals.append((dom, r["N"], r["excess"]))
            elif resolvable:
                b = max(resolvable, key=lambda r: (r.get("excess") or -9))
                print(f"    scan: best resolvable {b['N']}/pi excess "
                      f"{(b.get('excess') or float('nan')):.1f} -- below bar")
            else:
                print(f"    scan: no register resolvable on effective support")
        results[dom] = rec

    heartbeat(100, nlakes, nlakes, "writing portrait", t0)
    UNIFIED.mkdir(parents=True, exist_ok=True)
    (UNIFIED/"period_portrait.json").write_text(json.dumps(
        {k: ({"skipped": True, "n_used": v.get("n_used"), "n_total": v.get("n_total")}
             if v.get("skipped") else
             {"support": v.get("support"), "shape": v.get("shape"),
              "resolvable": v.get("resolvable"), "sampled": v.get("sampled")})
         for k, v in results.items()}, indent=2, default=float))

    if not skip_census:
        print("\n" + "="*72)
        print("  SURVEY-WIDE REGISTER CENSUS")
        print("="*72)
        if survey_signals:
            from collections import Counter
            for N, c in sorted(Counter(n for _,n,_ in survey_signals).items()):
                doms = [d for d,n,_ in survey_signals if n==N]
                print(f"    {N}/pi : {c} domain(s) -- {', '.join(doms)}")
        else:
            print("  NO register is both resolved and locked above the bar by ANY")
            print("  domain on effective support. The survey, measured honestly,")
            print("  does not currently demonstrate a register. This is a")
            print("  measurement of the instrument's reach, not a claim about the")
            print("  framework. (Mondy Item 8.)")
        print("="*72)

    return True, results


def main():
    ap = argparse.ArgumentParser(description="KishLattice PERIOD engine (1D)")
    ap.add_argument("--from", dest="start", choices=STAGES, default="logify")
    ap.add_argument("--skip-figures", action="store_true")
    ap.add_argument("--support-only", action="store_true")
    ap.add_argument("--skip-census", action="store_true")
    ap.add_argument("--cap", type=int, default=None, help="sample cap (default 2M / env KLGHS_CAP)")
    a = ap.parse_args()

    cap = a.cap if a.cap else cap_from_env()
    LOGS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    logpath = LOGS / f"run_period_{stamp}.log"
    tee = Tee(logpath)
    sys.stdout = tee

    fp = fingerprint()
    t_all = time.time()
    heartbeat_reset(t_all)          # clean reset so the sidecar drops the prior run
    print("KishLattice Period Engine Run Log")
    print("="*72)
    print(f" started_utc : {utc()}")
    print(f" fingerprint : {fp}")
    print(resource_banner(cap))
    print(f" start stage : {a.start}   support gate: MANDATORY")
    print("="*72)

    start_idx = STAGES.index(a.start)
    try:
        if start_idx <= STAGES.index("logify"):
            print("\n[STAGE] logify")
            if not stage_logify():
                print("logify failed; aborting."); sys.exit(1)
        if start_idx <= STAGES.index("scan"):
            print("\n[STAGE] support + scan + census")
            ok, _ = stage_support_scan_census(
                cap, skip_scan=a.support_only,
                skip_census=(a.skip_census or a.support_only))
            if not ok: sys.exit(1)
        if not a.skip_figures and not a.support_only and start_idx <= STAGES.index("figures"):
            fig = ENGINE/"generate_figures_period.py"
            if fig.exists():
                print("\n[STAGE] figures")
                subprocess.run([sys.executable, str(fig)])
    finally:
        runtime = time.time() - t_all
        receipt = LOGS / f"run_period_{stamp}.receipt.txt"
        receipt.write_text(
            "KishLattice PERIOD Engine Run Receipt\n" + "="*48 + "\n"
            f"engine_version_period: {fp}\n"
            f"completed_utc: {utc()}\n"
            f"total_runtime_s: {runtime:.1f}\n"
            f"resources: {resource_banner(cap).strip()}\n"
            f"sample_cap: {cap}\n"
            f"log: {logpath.name}\n"
            "support gate: MANDATORY (effective-span resolution)\n")
        print(f"\nReceipt : {receipt}")
        print(f"Log     : {logpath}")
        print(f"Runtime : {runtime:.1f}s")
        sys.stdout = tee.stdout
        tee.close()


if __name__ == "__main__":
    main()
