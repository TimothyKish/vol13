import urllib.request
import json
import os

# NOAA restructured their directories and added a /coeffs/ folder.
URL = "https://www.ngdc.noaa.gov/IAGA/vmod/coeffs/igrf13coeffs.txt"
RAW_OUT_PATH = "../lake/raw/igrf13_raw.jsonl"

def build_raw_lake():
    print(f"[BUILD] Fetching IGRF-13 Gauss Coefficients from NOAA...")
    os.makedirs(os.path.dirname(RAW_OUT_PATH), exist_ok=True)
    
    # Beefed up User-Agent to bypass standard firewall blocks
    req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    
    records = []
    try:
        with urllib.request.urlopen(req) as response:
            lines = response.read().decode('utf-8').split('\n')
            
            # Find the column index for the 2020.0 epoch
            header_idx = -1
            for line in lines:
                if line.startswith("g/h"):
                    headers = line.split()
                    header_idx = headers.index("2020.0")
                    break
            
            if header_idx == -1:
                print("[!] Could not locate 2020.0 epoch column in header.")
                return

            for line in lines:
                parts = line.split()
                if len(parts) > 5 and parts[0] in ['g', 'h']:
                    records.append({
                        "type": parts[0],
                        "n": int(parts[1]),
                        "m": int(parts[2]),
                        "value_nT_2020": float(parts[header_idx]),
                        "source": "NOAA/IAGA IGRF-13"
                    })
                    
        with open(RAW_OUT_PATH, 'w') as f:
            for rec in records:
                f.write(json.dumps(rec) + '\n')
                
        print(f"[BUILD] Complete. {len(records)} harmonic coefficients written to {RAW_OUT_PATH}")

    except Exception as e:
        print(f"[!] Extraction failed: {e}")

if __name__ == "__main__":
    build_raw_lake()