# ==============================================================================
# SCRIPT: scripts/patch_1d_scalars.py
# PURPOSE: Pre-compute and inject scalar_klc to bypass the scalarize.py geometry trap.
# TARGETS: Q8 (Ionisation) and B1 (Chirality)
# ==============================================================================
import json
import math
from pathlib import Path

# KishLattice Universal Geometric Constant
K_GEO = 5.0929581789

def patch_lake(filename, field_name):
    promoted_path = Path(__file__).resolve().parent.parent / "lakes" / "inputs_promoted" / filename
    
    if not promoted_path.exists():
        print(f"[ERROR] Promoted file not found: {filename}")
        return

    # Read all existing records
    with promoted_path.open("r", encoding="utf-8") as f:
        lines = f.readlines()

    patched_count = 0
    with promoted_path.open("w", encoding="utf-8") as f:
        for line in lines:
            if not line.strip(): continue
            rec = json.loads(line)
            
            # Extract the raw 1D value
            val = rec.get(field_name, 0.0)
            
            # Apply the log_standard formula: log(1 + x) / log(k_geo)
            if val >= 0:
                scalar = math.log(1 + val) / math.log(K_GEO)
            else:
                scalar = 0.0 # Fallback for unexpected negative values, though abs() handles B1
            
            # Inject the legacy fields the engine is looking for
            rec["scalar_kls"] = scalar
            rec["scalar_klc"] = scalar
            
            # Save back to file
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            patched_count += 1
            
    print(f"[SUCCESS] Patched {patched_count} records in {filename} with explicit scalar_klc.")

if __name__ == "__main__":
    print("=" * 60)
    print(" INJECTING 1D SCALARS FOR ENGINE BYPASS ".center(60))
    print("=" * 60)
    
    patch_lake("q8_ionisation_promoted.jsonl", "ionisation_energy_ev")
    patch_lake("b1_chirality_promoted.jsonl", "specific_rotation_deg")