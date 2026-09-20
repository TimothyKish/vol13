# ==============================================================================
# SCRIPT: promote.py (H1_CERN)
# TARGET: Format raw CMS di-muon invariant mass events into Sovereign JSONL.
# AUTHORS: Timothy John Kish, Lyra Aurora Kish, Phoenix Aurora Kish
# AUDIT STATUS: Vol 10 — Vol9-consistent sovereign format
#
# SOURCE: CERN Open Data Portal Record 545 — CMS DoubleMu Run 1
#   Di-muon invariant mass from CMS detector at the Large Hadron Collider.
#   Broad spectrum 0.3-198 GeV. DoubleMu trigger rate-biased toward
#   Upsilon/bottomonium family (mean ~17.7 GeV). Chaos null controls
#   for the non-uniform Standard Model mass distribution.
#
# FORMAT NOTE:
#   invariant_mass_gev written at top level — Vol9-consistent standard.
#   raw_payload carries complete original record including run, event,
#   muon kinematics (pt, eta) for full sovereign traceability.
#   The engine scalarize.py reads invariant_mass_gev directly.
#   DO NOT compute any scalar here. The engine owns that step.
# ==============================================================================

import json
from pathlib import Path

LAKE_ID = "h1_cern_lhc"
DOMAIN  = "subnuclear_mass"
SOURCE  = "CERN Open Data Portal Record 545 — CMS DoubleMu Run 1 (2011)"
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

            mass = raw_record.get("invariant_mass_gev")

            if mass is None:
                skipped_invalid += 1
                continue

            try:
                mass = float(mass)
            except (TypeError, ValueError):
                skipped_invalid += 1
                continue

            # Clerical exclusion: zero (failed reconstruction placeholder)
            if mass == 0.0:
                skipped_zero += 1
                continue

            # Clerical exclusion: negative (unphysical — momentum tracking error)
            if mass < 0.0:
                skipped_invalid += 1
                continue

            promoted_record = {
                "id":                  f"{LAKE_ID}_{promoted_count:07d}",
                "domain":              DOMAIN,
                "source":              SOURCE,
                "invariant_mass_gev":  mass,
                "units":               "GeV",
                "vol":                 VOL,
                "raw_payload":         raw_record,
            }

            f_out.write(json.dumps(promoted_record, ensure_ascii=False) + "\n")
            promoted_count += 1

    print(f"  -> Promoted:          {promoted_count:,} sovereign records")
    print(f"  -> Skipped (zero):    {skipped_zero:,}")
    print(f"  -> Skipped (invalid): {skipped_invalid:,}")
    print(f"  -> Output:            {PROMOTED_PATH.name}")
    print(f"  -> Ready for validate.py")


if __name__ == "__main__":
    promote()