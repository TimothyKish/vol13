import json
from pathlib import Path

def clone_wrongbox(parent_filename, wrongbox_filename, wrongbox_domain):
    promoted_dir = Path("lakes/inputs_promoted")
    parent_path = promoted_dir / parent_filename
    wrongbox_path = promoted_dir / wrongbox_filename
    
    if not parent_path.exists():
        print(f"[SKIP] Parent not found: {parent_filename}")
        return

    count = 0
    with parent_path.open("r", encoding="utf-8") as fin, \
         wrongbox_path.open("w", encoding="utf-8") as fout:
        for line in fin:
            if not line.strip(): continue
            rec = json.loads(line)
            rec["domain"] = wrongbox_domain
            rec["lake_id"] = wrongbox_filename.replace("_promoted.jsonl", "")
            
            # THE MONDY FIX: Strip existing scalars to force intentional recalculation
            rec.pop("scalar_klc", None)
            rec.pop("scalar_kls", None)
            rec.pop("scalar_invariant", None)

            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
            count += 1
            
    print(f"[SUCCESS] Cloned {count} records -> {wrongbox_filename} (Scalars stripped for {wrongbox_domain})")

if __name__ == "__main__":
    print("Building Independent Wrongbox Lakes (Scalars Stripped)...")
    clone_wrongbox("p1_orbital_periods_promoted.jsonl", "p1_wrongbox_promoted.jsonl", "orbital_wrongbox")
    clone_wrongbox("k2_pulsar_periods_promoted.jsonl", "k2_wrongbox_promoted.jsonl", "stellar_wrongbox")
    clone_wrongbox("s2_stellar_kinematics_promoted.jsonl", "s2_wrongbox_promoted.jsonl", "kinematic_wrongbox")
    clone_wrongbox("materials_promoted.jsonl", "mat_wrongbox_promoted.jsonl", "materials_wrongbox")