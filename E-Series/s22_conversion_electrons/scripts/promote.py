import json
import os
import uuid
import sys

def promote():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    in_path = os.path.join(script_dir, "..", "lake", "inputs_raw", "s22_conversion_electrons.jsonl")
    out_dir = os.path.join(script_dir, "..", "lake", "inputs_promoted")
    out_path = os.path.join(out_dir, "s22_conversion_electrons_promoted.jsonl")

    if not os.path.exists(in_path):
        print(f"[ERROR] Raw lake not found: {in_path}")
        sys.exit(1)

    os.makedirs(out_dir, exist_ok=True)
    
    count = 0
    with open(in_path, 'r', encoding='utf-8') as fin, \
         open(out_path, 'w', encoding='utf-8') as fout:
        for line in fin:
            rec = json.loads(line)
            rec["entity_id"] = str(uuid.uuid4())
            rec["domain"] = "electron_conversion_kinematic"
            fout.write(json.dumps(rec) + '\n')
            count += 1

    print(f"[OK] Promoted {count} records to {out_path}")

if __name__ == "__main__":
    promote()