#!/usr/bin/env python3
"""
KishLattice Vol 12 — schema inspector (preflight_audit follow-up).

The first audit only looked at TOP-LEVEL keys, so any lake that stores its
physical values inside geometry_payload / _raw_payload was reported as
"FIELD ABSENT" when the data may be present and perfectly intact.

This script settles it:
  [1] dumps one full record per failing lake, so we can see real structure
  [2] recursively searches every nesting level for the configured field
  [3] classifies each lake:
        CONFIG-FIX   -> field exists at some path; fix addressing, no rebuild
        RENAME       -> a near-miss key exists (e.g. frequency_cm1)
        REBUILD      -> field genuinely absent at every depth

Usage (from vol12 root):
    python scripts/inspect_schema.py
    python scripts/inspect_schema.py --dump      # also print full sample records
"""

import json, os, sys, difflib

VOL_ROOT  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOLUMES   = os.path.join(VOL_ROOT, "configs", "volumes.json")
SCALARIZE = os.path.join(VOL_ROOT, "configs", "scalarize.json")
DUMP      = "--dump" in sys.argv


def resolve(entry, lake):
    p = entry.get("path") or f"lakes/inputs_promoted/{lake}_promoted.jsonl"
    return os.path.join(VOL_ROOT, p.replace("\\", "/"))


def first_record(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.strip():
                try:
                    return json.loads(line)
                except Exception:
                    return None
    return None


def walk(obj, prefix=""):
    """Yield (dotted_path, value) for every leaf and dict key at any depth."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else k
            yield p, v
            yield from walk(v, p)
    elif isinstance(obj, list) and obj:
        yield from walk(obj[0], f"{prefix}[0]")


def parse_maybe_json(v):
    """geometry_payload / _raw_payload are sometimes JSON-encoded strings."""
    if isinstance(v, str):
        s = v.strip()
        if s.startswith("{") or s.startswith("["):
            try:
                return json.loads(s)
            except Exception:
                return None
    return None


def find_field(rec, field):
    """Return list of dotted paths where `field` appears, at any depth,
    including inside JSON-encoded string payloads."""
    hits, allkeys = [], []
    stack = [(rec, "")]
    while stack:
        obj, pre = stack.pop()
        for path, val in walk(obj, pre):
            leaf = path.split(".")[-1].split("[")[0]
            allkeys.append(path)
            if leaf == field:
                hits.append((path, val))
            inner = parse_maybe_json(val)
            if inner is not None:
                stack.append((inner, path + "<json>"))
    return hits, allkeys


def main():
    vols = json.load(open(VOLUMES))["volumes"]
    doms = json.load(open(SCALARIZE))["domains"]
    enabled = {k: v for k, v in vols.items() if v.get("enabled")}

    print("=" * 78)
    print("Vol 12 SCHEMA INSPECTOR — nested field resolution")
    print("=" * 78)

    verdicts = {"CONFIG-FIX": [], "RENAME": [], "REBUILD": [], "OK-TOPLEVEL": []}

    for lake, e in sorted(enabled.items()):
        path = resolve(e, lake)
        if not os.path.exists(path):
            print(f"\n[{lake}]  MISSING FILE -> {path}")
            verdicts["REBUILD"].append((lake, "file not on disk"))
            continue

        field = doms.get(e["domain"], {}).get("field")
        if not field:
            continue

        rec = first_record(path)
        if rec is None:
            print(f"\n[{lake}]  UNREADABLE / EMPTY")
            verdicts["REBUILD"].append((lake, "unreadable"))
            continue

        if field in rec:
            verdicts["OK-TOPLEVEL"].append((lake, field))
            continue

        hits, allkeys = find_field(rec, field)
        print(f"\n[{lake}]  domain={e['domain']}  asks for '{field}'")
        if DUMP:
            print("  --- sample record ---")
            print("  " + json.dumps(rec, indent=2)[:1500].replace("\n", "\n  "))

        if hits:
            for p, v in hits[:3]:
                print(f"  FOUND at nested path: {p}   value={v!r}")
            verdicts["CONFIG-FIX"].append((lake, hits[0][0]))
            print(f"  VERDICT: CONFIG-FIX  (no rebuild — repoint scalarize.json)")
        else:
            leaves = sorted({p.split('.')[-1].split('[')[0] for p in allkeys})
            near = difflib.get_close_matches(field, leaves, n=4, cutoff=0.5)
            print(f"  all keys at any depth ({len(leaves)}): {leaves[:25]}")
            if near:
                print(f"  NEAR MATCHES: {near}")
                verdicts["RENAME"].append((lake, field, near))
                print(f"  VERDICT: RENAME  (no rebuild — field exists under another name)")
            else:
                verdicts["REBUILD"].append((lake, "field absent at every depth"))
                print(f"  VERDICT: REBUILD REQUIRED")

    print("\n" + "=" * 78)
    print("SUMMARY")
    print("=" * 78)
    for k in ("OK-TOPLEVEL", "CONFIG-FIX", "RENAME", "REBUILD"):
        items = verdicts[k]
        print(f"\n{k}: {len(items)}")
        for it in items:
            print("   ", it)

    n_rebuild = len(verdicts["REBUILD"])
    print("\n" + "-" * 78)
    print(f"Lakes actually requiring a promote.py rebuild: {n_rebuild}")
    print("Everything under CONFIG-FIX / RENAME is a scalarize.json edit only —")
    print("do NOT rebuild those lakes; it would break chain-of-custody vs Vol 11.")
    print("-" * 78)


if __name__ == "__main__":
    main()