# ==============================================================================
# SCRIPT: build_lake.py (U4_USGS_anatolian)
# TARGET: Pull M>=5.0 events from 1973 to 2025 for North Anatolian Fault.
#         Calculate the temporal gap (interval_days) between consecutive events.
# AUTHORS: Timothy John Kish & Lyra Aurora Kish
# ==============================================================================

import requests
import json
from pathlib import Path

USGS_API_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
FAULT_NAME = "u4_usgs_anatolian"

LAKE_DIR = Path(__file__).resolve().parent.parent / "lake"
LAKE_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = LAKE_DIR / f"{FAULT_NAME}_raw.jsonl"

def build():
    print(f"\n[{FAULT_NAME.upper()}] Initiating API pull from USGS...")
    params = {
        "format": "geojson",
        "minmagnitude": 5.0,
        "starttime": "1973-01-01",
        "endtime": "2025-01-01",
        "minlatitude": 38.0, "maxlatitude": 42.5,
        "minlongitude": 26.0, "maxlongitude": 44.0,
        "orderby": "time-asc", 
        "limit": 20000 
    }

    response = requests.get(USGS_API_URL, params=params, timeout=30)
    response.raise_for_status()
    features = response.json().get("features", [])
    
    total = len(features)
    print(f"  -> Retrieved {total} events.")
    if total < 2: return

    written, excluded = 0, 0
    with OUT_PATH.open("w", encoding="utf-8") as f:
        for i in range(1, total):
            prev_ms = features[i-1]["properties"]["time"]
            curr_ms = features[i]["properties"]["time"]
            interval_days = (curr_ms - prev_ms) / 86400000.0
            
            if interval_days == 0.0:
                excluded += 1
                continue
                
            raw_record = {
                "event_id_current": features[i]["id"],
                "event_id_previous": features[i-1]["id"],
                "time_current_ms": curr_ms,
                "time_previous_ms": prev_ms,
                "interval_days": interval_days,
                "magnitude_current": features[i]["properties"]["mag"],
                "place_current": features[i]["properties"]["place"],
                "coordinates_current": features[i]["geometry"]["coordinates"]
            }
            f.write(json.dumps(raw_record, ensure_ascii=False) + "\n")
            written += 1

    print(f"  -> Lake built: {OUT_PATH.name} ({written} intervals, {excluded} excluded)")

if __name__ == "__main__":
    build()