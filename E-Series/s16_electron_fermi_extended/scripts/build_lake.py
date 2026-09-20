#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_lake.py (s16_electron_fermi_extended)
Pulls Fermi Energies (E_F) for conductive materials from the Materials Project API.
"""

import os
import json
try:
    from mp_api.client import MPRester
except ImportError:
    print("[!] ERROR: Please run 'pip install mp-api' first.")
    exit(1)

# Get a free API key at https://next-gen.materialsproject.org/api
API_KEY = os.environ.get("MP_API_KEY", "aHQ7sEIFtfimcD35Lgp0lFMOmj2O0Ex6") 
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "lake", "raw", "mp_fermi_raw.jsonl")

def main():
    if not API_KEY or API_KEY == "YOUR_MP_API_KEY_HERE":
        print("[!] ERROR: Please edit build_lake.py and insert your MP_API_KEY.")
        return

    print("[*] Connecting to Materials Project API...")
    records = []
    
    with MPRester(API_KEY) as mpr:
        # Query for all metals (band_gap == 0)
        docs = mpr.materials.summary.search(
            band_gap=(0.0, 0.0), 
            fields=["material_id", "formula_pretty", "efermi"]  # Fixed key here
        )
        
        for doc in docs:
            if doc.efermi is not None:  # Fixed property access here
                records.append({
                    "material_id": str(doc.material_id),
                    "formula": doc.formula_pretty,
                    "fermi_energy_ev": float(doc.efermi),
                    "source": "Materials Project API"
                })

    print(f"[*] Extracted {len(records)} raw Fermi Energies.")
    
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")
            
    print(f"[+] Raw lake written: {os.path.abspath(OUT_PATH)}")

if __name__ == "__main__":
    main()