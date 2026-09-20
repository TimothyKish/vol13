"""
KishLattice Sovereign Lake Builder
Target: s19 Auger Electron Kinetic Energies
Source: NIST X-Ray/Auger Transition Database (Tab-Delimited ASCII)
"""

import json
import os
import sys

# Fleet target minimum density
FLOOR_TARGET = 5000  

def build_lake():
    # Resolve paths relative to the script location so it works universally
    script_dir = os.path.dirname(os.path.abspath(__file__))
    in_path = os.path.join(script_dir, "..", "lake", "inputs_raw", "nist_auger_raw.txt.txt")
    out_path = os.path.join(script_dir, "..", "lake", "inputs_raw", "s19_auger_electrons.jsonl")

    if not os.path.exists(in_path):
        print(f"[ERROR] Source file not found at: {in_path}")
        sys.exit(1)

    print(f"Ingesting NIST Auger ASCII data from {in_path}...")
    
    records = []
    
    with open(in_path, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()

    # 1. Find the header row (skip the preamble metadata)
    start_idx = 0
    for i, line in enumerate(lines):
        if line.startswith("Ele."):
            start_idx = i
            break
            
    if start_idx == 0 and not lines[0].startswith("Ele."):
        print("[ERROR] Could not locate the header row starting with 'Ele.'")
        sys.exit(1)

    headers = lines[start_idx].strip('\n').split('\t')
    
    # 2. Parse the data rows
    for line in lines[start_idx + 1:]:
        line = line.strip('\n')
        if not line:
            continue
            
        cols = line.split('\t')
        
        # Pad columns if the row is shorter than the header
        while len(cols) < len(headers):
            cols.append("")
            
        row = dict(zip(headers, cols))
        
        element = row.get('Ele.', '').strip()
        transition = row.get('Trans.', '').strip()
        
        # Energy extraction: Prioritize best empirical data
        energy_ev = None
        for col_name in ['Combined (eV)', 'Direct (eV)', 'Theory (eV)', 'Vapor (eV)']:
            val = row.get(col_name, '').strip()
            if val:
                try:
                    # Clean the value (NIST sometimes outputs "500.5 a" with a footnote letter)
                    val_clean = val.split()[0]
                    energy_ev = float(val_clean)
                    break # Found a valid energy, stop looking
                except ValueError:
                    continue
                    
        if element and transition and energy_ev is not None and energy_ev > 0:
            records.append({
                "element": element,
                "transition": transition,
                "energy_ev": energy_ev,
                "source": "NIST_Auger_ASCII"
            })

    # 3. Validation and Output
    n = len(records)
    print(f"Extracted {n} valid Auger transition energies.")

    if n < FLOOR_TARGET:
        print(f"[WARNING] Extracted count ({n}) is below the fleet floor of {FLOOR_TARGET}.")
        print("Proceeding, but flag this as a fragile puddle if it does not clear the ensemble gate.")
    else:
        print(f"[SUCCESS] Density clears the {FLOOR_TARGET} minimum floor.")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        for rec in records:
            f.write(json.dumps(rec) + '\n')

    print(f"[OK] Wrote {n} records to {out_path}")

if __name__ == "__main__":
    build_lake()