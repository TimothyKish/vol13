"""
kish_lake_io.py -- strict lake I/O for the Kish-Lattice forward engines.

CONTRACT (Aurora Protocol, Mondy ruling 2026-09-12):
  * A missing field is a NAMED FAILURE, never a silent substitution.
  * No random generation. No simulation. No "structural placeholder".
  * If a field cannot be resolved, the engine aborts and prints the keys
    that ARE present, so the schema can be fixed rather than guessed.
  * Field coverage is reported as a first-class number on every run.

This is the same rule that scalarize.py's legacy fallback violated for
twelve volumes, applied one level up.
"""

import json
import sys
from pathlib import Path

# Physical constants (CODATA / IAU)
G     = 6.67430e-11      # m^3 kg^-1 s^-2
C     = 2.99792458e8     # m/s  (exact)
M_SUN = 1.98892e30       # kg
AU    = 1.495978707e11   # m    (exact)
KPC   = 3.0856775814913673e19  # m

# Search order for field resolution. Runtime-asserted, per the shared
# field-mapping ruling.
#
# NOTE (2026-09-13): the probe showed p2_orbital_radius nests its real payload
# THREE levels down at meta.source_row._raw_payload. A one-level search misses
# it entirely -- which is exactly the field-resolution failure Vol 12 found in
# scalarize.py. The resolver is therefore recursive, with the shallowest match
# winning and the full path reported.
_CONTAINERS = ("", "_raw_payload", "payload", "meta", "raw", "data",
               "source_row", "record", "row")
_MAX_DEPTH = 5


class LakeAbort(SystemExit):
    pass


def die(msg, detail=None):
    print("\n" + "=" * 78)
    print("  ABORT -- " + msg)
    print("=" * 78)
    if detail:
        print(detail)
    print("\nNo values were simulated. Fix the lake or the field mapping and re-run.")
    raise LakeAbort(2)


def load_jsonl(path, label):
    p = Path(path)
    if not p.exists():
        die(f"lake not found: {p}",
            f"Expected {label} at this path. Check the working directory.")
    recs = []
    with open(p, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                recs.append(json.loads(line))
            except json.JSONDecodeError as e:
                die(f"malformed JSON at {p}:{i}", str(e))
    if not recs:
        die(f"lake is empty: {p}")
    return recs


def resolve(rec, names):
    """Return (value, 'dotted.path') for the first candidate name that
    resolves anywhere in the record, else (None, None).

    Breadth-first so the SHALLOWEST match wins -- a top-level field always
    beats a copy buried in meta.source_row.
    """
    frontier = [(rec, "")]
    depth = 0
    while frontier and depth <= _MAX_DEPTH:
        nxt = []
        for node, prefix in frontier:
            if not isinstance(node, dict):
                continue
            for nm in names:
                if nm in node and node[nm] not in (None, "", [], {}):
                    v = node[nm]
                    if not isinstance(v, (dict, list)):
                        return v, (f"{prefix}{nm}" if prefix else nm)
            for k, v in node.items():
                if isinstance(v, dict):
                    nxt.append((v, f"{prefix}{k}."))
        frontier = nxt
        depth += 1
    return None, None


def key_inventory(recs, limit=200):
    """Every scalar key path seen in the first `limit` records, recursively."""
    seen = {}

    def walk(node, prefix, depth):
        if depth > _MAX_DEPTH or not isinstance(node, dict):
            return
        for k, v in node.items():
            path = f"{prefix}{k}"
            if isinstance(v, dict):
                walk(v, path + ".", depth + 1)
            elif isinstance(v, list):
                seen.setdefault(path, f"[list len {len(v)}] " + repr(v[:1])[:36])
            else:
                seen.setdefault(path, repr(v)[:48])

    for rec in recs[:limit]:
        walk(rec, "", 0)
    return seen


def require(recs, spec, label):
    """
    spec: {logical_name: (candidate field names...)}
    Returns (rows, resolved_paths, coverage).
    Aborts if ANY logical field resolves in zero records.
    """
    resolved_paths = {}
    for logical, cands in spec.items():
        hit = None
        for rec in recs[:2000]:
            _, path = resolve(rec, cands)
            if path:
                hit = path
                break
        if hit is None:
            inv = key_inventory(recs)
            dump = "\n".join(f"    {k:<44} = {v}" for k, v in sorted(inv.items()))
            die(f"required field '{logical}' not present in {label}",
                "  Tried candidate names: " + ", ".join(cands) +
                "\n\n  Keys actually present in this lake:\n" + dump)
        resolved_paths[logical] = hit

    rows, dropped = [], 0
    for rec in recs:
        row = {}
        ok = True
        for logical, cands in spec.items():
            val, _ = resolve(rec, cands)
            if val is None:
                ok = False
                break
            try:
                row[logical] = float(val)
            except (TypeError, ValueError):
                ok = False
                break
        if ok:
            rows.append(row)
        else:
            dropped += 1

    cov = len(rows) / len(recs) if recs else 0.0
    if not rows:
        die(f"every record in {label} failed field extraction")
    return rows, resolved_paths, cov


def report_provenance(label, path, recs, rows, paths, cov):
    print(f"  lake           : {path}")
    print(f"  records read   : {len(recs):,}")
    print(f"  records usable : {len(rows):,}   coverage = {cov*100:.2f}%")
    for logical, p in paths.items():
        print(f"  field  {logical:<16} <- {p}")
    if cov < 0.50:
        print(f"  [WARNING] coverage below 50% -- the usable subset is a "
              f"selection, and any result is conditional on it.")
    print()
