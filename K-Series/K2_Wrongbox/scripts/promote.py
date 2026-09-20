# ==============================================================================
# SCRIPT: promote.py (K2 Pulsar Wrongbox)
# PURPOSE: Applies the WRONG dimensionality to the K2 Pulsar Periods lake.
# ==============================================================================
import json
import uuid
import csv
from datetime import datetime, timezone
from pathlib import Path

DOMAIN = "stellar_wrongbox"
LAKE_ID = "k2_wrongbox"
TARGET_FIELD = "P0_ms"

SCRIPT_DIR = Path(__file__).resolve().parent
# Pointing straight to the pristine raw ATNF CSV
RAW_PATH = SCRIPT_DIR.parents[1] / "K2_PulsarPeriods" / "lake" / "atnf_pulsars_raw.csv"

# THE FIX: parents[2] properly resolves to the Vol11 root directory!
PROMOTED_DIR = SCRIPT_DIR.parents[2] / "lakes" / "inputs_promoted"
PROMOTED_PATH = PROMOTED_DIR / f"{LAKE_ID}_promoted.jsonl"

def promote():
    print("=" * 60)
    print(f" {LAKE_ID.upper()} PROMOTION SCRIPT ".center(60))
    print("=" * 60)
    
    if not RAW_PATH.exists():
        print(f"ERROR: Raw CSV not found at {RAW_PATH}")
        return
        
    count = 0
    now_ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    
    with RAW_PATH.open("r", encoding="utf-8") as fin, PROMOTED_PATH.open("w", encoding="utf-8") as fout:
        reader = csv.DictReader(fin)
        for row in reader:
            raw_val = row.get("P0")
            
            # Specifically handle ATNF's empty strings and asterisks
            if raw_val is not None and str(raw_val).strip() not in ("", "*"):
                try:
                    # Clean the string, convert to float, then convert seconds to ms
                    clean_val = float(str(raw_val).strip()) * 1000.0
                    if clean_val <= 0: 
                        continue
                    
                    promoted_rec = {
                        "entity_id": str(uuid.uuid4()),
                        "domain": DOMAIN,
                        "volume": 11,
                        "lake_id": LAKE_ID,
                        TARGET_FIELD: clean_val, 
                        "geometry_payload": {"coordinates": [], "dimensionality": 1, "geometry_type": "scalar"},
                        "meta": {"source": "ATNF Pulsars (FALSIFICATION RUN)", "ingest_timestamp": now_ts, "sovereign": True},
                        "_raw_payload": dict(row) # Preserve the CSV row as a dict
                    }
                    fout.write(json.dumps(promoted_rec, ensure_ascii=False) + "\n")
                    count += 1
                except ValueError:
                    pass
                    
    print(f"SUCCESS: {count:,} records promoted to {PROMOTED_PATH.name}")

if __name__ == "__main__":
    promote()