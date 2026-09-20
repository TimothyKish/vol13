# ==============================================================================
# report_16_artifact_falsification.py
# KishLattice Visual Suite Plugin
#
# The Synthetic Proof. Plots the peak Chaos Z-Score against the Synthetic
# Z-Score at that exact same geometric register. Proves visually that the
# 16/pi clustering is a physical reality, not an artifact of the log-modulo
# transform, because smooth Gaussian data (Synthetic) fails to resonate.
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
from pathlib import Path

def generate(context):
    out_dir = context.get("output_dir")
    root_path = out_dir.parents[3] 
    generated_files = []

    print("    -> Plotting Artifact Falsification (Chaos vs Synthetic)...")

    z_scores_dict = context.get("z_scores", {})
    if not z_scores_dict:
        z_path = root_path / "lakes" / "unified" / "z_scores_master.json"
        if z_path.exists():
            with z_path.open("r", encoding="utf-8") as f:
                z_scores_dict = json.load(f)

    if not z_scores_dict:
        return generated_files

    plot_data = []

    for domain, z_data in z_scores_dict.items():
        if "null" in domain.lower() or domain.startswith("np") or domain.startswith("n4"):
            continue 

        # We specifically need the Vol 11 dual-dictionary
        if not isinstance(z_data, dict) or "chaos_z" not in z_data or "synthetic_z" not in z_data:
            continue

        chaos_scores = z_data["chaos_z"]
        synth_scores = z_data["synthetic_z"]

        if not chaos_scores or not synth_scores:
            continue

        # Find the register where the physical signal peaked
        peak_idx = np.argmax(chaos_scores)
        max_chaos_z = chaos_scores[peak_idx]
        
        # Grab the synthetic score AT THAT EXACT SAME REGISTER
        matching_synth_z = synth_scores[peak_idx]
        
        plot_data.append({
            "domain": domain.replace('_', ' ').title(),
            "chaos_z": max_chaos_z,
            "synth_z": matching_synth_z
        })

    if not plot_data:
        print("       [SKIP] No dual-Z-score data found for Artifact Falsification.")
        return generated_files

    fig, ax = plt.subplots(figsize=(10, 10))

    c_vals = [d["chaos_z"] for d in plot_data]
    s_vals = [d["synth_z"] for d in plot_data]
    labels = [d["domain"] for d in plot_data]

    # Draw the "Artifact Identity Line" (y=x). 
    # If the math caused the clustering, points would fall along this line.
    max_val = max(max(c_vals), 5)
    ax.plot([-2, max_val * 1.1], [-2, max_val * 1.1], color='red', linestyle='--', alpha=0.5, label="Mathematical Artifact Line (y=x)")
    
    # Draw the "True Signal Zone" line (Synthetic Z = 0)
    ax.axvline(x=0, color='blue', linestyle=':', linewidth=2, label="Gaussian Null Baseline (Z=0)")
    ax.axhline(y=5.0, color='green', linestyle='-', linewidth=1.5, label="STRONG Threshold (Z=5.0)")

    # Plot the domains
    ax.scatter(s_vals, c_vals, s=80, c='#9467bd', edgecolors='black', alpha=0.8, zorder=5)

    # Annotate strong signals
    for i, txt in enumerate(labels):
        if c_vals[i] >= 5.0:
            ax.annotate(txt, (s_vals[i], c_vals[i]), xytext=(5, 0), textcoords='offset points', 
                        fontsize=8, va='center', ha='left')

    # Formatting
    ax.set_xlim(-3, 3)
    ax.set_ylim(-1, max_val * 1.1)
    
    ax.set_title("Artifact Falsification: Physical Signal vs. Transform Bias\nProving the log-modulo transform does not self-generate geometric locks", fontsize=14, fontweight='bold')
    ax.set_xlabel("Synthetic Z-Score (Matched Smooth Gaussian)", fontsize=12)
    ax.set_ylabel("Chaos Z-Score (True Physical Distribution)", fontsize=12)
    
    ax.legend(loc="upper left", framealpha=0.9)
    ax.grid(True, alpha=0.3, linestyle='--')

    # Annotation box explaining the logic
    annotation_text = (
        "THE SYNTHETIC PROOF:\n"
        "If the 16/π resonance was just a mathematical artifact of\n"
        "converting data into log-space, perfectly smooth synthetic\n"
        "data bounded to the same limits would also resonate.\n"
        "Domains rising vertically while hugging Synthetic Z ≈ 0\n"
        "prove the signal exists in the physical data itself."
    )
    props = dict(boxstyle='round,pad=0.6', facecolor='white', edgecolor='black', alpha=0.9)
    ax.text(0.95, 0.05, annotation_text, transform=ax.transAxes, fontsize=9,
            verticalalignment='bottom', horizontalalignment='right', bbox=props, family='monospace')

    fig.tight_layout()
    plot_path = out_dir / "artifact_falsification.png"
    fig.savefig(plot_path, dpi=300)
    plt.close(fig)
    generated_files.append(plot_path)

    return generated_files