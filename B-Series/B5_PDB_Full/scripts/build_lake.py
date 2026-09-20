# ==============================================================================
# SCRIPT: build_lake.py (B4_PDB)
# TARGET: Pull Phi/Psi Ramachandran angles from RCSB Protein Data Bank.
#         Uses the PDB Search API v2 and Validation XML endpoints.
# AUTHORS: Timothy John Kish & Lyra Aurora Kish
# AUDIT STATUS: Pre-Promote Raw Build (FULL CATALOG PULL)
# ==============================================================================

import requests
import json
import gzip
import xml.etree.ElementTree as ET
from pathlib import Path

LAKE_NAME = "b4_pdb_protein"

# RCSB PDB APIs
SEARCH_API_URL = "https://search.rcsb.org/rcsbsearch/v2/query"
VALIDATION_URL_TEMPLATE = "https://files.rcsb.org/pub/pdb/validation_reports/{mid}/{pdb_id}/{pdb_id}_validation.xml.gz"

# Relative pathing
SCRIPT_DIR = Path(__file__).resolve().parent
LAKE_DIR = SCRIPT_DIR.parent / "lake"
LAKE_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = LAKE_DIR / f"{LAKE_NAME}_raw.jsonl"

def get_high_res_pdb_ids():
    """Queries PDB for ALL X-ray structures with resolution <= 2.5A"""
    print(f"  -> Querying PDB Search API for ALL high-resolution structures (this may take a moment)...")
    query = {
        "query": {
            "type": "terminal",
            "service": "text",
            "parameters": {
                "attribute": "rcsb_entry_info.resolution_combined",
                "operator": "less_or_equal",
                "value": 2.5
            }
        },
        "request_options": {
            "return_all_hits": True # The Lake Hound is officially unleashed
        },
        "return_type": "entry"
    }
    
    response = requests.post(SEARCH_API_URL, json=query)
    response.raise_for_status()
    data = response.json()
    return [item["identifier"].lower() for item in data.get("result_set", [])]

def build():
    print(f"\n[{LAKE_NAME.upper()}] Initiating FULL CATALOG extraction from RCSB PDB...")
    
    try:
        pdb_ids = get_high_res_pdb_ids()
        print(f"  -> Retrieved {len(pdb_ids):,} PDB IDs for full production lake.")
        print(f"  -> WARNING: This will process gigabytes of validation XMLs. Let it coast.")
    except Exception as e:
        print(f"  [ERROR] PDB Search API failed: {e}")
        return

    written = 0
    excluded_missing = 0
    excluded_unphysical = 0
    download_failures = 0

    with OUT_PATH.open("w", encoding="utf-8") as f:
        for idx, pdb_id in enumerate(pdb_ids):
            if idx % 500 == 0 and idx > 0:
                print(f"     ... processed {idx:,}/{len(pdb_ids):,} structures ({written:,} angles extracted) ...")
                
            mid = pdb_id[1:3]
            xml_url = VALIDATION_URL_TEMPLATE.format(mid=mid, pdb_id=pdb_id)
            
            try:
                resp = requests.get(xml_url, timeout=10)
                if resp.status_code != 200:
                    download_failures += 1
                    continue
                    
                # Decompress the GZIP payload in memory
                xml_content = gzip.decompress(resp.content)
                root = ET.fromstring(xml_content)
                
                # Find all ModelledSubgroup elements (amino acid residues)
                for subgroup in root.findall(".//ModelledSubgroup"):
                    phi_str = subgroup.get("phi")
                    psi_str = subgroup.get("psi")
                    
                    if not phi_str or not psi_str:
                        excluded_missing += 1
                        continue
                        
                    phi, psi = float(phi_str), float(psi_str)
                    
                    # Unphysical exclusion (angles must be between -180 and 180)
                    if not (-180.0 <= phi <= 180.0) or not (-180.0 <= psi <= 180.0):
                        excluded_unphysical += 1
                        continue
                        
                    base_record = {
                        "pdb_id": pdb_id.upper(),
                        "chain": subgroup.get("chain"),
                        "resnum": subgroup.get("resnum"),
                        "resname": subgroup.get("resname")
                    }
                    
                    # Phi Record
                    rec_phi = dict(base_record)
                    rec_phi["angle_type"] = "phi"
                    rec_phi["angle_degrees"] = phi
                    f.write(json.dumps(rec_phi, ensure_ascii=False) + "\n")
                    written += 1
                    
                    # Psi Record
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
        print(f"  -> Skipped {download_failures:,} structures (validation file missing/unreadable).")

if __name__ == "__main__":
    build()