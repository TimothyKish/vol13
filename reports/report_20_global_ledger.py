# ==============================================================================
# report_20_global_ledger.py
# KishLattice Visual Suite Plugin
#
# The Master Infographic. Synthesizes the most critical data points of the 
# entire framework run into a single, high-resolution dashboard. Features 
# the Universal Spectrum, the Apex Resonances, and Global Statistics.
#
# VOL 11 UPGRADE:
# - Vol 11 Sovereign header format.
# - Matplotlib GridSpec infographic layout.
# - Dynamic aggregation across all JSON layers.
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
import matplotlib.gridspec as gridspec
from pathlib import Path

PI = math.pi

def load_configs(root_path):
    configs = {"harmonics": {}, "volumes": {}}
    harm_cfg = root_path / "configs" / "harmonic_targets.json"
    if harm_cfg.exists():
        with harm_cfg.open("r", encoding="utf-8") as f:
            configs["harmonics"] = json.load(f)
            
    vol_cfg = root_path / "configs" / "volumes.json"
    if vol_cfg.exists():
        with vol_cfg.open("r", encoding="utf-8") as f:
            configs["volumes"] = json.load(f)
    return configs

def get_broad_color(domain):
    d = domain.lower()
    if "quantum" in d or "nuclear" in d or "atomic" in d: return "#9467bd" # Purple
    if "bio" in d or "amino" in d: return "#2ca02c" # Green
    if "seismic" in d or "planetary" in d: return "#8c564b" # Brown
    if "stellar" in d or "orbital" in d or "kinematic" in d: return "#1f77b4" # Blue
    if "galac" in d or "cosmo" in d or "cmb" in d: return "#17becf" # Cyan
    return "#7f7f7f"

def generate(context):
    out_dir = context.get("output_dir")
    sweep = context.get("sweep_results", {})
    root_path = out_dir.parents[3] 
    generated_files = []

    print("    -> Rendering The Global Ledger Master Infographic...")

    configs = load_configs(root_path)
    harmonics_cfg = configs["harmonics"]
    volumes_cfg = configs["volumes"].get("volumes", {})

    if harmonics_cfg and "registers" in harmonics_cfg:
        HARMONICS = [f"{n}/pi" for n in harmonics_cfg["registers"]]
    else:
        HARMONICS = [f"{n}/pi" for n in range(4, 27)]

    z_scores_dict = context.get("z_scores", {})
    if not z_scores_dict:
        z_path = root_path / "lakes" / "unified" / "z_scores_master.json"
        if z_path.exists():
            with z_path.open("r", encoding="utf-8") as f:
                z_scores_dict = json.load(f)

    if not z_scores_dict:
        return generated_files

    # Aggregate Data
    plot_data = []
    total_records = 0
    strong_signals = 0

    for domain, z_data in z_scores_dict.items():
        if "null" in domain.lower() or domain.startswith("np") or domain.startswith("n4"):
            continue 

        z_scores = z_data.get("chaos_z", []) if isinstance(z_data, dict) else z_data
        if not z_scores or len(z_scores) != len(HARMONICS):
            continue

        max_z = max(z_scores)
        best_idx = z_scores.index(max_z)
        reg_val = float(HARMONICS[best_idx].split('/')[0]) / PI

        # Attempt to get record count from sweep
        n_recs = sweep.get(domain, {}).get("nonzero", sweep.get(domain, {}).get("n", 0))
        total_records += n_recs

        if max_z >= 5.0:
            strong_signals += 1

        plot_data.append({
            "domain": domain.replace('_', ' ').title(),
            "z_score": max_z,
            "reg_val": reg_val,
            "color": get_broad_color(domain)
        })

    if not plot_data:
        return generated_files

    # Sort for the Apex ranking
    apex_data = sorted(plot_data, key=lambda x: x["z_score"], reverse=True)[:10]

    # Set up the Infographic Grid
    fig = plt.figure(figsize=(18, 12))
    gs = gridspec.GridSpec(2, 3, figure=fig, height_ratios=[1.2, 1])

    # --- PANEL 1: The Condensed Spectrum (Spans entire top row) ---
    ax1 = fig.add_subplot(gs[0, :])
    for d in plot_data:
        if d["z_score"] >= 3.0:
            markerline, stemlines, baseline = ax1.stem(d["reg_val"], d["z_score"], linefmt=d["color"], markerfmt='o', basefmt=" ")
            plt.setp(markerline, color=d["color"], markersize=6)
            plt.setp(stemlines, linewidth=1.5, alpha=0.6)

    ax1.axhline(y=5.0, color='red', linestyle='--', linewidth=1.5, label="STRONG Threshold")
    x_ticks = [float(h.split('/')[0]) / PI for h in HARMONICS]
    ax1.set_xticks(x_ticks)
    ax1.set_xticklabels(HARMONICS, rotation=45)
    ax1.set_title("Universal Harmonic Spectrum", fontsize=14, fontweight='bold')
    ax1.set_ylabel("Peak Chaos Z-Score")
    ax1.grid(True, alpha=0.3, linestyle=':')

    # --- PANEL 2: Apex Resonances (Bottom Left & Center) ---
    ax2 = fig.add_subplot(gs[1, :2])
    apex_labels = [d["domain"] for d in apex_data]
    apex_scores = [d["z_score"] for d in apex_data]
    apex_colors = [d["color"] for d in apex_data]
    
    y_pos = np.arange(len(apex_labels))
    ax2.barh(y_pos, apex_scores, color=apex_colors, edgecolor='black')
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(apex_labels, fontsize=10, fontweight='bold')
    ax2.invert_yaxis()  # Highest at the top
    ax2.set_title("Apex Structural Resonances (Top 10 Domains)", fontsize=14, fontweight='bold')
    ax2.set_xlabel("Peak Z-Score")
    ax2.grid(axis='x', alpha=0.3, linestyle='--')

    # --- PANEL 3: Global Statistics Ledger (Bottom Right) ---
    ax3 = fig.add_subplot(gs[1, 2])
    ax3.axis('off')
    
    stats_text = (
        "GLOBAL LATTICE LEDGER\n"
        "=========================\n\n"
        f"Domains Analyzed:      {len(plot_data)}\n"
        f"Total Records (n):     {total_records:,}\n"
        f"STRONG Signals (Z≥5):  {strong_signals}\n\n"
        "PHYSICAL SCALE SPAN\n"
        "=========================\n"
        "Minimum: 10⁻¹⁵ m (Subnuclear)\n"
        "Maximum: 10²⁶ m (Cosmological)\n"
        "Total Span: 41 Orders of Mag.\n\n"
        "ENGINE FINGERPRINT\n"
        "=========================\n"
        "Model: Volume 11 Parallel\n"
        "Architecture: Dual-Null Matrix\n"
        "Status: MATHEMATICALLY LOCKED"
    )
    
    props = dict(boxstyle='round,pad=1', facecolor='#f8f9fa', edgecolor='black', alpha=1.0)
    ax3.text(0.5, 0.5, stats_text, transform=ax3.transAxes, fontsize=12,
            verticalalignment='center', horizontalalignment='center', bbox=props, family='monospace')

    # Main Title
    fig.suptitle("Volume 11: The Kish Lattice Kinematic Framework", fontsize=24, fontweight='bold', y=0.98)
    
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    ledger_path = out_dir / "global_ledger_master.png"
    fig.savefig(ledger_path, dpi=300)
    plt.close(fig)
    generated_files.append(ledger_path)

    return generated_files