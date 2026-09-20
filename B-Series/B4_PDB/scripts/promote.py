# ==============================================================================
# SCRIPT: promote.py (B4_PDB)
# TARGET: Format raw protein backbone dihedral angles into Sovereign JSONL.
# AUTHORS: Timothy John Kish, Lyra Aurora Kish, Phoenix Aurora Kish
# AUDIT STATUS: Vol 10 — Vol9-consistent sovereign format
#
# SOURCE: Richardson Lab Top8000 — RCSB PDB validation reports
#   ~8,000 non-redundant protein chains, resolution <= 2.0 Angstrom.
#   Top8000 chain list from Richardson Lab GitHub (11-year-old static file).
#   Phi/psi Ramachandran dihedral angles extracted from GZIP validation XML.
#   See B4_PDB_README.md for full build methodology and source documentation.
#
# SOVEREIGN INTEGRITY NOTE:
#   Angles are SIGNED (-180 to +180 degrees). The signed value is the
#   physically correct measurement. It is preserved exactly as recorded.
#   The absolute value is NOT taken here. It is applied in the engine's
#   scalarize_biology_backbone() handler only.
#   This separation is the sovereign guarantee: the raw measurement is
#   preserved, and the transformation is owned by the engine.
#
# FORMAT NOTE:
#   angle_degrees written at top level — Vol9-consistent standard.
#   raw_payload carries complete original record including pdb_id, chain,
#   resnum, resname, angle_type for full sovereign traceability.
#   The engine scalarize.py reads angle_degrees and applies abs() internally.
#   DO NOT compute any scalar here. The engine owns that step.
# ==============================================================================

import json
from pathlib import Path

LAKE_ID = "b4_pdb_protein"
DOMAIN  = "biology_backbone"
SOURCE  = "Richardson Lab Top8000 non-redundant chains — RCSB PDB validation reports (resolution <= 2.0A)"
VOL     = 10

SCRIPT_DIR    = Path(__file__).resolve().parent
LAKE_DIR      = SCRIPT_DIR.parent / "lake"
RAW_PATH      = LAKE_DIR / f"{LAKE_ID}_raw.jsonl"
PROMOTED_PATH = LAKE_DIR / f"{LAKE_ID}_promoted.jsonl"


def promote():
    print(f"\n[{LAKE_ID.upper()}] Initiating Sovereign Promotion...")
    print(f"  Note: angle_degrees preserved SIGNED. abs() applied in engine only.")

    if not RAW_PATH.exists():
        print(f"  [ERROR] Raw lake not found at: {RAW_PATH}")
        return

    promoted_count   = 0
    skipped_missing  = 0
    skipped_invalid  = 0

    with RAW_PATH.open("r", encoding="utf-8") as f_in, \
         PROMOTED_PATH.open("w", encoding="utf-8") as f_out:

        for line_num, line in enumerate(f_in, 1):
            if not line.strip():
                continue

            try:
                raw_record = json.loads(line)
            except json.JSONDecodeError:
                print(f"  [WARN] Malformed JSON line {line_num}. Skipping.")
                skipped_invalid += 1
                continue

            angle = raw_record.get("angle_degrees")

            if angle is None:
                skipped_missing += 1
                continue

            try:
                angle = float(angle)
            except (TypeError, ValueError):
                skipped_invalid += 1
                continue

            # Physical bounds check: dihedral angles must be -180 to +180
            if not (-180.0 <= angle <= 180.0):
                skipped_invalid += 1
                continue

            promoted_record = {
                "id":            f"{LAKE_ID}_{promoted_count:07d}",
                "domain":        DOMAIN,
                "source":        SOURCE,
                "angle_degrees": angle,          # SIGNED — abs() in engine only
                "units":         "degrees",
                "vol":           VOL,
                "raw_payload":   raw_record,
            }

            f_out.write(json.dumps(promoted_record, ensure_ascii=False) + "\n")
            promoted_count += 1

            if promoted_count % 500_000 == 0:
                print(f"  ... {promoted_count:,} records promoted ...")

    print(f"  -> Promoted:          {promoted_count:,} sovereign records")
    print(f"  -> Skipped (missing): {skipped_missing:,}")
    print(f"  -> Skipped (invalid): {skipped_invalid:,}")
    print(f"  -> Output:            {PROMOTED_PATH.name}")
    print(f"  -> Ready for validate.py")


if __name__ == "__main__":
    promote()