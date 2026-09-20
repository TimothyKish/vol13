# ==============================================================================
# report_19_same_object_phase_scatter.py
# KishLattice Visual Suite Plugin
#
# The 2D Phase Space Grid. Dynamically pairs domains linked by the 
# "__same_object__" flag in volumes.json (e.g., Exoplanet Mass vs Radius) 
# and plots them against each other in 2D scalar space. Overlays the N/pi 
# lattice to visualize 2D intersection locking (Ramachandran Intersections).
#
# VOL 11 UPGRADE:
# - Vol 11 Sovereign header format.
# - Single-Pass Streaming architecture.
# - Dynamic volumes.json metadata parsing.
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

def get_same_object_pairs(volumes_dict):
    """Finds pairs of domains that measure the exact same physical objects."""
    pairs = []
    for vol_id, meta in volumes_dict.items():
        if not meta.get("enabled", True): continue
        if "__same_object__" in meta:
            dom_y = meta.get("domain")
            for linked_id in meta["__same_object__"]:
                linked_meta = volumes_dict.get(linked_id, {})
                if linked_meta.get("enabled", True):
                    dom_x = linked_meta.get("domain")
                    if dom_x and dom_y and dom_x != dom_y:
                        pairs.append((dom_x, dom_y))
    return list(set(pairs))

def stream_paired_scalars(unified_master_path, pairs):
    """
    Streams the unified master and attempts to pair scalars.
    Assumes preservation of row-order generation from promoted lakes.
    """
    target_domains = set([d for pair in pairs for d in pair])
    domain_scalars = {d: [] for d in target_domains}
    
    if not unified_master_path or not Path(unified_master_path).exists():
        return domain_scalars

    print(f"        [DATA] Streaming unified master for Phase Space Phase mapping...")
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

    print("    -> Plotting 2D Same-Object Phase Space Scatters...")

    configs = load_configs(root_path)
    harmonics_cfg = configs["harmonics"]
    volumes_cfg = configs["volumes"].get("volumes", {})

    if harmonics_cfg and "registers" in harmonics_cfg:
        HARMONICS = {f"{n}/pi": float(n) / PI for n in harmonics_cfg["registers"]}
    else:
        HARMONICS = {f"{n}/pi": float(n) / PI for n in range(4, 27)}

    pairs = get_same_object_pairs(volumes_cfg)
    if not pairs:
        print("       [SKIP] No '__same_object__' linkages found in volumes.json.")
        return generated_files

    domain_scalars = stream_paired_scalars(unified_master_path, pairs)

    for (dom_x, dom_y) in pairs:
        x_data = domain_scalars.get(dom_x, [])
        y_data = domain_scalars.get(dom_y, [])
        
        # We need exact 1:1 length for a phase scatter
        min_len = min(len(x_data), len(y_data))
        if min_len < 100:
            continue
            
        # Zip them safely
        X = np.array(x_data[:min_len])
        Y = np.array(y_data[:min_len])

        print(f"       [PLOT] 2D Phase Scatter: {dom_x} vs {dom_y} (n={min_len:,})")

        fig, ax = plt.subplots(figsize=(10, 10))
        
        # 2D KDE or tight scatter
        ax.scatter(X, Y, s=1, color='black', alpha=0.15)

        # Draw the 2D Lattice Grid
        for label, val in HARMONICS.items():
            # X-Axis Grid
            ax.axvline(x=val, color='blue', linestyle='--', linewidth=0.5, alpha=0.3)
            # Y-Axis Grid
            ax.axhline(y=val, color='blue', linestyle='--', linewidth=0.5, alpha=0.3)

        # Formatting to capture the primary harmonic bounding box
        x_max_val = max(X) if len(X) > 0 else 10
        y_max_val = max(Y) if len(Y) > 0 else 10
        cap = min(max(x_max_val, y_max_val) * 1.05, 9.0) # Cap at ~28/pi range
        
        ax.set_xlim(1.0, cap)
        ax.set_ylim(1.0, cap)

        ax.set_title(f"2D Geometric Intersections\n{dom_x.title()} vs {dom_y.title()}", fontsize=14, fontweight='bold')
        ax.set_xlabel(f"{dom_x.replace('_', ' ').title()} (Scalar N/π)", fontsize=12)
        ax.set_ylabel(f"{dom_y.replace('_', ' ').title()} (Scalar N/π)", fontsize=12)
        
        # Annotation Box
        props = dict(boxstyle='round,pad=0.6', facecolor='white', edgecolor='black', alpha=0.85)
        ax.text(0.98, 0.02, "Blue Grid: N/π Geometric Intersections\nDensity centers indicate 2D structural locking", 
                transform=ax.transAxes, fontsize=10, verticalalignment='bottom', horizontalalignment='right', 
                bbox=props, family='monospace')

        fig.tight_layout()
        safe_name = f"phase_scatter_{dom_x}_vs_{dom_y}".replace(" ", "_")
        plot_path = out_dir / f"{safe_name}.png"
        fig.savefig(plot_path, dpi=300)
        plt.close(fig)
        generated_files.append(plot_path)

    return generated_files