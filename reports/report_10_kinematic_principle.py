# ==============================================================================
# report_10_kinematic_principle.py
# KishLattice Visual Suite Plugin
#
# The Mic-Drop. Generates side-by-side comparative panels for domains that measure 
# the SAME physical objects using DIFFERENT physical properties (e.g., Stars).
# Visually proves that the N/pi resonance shifts based on the physical action, 
# not the object itself.
#
# VOL 11 UPGRADE:
# - Decoupled hardcoded harmonics (reads configs/harmonic_targets.json).
# - Direct ingest of z_scores_master.json (supports Chaos & Synthetic Z-scores).
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
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

def load_configs(root_path):
    """Load harmonic targets dynamically."""
    configs = {"harmonics": {}}
    harm_cfg = root_path / "configs" / "harmonic_targets.json"
    if harm_cfg.exists():
        with harm_cfg.open("r", encoding="utf-8") as f:
            configs["harmonics"] = json.load(f)
    return configs

# Define the thematic panels to generate
PROOF_FAMILIES = {
    "Stellar Proof": {
        "title": "The Kinematic Principle: Stellar Dynamics",
        "subtitle": "Observing the same 1.8M objects. Resonance shifts based on physical property measured.",
        "domains": [
            {"id": "stellar_colour", "label": "Stellar Color (EM Spectrum)"},
            {"id": "stellar_luminosity", "label": "Stellar Luminosity (EM Ceiling)"},
            {"id": "stellar", "label": "Stellar Distance (Positional/Null)"},
            {"id": "stellar_kinematic", "label": "Transverse Velocity (Kinematic)"}
        ]
    },
    "Orbital Proof": {
        "title": "The Kinematic Principle: Orbital Dynamics",
        "subtitle": "Observing the same 13,000 Exoplanets.",
        "domains": [
            {"id": "orbital_radius", "label": "Orbital Radius (Positional/Null)"},
            {"id": "orbital", "label": "Orbital Period (Kinematic)"}
        ]
    }
}

def generate(context):
    out_dir = context.get("output_dir")
    root_path = out_dir.parents[3] 
    generated_files = []

    print("    -> Plotting Kinematic Principle Panels (The Mic-Drop)...")

    # VOL 11: Dynamic Config Loading
    configs = load_configs(root_path)
    harmonics_cfg = configs["harmonics"]

    if harmonics_cfg and "registers" in harmonics_cfg:
        registers = harmonics_cfg["registers"]
        HARMONICS = [f"{n}/pi" for n in registers]
    else:
        # Fallback to Vol 10 standard
        HARMONICS = [f"{n}/pi" for n in range(4, 27)]

    # VOL 11: Z-Scores Loading
    z_scores_dict = context.get("z_scores", {})
    if not z_scores_dict:
        z_path = root_path / "lakes" / "unified" / "z_scores_master.json"
        if z_path.exists():
            with z_path.open("r", encoding="utf-8") as f:
                z_scores_dict = json.load(f)

    if not z_scores_dict:
        print("       [SKIP] Missing z_scores_master.json data.")
        return generated_files

    for family_name, family_data in PROOF_FAMILIES.items():
        num_domains = len(family_data["domains"])
        fig, axes = plt.subplots(1, num_domains, figsize=(6 * num_domains, 6), sharey=True)
        
        # Ensure axes is iterable even if there's only 1 subplot
        if num_domains == 1:
            axes = [axes]

        valid_panels = 0

        for i, dom_meta in enumerate(family_data["domains"]):
            domain_id = dom_meta["id"]
            
            # Handle possible domain mapping changes in Vol 11
            if domain_id not in z_scores_dict:
                if domain_id == "stellar" and "s1_gaia_parallax" in z_scores_dict:
                    domain_id = "s1_gaia_parallax"
                else:
                    print(f"       [WARN] Domain '{domain_id}' not found in z_scores for {family_name}.")
                    continue

            # Vol 11 Dual Z-Score compatibility
            z_data = z_scores_dict[domain_id]
            if isinstance(z_data, dict):
                z_scores = z_data.get("chaos_z", [])
            else:
                z_scores = z_data

            if not z_scores or len(z_scores) != len(HARMONICS):
                print(f"       [WARN] Invalid Z-Scores length for '{domain_id}'. Skipping.")
                continue

            valid_panels += 1
            ax = axes[i]
            x_pos = np.arange(len(HARMONICS))
            max_z = max(z_scores)

            # Color all bars grey, except the absolute peak which gets highlighted
            colors = ['#d3d3d3'] * len(HARMONICS)
            if max_z >= 5.0:
                best_idx = z_scores.index(max_z)
                colors[best_idx] = '#d62728' # Bold Red for the structural lock
                
            ax.bar(x_pos, z_scores, color=colors, edgecolor='black', linewidth=0.5)
            ax.axhline(y=5.0, color='green', linestyle='--', linewidth=1.5, label="STRONG Threshold")
            
            ax.set_xticks(x_pos)
            ax.set_xticklabels(HARMONICS, rotation=45, ha="right", fontsize=9)
            
            # Formatting individual subplots
            ax.set_title(dom_meta["label"], fontsize=12, fontweight='bold')
            if i == 0:
                ax.set_ylabel("Chaos Z-Score", fontsize=12)
            
            # Dynamic Y-axis to let the peaks breathe
            y_max = max(max_z * 1.1, 10) if max_z > 0 else 10
            ax.set_ylim(-2, y_max)
            ax.grid(axis='y', linestyle='--', alpha=0.5)

        if valid_panels > 0:
            fig.suptitle(f"{family_data['title']}\n{family_data['subtitle']}", fontsize=18, fontweight='bold', y=1.05)
            fig.tight_layout()
            
            safe_name = family_name.lower().replace(" ", "_")
            file_path = out_dir / f"principle_{safe_name}.png"
            fig.savefig(file_path, dpi=300, bbox_inches='tight')
            generated_files.append(file_path)
        
        plt.close(fig)

    return generated_files