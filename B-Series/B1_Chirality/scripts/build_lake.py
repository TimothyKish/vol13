# ==============================================================================
# SCRIPT: B1_Chirality/scripts/build_lake.py
# PURPOSE: Inject a Curated Golden Dataset of Empirical Specific Rotations.
# ==============================================================================
import json
from pathlib import Path

def build_lake():
    print("=" * 60)
    print(" B1 BUILDING RAW LAKE (CURATED CHIRAL GOLDEN DATASET) ".center(60))
    print("=" * 60)
    
    LAKE_DIR = Path(__file__).resolve().parent.parent / "lake"
    LAKE_DIR.mkdir(parents=True, exist_ok=True)
    RAW_PATH = LAKE_DIR / "b1_raw.jsonl"
    
    # Curated Empirical Specific Rotations [alpha]_D at ~20C
    chiral_data = [
        # Standard Amino Acids (L/D pairs)
        ("L-Alanine", 1.8), ("D-Alanine", -1.8),
        ("L-Arginine", 12.5), ("D-Arginine", -12.5),
        ("L-Asparagine", -5.3), ("D-Asparagine", 5.3),
        ("L-Aspartic Acid", 25.0), ("D-Aspartic Acid", -25.0),
        ("L-Cysteine", 6.5), ("D-Cysteine", -6.5),
        ("L-Glutamine", 6.1), ("D-Glutamine", -6.1),
        ("L-Glutamic Acid", 31.2), ("D-Glutamic Acid", -31.2),
        ("L-Histidine", -38.5), ("D-Histidine", 38.5),
        ("L-Isoleucine", 12.4), ("D-Isoleucine", -12.4),
        ("L-Leucine", 15.1), ("D-Leucine", -15.1),
        ("L-Lysine", 13.5), ("D-Lysine", -13.5),
        ("L-Methionine", -30.0), ("D-Methionine", 30.0),
        ("L-Phenylalanine", -34.5), ("D-Phenylalanine", 34.5),
        ("L-Proline", -86.2), ("D-Proline", 86.2),
        ("L-Serine", -7.5), ("D-Serine", 7.5),
        ("L-Threonine", -28.5), ("D-Threonine", 28.5),
        ("L-Tryptophan", -33.7), ("D-Tryptophan", 33.7),
        ("L-Tyrosine", -10.0), ("D-Tyrosine", 10.0),
        ("L-Valine", 5.6), ("D-Valine", -5.6),
        
        # Sugars / Carbohydrates
        ("D-Glucose", 52.7), ("L-Glucose", -52.7),
        ("D-Fructose", -92.4), ("L-Fructose", 92.4),
        ("D-Galactose", 80.2), ("L-Galactose", -80.2),
        ("D-Mannose", 14.2), ("L-Mannose", -14.2),
        ("Sucrose", 66.5), ("Lactose", 55.4), ("Maltose", 130.4),
        ("D-Ribose", -23.7), ("D-Arabinose", -105.0), ("L-Arabinose", 105.0),
        ("D-Xylose", 18.8), ("L-Xylose", -18.8),
        
        # Terpenes / Essential Oils
        ("(+)-Limonene", 125.6), ("(-)-Limonene", -125.6),
        ("(+)-Carvone", 61.2), ("(-)-Carvone", -61.2),
        ("(+)-Menthol", 50.1), ("(-)-Menthol", -50.1),
        ("(+)-Pinene", 51.0), ("(-)-Pinene", -51.0),
        ("(+)-Camphor", 44.1), ("(-)-Camphor", -44.1),
        
        # Chiral Organics and Pharmaceuticals
        ("(+)-Tartaric Acid", 12.0), ("(-)-Tartaric Acid", -12.0),
        ("L-DOPA", -13.1), ("D-DOPA", 13.1),
        ("(+)-Ibuprofen", 54.5), ("(-)-Ibuprofen", -54.5),
        ("L-Epinephrine", -50.0), ("D-Epinephrine", 50.0),
        ("(+)-Naproxen", 66.0), ("(-)-Naproxen", -66.0),
        ("L-Ascorbic Acid", 20.5), ("D-Ascorbic Acid", -20.5),
        ("(+)-Amphetamine", 35.6), ("(-)-Amphetamine", -35.6)
    ]
    
    count = 0
    with RAW_PATH.open("w", encoding="utf-8") as f:
        for name, rotation in chiral_data:
            rec = {
                "molecule_name": name,
                "specific_rotation_deg": rotation,
                "source": "Standard Empirical References [alpha]_D"
            }
            f.write(json.dumps(rec) + "\n")
            count += 1
            
    print(f"SUCCESS: Wrote {count} highly-curated chiral records to {RAW_PATH.name}")

if __name__ == "__main__":
    build_lake()