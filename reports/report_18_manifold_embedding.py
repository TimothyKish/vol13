# ==============================================================================
# report_18_manifold_embedding.py
# KishLattice Visual Suite Plugin
#
# The Topological Manifold Map. Uses manifold learning (t-SNE/Isomap) to project
# the 46-dimensional dual Z-score signatures (Chaos + Synthetic) of all domains 
# into a 2D topological phase space. Proves that physical domains self-organize 
# into distinct structural clusters based on their geometric resonance.
#
# VOL 11 UPGRADE:
# - Vol 11 Sovereign header format.
# - High-dimensional dual Z-score vectorization.
# - Dynamic manifold projection.
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
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

try:
    from sklearn.manifold import TSNE
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

def load_configs(root_path):
    configs = {"report": {}}
    rep_cfg = root_path / "reports" / "report_config.json"
    if rep_cfg.exists():
        with rep_cfg.open("r", encoding="utf-8") as f:
            configs["report"] = json.load(f)
    return configs

def get_family_color(domain, domain_families):
    # Standard Vol 11 Rainbow Map colors for continuity
    colors = {
        "kinematic": "#1f77b4", "electromagnetic": "#ff7f0e", 
        "quantum_molecular": "#9467bd", "nuclear": "#d62728", 
        "biological": "#2ca02c", "galactic": "#17becf", 
        "seismic": "#8c564b", "null": "#7f7f7f"
    }
    for family, domains in domain_families.items():
        if domain in domains:
            return colors.get(family, "#333333")
            
    # Fallback heuristics
    d = domain.lower()
    if "null" in d or "np" in d: return colors["null"]
    if "seismic" in d: return colors["seismic"]
    if "bio" in d or "amino" in d: return colors["biological"]
    if "stellar" in d or "orbital" in d: return colors["kinematic"]
    return "#333333"

def generate(context):
    out_dir = context.get("output_dir")
    root_path = out_dir.parents[3] 
    generated_files = []

    print("    -> Computing 46-Dimensional Topological Embedding (t-SNE)...")

    if not SKLEARN_AVAILABLE:
        print("       [SKIP] scikit-learn not installed. Cannot compute manifold embedding.")
        print("       [TIP] Run: pip install scikit-learn")
        return generated_files

    z_scores_dict = context.get("z_scores", {})
    if not z_scores_dict:
        z_path = root_path / "lakes" / "unified" / "z_scores_master.json"
        if z_path.exists():
            with z_path.open("r", encoding="utf-8") as f:
                z_scores_dict = json.load(f)

    if not z_scores_dict:
        return generated_files

    configs = load_configs(root_path)
    domain_families = configs["report"].get("domain_families", {})

    features = []
    labels = []
    colors = []
    sizes = []

    for domain, z_data in z_scores_dict.items():
        if not isinstance(z_data, dict) or "chaos_z" not in z_data or "synthetic_z" not in z_data:
            continue
            
        cz = z_data["chaos_z"]
        sz = z_data["synthetic_z"]
        
        if len(cz) < 20 or len(sz) < 20: 
            continue
            
        # Combine Chaos and Synthetic into a single 46-D structural signature
        vector = np.array(cz + sz)
        features.append(vector)
        labels.append(domain)
        colors.append(get_family_color(domain, domain_families))
        
        # Bubble size driven by maximum peak
        sizes.append(max(20, (max(cz)**2) * 5))

    if len(features) < 5:
        print("       [SKIP] Not enough valid high-dimensional data for a manifold embedding.")
        return generated_files

    # Execute t-SNE Dimensionality Reduction
    X = np.array(features)
    perplexity = min(30, len(features) - 1)
    tsne = TSNE(n_components=2, perplexity=perplexity, random_state=42, init='pca', learning_rate='auto')
    embedding = tsne.fit_transform(X)

    fig, ax = plt.subplots(figsize=(14, 10))
    
    scatter = ax.scatter(embedding[:, 0], embedding[:, 1], s=sizes, c=colors, edgecolors='black', alpha=0.8, zorder=5)

    # Annotate points
    for i, txt in enumerate(labels):
        clean_txt = txt.replace('_', ' ').title()
        ax.annotate(clean_txt, (embedding[i, 0], embedding[i, 1]), 
                    xytext=(0, 8), textcoords='offset points', 
                    ha='center', va='bottom', fontsize=8, fontweight='bold')

    # Remove arbitrary t-SNE coordinate axes (they have no physical units)
    ax.set_xticks([])
    ax.set_yticks([])

    ax.set_title("Kish Lattice Topological Manifold Map\nt-SNE Projection of 46-Dimensional Resonance Signatures", fontsize=16, fontweight='bold')
    
    # Custom Legend for Structural Families
    import matplotlib.patches as mpatches
    unique_colors = set(colors)
    legend_elements = [mpatches.Patch(facecolor=c, edgecolor='black', label='Structural Family') for c in unique_colors]
    # We rely on visual grouping rather than explicit text here to let the data speak, 
    # but we add a watermark explaining the projection
    
    annotation_text = (
        "TOPOLOGICAL EMBEDDING:\n"
        "• Input: 46-D Tensor per domain (23 Chaos Z, 23 Synthetic Z).\n"
        "• Output: 2D t-SNE Phase Space.\n"
        "Domains that cluster tightly share identical mathematical\n"
        "architectures across the entire N/π geometric lattice."
    )
    props = dict(boxstyle='round,pad=0.6', facecolor='white', edgecolor='black', alpha=0.9)
    ax.text(0.98, 0.02, annotation_text, transform=ax.transAxes, fontsize=10,
            verticalalignment='bottom', horizontalalignment='right', bbox=props, family='monospace')

    fig.tight_layout()
    map_path = out_dir / "topological_manifold_map.png"
    fig.savefig(map_path, dpi=300)
    plt.close(fig)
    generated_files.append(map_path)

    return generated_files