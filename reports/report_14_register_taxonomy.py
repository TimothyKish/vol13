# ==============================================================================
# report_14_register_taxonomy.py
# KishLattice Visual Suite Plugin
#
# The Register Taxonomy Matrix. Creates a categorical bubble chart mapping 
# physical domains (Y-axis) to their peak N/pi register (X-axis). Bubble 
# size represents the Z-score strength.
#
# VOL 11 UPGRADE:
# - Vol 11 Sovereign header format.
# - Dynamic register extraction from Z-scores master.
# ==============================================================================
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC.
# FOUNDER: Timothy John Kish
#
# LICENSE & TERMS OF USE:
# This software, including the 16/pi kinematic framework and scalarization
# engines, is open and available for scientific testing, empirical validation,
# and academic peer review.
# ==============================================================================

import json
import math
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

PI = math.pi

def load_configs(root_path):
    configs = {"harmonics": {}}
    harm_cfg = root_path / "configs" / "harmonic_targets.json"
    if harm_cfg.exists():
        with harm_cfg.open("r", encoding="utf-8") as f:
            configs["harmonics"] = json.load(f)
    return configs

def get_broad_category(domain):
    d = domain.lower()
    if "planck" in d or "quantum" in d or "molecular" in d or "atomic" in d or "nuclear" in d:
        return "Quantum & Atomic"
    elif "bio" in d or "amino" in d or "chirality" in d:
        return "Biological"
    elif "seismic" in d or "planetary" in d or "orbital" in d:
        return "Planetary & Orbital"
    elif "stellar" in d or "pulsar" in d:
        return "Stellar"
    elif "galac" in d or "cosmo" in d or "astro" in d or "cmb" in d or "gravitational" in d:
        return "Galactic & Cosmological"
    else:
        return "Other / Synthetic"

def generate(context):
    out_dir = context.get("output_dir")
    root_path = out_dir.parents[3] 
    generated_files = []

    print("    -> Rendering Register Taxonomy Matrix...")

    configs = load_configs(root_path)
    harmonics_cfg = configs["harmonics"]
    if harmonics_cfg and "registers" in harmonics_cfg:
        registers = [f"{n}/pi" for n in harmonics_cfg["registers"]]
    else:
        registers = [f"{n}/pi" for n in range(4, 27)]

    z_scores_dict = context.get("z_scores", {})
    if not z_scores_dict:
        z_path = root_path / "lakes" / "unified" / "z_scores_master.json"
        if z_path.exists():
            with z_path.open("r", encoding="utf-8") as f:
                z_scores_dict = json.load(f)

    if not z_scores_dict:
        return generated_files

    # Extract peak registers and z-scores
    plot_data = []
    categories = ["Quantum & Atomic", "Biological", "Planetary & Orbital", "Stellar", "Galactic & Cosmological", "Other / Synthetic"]
    
    for domain, z_data in z_scores_dict.items():
        if "null" in domain.lower() or domain.startswith("np") or domain.startswith("n4"):
            continue # Skip known nulls for the taxonomy

        z_scores = z_data.get("chaos_z", []) if isinstance(z_data, dict) else z_data
        if not z_scores or len(z_scores) != len(registers):
            continue
            
        max_z = max(z_scores)
        if max_z < 3.0: 
            continue # Only plot domains that show at least a weak signal
            
        peak_idx = np.argmax(z_scores)
        peak_reg = registers[peak_idx]
        cat = get_broad_category(domain)
        
        plot_data.append({
            "domain": domain.replace('_', ' ').title(),
            "category": cat,
            "register_idx": peak_idx,
            "z_score": max_z
        })

    if not plot_data:
        print("       [SKIP] No significant signals found to populate Taxonomy Matrix.")
        return generated_files

    fig, ax = plt.subplots(figsize=(14, 8))

    # Assign Y positions based on category
    y_mapping = {cat: i for i, cat in enumerate(reversed(categories))}
    
    x_vals = []
    y_vals = []
    sizes = []
    labels = []

    for item in plot_data:
        x_vals.append(item["register_idx"])
        y_vals.append(y_mapping[item["category"]])
        # Exponential scaling for bubble size to emphasize 5+ sigma hits
        sizes.append((item["z_score"] ** 2) * 15)
        labels.append(item["domain"])

    scatter = ax.scatter(x_vals, y_vals, s=sizes, c=y_vals, cmap='Set2', alpha=0.7, edgecolors='black', linewidth=1)

    # Annotate the strongest signals
    for i in range(len(plot_data)):
        if plot_data[i]["z_score"] >= 5.0:
            ax.annotate(plot_data[i]["domain"], 
                        (x_vals[i], y_vals[i]), 
                        xytext=(0, 10), textcoords='offset points',
                        ha='center', va='bottom', fontsize=8, fontweight='bold')

    ax.set_xticks(range(len(registers)))
    ax.set_xticklabels(registers, rotation=45, ha="right", fontsize=9)
    
    ax.set_yticks(range(len(categories)))
    ax.set_yticklabels(reversed(categories), fontsize=11, fontweight='bold')

    ax.set_title("Kish Lattice Register Taxonomy\nMapping Physical Domains to their Peak N/π Geometric Harmonics", fontsize=16, fontweight='bold')
    ax.set_xlabel("Geometric Register (N/π)", fontsize=12)
    ax.grid(True, alpha=0.3, linestyle='--')

    # Legend for Z-score sizes
    l1 = plt.scatter([],[], s=(3**2)*15, edgecolors='none', color='gray', alpha=0.5)
    l2 = plt.scatter([],[], s=(5**2)*15, edgecolors='none', color='gray', alpha=0.5)
    l3 = plt.scatter([],[], s=(10**2)*15, edgecolors='none', color='gray', alpha=0.5)
    
    legend = plt.legend([l1, l2, l3], ['3 Sigma', '5 Sigma', '10+ Sigma'], 
                        title="Z-Score Strength", loc='lower right', frameon=True, borderpad=1)

    fig.tight_layout()
    tax_path = out_dir / "register_taxonomy_matrix.png"
    fig.savefig(tax_path, dpi=300)
    plt.close(fig)
    generated_files.append(tax_path)

    return generated_files