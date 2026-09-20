# ==============================================================================
# SCRIPT: validate.py (H1_CERN)
# TARGET: Litmus gate for CMS di-muon invariant mass lake.
# AUTHORS: Timothy John Kish, Lyra Aurora Kish, Phoenix Aurora Kish
# AUDIT STATUS: Vol 10 sovereign validation — Vol9-consistent standard
#
# LITMUS STANDARD: stdev / span < 0.28
#   Computed on RAW invariant_mass_gev values (in GeV).
#   Matches the Vol 9 validation standard applied to all prior lakes.
#
# EXPECTED BEHAVIOUR:
#   The di-muon mass distribution is NOT uniform. The DoubleMu trigger
#   preferentially captures Upsilon/bottomonium resonances (9-10 GeV),
#   producing a right-skewed distribution with a dominant peak near 17 GeV
#   and a long tail toward 198 GeV. This is Standard Model physics, not
#   a scalarization artifact. The chaos null is built from the same
#   non-uniform distribution and controls for this correctly.
#   A moderate stdev/span ratio is expected given the resonance structure.
# ==============================================================================

import json
import math
from pathlib import Path

LAKE_ID       = "h1_cern_lhc"
DOMAIN        = "subnuclear_mass"
FIELD         = "invariant_mass_gev"
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
    print(f"    Min:                  {v_min:.4f} GeV")
    print(f"    Max:                  {v_max:.4f} GeV")
    print(f"    Span:                 {v_span:.4f} GeV")
    print(f"    Mean:                 {v_mean:.4f} GeV")
    print(f"    StDev:                {v_std:.4f} GeV")
    print(f"    StDev / Span:         {ratio:.4f}")
    print()

    if ratio < LITMUS_LIMIT:
        print(f"  LITMUS: PASS ({ratio:.4f} < {LITMUS_LIMIT})")
        print(f"  Note: Non-uniform distribution expected (DoubleMu trigger bias).")
        print(f"  Chaos null controls for Standard Model resonance structure.")
        print(f"  Lake cleared for admission to volumes.json.")
    else:
        print(f"  LITMUS: FAIL ({ratio:.4f} >= {LITMUS_LIMIT})")
        print(f"  Investigate before enabling in pipeline.")


if __name__ == "__main__":
    validate()