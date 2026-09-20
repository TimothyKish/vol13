import json
import os

# Ashcroft & Mermin, Solid State Physics (1976)
# Table 2.1: Fermi velocities for elemental free-electron metals (v_F in 10^8 cm/s)
ashcroft_mermin_data = [
    {"element": "Li", "Z": 3, "v_F_10_8_cm_s": 1.29},
    {"element": "Na", "Z": 11, "v_F_10_8_cm_s": 1.07},
    {"element": "K", "Z": 19, "v_F_10_8_cm_s": 0.86},
    {"element": "Rb", "Z": 37, "v_F_10_8_cm_s": 0.81},
    {"element": "Cs", "Z": 55, "v_F_10_8_cm_s": 0.75},
    {"element": "Cu", "Z": 29, "v_F_10_8_cm_s": 1.57},
    {"element": "Ag", "Z": 47, "v_F_10_8_cm_s": 1.39},
    {"element": "Au", "Z": 79, "v_F_10_8_cm_s": 1.40},
    {"element": "Be", "Z": 4, "v_F_10_8_cm_s": 2.25},
    {"element": "Mg", "Z": 12, "v_F_10_8_cm_s": 1.58},
    {"element": "Ca", "Z": 20, "v_F_10_8_cm_s": 1.28},
    {"element": "Sr", "Z": 38, "v_F_10_8_cm_s": 1.18},
    {"element": "Ba", "Z": 56, "v_F_10_8_cm_s": 1.06},
    {"element": "Al", "Z": 13, "v_F_10_8_cm_s": 2.02},
    {"element": "Ga", "Z": 31, "v_F_10_8_cm_s": 1.74},
    {"element": "In", "Z": 49, "v_F_10_8_cm_s": 1.74},
    {"element": "Tl", "Z": 81, "v_F_10_8_cm_s": 1.65},
    {"element": "Sn", "Z": 50, "v_F_10_8_cm_s": 1.90},
    {"element": "Pb", "Z": 82, "v_F_10_8_cm_s": 1.83},
    {"element": "Bi", "Z": 83, "v_F_10_8_cm_s": 1.96},
    {"element": "Sb", "Z": 51, "v_F_10_8_cm_s": 1.89}
]

RAW_OUT_PATH = "../lake/raw/ashcroft_mermin_fermi_velocities.jsonl"

def build_raw_lake():
    print("[BUILD] Generating L_fermi_velocity raw lake...")
    os.makedirs(os.path.dirname(RAW_OUT_PATH), exist_ok=True)
    
    with open(RAW_OUT_PATH, 'w') as f:
        for record in ashcroft_mermin_data:
            record["source_table"] = "Ashcroft & Mermin Table 2.1"
            f.write(json.dumps(record) + '\n')
            
    print(f"[BUILD] Complete. {len(ashcroft_mermin_data)} elemental conductors written to {RAW_OUT_PATH}")

if __name__ == "__main__":
    build_raw_lake()