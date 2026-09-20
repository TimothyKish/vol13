# ==============================================================================
# report_08_subnuclear_dual.py
# KishLattice Visual Suite Plugin
#
# Analyzes the H1 CERN Di-Muon mass spectrum, mapping known Standard Model 
# resonances (J/psi, Upsilon, Z Boson) against the KLGHS scalar distribution 
# to investigate the 13/pi and 22/pi dual-peak structural lock.
#
# VOL 11 UPGRADE:
# - Aligned with Vol 11 Sovereign header format.
# - Decoupled hardcoded harmonics (reads configs/harmonic_targets.json).
# - Ported Single-Pass Streaming architecture to read directly from 
#   unified_master (domain: subnuclear_mass), ensuring 1:1 scalar parity.
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
LOG_K = math.log(16.0 / PI)

# Known Standard Model Resonances (Mass in GeV)
SM_RESONANCES = {
    "J/ψ (~3.1 GeV)": 3.1,
    "Upsilon (Υ) (~9.5 GeV)": 9.5,
    "Z Boson (~91.2 GeV)": 91.2
}

def load_configs(root_path):
    """Load harmonic targets dynamically."""
    configs = {"harmonics": {}}
    harm_cfg = root_path / "configs" / "harmonic_targets.json"
    if harm_cfg.exists():
        with harm_cfg.open("r", encoding="utf-8") as f:
            configs["harmonics"] = json.load(f)
    return configs

def load_scalars_from_unified_master(unified_master_path, target_domain):
    """
    Stream through the unified master ONCE and collect scalar_klc values
    specifically for the target bespoke domain.
    """
    scalars = []
    if not unified_master_path or not Path(unified_master_path).exists():
        print("        [WARN] unified_master_path missing or invalid.")
        return scalars

    master_path = Path(unified_master_path)
    print(f"        [DATA] Streaming unified master for {target_domain} scalars...")
    
    with master_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            try:
                rec = json.loads(line)
                if rec.get("domain") == target_domain:
                    sc = rec.get("scalar_klc")
                    if sc is not None:
                        sc_float = float(sc)
                        if math.isfinite(sc_float) and sc_float > 0:
                            scalars.append(sc_float)
            except (json.JSONDecodeError, ValueError, TypeError):
                continue

    return scalars

def generate(context):
    out_dir = context.get("output_dir")
    master_path = context.get("unified_master_path")
    root_path = out_dir.parents[3] 
    generated_files = []

    print("    -> Plotting Subnuclear Dual-Peak Resonance Map...")

    # VOL 11: Dynamic Config Loading
    configs = load_configs(root_path)
    harmonics_cfg = configs["harmonics"]

    if harmonics_cfg and "registers" in harmonics_cfg:
        registers = harmonics_cfg["registers"]
        HARMONICS = {f"{n}/pi": float(n) / PI for n in registers}
    else:
        # Fallback to Vol 10 standard
        HARMONICS = {f"{n}/pi": float(n) / PI for n in range(4, 27)}

    # Stream the scalars directly from the unified master
    scalars = load_scalars_from_unified_master(master_path, "subnuclear_mass")
    
    if not scalars:
        print("       [WARN] No records found for 'subnuclear_mass' in unified_master.")
        return generated_files

    print(f"       [PLOT] Subnuclear target located: {len(scalars):,} records.")

    fig, ax = plt.subplots(figsize=(14, 7))

    x_max = max(HARMONICS.values()) + 0.5
    bins = np.arange(0, x_max, 0.05)
    
    # Plot the raw scalar density
    ax.hist(scalars, bins=bins, color='lightgrey', edgecolor='black', linewidth=0.5, alpha=0.8)

    # Plot the Universal Harmonic Registers
    for label, val in HARMONICS.items():
        if label in ["13/pi", "22/pi"]:
            ax.axvline(x=val, color='gold', linestyle='-', linewidth=2.5, zorder=5)
            ax.text(val + 0.05, ax.get_ylim()[1] * 0.85, f"STRONG\n{label}", 
                    color='goldenrod', fontweight='bold', fontsize=10, rotation=90)
        else:
            ax.axvline(x=val, color='gray', linestyle='--', linewidth=0.5, alpha=0.4, zorder=1)

    # Plot Actual Standard Model Resonances
    for name, mass in SM_RESONANCES.items():
        # Scalarize the empirical mass (GeV)
        scalar_val = math.log(mass + 1) / LOG_K
        
        ax.axvline(x=scalar_val, color='darkred', linestyle=':', linewidth=2, zorder=6)
        ax.text(scalar_val - 0.05, ax.get_ylim()[1] * 0.85, name, 
                color='darkred', fontweight='bold', fontsize=10, rotation=90, ha='right')

    # Annotation Box
    annotation_text = (
        "SUBNUCLEAR DUAL-PEAK ANALYSIS:\n"
        "• Grey Histogram: Scalar distribution of di-muon invariant mass events.\n"
        "• Red Dotted Lines: Actual Standard Model particle resonances.\n"
        "• Gold Lines: The 13/π and 22/π registers that triggered Z > 50.\n"
        "This checks if the CMS mass distribution structurally overlaps with the lattice."
    )
    props = dict(boxstyle='round,pad=0.6', facecolor='white', edgecolor='black', alpha=0.85)
    ax.text(0.98, 0.95, annotation_text, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', horizontalalignment='right', bbox=props, family='monospace')

    ax.set_xlim(0, x_max)
    ax.set_xlabel("Scalar Modulus (N/π)", fontsize=12)
    ax.set_ylabel("Event Count", fontsize=12)
    ax.set_title("H1 CERN Di-Muon Mass Spectrum\nTesting the 13/π and 22/π Dual-Peak Architecture", fontsize=14, fontweight='bold')
    
    map_path = out_dir / "subnuclear_resonance_map.png"
    fig.tight_layout()
    fig.savefig(map_path, dpi=300)
    plt.close(fig)
    generated_files.append(map_path)

    return generated_files