# ==============================================================================
# SCRIPT: Q8_Ionisation/scripts/build_lake.py
# PURPOSE: STRICT EMPIRICAL EXTRACTION (NIST ASD Deep Bore, No Synthetics)
# ==============================================================================
import urllib.request
import urllib.parse
import json
import re
from pathlib import Path

def build_lake():
    print("=" * 60)
    print(" Q8 BUILDING RAW LAKE (STRICT NIST EMPIRICAL ONLY) ".center(60))
    print("=" * 60)
    
    SCRIPT_DIR = Path(__file__).resolve().parent
    LAKE_DIR = SCRIPT_DIR.parent / "lake"
    RAW_PATH = LAKE_DIR / "q8_raw.jsonl"
    
    records = []
    
    # NIST API Pull - Stages I-XX
    url = "https://physics.nist.gov/cgi-bin/ASD/ie.pl?spectra=H-Rg+I-XX&units=1&format=1&order=0&at_num_out=on&sp_name_out=on&ion_charge_out=on"
    print("Contacting NIST Atomic Spectra Database (Deep Bore: Stages 1-20)...")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=120) as response:
            lines = response.read().decode('utf-8').split('\n')
            
        for line in lines:
            if '|' not in line or 'Ionization' in line or '---' in line: continue
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 4:
                atomic_num = parts[0]
                spectrum = parts[1]
                ion_charge = parts[2]
                ie_raw = parts[3]
                ie_clean = re.sub(r'[\(\[].*?[\)\]]', '', ie_raw).strip()
                
                if ie_clean and atomic_num.isdigit():
                    try:
                        records.append({
                            "atomic_number": int(atomic_num),
                            "spectrum": spectrum,
                            "ion_charge": int(ion_charge),
                            "ionisation_energy_ev": float(ie_clean),
                            "source": "NIST ASD (Strict Empirical)"
                        })
                    except ValueError: pass
        print(f" -> Extracted {len(records)} purely empirical records from NIST.")
    except Exception as e:
        print(f"CRITICAL ERROR: NIST fetch failed ({e}).")
        return

    with RAW_PATH.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")
            
    print(f"SUCCESS: Total {len(records)} pristine empirical records written to {RAW_PATH.name}")

if __name__ == "__main__":
    build_lake()