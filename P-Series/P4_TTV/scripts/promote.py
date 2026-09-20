# ==============================================================================
# SCRIPT: promote.py (P4_TTV)
# TARGET: Format raw Kepler transit timing variations into Sovereign JSONL.
# AUTHORS: Timothy John Kish, Lyra Aurora Kish, Phoenix Aurora Kish
# AUDIT STATUS: Vol 10 — Vol9-consistent sovereign format
#
# SOURCE: VizieR J/ApJS/225/9 Holczer et al. 2016 — table3
#   NASA TAP and legacy workspace API were both offline during build.
#   Sovereign redirect to VizieR immutable catalog. Documented in README.
#   O-C column = Transit Timing Variation (Observed minus Calculated).
#   Values are in minutes natively. Already absolute magnitude.
#
# FORMAT NOTE:
#   ttv_absolute_minutes written at top level — Vol9-consistent standard.
#   raw_payload carries complete original record including signed raw_ttv_minutes.
#   The signed value is preserved in raw_payload for sovereign integrity.
#   The engine scalarize.py reads ttv_absolute_minutes directly.
#   DO NOT compute any scalar here. The engine owns that step.
# ==============================================================================

import json
from pathlib import Path

LAKE_ID = "p4_ttv"
DOMAIN  = "orbital_ttv"
SOURCE  = "VizieR J/ApJS/225/9 Holczer et al. 2016 — Kepler TTV table3 (O-C column)"
VOL     = 10

SCRIPT_DIR    = Path(__file__).resolve().parent
LAKE_DIR      = SCRIPT_DIR.parent / "lake"
RAW_PATH      = LAKE_DIR / f"{LAKE_ID}_raw.jsonl"
PROMOTED_PATH = LAKE_DIR / f"{LAKE_ID}_promoted.jsonl"


def promote():
    print(f"\n[{LAKE_ID.upper()}] Initiating Sovereign Promotion...")

    if not RAW_PATH.exists():
        print(f"  [ERROR] Raw lake not found at: {RAW_PATH}")
        return

    promoted_count  = 0
    skipped_zero    = 0
    skipped_invalid = 0

    with RAW_PATH.open("r", encoding="utf-8") as f_in, \
         PROMOTED_PATH.open("w", encoding="utf-8") as f_out:

        for line_num, line in enumerate(f_in, 1):
            if not line.strip():
                continue

            try:
                raw_record = json.loads(line)
            except json.JSONDecodeError:
                print(f"  [WARN] Malformed JSON line {line_num}. Skipping.")
                continue

            ttv_abs = raw_record.get("ttv_absolute_minutes")

            if ttv_abs is None:
                skipped_invalid += 1
                continue

            try:
                ttv_abs = float(ttv_abs)
            except (TypeError, ValueError):
                skipped_invalid += 1
                continue

            # Zero placeholder — already excluded in build but guard here
            if ttv_abs == 0.0:
                skipped_zero += 1
                continue

            # Unphysical guard — already excluded in build but guard here
            if ttv_abs > 1440.0:
                skipped_invalid += 1
                continue

            if ttv_abs < 0:
                skipped_invalid += 1
                continue

            promoted_record = {
                "id":                   f"{LAKE_ID}_{promoted_count:07d}",
                "domain":               DOMAIN,
                "source":               SOURCE,
                "ttv_absolute_minutes": ttv_abs,
                "units":                "minutes",
                "vol":                  VOL,
                "raw_payload":          raw_record,
            }

            f_out.write(json.dumps(promoted_record, ensure_ascii=False) + "\n")
            promoted_count += 1

    print(f"  -> Promoted:        {promoted_count:,} sovereign records")
    print(f"  -> Skipped (zero):  {skipped_zero:,}")
    print(f"  -> Skipped (other): {skipped_invalid:,}")
    print(f"  -> Output:          {PROMOTED_PATH.name}")
    print(f"  -> Ready for validate.py")


if __name__ == "__main__":
    promote()