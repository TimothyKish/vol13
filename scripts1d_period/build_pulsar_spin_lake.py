#!/usr/bin/env python3
# ==============================================================================
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC. FOUNDER: Timothy John Kish
# Open for scientific testing / peer review. Cite "KishLattice 16/pi Initiative".
# ==============================================================================
#
# build_pulsar_spin_lake.py  --  single-population period-lake, no stitching.
#
# ATTRIBUTE: neutron-star rotation frequency (Hz). ONE population (ATNF pulsar
# catalogue), ONE attribute (spin frequency), ONE source. No unit-conversion
# seams, no cross-scale composition -- the honest single-population wide lake.
#
# PRE-REGISTRATION (filed before the run, Timothy + Atlas, 2026-09-10):
#   * register: UNKNOWN. The period engine's winning register is downstream of
#     sample support shape, so a guess tests the wrong thing.
#   * THE CLAIM IS INVARIANCE, NOT LOCATION. The falsifiable prediction is:
#     "whatever register wins, it survives bootstrap/split-half resampling AND
#      clears the look-elsewhere bar." If the register wanders under resampling
#      it was binning, not a lock -- and that is reported as the result.
#   * FULL population, no cut. Magnetars, MSPs, accreting -- all of it. If a
#     sub-population distorts the support, the histogram shows it; we do not
#     pre-exclude, because a cut is a selection choice we would have to justify.
#
# FIELD PRIORITY: F0 (spin frequency, Hz) where present; else 1/P0 (P0 in s).
# Reads the promoted lake if present, else the raw ATNF lake. Writes a period
# lake carrying raw x=frequency only (no modulus, no scalar -- period-engine
# contract). Domain tag: pulsar_spin.
#
# Run:  python engine1d_period/build_pulsar_spin_lake.py
# ==============================================================================
import json, math, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "lakes1d_period" / "inputs_promoted"
OUT = OUT_DIR / "L_pulsar_spin_promoted.jsonl"

# candidate sources, in order of preference (promoted first, then raw)
SOURCES = [
    ROOT / "lakes" / "inputs_promoted" / "k2_pulsar_periods_promoted.jsonl",
    ROOT / "K-Series" / "K2_PulsarPeriods" / "lake" / "atnf_pulsars_raw.csv",
    ROOT / "fresh_atnf_raw.jsonl",
]

def find_freq(rec):
    """Return spin frequency in Hz, or None. F0 first, then 1/P0."""
    def dig(keys):
        for k in keys:
            if k in rec:
                return rec[k]
            for cont in ("_raw_payload", "meta"):
                sub = rec.get(cont, {})
                if isinstance(sub, dict) and k in sub:
                    return sub[k]
        return None
    # F0 in Hz
    f0 = dig(["F0", "f0", "spin_frequency_hz", "freq_hz", "frequency"])
    if f0 is not None:
        try:
            v = float(f0)
            if v > 0 and math.isfinite(v):
                return v, "F0"
        except (TypeError, ValueError):
            pass
    # fall back to 1/P0, P0 in seconds (or ms -> detect)
    p0 = dig(["P0", "p0", "period_s", "spin_period_s", "p0_s"])
    if p0 is not None:
        try:
            v = float(p0)
            if v > 0 and math.isfinite(v):
                return 1.0 / v, "1/P0"
        except (TypeError, ValueError):
            pass
    p0ms = dig(["p0_ms", "period_ms"])
    if p0ms is not None:
        try:
            v = float(p0ms)
            if v > 0 and math.isfinite(v):
                return 1000.0 / v, "1/P0(ms)"
        except (TypeError, ValueError):
            pass
    return None, None

def load_csv(path):
    import csv
    rows = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows

def main():
    src = next((s for s in SOURCES if s.exists()), None)
    if src is None:
        print("[!] no pulsar source found. Looked for:")
        for s in SOURCES: print("   ", s)
        sys.exit(2)
    print(f"[*] source: {src}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    records = []
    if src.suffix == ".csv":
        records = load_csv(src)
    else:
        for line in open(src, encoding="utf-8"):
            line = line.strip()
            if line:
                try: records.append(json.loads(line))
                except json.JSONDecodeError: pass

    n_in = n_out = 0
    used = {"F0": 0, "1/P0": 0, "1/P0(ms)": 0}
    freqs = []
    with open(OUT, "w", encoding="utf-8") as wf:
        for i, rec in enumerate(records):
            n_in += 1
            f, how = find_freq(rec)
            if f is None:
                continue
            used[how] = used.get(how, 0) + 1
            freqs.append(f)
            wf.write(json.dumps({
                "entity_id": rec.get("entity_id", rec.get("PSRJ", rec.get("NAME", f"psr_{i}"))),
                "domain": "pulsar_spin",
                "lake_id": "L_pulsar_spin",
                "universal_hz": f,
                "meta": {"source": str(src.name), "derived_from": how,
                         "single_population": True, "stitched": False,
                         "prereg": "register UNKNOWN; claim is invariance not location"},
            }) + "\n")
            n_out += 1

    print(f"[*] {n_in:,} records in -> {n_out:,} pulsar_spin records out")
    print(f"    frequency source: {used}")
    if freqs:
        lnf = [math.log(x) for x in freqs]
        span = max(lnf) - min(lnf)
        print(f"    frequency bounds: {min(freqs):.4e} Hz .. {max(freqs):.4e} Hz")
        print(f"    raw log-span: {span:.2f} nat ({span/math.log(10):.1f} decades)")
        print(f"    (effective span + shape come from histogram_view; this is min-max only)")
    print(f"[*] written: {OUT}")
    print("\n  NEXT (pre-registered order):")
    print("    1. logify.json: add pulsar_spin -> field 'universal_hz', combine identity")
    print("    2. python engine1d_period/logify.py")
    print("    3. python engine1d_period/histogram_view.py lakes1d_period/logified/L_pulsar_spin_logified.jsonl")
    print("       -- SHAPE must read FILLED before the register means anything")
    print("    4. python engine1d_period/register_stability.py  (the invariance test)")

if __name__ == "__main__":
    main()