# ==============================================================================
# report_09_floor_smear.py
# KishLattice Visual Suite Plugin
#
# The 4/pi Investigation. Isolates all records in the "Floor Zone" (scalar < 5/pi)
# and plots a high-resolution distribution to determine if 4/pi is truly empty,
# or if physical records are smeared across the boundary without locking.
#
# VOL 11 UPGRADE:
# - Aligned with Vol 11 Sovereign header format.
# - Ported Single-Pass Streaming architecture to read directly from 
#   unified_master, ensuring exact 1:1 scalar parity with the pinch stage
#   and drastically reducing disk I/O load.
# - Dynamically patches legacy manifests for the B4/B5 Sovereign Split.
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
FIVE_PI = 5.0 / PI
FOUR_PI = 4.0 / PI

def load_manifest(reports_dir):
    manifest_path = reports_dir / "domain_manifest.json"
    if not manifest_path.exists(): 
        return {}
    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    # --- VOL 11 SOVEREIGN SPLIT PATCH ---
    # Automatically upgrade the manifest in memory so the engine plots the new lakes
    if "biology_backbone" in manifest:
        manifest.pop("biology_backbone")
        
    # Inject the new sovereign domains if they aren't already there
    if "biology_backbone_top8000" not in manifest:
        manifest["biology_backbone_top8000"] = {
            "title": "B4 PDB Protein Backbone (Top8000 High-Res)",
            "file": "b4_pdb_protein_promoted.jsonl"
        }
    if "biology_backbone_full" not in manifest:
        manifest["biology_backbone_full"] = {
            "title": "B5 PDB Protein Backbone (Full RCSB Catalog)",
            "file": "b5_pdb_full_protein_promoted.jsonl"
        }
    # ------------------------------------
    
    return manifest

def load_scalars_from_unified_master(unified_master_path, target_domains):
    """
    Stream through the unified master ONCE and collect scalar_klc values
    for all target domains simultaneously to eliminate multi-file I/O overhead.
    """
    domain_scalars = {d: [] for d in target_domains}
    
    if not unified_master_path or not Path(unified_master_path).exists():
        print("        [WARN] unified_master_path missing or invalid.")
        return domain_scalars

    master_path = Path(unified_master_path)
    print("        [DATA] Streaming unified master for scalar_klc values...")
    
    with master_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
                domain = rec.get("domain")
                if domain in domain_scalars:
                    sc = rec.get("scalar_klc")
                    if sc is not None:
                        sc_float = float(sc)
                        if math.isfinite(sc_float) and sc_float > 0:
                            domain_scalars[domain].append(sc_float)
            except (json.JSONDecodeError, ValueError, TypeError):
                continue

    return domain_scalars

def generate(context):
    out_dir = context.get("output_dir")
    unified_master_path = context.get("unified_master_path")
    root_path = out_dir.parents[3] 
    generated_files = []

    print("    -> Investigating the 4/pi Floor Smear...")
    
    manifest = load_manifest(root_path / "reports")
    if not manifest:
        print("       [SKIP] domain_manifest.json not found.")
        return generated_files

    target_domains = set(manifest.keys())
    domain_scalars = load_scalars_from_unified_master(unified_master_path, target_domains)

    for domain, meta in manifest.items():
        try:
            scalars = domain_scalars.get(domain, [])
            total_records = len(scalars)
            
            if total_records == 0:
                continue
                
            floor_scalars = [s for s in scalars if s < FIVE_PI]
            
            if not floor_scalars:
                continue
                
            floor_scalars = np.array(floor_scalars)
            percent_in_floor = (len(floor_scalars) / total_records) * 100

            print(f"       [PLOT] {domain}: {len(floor_scalars)} records found in Floor Zone ({percent_in_floor:.2f}% of total).")

            # Plotting the Floor Zone
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # High resolution bins for just the 0.0 to 5/pi range
            bins = np.arange(0, FIVE_PI, 0.02)
            ax.hist(floor_scalars, bins=bins, color='#d3d3d3', edgecolor='black', linewidth=0.5, alpha=0.8)

            # Mark the Harmonic Registers
            ax.axvline(x=FOUR_PI, color='red', linestyle='-', linewidth=2, label="4/π Floor Register")
            ax.axvline(x=FIVE_PI, color='blue', linestyle='--', linewidth=1.5, label="5/π Boundary")
            
            # Formatting
            ax.set_xlim(0, FIVE_PI)
            ax.set_xlabel("Scalar Modulus (N/π)", fontsize=12)
            ax.set_ylabel("Record Count", fontsize=12)
            ax.set_title(f"Floor Zone Smear Analysis: {meta['title']}\nOnly showing data < 5/π ({percent_in_floor:.1f}% of domain total)", fontsize=14, fontweight='bold')
            
            ax.legend(loc='upper right')
            ax.grid(True, linestyle='--', alpha=0.5)

            smear_path = out_dir / f"floor_smear_{domain}.png"
            fig.tight_layout()
            fig.savefig(smear_path, dpi=300)
            plt.close(fig)
            generated_files.append(smear_path)
            
        except Exception as e:
            print(f"       [FAIL] Error plotting floor smear for {domain}: {e}")
            continue

    return generated_files