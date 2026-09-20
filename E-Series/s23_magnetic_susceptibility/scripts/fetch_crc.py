"""
KishLattice Sovereign Lake Fetcher
Target: s23 Magnetic Susceptibility (Molar)
Source: Wikipedia (Mirror of CRC Handbook of Chemistry and Physics)
"""

import pandas as pd
import requests
import os
import sys

def fetch_crc_wiki():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    raw_dir = os.path.join(script_dir, "..", "lake", "inputs_raw")
    out_csv = os.path.join(raw_dir, "crc_molar_susceptibilities.csv")
    os.makedirs(raw_dir, exist_ok=True)

    url = "https://en.wikipedia.org/wiki/Magnetic_susceptibility_of_the_elements_and_inorganic_compounds"
    print(f"Scraping CRC Handbook mirror from Wikipedia...\nURL: {url}")

    try:
        # Wikipedia blocks default Python scrapers. We must declare a polite User-Agent.
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status() # Will raise an exception for 403 or 404
        
        # Feed the raw HTML string into Pandas
        tables = pd.read_html(response.text)
        print(f"Found {len(tables)} tables on page. Extracting records...")

        records = []
        for df in tables:
            # We only want the tables that contain the actual chemical data
            if "Substance" in df.columns and "Formula" in df.columns:
                # Find the column containing the molar susceptibility (χmol)
                chi_cols = [c for c in df.columns if 'mol' in str(c).lower() or 'χ' in str(c)]
                if not chi_cols:
                    continue
                chi_col = chi_cols[0]

                for _, row in df.iterrows():
                    mat = str(row["Substance"]).strip()
                    form = str(row["Formula"]).strip()
                    raw_val = str(row[chi_col]).strip()

                    # Clean typography (Wiki uses unicode minus signs and citation brackets like [1])
                    clean_val = raw_val.split('[')[0].replace('−', '-').replace(',', '').strip()

                    try:
                        chi_val = float(clean_val)
                        records.append({
                            "material": mat,
                            "formula": form,
                            "type": "molar",
                            "chi_value_cgs": chi_val
                        })
                    except ValueError:
                        # Skip empty rows or malformed text
                        pass

        if not records:
            print("[ERROR] Could not extract any records. Table format may have changed.")
            sys.exit(1)

        # Convert to DataFrame and save to CSV
        final_df = pd.DataFrame(records)
        final_df.to_csv(out_csv, index=False)
        print(f"[OK] Successfully extracted {len(records)} molar susceptibilities.")
        print(f"[OK] Saved to: {out_csv}")

    except Exception as e:
        print(f"[ERROR] Failed to fetch or parse data.\nDetails: {e}")
        sys.exit(1)

if __name__ == "__main__":
    fetch_crc_wiki()