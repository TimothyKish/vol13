import json, os, statistics, uuid

def promote():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    in_path = os.path.join(script_dir, "..", "lake", "inputs_raw", "s23_susceptibility_raw.jsonl")
    out_dir = os.path.join(script_dir, "..", "lake", "inputs_promoted")
    os.makedirs(out_dir, exist_ok=True)
    
    dia, para = [], []
    prov_dia, prov_para = {}, {}
    
    with open(in_path, 'r', encoding='utf-8') as f:
        for line in f:
            rec = json.loads(line)
            chi = rec["chi_molar_cgs"]
            rec["entity_id"] = str(uuid.uuid4())
            rec["klghs_abs_chi"] = abs(chi)
            rec["is_levitator"] = True if chi < -200.0 else False
            rec["material_class"] = "element" if len(rec["formula"]) <= 2 and not any(c.isdigit() for c in rec["formula"]) else "compound"
            prov = rec.get("provenance", "measured")
            
            if chi < 0:
                rec["domain"] = "electron_dia_susceptibility"
                dia.append(rec)
                prov_dia[prov] = prov_dia.get(prov, 0) + 1
            elif chi > 0:
                rec["domain"] = "electron_para_susceptibility"
                para.append(rec)
                prov_para[prov] = prov_para.get(prov, 0) + 1

    dia_med = statistics.median([r["klghs_abs_chi"] for r in dia]) if dia else 0
    para_med = statistics.median([r["klghs_abs_chi"] for r in para]) if para else 0
    for r in dia: r["magnitude_tier"] = "strong" if r["klghs_abs_chi"] > dia_med else "weak"
    for r in para: r["magnitude_tier"] = "strong" if r["klghs_abs_chi"] > para_med else "weak"
    
    with open(os.path.join(out_dir, "s23_dia_promoted.jsonl"), 'w', encoding='utf-8') as f:
        for r in dia: f.write(json.dumps(r) + '\n')
    with open(os.path.join(out_dir, "s23_para_promoted.jsonl"), 'w', encoding='utf-8') as f:
        for r in para: f.write(json.dumps(r) + '\n')

    print("\n" + "="*40)
    print(" MONDY POWER REPORT")
    print("="*40)
    print(f"DIA SUB-LAKE: n = {len(dia)}")
    for p, count in prov_dia.items(): print(f"  - Provenance [{p}]: {count}")
    print(f"\nPARA SUB-LAKE: n = {len(para)}")
    for p, count in prov_para.items(): print(f"  - Provenance [{p}]: {count}")
    print("="*40 + "\n")

if __name__ == "__main__": promote()