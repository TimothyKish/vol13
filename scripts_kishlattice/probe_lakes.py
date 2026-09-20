"""
probe_lakes.py -- run this FIRST.

Dumps the real schema of every lake the kinematic engines need, so the
field mapping is established from what is there rather than guessed.
Prints one line per key path with an example value.

Usage:
    python probe_lakes.py
    python probe_lakes.py path/to/some_lake.jsonl      # single lake
"""

import sys
from pathlib import Path
from kish_lake_io import load_jsonl, key_inventory

DEFAULT = [
    "./lakes_kishlattice/inputs_promoted/p2_orbital_radius_promoted.jsonl",
    "./lakes_kishlattice/inputs_promoted/l1_gwtc_promoted.jsonl",
    "./lakes_kishlattice/inputs_promoted/g1_galaxy_kinematics_promoted.jsonl",
    "./lakes_kishlattice/inputs_promoted/b3_amino.jsonl",
]


def probe(path):
    p = Path(path)
    print("=" * 78)
    print(f" {p}")
    print("=" * 78)
    if not p.exists():
        print("  NOT FOUND\n")
        return
    recs = load_jsonl(p, p.name)
    print(f"  records: {len(recs):,}\n")
    inv = key_inventory(recs)
    for k, v in sorted(inv.items()):
        print(f"    {k:<46} = {v}")
    # show one whole record so nested structure is visible
    print("\n  --- first record, verbatim (truncated to 1200 chars) ---")
    import json
    print("  " + json.dumps(recs[0])[:1200])
    print()


if __name__ == "__main__":
    targets = sys.argv[1:] or DEFAULT
    for t in targets:
        probe(t)
