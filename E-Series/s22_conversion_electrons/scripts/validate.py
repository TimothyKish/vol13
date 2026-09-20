"""
KishLattice Sovereign Lake Validator
Target: L_conversion_electrons_promoted
Action: Verifies schema, domain constraints, and physics bounds for both real and scramble lakes.
"""

import json
import os
import sys

def validate_lake(filepath, expected_domain):
    if not os.path.exists(filepath):
        print(f"[FAIL] Promoted lake not found: {filepath}")
        return False

    print(f"\nValidating {os.path.basename(filepath)}...")

    count = 0
    err_domain = 0
    err_physics = 0
    velocities = []

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            rec = json.loads(line)
            count += 1
            
            # Check domain
            if rec.get("domain") != expected_domain:
                err_domain += 1
                
            # Check velocity (must be a positive float)
            vel = rec.get("velocity_ms")
            if not isinstance(vel, (int, float)) or vel <= 0:
                err_physics += 1
            else:
                velocities.append(vel)

    if err_domain > 0 or err_physics > 0:
        print(f"[FAIL] Validation rejected.")
        print(f"  Missing/Bad Domain: {err_domain}")
        print(f"  Missing/Bad Velocity: {err_physics}")
        return False

    print(f"[OK] Validation PASSED.")
    print(f"  Total Records: {count}")
    if velocities:
        # Prevent max() from crashing on massive arrays by using min/max
        v_min, v_max = min(velocities), max(velocities)
        v_mean = sum(velocities)/len(velocities)
        print(f"  Velocity Range: {v_min:.2f} m/s to {v_max:.2f} m/s")
        print(f"  Mean Velocity:  {v_mean:.2f} m/s")
    
    return True

def validate():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # We validate the final files sitting in the main engine folder
    real_path = os.path.join(script_dir, "..", "..", "..", "lakes", "inputs_promoted", "L_conversion_electrons_promoted.jsonl")
    scramble_path = os.path.join(script_dir, "..", "..", "..", "lakes", "inputs_promoted", "L_conversion_scramble_ctrl_promoted.jsonl")

    real_ok = validate_lake(real_path, "electron_conversion_kinematic")
    scramble_ok = validate_lake(scramble_path, "electron_conversion_scramble_ctrl")

    if real_ok and scramble_ok:
        print("\n[SUCCESS] LAKES ARE READY FOR MAIN ENGINE STITCHING.")
    else:
        sys.exit(1)

if __name__ == "__main__":
    validate()