"""
KishLattice Sovereign Lake Builder
Target: s18 Compton Recoil Electrons
Source: IAEA Livechart REST API (Gamma -> Compton Edge)
"""

import urllib.request
import csv
import json
import os
import sys
import concurrent.futures
from io import StringIO

URL_NUCLIDES = "https://www-nds.iaea.org/relnsd/v0/data?fields=ground_states&nuclides=all"
URL_DECAY = "https://www-nds.iaea.org/relnsd/v0/data?fields=decay_rads&nuclides={}&rad_types=g"

FLOOR_TARGET = 5000
ME_EV = 510998.95  # Electron rest mass in eV

def fetch_data(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'KishLattice-Sovereign-Probe/1.0'})
    try:
        # Added errors='replace' to prevent encoding crashes from weird byte responses
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.read().decode('utf-8', errors='replace')
    except Exception:
        return ""

def process_nuclide(nuclide):
    try:
        url = URL_DECAY.format(nuclide)
        csv_data = fetch_data(url)
        
        # If the server rate-limits us with an HTML error page, skip it
        if not csv_data or "<html" in csv_data.lower():
            return []
        
        records = []
        reader = csv.DictReader(StringIO(csv_data))
        if not reader.fieldnames:
            return []
            
        for row in reader:
            try:
                # URL already guarantees rad_types=g. Just grab the energy.
                energy_str = row.get('energy', row.get('energy_keV', '0'))
                if not energy_str:
                    continue
                    
                gamma_kev = float(energy_str)
                gamma_ev = gamma_kev * 1000.0
                
                if gamma_ev > 0:
                    # Calculate the maximum Compton recoil energy (Compton Edge)
                    compton_edge_ev = (2 * (gamma_ev ** 2)) / (ME_EV + 2 * gamma_ev)
                    
                    records.append({
                        "nuclide": nuclide,
                        "gamma_ev": gamma_ev,
                        "energy_ev": compton_edge_ev,
                        "intensity": row.get('intensity', ''),
                        "source": "IAEA_Livechart_API_Compton_Derived"
                    })
            except ValueError:
                continue
        return records
    except Exception as e:
        # If anything goes catastrophically wrong with this specific nuclide, drop it and survive.
        return []

def build_lake():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    raw_dir = os.path.join(script_dir, "..", "lake", "inputs_raw")
    out_path = os.path.join(raw_dir, "s18_compton_electrons.jsonl")
    os.makedirs(raw_dir, exist_ok=True)

    print("Stage 1: Fetching master nuclide index from IAEA...")
    index_csv = fetch_data(URL_NUCLIDES)
    if not index_csv:
        print("[ERROR] Failed to fetch nuclide index.")
        sys.exit(1)

    nuclides = []
    reader = csv.DictReader(StringIO(index_csv))
    for row in reader:
        z, n, symbol = row.get('z', '').strip(), row.get('n', '').strip(), row.get('symbol', '').strip()
        if z and n and symbol:
            nuclides.append(f"{int(z) + int(n)}{symbol.lower()}")

    print(f"Stage 2: Fetching Gamma transitions for {len(nuclides)} nuclides to calculate Compton recoil...")
    all_recoil_records = []
    
    # Dropped to 5 workers to respect IAEA rate limits
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(process_nuclide, nuc): nuc for nuc in nuclides}
        for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
            all_recoil_records.extend(future.result())
            if i % 500 == 0 or i == len(nuclides):
                print(f"  ...scanned {i}/{len(nuclides)} nuclides. Generated {len(all_recoil_records)} Compton recoils.")

    n = len(all_recoil_records)
    print(f"\n[OK] Extracted {n} valid Compton recoil energies.")

    with open(out_path, 'w', encoding='utf-8') as f:
        for rec in all_recoil_records:
            f.write(json.dumps(rec) + '\n')

    print(f"[OK] Wrote JSONL lake to {out_path}")

if __name__ == "__main__":
    build_lake()