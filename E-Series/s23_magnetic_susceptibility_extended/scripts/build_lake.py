import csv, json, os

def build_lake():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    in_csv = os.path.join(script_dir, "..", "lake", "inputs_raw", "s23_merged_baseline.csv")
    out_jsonl = os.path.join(script_dir, "..", "lake", "inputs_raw", "s23_susceptibility_raw.jsonl")
    
    records = []
    with open(in_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append({
                "material": row["material"],
                "formula": row["formula"],
                "chi_molar_cgs": float(row["chi_value_cgs"]),
                "provenance": row.get("provenance", "measured"),
                "source": row["source"]
            })
    
    with open(out_jsonl, 'w', encoding='utf-8') as f:
        for r in records: f.write(json.dumps(r) + '\n')
    print(f"[OK] Wrote {len(records)} raw records to s23_susceptibility_raw.jsonl")

if __name__ == "__main__":
    build_lake()