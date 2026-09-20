# ==============================================================================
# report_04_batch_stability.py
# KishLattice Visual Suite Plugin
#
# The Sub-Sampler. Identifies small-N domains, draws 10 independent 80% subsamples,
# and re-runs the exact 24-Cell Modular Resonance lock_rate formula to test
# signal stability without relying on the log parser.
#
# VOL 11 UPGRADE:
# - Decoupled hardcoded harmonics (reads configs/harmonic_targets.json).
# - Decoupled hardcoded thresholds (CONTAINER & LOCK_THRESHOLD dynamic).
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
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

PI = math.pi

def load_configs(root_path):
    """Load harmonic targets dynamically."""
    configs = {"harmonics": {}}
    harm_cfg = root_path / "configs" / "harmonic_targets.json"
    if harm_cfg.exists():
        with harm_cfg.open("r", encoding="utf-8") as f:
            configs["harmonics"] = json.load(f)
    return configs

def compute_modular_z_score(scalars, register_val, container=24.0, lock_threshold=0.05):
    """
    Executes the true KishLattice Modular Resonance check dynamically.
    rp = (s / target) * container.
    Checks if rp lands within +/- lock_threshold of an integer.
    """
    n = len(scalars)
    if n == 0: return 0

    # The modular projection
    rp = (scalars / register_val) * container
    nearest = np.maximum(1, np.round(rp))
    
    # Count how many records locked onto the modular grid
    locked = np.sum(np.abs(rp - nearest) < lock_threshold)
    p_real = locked / n
    
    # Under a uniform chaos distribution, the probability of landing 
    # within +/- threshold of any integer is exactly 2 * threshold.
    p_null = 2 * lock_threshold
    variance = (p_null * (1 - p_null)) / n
    
    if variance > 0:
        return (p_real - p_null) / math.sqrt(variance)
    return 0

def generate(context):
    out_dir = context.get("output_dir")
    master_path = context.get("unified_master_path")
    sweep = context.get("sweep_results", {})
    root_path = out_dir.parents[3] 
    generated_files = []

    print("    -> Initiating 24-Cell Batch Stability Sub-Sampler...")

    # VOL 11: Dynamic Config Loading
    configs = load_configs(root_path)
    harmonics_cfg = configs["harmonics"]

    if harmonics_cfg and "registers" in harmonics_cfg:
        registers = harmonics_cfg["registers"]
        HARMONICS = [f"{n}/pi" for n in registers]
        CONTAINER = float(harmonics_cfg.get("container", 24.0))
        LOCK_THRESHOLD = float(harmonics_cfg.get("lock_threshold", 0.05))
    else:
        # Fallback to Vol 10 standard
        HARMONICS = [f"{n}/pi" for n in range(4, 27)]
        CONTAINER = 24.0
        LOCK_THRESHOLD = 0.05

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

    # 1. Identify Target Small Domains
    target_domains = {}
    for domain, meta in sweep.items():
        n_obs = meta.get("n", 0)
        if 20 <= n_obs < 1000 and domain in z_scores_dict:
            
            # Vol 11 Dual Z-Score compatibility
            z_data = z_scores_dict[domain]
            if isinstance(z_data, dict):
                original_z_scores = z_data.get("chaos_z", [])
            else:
                original_z_scores = z_data
                
            if not original_z_scores:
                continue

            max_z = max(original_z_scores)
            
            if max_z > 2.0 and len(original_z_scores) == len(HARMONICS):
                best_idx = original_z_scores.index(max_z)
                best_register_str = HARMONICS[best_idx]
                best_register_val = float(best_register_str.split('/')[0]) / PI
                
                target_domains[domain] = {
                    "n": n_obs,
                    "register": best_register_str,
                    "reg_val": best_register_val,
                    "original_z": max_z,
                    "scalars": []
                }

    if not target_domains:
        return generated_files

    # 2. Extract Data directly from unified master
    if master_path and master_path.exists():
        with master_path.open("r", encoding="utf-8") as f:
            for line in f:
                if any(f'"{d}"' in line for d in target_domains.keys()):
                    try:
                        rec = json.loads(line)
                        dom = rec.get("domain")
                        if dom in target_domains:
                            sc = rec.get("scalar_klc")
                            if sc is not None and float(sc) > 0:
                                target_domains[dom]["scalars"].append(float(sc))
                    except:
                        continue

    # 3. Run Sub-Sampling Math using the True 24-Cell Function
    stability_data = {}
    for domain, data in target_domains.items():
        scalars = np.array(data["scalars"])
        if len(scalars) < 20: continue
            
        print(f"       [SAMPLE] Testing {domain} via modular check at {data['register']}...")
        subsample_size = int(len(scalars) * 0.8)
        sub_z_scores = []
        
        for i in range(10):
            np.random.seed(42 + i + len(domain))
            sample = np.random.choice(scalars, size=subsample_size, replace=False)
            
            # Use the true modular lock_rate function, passing dynamic configs
            z = compute_modular_z_score(sample, data["reg_val"], CONTAINER, LOCK_THRESHOLD)
            sub_z_scores.append(z)
            
        stability_data[domain] = {
            "title": domain.replace('_', ' ').title(),
            "register": data["register"],
            "original_z": data["original_z"],
            "subsamples": sub_z_scores
        }

    if not stability_data: return generated_files

    # =========================================================================
    # PLOT: THE STABILITY VIOLIN
    # =========================================================================
    print("    -> Rendering Stability Violin Plot...")
    sorted_domains = sorted(stability_data.keys(), key=lambda d: stability_data[d]["original_z"], reverse=True)
    plot_data = [stability_data[d]["subsamples"] for d in sorted_domains]
    labels = [f"{stability_data[d]['title']}\n({stability_data[d]['register']})" for d in sorted_domains]
    
    fig, ax = plt.subplots(figsize=(14, 8))
    parts = ax.violinplot(plot_data, showmeans=True, showextrema=True)
    
    for pc in parts['bodies']:
        pc.set_facecolor('#1f77b4')
        pc.set_edgecolor('black')
        pc.set_alpha(0.6)
        
    parts['cmeans'].set_color('red')
    parts['cmeans'].set_linewidth(2)
    
    for i, d in enumerate(sorted_domains):
        ax.plot(i + 1, stability_data[d]["original_z"], marker='*', color='gold', markersize=12, markeredgecolor='black', zorder=10)

    ax.axhline(y=5.0, color='green', linestyle='--', linewidth=1.5, label="STRONG Threshold (Z=5.0)")

    ax.set_xticks(np.arange(1, len(labels) + 1))
    ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=9)
    ax.set_ylabel("Modular Resonance Z-Score", fontsize=12)
    ax.set_title(f"{int(CONTAINER)}-Cell Batch Stability: 80% Sub-Sampling on Small Domains\nViolin distribution of 10 random permutations via modular resonance lock_rate.", fontsize=14, fontweight='bold')
    ax.grid(axis='y', linestyle='--', alpha=0.5)

    import matplotlib.lines as mlines
    star = mlines.Line2D([], [], color='gold', marker='*', linestyle='None', markersize=10, markeredgecolor='black', label='Original Z-Score (100% Data)')
    mean_line = mlines.Line2D([], [], color='red', linewidth=2, label='Mean Modular Z-Score (80% Data)')
    ax.legend(handles=[star, mean_line], loc='upper right')

    violin_path = out_dir / "batch_stability_violin.png"
    fig.tight_layout()
    fig.savefig(violin_path, dpi=300)
    plt.close(fig)
    generated_files.append(violin_path)

    return generated_files