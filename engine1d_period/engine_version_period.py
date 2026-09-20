#!/usr/bin/env python3
# ==============================================================================
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC. FOUNDER: Timothy John Kish
# Open for scientific testing / peer review. Cite "KishLattice 16/pi Initiative".
# ==============================================================================
#
# engine_version_period.py  --  Period-engine fingerprint (same method as the
# phase engine's engine_version.py, Vol 10). Five files fully determine period
# output. NOTE the slot list differs from the phase engine -- there is no chaos
# builder and no phase pinch; the statistic is self-contained in periodogram.py.
#
#   [0:32]    engine1d_period/logify.py
#   [32:64]   engine1d_period/periodogram.py
#   [64:96]   configs1d_period/logify.json
#   [96:128]  configs1d_period/harmonic_targets.json   (or shared configs/)
#
# Every period-engine run receipt carries this 128-char fingerprint. A change to
# the statistic, the field map, or the register family shows as a slot diff --
# the same trust mechanism that let Vol 13 trace the subnuclear_mass move to the
# log1p patch in one line.
# ==============================================================================
import hashlib, sys, argparse
from pathlib import Path
from datetime import datetime, timezone

SLOTS = [
    ("logify_py",          "engine1d_period", "logify.py"),
    ("periodogram_py",     "engine1d_period", "periodogram.py"),
    ("kish_period_io_py",  "engine1d_period", "kish_period_io.py"),
    ("logify_json",        "configs1d_period", "logify.json"),
    ("harmonic_targets",   "configs1d_period", "harmonic_targets.json"),
]

def _md5(p: Path) -> str:
    h = hashlib.md5()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def _base(base=None) -> Path:
    return Path(base) if base else Path(__file__).resolve().parent.parent

def compute(base=None) -> str:
    b = _base(base); segs = []
    for name, sub, fn in SLOTS:
        p = b / sub / fn
        if not p.exists():
            raise FileNotFoundError(f"period fingerprint requires {p} (slot {name})")
        segs.append(_md5(p))
    return "".join(segs)

def parse(v: str) -> dict:
    return {SLOTS[i][0]: v[i*32:(i+1)*32] for i in range(len(v)//32)}

def main():
    ap = argparse.ArgumentParser(description="KishLattice period-engine fingerprint")
    ap.add_argument("--verify", metavar="V"); ap.add_argument("--base")
    a = ap.parse_args()
    if a.verify:
        cur = compute(a.base)[:len(a.verify)]
        ok = cur == a.verify
        print("VERIFIED" if ok else "MISMATCH")
        if not ok:
            for k in parse(a.verify):
                if parse(a.verify)[k] != parse(cur).get(k): print("  changed:", k)
        sys.exit(0 if ok else 1)
    v = compute(a.base)
    print(v); print()
    for k, h in parse(v).items():
        lbl = next(f"{s}/{fn}" for n, s, fn in SLOTS if n == k)
        print(f"  {k:<20} {h}   ({lbl})")

if __name__ == "__main__":
    main()
