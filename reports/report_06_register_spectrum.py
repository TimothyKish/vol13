# ==============================================================================
# report_06_register_spectrum.py
# KishLattice Visual Suite Plugin
#
# The "Rainbow Map". Plots the peak Z-score for every domain across the 
# universal N/pi axis. Colors domains by their harmonic family to visually 
# prove the clustering of physical properties (e.g., Kinematics in blue).
#
# VOL 11 UPGRADE:
# - Aligned with Vol 11 Sovereign header format.
# - Decoupled hardcoded domains and families (reads reports/report_config.json).
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
import math
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

PI = math.pi

FAMILY_COLORS = {
    "kinematic": "#1f77b4",         # Blue
    "electromagnetic": "#ff7f0e",   # Orange
    "quantum_molecular": "#9467bd", # Purple
    "nuclear": "#d62728",           # Red
    "biological": "#2ca02c",        # Green
    "galactic": "#17becf",          # Cyan
    "cosmic": "#000080",            # Navy
    "seismic": "#8c564b",           # Brown
    "null": "#7f7f7f"               # Grey
}

def load_manifest(reports_dir):
    manifest_path = reports_dir / "domain_manifest.json"
    if not manifest_path.exists(): 
        return {}
    with manifest_path.open("r", encoding="utf-8") as f:
        return json.load(f)

def load_configs(root_path):
    """Load both report configurations and harmonic targets dynamically."""
    configs = {"report": {}, "harmonics": {}}
    
    rep_cfg = root_path / "reports" / "report_config.json"
    if rep_cfg.exists():
        with rep_cfg.open("r", encoding="utf-8") as f:
            configs["report"] = json.load(f)
            
    harm_cfg = root_path / "configs" / "harmonic_targets.json"
    if harm_cfg.exists():
        with harm_cfg.open("r", encoding="utf-8") as f:
            configs["harmonics"] = json.load(f)
            
    return configs

def get_domain_color(domain, domain_families):
    """Maps a domain to its family color using report_config.json."""
    for family, domains in domain_families.items():
        if domain in domains:
            return FAMILY_COLORS.get(family, "#333333")
            
    # Intelligent fallbacks if domain is missing from config
    dom_lower = domain.lower()
    if any(k in dom_lower for k in ["stellar", "orbital", "planetary"]): return FAMILY_COLORS["kinematic"]
    if "biology" in dom_lower or "amino" in dom_lower: return FAMILY_COLORS["biological"]
    if any(k in dom_lower for k in ["quantum", "molecular", "chemistry"]): return FAMILY_COLORS["quantum_molecular"]
    if "nuclear" in dom_lower or "cern" in dom_lower: return FAMILY_COLORS["nuclear"]
    if "seismic" in dom_lower: return FAMILY_COLORS["seismic"]
    if "null" in dom_lower: return FAMILY_COLORS["null"]
    
    return "#333333"

def generate(context):
    out_dir = context.get("output_dir")
    root_path = out_dir.parents[3] 
    generated_files = []

    print("    -> Plotting Register Spectrum (Rainbow Map)...")

    manifest = load_manifest(root_path / "reports")
    if not manifest:
        print("       [SKIP] domain_manifest.json not found.")
        return generated_files

    # VOL 11: Dynamic Config Loading
    configs = load_configs(root_path)
    report_cfg = configs["report"]
    harmonics_cfg = configs["harmonics"]
    
    domain_families = report_cfg.get("domain_families", {})

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

    peak_data = []

    for domain, meta in manifest.items():
        if domain not in z_scores_dict:
            continue
            
        # Vol 11 Dual Z-Score compatibility
        z_data = z_scores_dict[domain]
        z_scores = z_data.get("chaos_z", []) if isinstance(z_data, dict) else z_data
        
        if not z_scores or len(z_scores) != len(HARMONICS):
            continue

        max_z = max(z_scores)
        if max_z < 3.0: 
            continue # Only plot moderate-to-strong signals

        best_idx = z_scores.index(max_z)
        best_reg_str = HARMONICS[best_idx]
        reg_val = float(best_reg_str.split('/')[0]) / PI

        color = get_domain_color(domain, domain_families)

        peak_data.append({
            "domain": domain,
            "z_score": max_z,
            "reg_val": reg_val,
            "reg_str": best_reg_str,
            "color": color
        })

    if not peak_data:
        print("       [WARN] No peaks found above Z=3.0.")
        return generated_files

    # Sort by register value to prevent chaotic rendering
    peak_data.sort(key=lambda x: x["reg_val"])

    fig, ax = plt.subplots(figsize=(16, 8))

    for d in peak_data:
        markerline, stemlines, baseline = ax.stem(
            d["reg_val"], d["z_score"], 
            linefmt=d["color"], markerfmt='o', basefmt=" "
        )
        plt.setp(markerline, color=d["color"], markersize=8)
        plt.setp(stemlines, linewidth=2, alpha=0.7)
        
        # Annotate domain name
        # Alternate text heights slightly to prevent overlapping
        y_offset = d["z_score"] + 2
        ax.text(d["reg_val"], y_offset, d["domain"].replace('_', ' ').title(), 
                rotation=45, ha='left', va='bottom', fontsize=8, color=d["color"], fontweight='bold')

    # Formatting
    x_ticks = [float(h.split('/')[0]) / PI for h in HARMONICS]
    ax.set_xticks(x_ticks)
    ax.set_xticklabels(HARMONICS, rotation=45)
    
    # Cap Y-axis if a single domain (like stellar_colour) blows out the scale
    max_overall_z = max([d["z_score"] for d in peak_data])
    ax.set_ylim(0, max_overall_z * 1.25)
    
    x_min = min(x_ticks) - 0.5
    x_max = max(x_ticks) + 0.5
    ax.set_xlim(x_min, x_max)
    
    ax.axhline(y=5.0, color='green', linestyle='--', linewidth=1.5, label="STRONG Threshold (Z=5.0)")
    
    ax.set_xlabel("Harmonic Register (N/π)", fontsize=12)
    ax.set_ylabel("Peak Modular Z-Score", fontsize=12)
    ax.set_title("The Harmonic Spectrum Map\nStructural Self-Organization of Physical Domains", fontsize=16, fontweight='bold')
    
    # Build custom legend based on active families
    import matplotlib.patches as mpatches
    legend_elements = [mpatches.Patch(color=color, label=family.replace('_', ' ').title()) 
                       for family, color in FAMILY_COLORS.items() if any(d['color'] == color for d in peak_data)]
    
    if legend_elements:
        ax.legend(handles=legend_elements, loc='upper left', title="Harmonic Families")
    
    ax.grid(True, linestyle='--', alpha=0.5)

    spectrum_path = out_dir / "register_spectrum_full.png"
    fig.tight_layout()
    fig.savefig(spectrum_path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    generated_files.append(spectrum_path)

    return generated_files