"""
KishLattice Sovereign Lake Builder
Target: s22 Conversion Electrons
Source: IAEA Livechart REST API (Two-Stage Parallel Live Fetch)
"""

import urllib.request
import csv
import json
import os
import sys
import concurrent.futures
from io import StringIO

URL_NUCLIDES = "https://www-nds.iaea.org/relnsd/v0/data?fields=ground_states&nuclides=all"
URL_DECAY = "https://www-nds.iaea.org/relnsd/v0/data?fields=decay_rads&nuclides={}&rad_types=e"

FLOOR_TARGET = 5000

def fetch_data(url):
    # The IAEA API occasionally drops requests without a User-Agent
    req = urllib.request.Request(url, headers={'User-Agent': 'KishLattice-Sovereign-Probe/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.read().decode('utf-8')
    except Exception:
        return ""

def process_nuclide(nuclide):
    url = URL_DECAY.format(nuclide)
    csv_data = fetch_data(url)
    if not csv_data:
        return []
    
    records = []
    # The API returns CSV text. We parse it in memory.
    reader = csv.DictReader(StringIO(csv_data))
    if not reader.fieldnames:
        return []
        
    for row in reader:
        # IAEA returns both Auger ('a') and Conversion ('ce') under rad_types=e
        rad_type = row.get('type', row.get('radiation', '')).strip().lower()
        
        if rad_type == 'ce':
            try:
                # IAEA provides energy in keV. We convert to eV for the kinematic scalar.
                energy_kev = float(row.get('energy', 0))
                energy_ev = energy_kev * 1000.0
                
                if energy_ev > 0:
                    records.append({
                        "nuclide": nuclide,
                        "energy_ev": energy_ev,
                        "intensity": row.get('intensity', ''),
                        "source": "IAEA_Livechart_API"
                    })
            except ValueError:
                continue
    return records

def build_lake():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    raw_dir = os.path.join(script_dir, "..", "lake", "inputs_raw")
    raw_csv_path = os.path.join(raw_dir, "iaea_conversion_electrons_raw.csv")
    out_path = os.path.join(raw_dir, "s22_conversion_electrons.jsonl")
    
    os.makedirs(raw_dir, exist_ok=True)

    print("Stage 1: Fetching master nuclide index from IAEA...")
    index_csv = fetch_data(URL_NUCLIDES)
    if not index_csv:
        print("[ERROR] Failed to fetch nuclide index. Check internet connection.")
        sys.exit(1)

    nuclides = []
    reader = csv.DictReader(StringIO(index_csv))
    for row in reader:
        z = row.get('z', '').strip()
        n = row.get('n', '').strip()
        symbol = row.get('symbol', '').strip()
        if z and n and symbol:
            mass = int(z) + int(n)
            # IAEA API requires nuclide formatted as mass+symbol (e.g., '135xe')
            nuclide_id = f"{mass}{symbol.lower()}"
            nuclides.append(nuclide_id)

    total_nuclides = len(nuclides)
    print(f"Discovered {total_nuclides} total nuclides.")
    print("Stage 2: Beginning parallel fetch for Conversion Electrons (CE)...")
    print("This requires ~3,500 rapid API calls. ETA: 1-2 minutes. Do not interrupt...")

    all_ce_records = []
    
    # Use ThreadPoolExecutor to prevent sequential blocking. 10 workers is polite but fast.
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_nuclide, nuc): nuc for nuc in nuclides}
        completed = 0
        for future in concurrent.futures.as_completed(futures):
            completed += 1
            result = future.result()
            all_ce_records.extend(result)
            
            if completed % 500 == 0 or completed == total_nuclides:
                print(f"  ...scanned {completed}/{total_nuclides} nuclides. Found {len(all_ce_records)} CE records so far.")

    n = len(all_ce_records)
    print(f"\n[OK] Extracted {n} total valid Conversion Electron energies.")

    if n < FLOOR_TARGET:
        print(f"[WARNING] Extracted count ({n}) is below the fleet floor of {FLOOR_TARGET}.")
    else:
        print(f"[SUCCESS] Density clears the {FLOOR_TARGET} minimum floor.")

    # Write the raw CSV audit trail
    if all_ce_records:
        with open(raw_csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=all_ce_records[0].keys())
            writer.writeheader()
            writer.writerows(all_ce_records)

    # Write the JSONL lake
    with open(out_path, 'w', encoding='utf-8') as f:
        for rec in all_ce_records:
            f.write(json.dumps(rec) + '\n')

    print(f"[OK] Wrote raw audit trail to {raw_csv_path}")
    print(f"[OK] Wrote JSONL lake to {out_path}")

if __name__ == "__main__":
    build_lake()