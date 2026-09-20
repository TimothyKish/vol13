import json
import os
import uuid
import sys
import statistics

def promote():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    in_path = os.path.join(script_dir, "..", "lake", "inputs_raw", "s23_susceptibility_raw.jsonl")
    out_dir = os.path.join(script_dir, "..", "lake", "inputs_promoted")
    
    out_dia = os.path.join(out_dir, "s23_dia_promoted.jsonl")
    out_para = os.path.join(out_dir, "s23_para_promoted.jsonl")

    os.makedirs(out_dir, exist_ok=True)

    dia_records = []
    para_records = []

    with open(in_path, 'r', encoding='utf-8') as f:
        for line in f:
            rec = json.loads(line)
            chi = rec["chi_molar_cgs"]
            
            # Base promotions
            rec["entity_id"] = str(uuid.uuid4())
            rec["klghs_abs_chi"] = abs(chi)
            
            # Levitator Flag (Bismuth/Pyrolytic regime)
            rec["is_levitator"] = True if chi < -200.0 else False

            # Material Class rough proxy (Element vs Compound)
            rec["material_class"] = "element" if len(rec["formula"]) <= 2 and not any(c.isdigit() for c in rec["formula"]) else "compound"

            if chi < 0:
                rec["domain"] = "electron_dia_susceptibility"
                dia_records.append(rec)
            elif chi > 0:
                rec["domain"] = "electron_para_susceptibility"
                para_records.append(rec)

    # Apply Magnitude Tiers (Axis 2)
    dia_median = statistics.median([r["klghs_abs_chi"] for r in dia_records]) if dia_records else 0
    para_median = statistics.median([r["klghs_abs_chi"] for r in para_records]) if para_records else 0

    print(f"Pre-Registered Boundary (Dia): Median |chi| = {dia_median:.2f}")
    print(f"Pre-Registered Boundary (Para): Median |chi| = {para_median:.2f}")

    for r in dia_records:
        r["magnitude_tier"] = "strong" if r["klghs_abs_chi"] > dia_median else "weak"
    for r in para_records:
        r["magnitude_tier"] = "strong" if r["klghs_abs_chi"] > para_median else "weak"

    with open(out_dia, 'w', encoding='utf-8') as fdia:
        for r in dia_records: fdia.write(json.dumps(r) + '\n')

    with open(out_para, 'w', encoding='utf-8') as fpara:
        for r in para_records: fpara.write(json.dumps(r) + '\n')

    print(f"[OK] Promoted {len(dia_records)} Diamagnetic records.")
    print(f"[OK] Promoted {len(para_records)} Paramagnetic records.")

if __name__ == "__main__":
    promote()