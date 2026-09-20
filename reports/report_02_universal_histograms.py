# ==============================================================================
# report_02_universal_histograms.py
# KishLattice Visual Suite Plugin
# 
# A universal fleet-wide histogram generator. Reads domain_manifest.json to
# dynamically plot the scalar density distribution for ALL domains, overlaying
# active N/pi registers to automatically visually identify single, dual, or
# triple peaks.
# 
# VOL 11 UPGRADE:
# - Decoupled hardcoded harmonics (reads configs/harmonic_targets.json).
# - Direct ingest of z_scores_master.json (supports Chaos & Synthetic Z-scores).
# - Deprecated the legacy text-based log parser.
# - Preserved streaming unified master scalar extraction.
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

def load_manifest(reports_dir):
    manifest_path = reports_dir / "domain_manifest.json"
    if not manifest_path.exists(): return {}
    with manifest_path.open("r", encoding="utf-8") as f: return json.load(f)

def load_configs(root_path):
    configs = {"harmonics": {}}
    harm_cfg = root_path / "configs" / "harmonic_targets.json"
    if harm_cfg.exists():
        with harm_cfg.open("r", encoding="utf-8") as f:
            configs["harmonics"] = json.load(f)
    return configs

def load_scalars_from_unified_master(unified_master_path, target_domains):
    domain_scalars = {d: [] for d in target_domains}
    if not unified_master_path or not Path(unified_master_path).exists(): return domain_scalars

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
            except: continue
    return domain_scalars

def generate(context):
    out_dir = context.get("output_dir")
    unified_master_path = context.get("unified_master_path")
    root_path = out_dir.parents[3]
    reports_dir = root_path / "reports"

    manifest = load_manifest(reports_dir)
    generated_files = []

    if not manifest: return generated_files

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

    if not z_scores_dict: return generated_files

    target_domains = set(manifest.keys())
    domain_scalars = load_scalars_from_unified_master(unified_master_path, target_domains)

    for domain, meta in manifest.items():
        try:
            if domain not in z_scores_dict: continue

            z_data = z_scores_dict[domain]
            z_scores = z_data.get("chaos_z", []) if isinstance(z_data, dict) else z_data

            strong_labels = [list(HARMONICS.keys())[i] for i, z in enumerate(z_scores) if z >= 5.0]

            scalars = domain_scalars.get(domain, [])
            if not scalars: continue

            scalars = np.array(scalars)
            fig, ax = plt.subplots(figsize=(14, 7))

            highest_register_val = max(HARMONICS.values())
            x_max = max(np.max(scalars) * 1.1, highest_register_val + 0.5)
            bins = np.arange(0, x_max, 0.05)

            ax.hist(scalars, bins=bins, color='lightgrey', edgecolor='black', linewidth=0.5, alpha=0.7)

            for label, val in HARMONICS.items():
                if label in strong_labels:
                    ax.axvline(x=val, color='#1f77b4', linestyle='-', linewidth=2.5, zorder=5)
                    ax.text(val + 0.05, ax.get_ylim()[1] * 0.9, f"STRONG\n{label}", color='#1f77b4', fontweight='bold', fontsize=10, rotation=90)
                else:
                    ax.axvline(x=val, color='gray', linestyle='--', linewidth=0.5, alpha=0.4, zorder=1)

            annotation_text = (
                "UNIVERSAL HARMONIC HISTOGRAM:\n"
                "\u2022 Grey Histogram: Pipeline scalar_klc positional density.\n"
                "\u2022 Solid Blue Lines: Confirmed STRONG registers (Z \u2265 5.0).\n\n"
                "NOTE ON 24-CELL COUPLING:\n"
                "STRONG registers mark 24-cell harmonic coupling excess\n"
                "above the chaos null baseline \u2014 a resonance measurement in the\n"
                "24-cell container \u2014 not positional density in scalar space."
            )
            props = dict(boxstyle='round,pad=0.6', facecolor='white', edgecolor='black', alpha=0.9)
            ax.text(0.98, 0.95, annotation_text, transform=ax.transAxes, fontsize=9, verticalalignment='top', horizontalalignment='right', bbox=props, family='monospace')

            ax.set_xlim(0, x_max)
            ax.set_xlabel("Scalar Modulus (N/\u03c0)", fontsize=12)
            ax.set_ylabel("Record Count", fontsize=12)
            ax.set_title(f"{meta['title']}\nScalar Distribution and Multi-Peak Detection (n={len(scalars):,})", fontsize=14, fontweight='bold')

            hist_path = out_dir / f"histogram_{domain}.png"
            fig.tight_layout()
            fig.savefig(hist_path, dpi=300)
            plt.close(fig)
            generated_files.append(hist_path)

        except Exception as e:
            print(f"        [FAIL] Error plotting histogram for {domain}: {e}")
        finally:
            plt.close('all')

    return generated_files