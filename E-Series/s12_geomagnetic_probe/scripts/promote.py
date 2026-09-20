import json
import os

RAW_IN_PATH = "../lake/raw/igrf13_raw.jsonl"
PROMOTED_OUT_PATH = "../lake/promoted/L_igrf_promoted.jsonl"

def promote_lake():
    print("[PROMOTE] Standardizing L_igrf for KLGHS pipeline...")
    os.makedirs(os.path.dirname(PROMOTED_OUT_PATH), exist_ok=True)
    
    promoted_count = 0
    with open(RAW_IN_PATH, 'r') as infile, open(PROMOTED_OUT_PATH, 'w') as outfile:
        for line in infile:
            raw = json.loads(line.strip())
            
            # KLGHS tests absolute geometric magnitude
            amplitude_nT = abs(raw["value_nT_2020"])
            
            # Construct the sovereign record
            promoted_record = {
                "harmonic_type": raw["type"],
                "degree_n": raw["n"],
                "order_m": raw["m"],
                "raw_value_nT": raw["value_nT_2020"],
                "amplitude_nT": amplitude_nT,
                "source": raw["source"],
                "klghs_natural_unit": "nT",
                "klghs_transform": "log_standard"
            }
            
            outfile.write(json.dumps(promoted_record) + '\n')
            promoted_count += 1
            
    print(f"[PROMOTE] Successfully standardized {promoted_count} records to absolute 1 nT units.")
    print(f"[PROMOTE] Promoted lake ready at: {PROMOTED_OUT_PATH}")

if __name__ == "__main__":
    promote_lake()