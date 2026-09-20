#!/usr/bin/env python3
# ==============================================================================
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC.
# FOUNDER: Timothy John Kish
# LICENSE & TERMS OF USE: Open for scientific testing, empirical validation, and
# academic peer review. Any publication, derivative code, dataset generation, or
# public distribution relying on this framework must explicitly cite the
# "KishLattice 16/pi Initiative" and credit Timothy John Kish. Commercial use or
# uncredited reproduction is prohibited without written permission.
# ==============================================================================
#
# logify.py  --  PERIOD ENGINE scalarizer (1D)
#
# DESIGN CONTRACT, and how it differs from the phase engine's scalarize.py:
#
#   * NO MODULUS is applied here. The phase engine computes ln(1+x/x0)/ln(k_geo)
#     at promotion, baking k_geo into every record. The period engine stores the
#     RAW positive quantity x and takes ln(x) at TEST time (see periodogram.py),
#     with the modulus entering only as the scanned register. This is what makes
#     the period lake framework-agnostic (Vol 12, Ch 11) and it is deliberate.
#
#   * NO x0. x0 is the phase origin; the period statistic has no phase origin
#     (Vol 12 degeneracy result). There is nothing to pre-register and nothing
#     to tune. If a logify.json entry contains 'x0' the run ABORTS -- carrying
#     an x0 here would be a silent re-import of the phase engine's free parameter.
#
#   * NO sector normalisation, ever. Trial 2b / Erratum 4a: a per-sector additive
#     shift is Form C. If a source record carries scalar_klc / sector_normalized
#     the run ABORTS unless KLGHS_PERIOD_ALLOW_NORM=1 is set explicitly.
#
#   * Field resolution is IDENTICAL to the phase engine (resolve_field), so the
#     two engines read the same promoted lakes through the same contract. Mondy's
#     ruling: shared field mapping is permitted, and MUST carry runtime assertions.
#
# Output: writes <lake>_logified.jsonl carrying entity_id, domain, lake_id,
# the raw positive scalar x under key 'klghs_x', its ln under 'klghs_lnx' (a
# convenience; the periodogram recomputes it), the target_register, and the
# untouched provenance. No modulus, no k_geo, anywhere in the output.
# ==============================================================================

import json
import math
import os
import sys
from pathlib import Path

MAX_RESOLVE_DEPTH = 6
STRICT_MODE = os.environ.get("KLGHS_PERIOD_STRICT", "1") == "1"
ALLOW_NORM  = os.environ.get("KLGHS_PERIOD_ALLOW_NORM", "0") == "1"

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "configs1d_period" / "logify.json"
IN_DIR  = ROOT / "lakes1d_period" / "inputs_promoted"
OUT_DIR = ROOT / "lakes1d_period" / "logified"

# ---- dispatch telemetry (same philosophy as the phase engine) ----------------
_report = {}
def _note(domain, route):
    _report.setdefault(domain, {"routes": {}, "fail": None})
    _report[domain]["routes"][route] = _report[domain]["routes"].get(route, 0) + 1
def _fail(domain, reason, detail):
    _report.setdefault(domain, {"routes": {}, "fail": None})
    _report[domain]["fail"] = (reason, detail)


def _dotted(record, path):
    cur = record
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def resolve_field(record, field):
    """(value, dotted_path) or (None, None). Identical contract to scalarize.py."""
    if not field:
        return (None, None)
    if "." in field:
        val = _dotted(record, field)
        return (None, None) if val is None else (val, field)
    frontier = [(record, "")]
    depth = 0
    while frontier and depth <= MAX_RESOLVE_DEPTH:
        nxt = []
        for obj, prefix in frontier:
            if not isinstance(obj, dict):
                continue
            if field in obj and obj[field] is not None:
                return (obj[field], f"{prefix}.{field}" if prefix else field)
            for k, v in obj.items():
                if isinstance(v, dict):
                    nxt.append((v, f"{prefix}.{k}" if prefix else k))
        frontier = nxt
        depth += 1
    return (None, None)


def _load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    # RUNTIME ASSERTION 1: no modulus and no phase origin may DRIVE COMPUTATION.
    # We check the computational surface -- config keys and per-domain entry keys --
    # NOT free-text notes. A prohibition written in a 'note'/'description' string
    # (e.g. "no modulus appears here") must not trip the guard; only an actual
    # k_geo / modulus / x0 KEY that the engine would read is a violation.
    banned = {"k_geo", "modulus", "x0"}
    top_keys = set(cfg.keys())
    hit = banned & top_keys
    for dom, entry in cfg.get("domains", {}).items():
        if isinstance(entry, dict):
            hit |= (banned & set(entry.keys()))
    if hit:
        raise SystemExit(
            f"[logify] ABORT: banned computational key(s) {sorted(hit)} present in "
            f"logify.json. The period engine carries no modulus and no phase origin. "
            f"Remove the key(s). (Free-text notes mentioning these words are fine.)"
        )
    return cfg["domains"]


def combine(record, entry):
    """Return positive raw scalar x, or (None, reason)."""
    ctype = entry.get("combine", "identity")
    if ctype == "quadrature":
        acc = 0.0
        for fld in entry["fields"]:
            v, _ = resolve_field(record, fld)
            if v is None:
                return None, f"missing field {fld}"
            acc += float(v) ** 2
        x = math.sqrt(acc)
    else:
        v, path = resolve_field(record, entry["field"])
        if v is None:
            return None, f"field {entry['field']} unresolved"
        x = abs(float(v)) if ctype == "abs" else float(v)
    if not (x > 0) or not math.isfinite(x):
        return None, f"non-positive or non-finite x={x}"
    return x, None


def logify_record(record, domain, entry):
    # RUNTIME ASSERTION 2: refuse sector-normalised source records (Form C guard)
    if not ALLOW_NORM:
        meta = record.get("meta", {}) or {}
        if meta.get("sector_normalized") or ("scalar_klc" in record and
                                             record.get("scalar_klc") != record.get("scalar_kls")):
            _fail(domain, "SECTOR_NORMALIZED",
                  "source carries sector normalisation; period engine forbids it (Erratum 4a)")
            return None
    x, reason = combine(record, entry)
    if x is None:
        _fail(domain, "NO_SCALAR", reason)
        return None
    _note(domain, "logified")
    return {
        "entity_id":  record.get("entity_id"),
        "domain":     record.get("domain", domain),
        "lake_id":    record.get("lake_id"),
        "klghs_x":    x,
        "klghs_lnx":  math.log(x),
        "target_register": entry.get("target_register"),
        "provenance": record.get("meta", {}),
    }


def main():
    domains = _load_config()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not IN_DIR.exists():
        raise SystemExit(f"[logify] no input dir {IN_DIR}")

    # map lake files by domain via the record's own 'domain' field
    for src in sorted(IN_DIR.glob("*_promoted.jsonl")):
        out = OUT_DIR / (src.stem.replace("_promoted", "") + "_logified.jsonl")
        n_in = n_out = 0
        with open(src, encoding="utf-8") as fh, open(out, "w", encoding="utf-8") as wf:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                n_in += 1
                rec = json.loads(line)
                dom = rec.get("domain")
                if dom not in domains:
                    continue
                res = logify_record(rec, dom, domains[dom])
                if res is not None:
                    wf.write(json.dumps(res) + "\n")
                    n_out += 1
        print(f"  logify {src.name}: {n_in} -> {n_out}")

    # dispatch report + STRICT abort
    print("\n  DISPATCH REPORT")
    aborted = False
    for dom, info in _report.items():
        routes = info["routes"]
        if info["fail"]:
            reason, detail = info["fail"]
            print(f"    [{dom}] FAIL {reason}: {detail}")
            if STRICT_MODE and reason in ("SECTOR_NORMALIZED",):
                aborted = True
        else:
            print(f"    [{dom}] {routes}")
    if aborted:
        raise SystemExit("[logify] ABORT under KLGHS_PERIOD_STRICT: Form C guard fired.")


if __name__ == "__main__":
    main()