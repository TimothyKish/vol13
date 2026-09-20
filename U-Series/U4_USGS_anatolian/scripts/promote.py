# ==============================================================================
# SCRIPT: promote.py (U4_USGS_anatolian)
# TARGET: Format raw seismic temporal intervals into the Sovereign JSONL format.
# AUTHORS: Timothy John Kish, Lyra Aurora Kish, Phoenix Aurora Kish
# AUDIT STATUS: Vol 10 — Corrected to Vol9-consistent sovereign format
#
# FORMAT NOTE:
#   The domain-specific measurement field (interval_days) is written at the
#   top level of the promoted record, matching the Vol 9 sovereign standard.
#   The raw_payload carries the complete original record unchanged.
#   The engine scalarize.py reads interval_days directly — no kish_field.
#   DO NOT compute any scalar here. The engine owns that step.
# ==============================================================================

import json
from pathlib import Path

LAKE_ID = "u4_usgs_anatolian"
DOMAIN  = "seismic_temporal"
SOURCE  = "USGS Earthquake Hazards Program FDSNWS — North Anatolian fault M>=5.0 depth 0-50km"
VOL     = 10

SCRIPT_DIR     = Path(__file__).resolve().parent
LAKE_DIR       = SCRIPT_DIR.parent / "lake"
RAW_PATH       = LAKE_DIR / f"{LAKE_ID}_raw.jsonl"
PROMOTED_PATH  = LAKE_DIR / f"{LAKE_ID}_promoted.jsonl"


def promote():
    print(f"\n[{LAKE_ID.upper()}] Initiating Sovereign Promotion...")

    if not RAW_PATH.exists():
        print(f"  [ERROR] Raw lake not found at: {RAW_PATH}")
        return

    promoted_count  = 0
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

            interval_days = raw_record.get("interval_days")

            if interval_days is None or interval_days <= 0:
                skipped_invalid += 1
                continue

            promoted_record = {
                "id":           f"{LAKE_ID}_{promoted_count:07d}",
                "domain":       DOMAIN,
                "source":       SOURCE,
                "interval_days": interval_days,
                "units":        "days",
                "vol":          VOL,
                "raw_payload":  raw_record,
            }

            f_out.write(json.dumps(promoted_record, ensure_ascii=False) + "\n")
            promoted_count += 1

    print(f"  -> Promoted:  {promoted_count:,} sovereign records")
    print(f"  -> Skipped:   {skipped_invalid:,} invalid intervals")
    print(f"  -> Output:    {PROMOTED_PATH.name}")
    print(f"  -> Ready for validate.py")


if __name__ == "__main__":
    promote()