# ==============================================================================
# report_17_cross_scale_bridge.py
# KishLattice Visual Suite Plugin
#
# The 35 Orders of Magnitude Map. Plots the Peak Z-Score of strong domains
# across a logarithmic x-axis representing the approximate physical size (in meters)
# of the objects being measured. Visually proves scale-invariance.
#
# VOL 11 UPGRADE:
# - Vol 11 Sovereign header format.
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

# Approximate Scale Mapping in Meters (10^X)
SCALE_MAP = {
    "subnuclear": 1e-15,
    "quantum": 1e-10,
    "atomic": 1e-10,
    "chemistry": 1e-9,
    "molecular": 1e-9,
    "biology": 1e-8,
    "amino": 1e-9,
    "protein": 1e-8,
    "materials": 1e-6,
    "seismic": 1e5,
    "planetary": 1e7,
    "orbital": 1e11,
    "stellar": 1e9,
    "galactic": 1e21,
    "cosmology": 1e25,
    "cmb": 1e26,
    "gravitational": 1e22
}

def get_approx_scale(domain):
    dom_lower = domain.lower()
    for key, meters in SCALE_MAP.items():
        if key in dom_lower:
            return meters
    return None

def generate(context):
    out_dir = context.get("output_dir")
    root_path = out_dir.parents[3] 
    generated_files = []

    print("    -> Rendering Cross-Scale Bridge Map (35 Orders of Magnitude)...")

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

        z_scores = z_data.get("chaos_z", []) if isinstance(z_data, dict) else z_data
        if not z_scores: continue
            
        max_z = max(z_scores)
        if max_z < 3.0: 
            continue # We only plot validated signals

        scale = get_approx_scale(domain)
        if scale is not None:
            plot_data.append({
                "domain": domain.replace('_', ' ').title(),
                "scale": scale,
                "z_score": max_z
            })

    if not plot_data:
        print("       [SKIP] Not enough scalable domains found.")
        return generated_files

    fig, ax = plt.subplots(figsize=(14, 7))

    x_vals = [d["scale"] for d in plot_data]
    y_vals = [d["z_score"] for d in plot_data]
    labels = [d["domain"] for d in plot_data]

    ax.scatter(x_vals, y_vals, s=100, c='#17becf', edgecolors='black', alpha=0.8, zorder=5)

    # Prevent label overlaps using simple vertical offsets
    for i, txt in enumerate(labels):
        offset = 5 if i % 2 == 0 else -12
        ax.annotate(txt, (x_vals[i], y_vals[i]), xytext=(0, offset), textcoords='offset points', 
                    fontsize=8, va='center', ha='center', fontweight='bold')

    ax.set_xscale('log')
    
    # Add human-readable scale zones
    ax.axvspan(1e-16, 1e-12, color='red', alpha=0.05, label="Sub-Nuclear / Quantum")
    ax.axvspan(1e-11, 1e-6, color='green', alpha=0.05, label="Atomic / Molecular / Biological")
    ax.axvspan(1e3, 1e8, color='blue', alpha=0.05, label="Planetary / Seismic")
    ax.axvspan(1e9, 1e14, color='orange', alpha=0.05, label="Stellar / Orbital")
    ax.axvspan(1e18, 1e27, color='purple', alpha=0.05, label="Galactic / Cosmological")

    ax.axhline(y=5.0, color='red', linestyle='--', linewidth=1.5, label="STRONG Threshold (Z=5.0)")

    ax.set_xlim(1e-16, 1e27)
    
    # Cap the Y-axis if a single Z-score is insanely high to keep the rest readable
    max_z = max(y_vals)
    ax.set_ylim(0, min(max_z * 1.2, 80))

    ax.set_title("The Cross-Scale Bridge: Scale Invariance of the Kish Lattice\nStructural resonance across 35 orders of magnitude", fontsize=16, fontweight='bold')
    ax.set_xlabel("Approximate Physical Scale of Phenomenon (Meters) [Log Scale]", fontsize=12)
    ax.set_ylabel("Peak Geometric Z-Score", fontsize=12)

    # Push legend to the bottom to avoid overlapping with high Z-scores
    ax.legend(loc="lower center", ncol=3, framealpha=0.9, bbox_to_anchor=(0.5, -0.25))
    ax.grid(True, alpha=0.3, linestyle='--')

    fig.tight_layout()
    plot_path = out_dir / "cross_scale_bridge.png"
    fig.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    generated_files.append(plot_path)

    return generated_files