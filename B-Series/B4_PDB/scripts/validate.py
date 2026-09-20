# ==============================================================================
# SCRIPT: validate.py (B4_PDB)
# TARGET: Litmus gate for Richardson Lab Top8000 protein backbone angle lake.
# AUTHORS: Timothy John Kish, Lyra Aurora Kish, Phoenix Aurora Kish
# AUDIT STATUS: Vol 10 sovereign validation — Vol9-consistent standard
#
# LITMUS STANDARD: stdev / span < 0.28
#   Computed on absolute values of raw angle_degrees (in degrees).
#   abs() taken here for litmus consistency — the scalarize engine also
#   applies abs() before the log formula.
#   Matches the Vol 9 validation standard applied to all prior lakes.
#
# EXPECTED BEHAVIOUR:
#   The Ramachandran phi/psi distribution is NOT uniform. It clusters in
#   two main allowed regions: alpha helix (phi ~-60, psi ~-45) and beta
#   sheet (phi ~-120, psi ~+135). The forbidden region (phi > 0 for
#   non-glycine) is almost entirely absent.
#   After taking abs(), the distribution spans 0 to 180 degrees.
#   A moderate stdev/span ratio is expected reflecting the two-cluster
#   structure. The chaos null controls for the non-uniform Ramachandran
#   distribution exactly.
# ==============================================================================

import json
import math
from pathlib import Path

LAKE_ID       = "b4_pdb_protein"
DOMAIN        = "biology_backbone"
FIELD         = "angle_degrees"
LITMUS_LIMIT  = 0.28

SCRIPT_DIR    = Path(__file__).resolve().parent
LAKE_DIR      = SCRIPT_DIR.parent / "lake"
PROMOTED_PATH = LAKE_DIR / f"{LAKE_ID}_promoted.jsonl"


def validate():
    print(f"\n[{LAKE_ID.upper()}] Running Litmus Validation...")
    print(f"  Field:         |{FIELD}| absolute values — Vol9-consistent standard")
    print(f"  Litmus limit:  stdev/span < {LITMUS_LIMIT}")
    print(f"  Note: This lake has 3.3M records. Validation will take ~30 seconds.")

    if not PROMOTED_PATH.exists():
        print(f"  [ERROR] Promoted lake not found: {PROMOTED_PATH}")
        return

    values    = []
    malformed = 0
    missing   = 0
    invalid   = 0
    count     = 0

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
                fval = abs(float(val))     # abs() consistent with engine handler
            except (TypeError, ValueError):
                invalid += 1
                continue

            values.append(fval)
            count += 1

            if count % 500_000 == 0:
                print(f"  ... {count:,} records read ...")

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
    print(f"  Results (|{FIELD}| absolute values):")
    print(f"    Total valid records:  {total:,}")
    print(f"    Malformed lines:      {malformed:,}")
    print(f"    Missing field:        {missing:,}")
    print(f"    Invalid values:       {invalid:,}")
    print(f"    Min:                  {v_min:.4f} degrees")
    print(f"    Max:                  {v_max:.4f} degrees")
    print(f"    Span:                 {v_span:.4f} degrees")
    print(f"    Mean:                 {v_mean:.4f} degrees")
    print(f"    StDev:                {v_std:.4f} degrees")
    print(f"    StDev / Span:         {ratio:.4f}")
    print()

    if ratio < LITMUS_LIMIT:
        print(f"  LITMUS: PASS ({ratio:.4f} < {LITMUS_LIMIT})")
        print(f"  Note: Non-uniform distribution expected (Ramachandran allowed regions).")
        print(f"  Chaos null controls for phi/psi clustering.")
        print(f"  Lake cleared for admission to volumes.json.")
    else:
        print(f"  LITMUS: FAIL ({ratio:.4f} >= {LITMUS_LIMIT})")
        print(f"  Investigate before enabling in pipeline.")


if __name__ == "__main__":
    validate()