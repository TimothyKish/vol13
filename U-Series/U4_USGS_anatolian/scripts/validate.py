# ==============================================================================
# SCRIPT: validate.py (U-Series — seismic temporal)
# TARGET: Litmus gate for seismic temporal interval lakes.
# AUTHORS: Timothy John Kish, Lyra Aurora Kish, Phoenix Aurora Kish
# AUDIT STATUS: Vol 10 sovereign validation — Vol9-consistent standard
#
# LITMUS STANDARD: stdev / span < 0.28
#   Computed on RAW measurement values (interval_days in days).
#   This matches the Vol 9 validation standard applied to all prior lakes.
#   The litmus catches degenerate distributions where all values cluster
#   at a single point (stdev/span near zero) or the formula produces
#   a constant output. It does not measure the scalar distribution.
#
# NOTE ON SCALAR-SPACE LITMUS:
#   Computing stdev/span on Kish scalar values is more rigorous since
#   the chaos null operates in scalar space. However that approach requires
#   threshold recalibration against all Vol 9 lakes. Deferred to Vol 11.
#   For Vol 10 consistency this validate.py measures raw values.
#
# USAGE: Set LAKE_ID per lake and run from scripts/ folder.
#   U1: LAKE_ID = "u1_usgs_san_andreas"
#   U2: LAKE_ID = "u2_usgs_cascadia"
#   U3: LAKE_ID = "u3_usgs_japan_trench"
#   U4: LAKE_ID = "u4_usgs_anatolian"
# ==============================================================================

import json
import math
from pathlib import Path

# SET THIS PER LAKE
LAKE_ID = "u4_usgs_anatolian"

DOMAIN        = "seismic_temporal"
FIELD         = "interval_days"
LITMUS_LIMIT  = 0.28

SCRIPT_DIR    = Path(__file__).resolve().parent
LAKE_DIR      = SCRIPT_DIR.parent / "lake"
PROMOTED_PATH = LAKE_DIR / f"{LAKE_ID}_promoted.jsonl"


def validate():
    print(f"\n[{LAKE_ID.upper()}] Running Litmus Validation...")
    print(f"  Field:         {FIELD} (raw values — Vol9-consistent standard)")
    print(f"  Litmus limit:  stdev/span < {LITMUS_LIMIT}")

    if not PROMOTED_PATH.exists():
        print(f"  [ERROR] Promoted lake not found: {PROMOTED_PATH}")
        return

    values    = []
    malformed = 0
    missing   = 0
    invalid   = 0

    with PROMOTED_PATH.open("r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                malformed += 1
                continue

            val = record.get(FIELD)
            if val is None:
                missing += 1
                continue
            try:
                fval = float(val)
            except (TypeError, ValueError):
                invalid += 1
                continue
            if fval <= 0:
                invalid += 1
                continue
            values.append(fval)

    total = len(values)
    if total == 0:
        print(f"  [FAIL] No valid values. Malformed:{malformed} Missing:{missing} Invalid:{invalid}")
        return

    v_min  = min(values)
    v_max  = max(values)
    v_span = v_max - v_min
    v_mean = sum(values) / total
    v_var  = sum((x - v_mean) ** 2 for x in values) / total
    v_std  = math.sqrt(v_var)
    ratio  = v_std / v_span if v_span > 0 else float('inf')

    print()
    print(f"  Results (raw {FIELD} values):")
    print(f"    Total valid records:  {total:,}")
    print(f"    Malformed lines:      {malformed:,}")
    print(f"    Missing field:        {missing:,}")
    print(f"    Invalid values:       {invalid:,}")
    print(f"    Min:                  {v_min:.6f} days")
    print(f"    Max:                  {v_max:.6f} days")
    print(f"    Span:                 {v_span:.6f} days")
    print(f"    Mean:                 {v_mean:.6f} days")
    print(f"    StDev:                {v_std:.6f} days")
    print(f"    StDev / Span:         {ratio:.4f}")
    print()

    if ratio < LITMUS_LIMIT:
        print(f"  LITMUS: PASS ({ratio:.4f} < {LITMUS_LIMIT})")
        print(f"  Lake cleared for admission to volumes.json.")
    else:
        print(f"  LITMUS: FAIL ({ratio:.4f} >= {LITMUS_LIMIT})")
        print(f"  Investigate before enabling in pipeline.")


if __name__ == "__main__":
    validate()