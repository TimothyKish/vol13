# ==============================================================================
# SCRIPT: build_lake.py (B4_PDB)
# TARGET: Pull Phi/Psi Ramachandran angles from Richardson Lab Top8000.
#         Uses a local list of non-redundant, high-resolution chains.
# AUTHORS: Timothy John Kish & Lyra Aurora Kish
# AUDIT STATUS: Pre-Promote Raw Build (Top8000 Curated Subset)
# ==============================================================================

import requests
import json
import gzip
import re
import xml.etree.ElementTree as ET
from pathlib import Path

LAKE_NAME = "b4_pdb_protein"
DATASET_TAG = "Top8000_Richardson_2.0A"

VALIDATION_URL_TEMPLATE = "https://files.rcsb.org/pub/pdb/validation_reports/{mid}/{pdb_id}/{pdb_id}_validation.xml.gz"

SCRIPT_DIR = Path(__file__).resolve().parent
LAKE_DIR = SCRIPT_DIR.parent / "lake"
LAKE_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = LAKE_DIR / f"{LAKE_NAME}_raw.jsonl"
CHAIN_LIST_PATH = SCRIPT_DIR / "top8000_chains.txt"

def load_top8000_chains():
    """
    Reads the local Top8000 chain list. 
    Accepts various formats: '1ABC A', '1abc_A', '1abc,A', or '1abcA'
    """
    if not CHAIN_LIST_PATH.exists():
        print(f"\n[ERROR] Missing {CHAIN_LIST_PATH.name}!")
        print("  -> Please download the chain list from Top8000 (Duke) or PISCES.")
        print("  -> Save it as 'top8000_chains.txt' in this scripts folder.")
        print("  -> Format per line: PDBID CHAIN (e.g., '1MBO A' or '1mbo_A')")
        return None

    chains_to_process = []
    with open(CHAIN_LIST_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"): continue
            
            # Smart parsing for PDB/Chain pairs
            matches = re.findall(r'[a-zA-Z0-9]+', line)
            if len(matches) >= 2:
                pdb_id = matches[0][:4].lower()
                chain_id = matches[1]
                chains_to_process.append((pdb_id, chain_id))
            elif len(matches) == 1 and len(matches[0]) >= 5:
                # Format like 1ABCA
                pdb_id = matches[0][:4].lower()
                chain_id = matches[0][4:]
                chains_to_process.append((pdb_id, chain_id))
                
    return chains_to_process

def build():
    print(f"\n[{LAKE_NAME.upper()}] Initiating extraction for Top8000 Curated Chains...")
    
    chain_targets = load_top8000_chains()
    if not chain_targets:
        return
        
    print(f"  -> Loaded {len(chain_targets):,} specific PDB/Chain targets from local list.")

    written = 0
    excluded_missing = 0
    excluded_unphysical = 0
    download_failures = 0

    with OUT_PATH.open("w", encoding="utf-8") as f:
        for idx, (pdb_id, target_chain) in enumerate(chain_targets):
            if idx % 100 == 0 and idx > 0:
                print(f"     ... processed {idx:,}/{len(chain_targets):,} chains ({written:,} angles extracted) ...")
                
            mid = pdb_id[1:3]
            xml_url = VALIDATION_URL_TEMPLATE.format(mid=mid, pdb_id=pdb_id)
            
            try:
                resp = requests.get(xml_url, timeout=10)
                if resp.status_code != 200:
                    download_failures += 1
                    continue
                    
                xml_content = gzip.decompress(resp.content)
                root = ET.fromstring(xml_content)
                
                for subgroup in root.findall(".//ModelledSubgroup"):
                    # MONDY DIRECTIVE: Only extract the specifically designated chain
                    if subgroup.get("chain") != target_chain:
                        continue
                        
                    phi_str = subgroup.get("phi")
                    psi_str = subgroup.get("psi")
                    
                    if not phi_str or not psi_str:
                        excluded_missing += 1
                        continue
                        
                    phi, psi = float(phi_str), float(psi_str)
                    
                    if not (-180.0 <= phi <= 180.0) or not (-180.0 <= psi <= 180.0):
                        excluded_unphysical += 1
                        continue
                        
                    base_record = {
                        "dataset": DATASET_TAG,
                        "pdb_id": pdb_id.upper(),
                        "chain": target_chain,
                        "resnum": subgroup.get("resnum"),
                        "resname": subgroup.get("resname")
                    }
                    
                    # Phi Record - MONDY DIRECTIVE: Keep raw signed angle!
                    rec_phi = dict(base_record)
                    rec_phi["angle_type"] = "phi"
                    rec_phi["angle_degrees"] = phi
                    f.write(json.dumps(rec_phi, ensure_ascii=False) + "\n")
                    written += 1
                    
                    # Psi Record - MONDY DIRECTIVE: Keep raw signed angle!
                    rec_psi = dict(base_record)
                    rec_psi["angle_type"] = "psi"
                    rec_psi["angle_degrees"] = psi
                    f.write(json.dumps(rec_psi, ensure_ascii=False) + "\n")
                    written += 1
                    
            except Exception:
                download_failures += 1
                continue

    print(f"  -> Lake built: {OUT_PATH.name}")
    print(f"  -> Total angles recorded: {written:,}")
    print(f"  -> Excluded {excluded_missing:,} residues (missing phi/psi).")
    print(f"  -> Excluded {excluded_unphysical:,} residues (out of bounds).")
    if download_failures > 0:
        print(f"  -> Skipped {download_failures:,} chains (validation file missing/unreadable).")

if __name__ == "__main__":
    build()