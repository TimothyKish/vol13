import requests

VIZIER_URL = "https://vizier.cds.unistra.fr/viz-bin/asu-tsv"

def sniff():
    print("Sniffing VizieR J/ApJS/225/9/table3...")
    params = {
        "-source": "J/ApJS/225/9/table3",
        "-out.max": "50", # Just grab the first 50 rows
    }
    
    response = requests.get(VIZIER_URL, params=params, stream=True)
    
    print("\n--- RAW VIZIER OUTPUT START ---")
    lines = response.text.splitlines()
    for i, line in enumerate(lines[:60]):
        # We replace actual tabs with a visible [TAB] marker so we can see the exact formatting
        visible_line = line.replace("\t", " [TAB] ")
        print(f"Line {i:02d}: {visible_line}")
    print("--- RAW VIZIER OUTPUT END ---\n")

if __name__ == "__main__":
    sniff()