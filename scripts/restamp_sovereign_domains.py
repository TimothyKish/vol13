# ==============================================================================
# SCRIPT: scripts/restamp_sovereign_domains.py
# PURPOSE: Un-merge weak lakes by asserting domain sovereignty.
# ==============================================================================
import json
from pathlib import Path

def restamp():
    print("=" * 60)
    print(" RESTAMPING SOVEREIGN DOMAINS ".center(60))
    print("=" * 60)
    
    promoted_dir = Path(__file__).resolve().parent.parent / "lakes" / "inputs_promoted"
    
    # Map the files to their true sovereign domains
    fixes = {
        "b1_chirality_promoted.jsonl": "biology_chirality",
        "q2_molecular_geometry_promoted.jsonl": "quantum_molecular_geometry",
        "q3_molecular_vibration_promoted.jsonl": "quantum_molecular_vibration",
        "q8_ionisation_promoted.jsonl": "atomic_ionisation"
    }

    for filename, new_domain in fixes.items():
        filepath = promoted_dir / filename
        if not filepath.exists():
            print(f"SKIPPED: {filename} not found.")
            continue

        with filepath.open("r", encoding="utf-8") as f:
            lines = f.readlines()

        count = 0
        with filepath.open("w", encoding="utf-8") as f:
            for line in lines:
                if not line.strip(): continue
                rec = json.loads(line)
                # Overwrite the generic domain with the sovereign domain
                rec["domain"] = new_domain
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                count += 1
                
        print(f"SUCCESS: Restamped {count} records in {filename} to -> '{new_domain}'")

if __name__ == "__main__":
    restamp()