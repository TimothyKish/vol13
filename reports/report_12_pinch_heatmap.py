# ==============================================================================
# report_12_pinch_heatmap.py
# KishLattice Visual Suite Plugin
#
# The Distance Matrix Heatmap. Reads the 3D pinch_table_cross_domain matrix
# and flattens it into a 2D similarity heatmap based on 'dist_lock'.
# Domains are sorted by their primary harmonic register to naturally group
# physical families together (Seriation/Block-Diagonal representation).
#
# VOL 11 UPGRADE:
# - Vol 11 Sovereign header format.
# - Matrix Seriation based on Z-score registers.
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
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

def generate(context):
    out_dir = context.get("output_dir")
    pinch = context.get("pinch_table", {})
    root_path = out_dir.parents[3] 
    generated_files = []

    print("    -> Rendering Cross-Domain Distance Matrix Heatmap...")

    if not pinch:
        print("       [SKIP] pinch_table_cross_domain not found in context.")
        return generated_files

    # 1. Get Z-Scores to determine natural ordering
    z_scores_dict = context.get("z_scores", {})
    if not z_scores_dict:
        z_path = root_path / "lakes" / "unified" / "z_scores_master.json"
        if z_path.exists():
            with z_path.open("r", encoding="utf-8") as f:
                z_scores_dict = json.load(f)

    # Extract all unique domains present in the pinch table
    domains = sorted(list(pinch.keys()))
    if not domains: return generated_files

    # 2. Seriation: Order domains by their Peak Harmonic Register
    # This ensures that all domains locking to 16/pi are grouped together, 25/pi together, etc.
    domain_order_keys = []
    for d in domains:
        peak_idx = 0
        if d in z_scores_dict:
            z_data = z_scores_dict[d]
            z_scores = z_data.get("chaos_z", []) if isinstance(z_data, dict) else z_data
            if z_scores:
                peak_idx = np.argmax(z_scores)
        domain_order_keys.append((peak_idx, d))
    
    # Sort by Peak Register Index, then alphabetically
    domain_order_keys.sort()
    sorted_domains = [d for _, d in domain_order_keys]

    n = len(sorted_domains)
    matrix = np.zeros((n, n))

    # 3. Populate the Matrix using Max 'dist_lock' across all harmonics
    for i, dom_a in enumerate(sorted_domains):
        for j, dom_b in enumerate(sorted_domains):
            if i == j:
                matrix[i, j] = 1.0  # Perfect self-similarity
            else:
                cell = pinch.get(dom_a, {}).get(dom_b, {})
                if cell:
                    # Find the maximum dist_lock across all tested harmonics for this pair
                    max_lock = max([data.get("dist_lock", 0) for data in cell.values()])
                    matrix[i, j] = max_lock

    # 4. Plot the Heatmap
    fig, ax = plt.subplots(figsize=(14, 12))
    
    # Use 'viridis' or 'plasma' for high topological contrast
    cax = ax.imshow(matrix, cmap='viridis', aspect='auto', vmin=np.percentile(matrix, 5), vmax=1.0)
    
    # Labels
    clean_labels = [d.replace('_', ' ').title() for d in sorted_domains]
    ax.set_xticks(np.arange(n))
    ax.set_yticks(np.arange(n))
    ax.set_xticklabels(clean_labels, rotation=90, ha="right", fontsize=8)
    ax.set_yticklabels(clean_labels, fontsize=8)

    # Add colorbar
    cbar = fig.colorbar(cax, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label('Cross-Domain Geometric Similarity (dist_lock)', rotation=270, labelpad=15)

    ax.set_title("Geometric Distance Matrix Heatmap\nDomains sorted by primary harmonic register to reveal structural clustering", fontsize=16, fontweight='bold')
    
    fig.tight_layout()
    heatmap_path = out_dir / "distance_matrix_heatmap.png"
    fig.savefig(heatmap_path, dpi=300)
    plt.close(fig)
    generated_files.append(heatmap_path)

    return generated_files