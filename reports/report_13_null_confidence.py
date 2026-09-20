# ==============================================================================
# report_13_null_confidence.py
# KishLattice Visual Suite Plugin
#
# The Power of Nothing. Isolates explicitly defined "null", "scrambled", 
# or "chaos" domains and plots their Z-score density against a standard 
# normal distribution. 
#
# VOL 11 UPGRADE:
# - Vol 11 Sovereign header format.
# - Direct ingestion of the dual z_scores_master.json
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
from scipy.stats import norm
from pathlib import Path

def generate(context):
    out_dir = context.get("output_dir")
    root_path = out_dir.parents[3] 
    generated_files = []

    print("    -> Plotting Null Confidence & Statistical Power...")

    z_scores_dict = context.get("z_scores", {})
    if not z_scores_dict:
        z_path = root_path / "lakes" / "unified" / "z_scores_master.json"
        if z_path.exists():
            with z_path.open("r", encoding="utf-8") as f:
                z_scores_dict = json.load(f)

    if not z_scores_dict:
        return generated_files

    # Identify Null/Control Domains (keywords: null, scrambled, np1, n4, etc.)
    null_domains = {}
    for domain, z_data in z_scores_dict.items():
        if "null" in domain.lower() or domain.startswith("np") or domain.startswith("n4"):
            z_scores = z_data.get("chaos_z", []) if isinstance(z_data, dict) else z_data
            if z_scores:
                null_domains[domain] = z_scores

    if not null_domains:
        print("       [SKIP] No explicit Null/Control domains found for confidence plotting.")
        return generated_files

    fig, ax = plt.subplots(figsize=(12, 7))

    # Plot theoretical standard normal distribution
    x_axis = np.linspace(-4, 4, 1000)
    y_axis = norm.pdf(x_axis, 0, 1)
    ax.plot(x_axis, y_axis, color='black', linestyle='--', linewidth=2, label="Theoretical Gaussian Noise (Mean=0, Std=1)")

    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    
    for idx, (domain, scores) in enumerate(null_domains.items()):
        c = colors[idx % len(colors)]
        # We plot the KDE/Histogram of the Z-scores across all registers for this null lake
        ax.hist(scores, bins=15, density=True, alpha=0.5, color=c, edgecolor='black', 
                label=f"{domain.replace('_', ' ').title()} (Max Z={max(scores):.2f})")

    ax.axvline(x=5.0, color='red', linestyle='-', linewidth=2, label="Discovery Threshold (5 Sigma)")
    
    # Force x-axis to show the 5-sigma line even if data doesn't reach it
    ax.set_xlim(-3, 6)
    
    ax.set_title("Statistical Power of Null Domains\nConfirming the 16/π framework does not generate false positives from true noise", fontsize=14, fontweight='bold')
    ax.set_xlabel("Z-Score")
    ax.set_ylabel("Probability Density")
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3, linestyle=':')

    fig.tight_layout()
    plot_path = out_dir / "null_confidence_curves.png"
    fig.savefig(plot_path, dpi=300)
    plt.close(fig)
    generated_files.append(plot_path)

    return generated_files