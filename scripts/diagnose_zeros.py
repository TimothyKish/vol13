import json
from pathlib import Path

def diagnose():
    promoted_dir = Path("lakes/inputs_promoted")
    
    failed_lakes = [
        "q8_ionisation_promoted.jsonl", "b1_chirality_promoted.jsonl", 
        "g1c_mass_promoted.jsonl", "k2a_spindown_promoted.jsonl", 
        "k2b_dm_promoted.jsonl", "k2c_age_promoted.jsonl", 
        "k2d_bfield_promoted.jsonl", "h1b_pt_lead_promoted.jsonl", 
        "h1c_pt_sublead_promoted.jsonl", "h1d_eta_promoted.jsonl",
        "g1a_radius_promoted.jsonl", "g1b_sersic_promoted.jsonl",
        "p_transit_promoted.jsonl", "p_ecc_promoted.jsonl", "p_incl_promoted.jsonl"
    ]
    
    print(f"{'LAKE':<35} | {'AVAILABLE DATA FIELDS (KEYS)'}")
    print("-" * 80)
    
    for filename in failed_lakes:
        filepath = promoted_dir / filename
        if filepath.exists():
            with filepath.open("r", encoding="utf-8") as f:
                first_line = f.readline()
                if first_line:
                    rec = json.loads(first_line)
                    # Filter out standard KishLattice schema keys to just see the data payloads
                    keys = [k for k in rec.keys() if k not in ["entity_id", "domain", "volume", "lake_id", "geometry_payload", "meta", "_raw_payload", "scalar_klc", "scalar_kls"]]
                    print(f"{filename:<35} | {keys}")
                else:
                    print(f"{filename:<35} | EMPTY FILE")
        else:
            print(f"{filename:<35} | FILE NOT FOUND")

if __name__ == "__main__":
    diagnose()