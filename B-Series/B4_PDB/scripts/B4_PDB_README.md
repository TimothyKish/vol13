# B4_PDB: Protein Backbone Ramachandran Angles
**Lake Build Log & Post-Mortem**
**Dataset:** Top8000 Curated Subset (Richardson Lab, Duke University)
**Date:** May 2026
**Architect:** Timothy John Kish
**Lake Hound:** Lyra Aurora Kish

## Overview
This document outlines the sourcing, extraction, and geometric processing of the `B4_PDB` sovereign lake. The target for this lake is the backbone dihedral angles ($\phi$ and $\psi$) of organic proteins. 

To ensure the highest scientific rigor, this lake does not blindly pull the entire Protein Data Bank (which contains massive experimental noise, low-resolution structures, and taxonomic redundancy). Instead, it targets the **Top8000** dataset—a gold-standard, curated list of non-redundant, high-resolution ($\leq 2.0\AA$), high-quality protein chains compiled by the Richardson Lab at Duke University.

## Data Sourcing: The 11-Year-Old Gem
Old World scientific infrastructure is prone to link rot and UI decay. While the original interactive web portals for the Top8000 have become difficult to navigate, the primary source data was securely committed to version control. 

The master list of non-redundant chains has been sitting untouched and perfectly preserved in the Richardson Lab's GitHub repository for 11 years. We bypass the decayed web UI and pull straight from the static repository.

### Reproducibility Instructions
To replicate the generation of the `top8000_chains.txt` seed file:
1. Navigate to the Richardson Lab reference repository:
   `https://github.com/rlabduke/reference_data/tree/master/Top8000`
2. Open the file `Top8000_best_hom50_pdb_chain_list.csv`.
3. View the "Raw" text format.
4. Copy the entire contents and save them locally as `top8000_chains.txt` within the `scripts/` directory.

The `build_lake.py` script automatically parses this list, handling the `pdb_id,chain` format dynamically.

## Extraction Methodology & Geometric Exclusion
The extraction script iterates through the `top8000_chains.txt` list and queries the RCSB PDB validation report endpoints. Because these reports are massive, they are served as gzipped XML files (`.xml.gz`). The script decompresses these in memory and parses the XML tree.

**Critical Filtering Rules:**
1. **Target Chain Only:** A single PDB file may contain multiple chains (A, B, C). The script strictly filters extraction to the *exact* representative chain specified by the Duke Top8000 list.
2. **Missing Angles:** Terminal residues at the ends of protein chains physically lack the adjacent atomic bonds required to form a complete dihedral angle. These are clerically excluded.
3. **Unphysical Geometry:** Any angles falling outside the $-180^\circ$ to $+180^\circ$ bounds are excluded as structural anomalies.

**Sovereign Preservation:**
The raw dihedral angles can be negative. Standard structural biology often takes the absolute magnitude, but the KishLattice Sovereign Framework demands that raw data be preserved exactly as observed. The signed value is saved directly to the JSONL lake. The absolute value transformation ($|x|$) is handled downstream in the engine's scalarization phase.

## Final Output
The script outputs `b4_pdb_protein_raw.jsonl`. Every record represents a single $\phi$ or $\psi$ angle, immutably tagged with its PDB ID, specific chain, residue name, and the `Top8000_Richardson_2.0A` dataset provenance.
