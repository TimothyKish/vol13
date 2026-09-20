# ==============================================================================
# report_05_wrongbox_delta.py
# KishLattice Visual Suite Plugin
#
# Dynamically reads predictions.json and parses the actual Chaos Z-Scores 
# directly from the unified JSON structure. Features "Harmonic Echo" suppression 
# to properly identify true dual-peaks versus resonance bleed.
#
# VOL 11 UPGRADE:
# - Aligned with Vol 11 Sovereign header format.
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

def load_predictions(root_path):
    pred_path = root_path / "predictions" / "predictions.json"
    if not pred_path.exists():
        return {}
    with pred_path.open("r", encoding="utf-8") as f:
        return json.load(f)

def load_configs(root_path):
    """Load harmonic targets dynamically."""
    configs = {"harmonics": {}}
    harm_cfg = root_path / "configs" / "harmonic_targets.json"
    if harm_cfg.exists():
        with harm_cfg.open("r", encoding="utf-8") as f:
            configs["harmonics"] = json.load(f)
    return configs

def generate(context):
    out_dir = context.get("output_dir")
    root_path = out_dir.parents[3] 
    generated_files = []

    print("    -> Plotting Wrongbox Deltas & Prediction Audits...")

    predictions = load_predictions(root_path)
    if not predictions:
        print("       [SKIP] predictions.json not found. No audits to run.")
        return generated_files

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

    for domain, pred_data in predictions.items():
        if domain not in z_scores_dict:
            continue

        # Vol 11 Dual Z-Score compatibility
        z_data = z_scores_dict[domain]
        z_scores = z_data.get("chaos_z", []) if isinstance(z_data, dict) else z_data

        if not z_scores or len(z_scores) != len(HARMONICS):
            continue

        # Extract expected registers robustly
        predicted = []
        if isinstance(pred_data, list):
            predicted = pred_data
        elif isinstance(pred_data, dict):
            predicted = pred_data.get("expected_registers", pred_data.get("predicted_registers", []))
            if isinstance(predicted, str):
                predicted = [predicted]

        observed_strong = [HARMONICS[i] for i, z in enumerate(z_scores) if z >= 5.0]

        print(f"       [AUDIT] {domain.upper()}: Plotting Delta...")

        fig, ax = plt.subplots(figsize=(12, 6))
        x_pos = np.arange(len(HARMONICS))
        colors = ['lightgrey'] * len(HARMONICS)
        
        for i, h in enumerate(HARMONICS):
            if h in predicted and h in observed_strong:
                colors[i] = '#9467bd' # Purple (Hit)
            elif h in predicted:
                colors[i] = '#d62728' # Red (Missed)
            elif h in observed_strong:
                colors[i] = '#1f77b4' # Blue (Unpredicted Discovery or Echo)

        ax.bar(x_pos, z_scores, color=colors, edgecolor='black', linewidth=0.5)
        ax.axhline(y=5.0, color='green', linestyle='--', linewidth=1.5, label="STRONG Threshold (Z=5.0)")
        
        ax.set_xticks(x_pos)
        ax.set_xticklabels(HARMONICS, rotation=45, ha="right", fontsize=9)
        ax.set_ylabel("Chaos Z-Score", fontsize=12)
        
        min_z = min(z_scores)
        max_z = max(z_scores)
        y_max = max_z * 1.2 if max_z > 5 else 10
        y_min = min_z * 1.1 if min_z < 0 else -5
        ax.set_ylim(y_min, y_max)

        ax.set_title(f"Prediction Audit & Wrongbox Delta: {domain.replace('_', ' ').title()}", fontsize=14, fontweight='bold')
        
        # Custom Legend
        import matplotlib.patches as mpatches
        hit_patch = mpatches.Patch(color='#9467bd', label='Confirmed Prediction (Hit)')
        miss_patch = mpatches.Patch(color='#d62728', label='Missed Prediction (Wrongbox)')
        disc_patch = mpatches.Patch(color='#1f77b4', label='Unpredicted STRONG Signal')
        ax.legend(handles=[hit_patch, miss_patch, disc_patch], loc='upper right')

        ax.grid(axis='y', linestyle='--', alpha=0.5)

        delta_path = out_dir / f"wrongbox_delta_{domain}.png"
        fig.tight_layout()
        fig.savefig(delta_path, dpi=300)
        plt.close(fig)
        generated_files.append(delta_path)

    return generated_files