# ==============================================================================
# report_01_domain_Ramachandran_scatters.py
# KishLattice Visual Suite Plugin
#
# Universal scatter-plot generator utilizing actual JSON Z-Scores
# and deep-payload extraction for promoted lakes.
#
# VOL 11 UPGRADE:
# - Decoupled hardcoded domains (reads reports/report_config.json).
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
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import matplotlib.patches as mpatches
from pathlib import Path

PI = math.pi
LOG_K = math.log(16.0 / PI)
TOLERANCE = 0.106

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

def generate(context):
    out_dir = context.get("output_dir")
    generated_files = []

    print("    -> Plotting Ramachandran Principle Scatters...")

    root_path = out_dir.parents[3]
    manifest = load_manifest(root_path / "reports")
    promoted_dir = root_path / "lakes" / "inputs_promoted"

    if not manifest:
        print("       [SKIP] domain_manifest.json not found.")
        return generated_files

    # VOL 11: Dynamic Config Loading
    configs = load_configs(root_path)
    report_cfg = configs["report"]
    harmonics_cfg = configs["harmonics"]

    # 1. Setup Ramachandran Domains dynamically (PATCHED FOR SOVEREIGN SPLIT)
    ram_domains = report_cfg.get("ramachandran_domains", [
        "biology_backbone_top8000", "biology_backbone_full", "subnuclear_mass", "orbital_ttv"
    ])

    # 2. Setup Harmonics dynamically
    if harmonics_cfg and "registers" in harmonics_cfg:
        registers = harmonics_cfg["registers"]
        HARMONICS = [f"{n}/pi" for n in registers]
    else:
        # Fallback to Vol 10 standard
        HARMONICS = [f"{n}/pi" for n in range(4, 27)]

    # 3. Z-Scores Loading (gracefully handles Vol 11 context injection or direct file read)
    z_scores_dict = context.get("z_scores", {})
    if not z_scores_dict:
        z_path = root_path / "lakes" / "unified" / "z_scores_master.json"
        if z_path.exists():
            with z_path.open("r", encoding="utf-8") as f:
                z_scores_dict = json.load(f)

    for domain, meta in manifest.items():
        # Vol 11: Use report_config.json routing instead of hardcoding
        if domain not in ram_domains:
            continue

        promoted_file = promoted_dir / meta["file"]
        if not promoted_file.exists():
            print(f"       [WARN] Missing promoted lake for {domain}")
            continue

        try:
            scalars = []
            with promoted_file.open("r", encoding="utf-8") as f:
                for line in f:
                    rec = json.loads(line)
                    s = rec.get("scalar_klc")
                    if s is not None:
                        scalars.append(s)

            # Vol 11 Dual Z-Score compatibility
            z_data = z_scores_dict.get(domain, {})
            if isinstance(z_data, dict):
                # Vol 11 format: {"chaos_z": [...], "synthetic_z": [...]}
                # Primary visualization driven by chaos_z to match original
                z_scores = z_data.get("chaos_z", [])
            else:
                # Vol 10 fallback: flat list [...]
                z_scores = z_data

            max_z = max(z_scores) if z_scores else 0
            best_reg = "N/A"
            if max_z > 0 and len(z_scores) == len(HARMONICS):
                best_reg = HARMONICS[z_scores.index(max_z)]

            print(f"       [PLOT] {domain} (n={len(scalars):,}) | Peak Z: {max_z:.2f} at {best_reg}")

            fig, ax = plt.subplots(figsize=(12, 6))

            # --- The Physical Mapping ---
            # Y-axis is arbitrary uniform jitter to create a density scatter strip
            y_jitter = np.random.uniform(0, 1, len(scalars))

            # Plot the actual scalars
            ax.scatter(scalars, y_jitter, alpha=0.3, s=2, color='black', label="Observed Record")

            # Overlay the 24-Cell Locking Regions (Colored Bands)
            for i, h_str in enumerate(HARMONICS):
                n_val = float(h_str.split('/')[0])
                target = n_val / PI

                # If this harmonic corresponds to the peak Z-score, highlight it brightly
                if h_str == best_reg and max_z >= 5.0:
                    band_color = 'red'
                    band_alpha = 0.25
                else:
                    band_color = 'blue'
                    band_alpha = 0.08

                # The mathematical lock zone where physical states are "permitted"
                ax.axvspan(target - TOLERANCE, target + TOLERANCE, color=band_color, alpha=band_alpha)

            # Add proxy lines for exact center nodes
            for h_str in HARMONICS:
                n_val = float(h_str.split('/')[0])
                target = n_val / PI
                ax.axvline(x=target, color='white', linestyle=':', linewidth=0.5, alpha=0.5)

            ax.set_yticks([]) # Hide Y axis as it's just jitter
            ax.set_ylim(-0.1, 1.1)

            # Formatting
            x_max = max(scalars) if scalars else 10
            x_max = min(x_max, 9.0) # Cap view at 26/pi range
            ax.set_xlim(1.0, x_max)

            ax.set_xlabel("Scalar Modulus (N/π)", fontsize=12)
            ax.set_title(f"{meta['title']}\nStructural Validation of the 24-Cell Ramachandran Kinematic Locks\n(n={len(scalars):,})", fontsize=14, fontweight='bold')

            # Custom Legend
            record_dot = mlines.Line2D([], [], color='black', marker='o', linestyle='None', markersize=5, alpha=0.5, label='Physical Record')
            lock_band = mpatches.Patch(color='blue', alpha=0.15, label='Geometric Permitted Zone (Lock)')
            peak_band = mpatches.Patch(color='red', alpha=0.3, label=f'Dominant Structural Resonance ({best_reg}, Z={max_z:.1f})')

            leg = ax.legend(handles=[record_dot, lock_band, peak_band], loc='upper left', framealpha=0.9)
            for lh in leg.legend_handles:
                lh.set_alpha(1)
            ax.grid(True, linestyle='--', alpha=0.5)

            scatter_path = out_dir / f"scatter_{domain}.png"

            # --- RAMACHANDRAN LOCK ANNOTATION BOX ---
            annotation_text = (
                "THE RAMACHANDRAN LOCK PRINCIPLE:\n"
                "• Grey Sweep: Raw measurement projected into scalar space.\n"
                "• Colored Bands (Locks): 'Permitted' geometries where physical states\n"
                "  achieve kinematic resonance at exact N/π integers.\n"
                "• Empty Gaps (Voids): 'Forbidden' geometries (dissonance/instability).\n"
                "The 1D scalar lattice acts as a structural filter for physical reality."
            )

            # Place a semi-transparent text box in the bottom right corner
            props = dict(boxstyle='round,pad=0.6', facecolor='white', edgecolor='black', alpha=0.85)
            ax.text(0.98, 0.03, annotation_text, transform=ax.transAxes, fontsize=9,
                    verticalalignment='bottom', horizontalalignment='right', bbox=props,
                    family='monospace')

            fig.tight_layout()
            fig.savefig(scatter_path, dpi=300)
            plt.close(fig)
            generated_files.append(scatter_path)

        except Exception as e:
            print(f"       [FAIL] Critical error plotting {domain}: {e}")
            continue

    return generated_files