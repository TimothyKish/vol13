# ==============================================================================
# report_11_seismic_sovereign.py
# KishLattice Visual Suite Plugin
#
# The Seismic Sovereign Audit. Isolates the pre-registered sovereign fault lakes
# (Japan, Cascadia, San Andreas, Anatolian) into a 4-panel comparison grid to 
# test if seismic temporal intervals lock to the 17/pi or 18/pi kinematic registers 
# when separated from global noise.
#
# VOL 11 UPGRADE:
# - Vol 11 Sovereign header format.
# - Single-Pass Streaming from unified_master.
# - Dynamic Z-score dictionary ingestion.
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

TARGET_DOMAINS = [
    "seismic_japan",
    "seismic_cascadia",
    "seismic_san_andreas",
    "seismic_anatolian"
]

def load_configs(root_path):
    configs = {"harmonics": {}}
    harm_cfg = root_path / "configs" / "harmonic_targets.json"
    if harm_cfg.exists():
        with harm_cfg.open("r", encoding="utf-8") as f:
            configs["harmonics"] = json.load(f)
    return configs

def load_scalars_from_unified_master(unified_master_path, target_domains):
    domain_scalars = {d: [] for d in target_domains}
    if not unified_master_path or not Path(unified_master_path).exists():
        return domain_scalars

    print("        [DATA] Streaming unified master for Sovereign Seismic lakes...")
    with Path(unified_master_path).open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            try:
                rec = json.loads(line)
                domain = rec.get("domain")
                if domain in domain_scalars:
                    sc = rec.get("scalar_klc")
                    if sc is not None and float(sc) > 0:
                        domain_scalars[domain].append(float(sc))
            except:
                continue
    return domain_scalars

def generate(context):
    out_dir = context.get("output_dir")
    unified_master_path = context.get("unified_master_path")
    root_path = out_dir.parents[3] 
    generated_files = []

    print("    -> Plotting 4-Panel Seismic Sovereign Audit...")

    configs = load_configs(root_path)
    harmonics_cfg = configs["harmonics"]
    if harmonics_cfg and "registers" in harmonics_cfg:
        HARMONICS = {f"{n}/pi": float(n) / PI for n in harmonics_cfg["registers"]}
    else:
        HARMONICS = {f"{n}/pi": float(n) / PI for n in range(4, 27)}

    z_scores_dict = context.get("z_scores", {})
    if not z_scores_dict:
        z_path = root_path / "lakes" / "unified" / "z_scores_master.json"
        if z_path.exists():
            with z_path.open("r", encoding="utf-8") as f:
                z_scores_dict = json.load(f)

    domain_scalars = load_scalars_from_unified_master(unified_master_path, TARGET_DOMAINS)
    
    # Check if we have data (will gracefully skip during Vol 10 regression)
    if not any(len(v) > 0 for v in domain_scalars.values()):
        print("       [SKIP] Sovereign seismic domains not found in unified master (likely disabled).")
        return generated_files

    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    axes = axes.flatten()

    for i, domain in enumerate(TARGET_DOMAINS):
        ax = axes[i]
        scalars = domain_scalars.get(domain, [])
        
        if not scalars:
            ax.text(0.5, 0.5, f"No Data: {domain}\\n(Lake Disabled or Empty)", 
                    ha='center', va='center', fontsize=12, color='gray')
            ax.set_title(domain.replace('_', ' ').title())
            ax.axis('off')
            continue

        scalars = np.array(scalars)
        z_data = z_scores_dict.get(domain, {})
        z_scores = z_data.get("chaos_z", []) if isinstance(z_data, dict) else z_data
        
        max_z = max(z_scores) if z_scores else 0
        best_reg = list(HARMONICS.keys())[z_scores.index(max_z)] if z_scores and max_z > 0 else "N/A"

        x_max = max(HARMONICS.values()) + 0.5
        bins = np.arange(0, x_max, 0.05)
        ax.hist(scalars, bins=bins, color='#8c564b', edgecolor='black', linewidth=0.5, alpha=0.7)

        for label, val in HARMONICS.items():
            if label == best_reg and max_z >= 3.0:
                ax.axvline(x=val, color='red', linestyle='-', linewidth=2)
                ax.text(val + 0.05, ax.get_ylim()[1] * 0.85, f"Z={max_z:.1f}\\n{label}", color='darkred', fontweight='bold', rotation=90)
            elif label in ["17/pi", "18/pi"]:
                # Always mark the predicted tidal/kinematic family
                ax.axvline(x=val, color='blue', linestyle='--', linewidth=1.5, alpha=0.6)
            else:
                ax.axvline(x=val, color='gray', linestyle=':', linewidth=0.5, alpha=0.3)

        ax.set_xlim(0, x_max)
        ax.set_title(f"{domain.replace('_', ' ').title()} (n={len(scalars):,})", fontsize=12, fontweight='bold')
        ax.set_xlabel("Scalar Modulus (N/π)")
        ax.set_ylabel("Count")

    fig.suptitle("Volume 11 Seismic Sovereign Falsification Audit\nTesting independent fault systems against the 17/π & 18/π prediction", fontsize=16, fontweight='bold')
    fig.tight_layout()
    
    panel_path = out_dir / "seismic_sovereign_falsification.png"
    fig.savefig(panel_path, dpi=300)
    plt.close(fig)
    generated_files.append(panel_path)

    return generated_files