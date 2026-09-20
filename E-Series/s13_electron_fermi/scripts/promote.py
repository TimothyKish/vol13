import json
import os

RAW_IN_PATH = "../lake/raw/ashcroft_mermin_fermi_velocities.jsonl"
PROMOTED_OUT_PATH = "../lake/promoted/L_fermi_velocity_promoted.jsonl"

def promote_lake():
    print("[PROMOTE] Standardizing L_fermi_velocity for KLGHS pipeline...")
    os.makedirs(os.path.dirname(PROMOTED_OUT_PATH), exist_ok=True)
    
    promoted_count = 0
    with open(RAW_IN_PATH, 'r') as infile, open(PROMOTED_OUT_PATH, 'w') as outfile:
        for line in infile:
            raw_record = json.loads(line.strip())
            
            # Convert 10^8 cm/s to pure m/s (10^8 cm/s = 10^6 m/s)
            fermi_vel_ms = raw_record["v_F_10_8_cm_s"] * 1_000_000
            
            # Construct the sovereign KLGHS record
            promoted_record = {
                "element": raw_record["element"],
                "Z": raw_record["Z"],
                "fermi_velocity_ms": fermi_vel_ms,
                "source": raw_record["source_table"],
                "klghs_natural_unit": "m/s",
                "klghs_transform": "log_standard"
            }
            
            outfile.write(json.dumps(promoted_record) + '\n')
            promoted_count += 1
            
    print(f"[PROMOTE] Successfully standardized {promoted_count} records to 1 m/s natural units.")
    print(f"[PROMOTE] Promoted lake ready at: {PROMOTED_OUT_PATH}")

if __name__ == "__main__":
    promote_lake()