# ==============================================================================
# report_03_power_analysis.py
# KishLattice Visual Suite Plugin
#
# Computes the statistical power and effect size for every domain. 
# Calculates the minimum 'n' required to achieve a STRONG signal (Z >= 5.0) 
# at 90% power, and classifies the robustness of each domain's peak signal.
#
# VOL 11 UPGRADE:
# - Aligned with Vol 11 Sovereign header format.
# - Direct ingest of z_scores_master.json (supports Chaos & Synthetic Z-scores).
# - Native integration with sweep_results.json for exact sample size (n).
# - Deprecated the legacy text-based log parser.
# ==============================================================================
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC.
# FOUNDER: Timothy John Kish
#
# LICENSE & TERMS OF USE:
# This software, including the 16/pi kinematic framework and scalarization
# engines, is open and available for scientific testing, empirical validation,
# and academic peer review.
#
# ATTRIBUTION REQUIREMENT:
# Any publication, derivative code, dataset generation, or public distribution
# relying on this framework must explicitly cite the "KishLattice 16/pi Initiative"
# and credit Timothy John Kish.
#
# Commercial utilization, proprietary harvesting, or uncredited reproduction
# is strictly prohibited without explicit written permission.
# ==============================================================================

import json
import math
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Power Analysis Constants
Z_ALPHA = 5.0   # Our strict STRONG threshold
Z_BETA = 1.645  # 90% Statistical Power

STATUS_COLORS = {
    "ROBUST": "#2ca02c",       # Green
    "ADEQUATE": "#1f77b4",     # Blue
    "FRAGILE": "#ff7f0e",      # Orange
    "UNDERPOWERED": "#d62728"  # Red
}

def load_manifest(reports_dir):
    manifest_path = reports_dir / "domain_manifest.json"
    if not manifest_path.exists(): 
        return {}
    with manifest_path.open("r", encoding="utf-8") as f:
        return json.load(f)

def generate(context):
    out_dir = context.get("output_dir")
    sweep = context.get("sweep_results", {})
    root_path = out_dir.parents[3] 
    generated_files = []

    print("    -> Calculating Statistical Power & Effect Sizes...")

    manifest = load_manifest(root_path / "reports")
    if not manifest:
        print("       [SKIP] domain_manifest.json not found.")
        return generated_files

    # VOL 11: Z-Scores Loading
    z_scores_dict = context.get("z_scores", {})
    if not z_scores_dict:
        z_path = root_path / "lakes" / "unified" / "z_scores_master.json"
        if z_path.exists():
            with z_path.open("r", encoding="utf-8") as f:
                z_scores_dict = json.load(f)

    if not z_scores_dict or not sweep:
        print("       [SKIP] Missing required z_scores or sweep_results data.")
        return generated_files

    analysis_data = []

    for domain, meta in manifest.items():
        if domain not in z_scores_dict or domain not in sweep:
            continue

        n = sweep[domain].get("nonzero", sweep[domain].get("n", 0))
        if n <= 0:
            continue

        # Vol 11 Dual Z-Score compatibility
        z_data = z_scores_dict[domain]
        z_scores = z_data.get("chaos_z", []) if isinstance(z_data, dict) else z_data
        
        if not z_scores:
            continue

        max_z = max(z_scores)
        
        # Effect Size Calculation (Cohen's d equivalent for our framework)
        # Z = effect_size * sqrt(n)  =>  effect_size = Z / sqrt(n)
        effect_size = max_z / math.sqrt(n) if max_z > 0 else 0
        
        # Minimum n required for 90% power at Z=5.0
        # n_min = (Z_alpha + Z_beta)^2 / (effect_size^2)
        if effect_size > 0:
            n_min = math.ceil(((Z_ALPHA + Z_BETA) ** 2) / (effect_size ** 2))
        else:
            n_min = float('inf')

        # Status Classification
        if max_z >= Z_ALPHA and n >= n_min:
            status = "ROBUST"
            color = STATUS_COLORS["ROBUST"]
        elif max_z >= Z_ALPHA and n < n_min:
            status = "FRAGILE"
            color = STATUS_COLORS["FRAGILE"]
        elif max_z < Z_ALPHA and n >= n_min:
            status = "ADEQUATE"
            color = STATUS_COLORS["ADEQUATE"]
        else:
            status = "UNDERPOWERED"
            color = STATUS_COLORS["UNDERPOWERED"]

        analysis_data.append({
            "domain": domain,
            "n": n,
            "z_score": max_z,
            "effect_size": effect_size,
            "n_min": n_min,
            "status": status,
            "color": color
        })

    if not analysis_data:
        print("       [WARN] No valid data found for power analysis.")
        return generated_files

    # Sort by Peak Z-Score descending
    analysis_data.sort(key=lambda x: x["z_score"], reverse=True)

    # =========================================================================
    # PLOT 1: The Power Ledger Table
    # =========================================================================
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10 + len(analysis_data) * 0.3), 
                                   gridspec_kw={'height_ratios': [1, 3]})
    
    # --- Top Subplot: Effect Size Scatter ---
    sizes = [d["n"] / max(100, max([x["n"] for x in analysis_data])) * 1000 + 50 for d in analysis_data]
    colors = [d["color"] for d in analysis_data]
    
    ax1.scatter([d["effect_size"] for d in analysis_data], 
                [d["z_score"] for d in analysis_data], 
                s=sizes, c=colors, alpha=0.7, edgecolors='black')
                
    ax1.axhline(y=5.0, color='green', linestyle='--', linewidth=1.5, label="STRONG Threshold (Z=5.0)")
    ax1.set_xlabel("Effect Size", fontsize=10)
    ax1.set_ylabel("Peak Z-Score", fontsize=10)
    ax1.set_title("Effect Size vs. Peak Z-Score (Bubble Size = n)", fontsize=12, fontweight='bold')
    ax1.grid(True, linestyle='--', alpha=0.5)

    # --- Bottom Subplot: The Table ---
    ax2.axis('tight')
    ax2.axis('off')

    col_labels = ['Domain', 'Sample Size (n)', 'Peak Z-Score', 'Effect Size', 'Min n for Z=5.0', 'Status']
    cell_text = []
    cell_colors = []

    for d in analysis_data:
        # Format n_min cleanly (handle infinity)
        n_min_str = f"{d['n_min']:,}" if d['n_min'] != float('inf') else "N/A"
        
        row = [
            d["domain"].replace('_', ' ').title(),
            f"{d['n']:,}",
            f"{d['z_score']:.2f}",
            f"{d['effect_size']:.4f}",
            n_min_str,
            d["status"]
        ]
        cell_text.append(row)
        
        # Color the background of the Status column
        row_colors = ['white'] * 5 + [d["color"]]
        cell_colors.append(row_colors)

    table = ax2.table(cellText=cell_text, cellColours=cell_colors, colLabels=col_labels, loc='center', cellLoc='center')
    
    # Table Formatting
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.5)

    # Make headers bold
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_text_props(weight='bold', color='black')
            cell.set_facecolor('#e0e0e0')
        elif col == 5: # Status column
            cell.set_text_props(weight='bold', color='white')

    fig.suptitle("Volume 11 Power Analysis Ledger\nEvaluating Sample Size Sufficiency for 90% Statistical Power", fontsize=16, fontweight='bold', y=0.98)
    
    table_path = out_dir / "power_analysis_table.png"
    fig.tight_layout()
    fig.savefig(table_path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    generated_files.append(table_path)

    return generated_files