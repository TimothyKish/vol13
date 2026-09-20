"""
KishLattice Sovereign Lake Builder
Target: s17 ARPES Bi2Se3
Source: Zenodo Record 12665275 (Hofmann Group)
Schema: Mapped to coords/kx, coords/ky, and data
"""

import os
import sys
import json
import requests
import h5py
import numpy as np

ZENODO_API = "https://zenodo.org/api/records/12665275"
FLOOR_TARGET = 5000

def build_lake():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    raw_dir = os.path.join(script_dir, "..", "lake", "inputs_raw")
    h5_path = os.path.join(raw_dir, "Bi2Se3_raw.h5")
    out_path = os.path.join(raw_dir, "s17_arpes_bi2se3.jsonl")
    os.makedirs(raw_dir, exist_ok=True)

    # 1. Sovereign Internet Fetch (Skip if already downloaded)
    if not os.path.exists(h5_path):
        print("Querying Zenodo API for Record 12665275...")
        response = requests.get(ZENODO_API).json()
        
        download_url = None
        for file_info in response.get('files', []):
            if 'Bi2Se3' in file_info['key']:
                download_url = file_info['links']['self']
                break
                
        if not download_url:
            print("[ERROR] Could not locate Bi2Se3 file in Zenodo manifest.")
            sys.exit(1)
            
        print(f"Downloading Bi2Se3 ARPES data from {download_url}...")
        with requests.get(download_url, stream=True) as r:
            r.raise_for_status()
            with open(h5_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"[OK] Downloaded to {h5_path}")
    else:
        print(f"Raw HDF5 already exists at {h5_path}. Skipping fetch.")

    # 2. Extract Data using exact schema
    print("Parsing HDF5 ARPES matrix...")
    records = []
    
    with h5py.File(h5_path, 'r') as f:
        # Load the 1D coordinate axes
        kx_vals = f['coords/kx'][:]
        ky_vals = f['coords/ky'][:]
        
        # Load the 3D intensity matrix (Energy x kx x ky)
        # Shape: (781, 438, 85)
        print("Loading 29-million point intensity matrix into memory...")
        Intensity = f['data'][:]

        # We only want the physical bands. Take the top 1% brightest pixels.
        print("Calculating 99th percentile threshold...")
        threshold = np.percentile(Intensity, 99)
        
        # Find indices where intensity exceeds threshold
        # indices[0] = energy, indices[1] = kx, indices[2] = ky
        indices = np.where(Intensity > threshold)
        
        print(f"Found {len(indices[0])} high-intensity electron hits. Mapping vectors...")
        for idx in range(len(indices[0])):
            kx = float(kx_vals[indices[1][idx]])
            ky = float(ky_vals[indices[2][idx]])
            
            # Calculate total absolute momentum vector magnitude k
            k_mag = float(np.sqrt(kx**2 + ky**2))
            
            if k_mag > 0:
                records.append({
                    "material": "Bi2Se3",
                    "momentum_k_inv_angstrom": k_mag,
                    "kx": kx,
                    "ky": ky,
                    "source": "Zenodo_12665275_ARPES"
                })

    n = len(records)
    print(f"\n[OK] Extracted {n} valid ARPES kinematic momentum vectors.")
    
    if n < FLOOR_TARGET:
        print(f"[WARNING] Count ({n}) is below the {FLOOR_TARGET} floor.")
    else:
        print(f"[SUCCESS] Density clears the {FLOOR_TARGET} minimum floor.")
        
    with open(out_path, 'w', encoding='utf-8') as f:
        for rec in records:
            f.write(json.dumps(rec) + '\n')
            
    print(f"[OK] Wrote JSONL lake to {out_path}")

if __name__ == "__main__":
    build_lake()