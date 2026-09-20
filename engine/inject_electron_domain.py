#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inject_electron_domain.py  —  add the 'domain' field to the two electron promoted
lakes so scalarize.py can route them (it reads record.get("domain")).

The working lakes (s2, b5, etc.) carry a top-level "domain" field; the electron
lakes were promoted without it. This makes them conform to the same record shape.

NON-DESTRUCTIVE: backs up each file to *.predomain_bak before rewriting.
Touches ONLY the two electron lakes. No engine change, no config change.

Run from the Sister Papers root:
    python engine/inject_electron_domain.py
"""
import json, os, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMOTED = os.path.join(ROOT, "lakes", "inputs_promoted")

# lake file -> domain to inject (matches volumes.json)
TARGETS = {
    "L_fermi_velocity_promoted.jsonl":  "quantum_kinematic",
    "L_emission_nist_promoted.jsonl":   "quantum_transitional",
    "L_igrf_promoted.jsonl":            "geomagnetic",
}

def inject(filename, domain):
    path = os.path.join(PROMOTED, filename)
    if not os.path.exists(path):
        print(f"  [SKIP] {filename} not found")
        return
    backup = path + ".predomain_bak"
    if not os.path.exists(backup):
        shutil.copy2(path, backup)
        print(f"  backed up -> {os.path.basename(backup)}")
    # read all, add domain, write back
    out_lines = []
    n = 0; already = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("domain") == domain:
                already += 1
            rec["domain"] = domain          # inject / overwrite to canonical
            out_lines.append(json.dumps(rec))
            n += 1
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out_lines) + "\n")
    print(f"  [{filename}] domain='{domain}' set on {n} records "
          f"({already} already had it)")

def main():
    print("Injecting 'domain' into electron promoted lakes...")
    for fn, dom in TARGETS.items():
        inject(fn, dom)
    print("\nDone. Re-run: python engine/run_pipeline.py --skip-figures")
    print("Watch unify stage for: [L_fermi_velocity] ... nonzero=21  and")
    print("                       [L_emission_nist] ... nonzero=189,330")
    print("                       [L_igrf] ... nonzero=195")

if __name__ == "__main__":
    main()