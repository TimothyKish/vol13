# ==============================================================================
# report_02_bridge_map.py
# KishLattice Visual Suite Plugin
#
# Builds a Force-Directed Network Graph of the Unified Universe.
# Nodes are physical domains (sized by their Peak Z-Score).
# Edges are shared Kinematic Resonances (colored by their specific N/pi register).
#
# VOL 11 UPGRADE:
# - Aligned with Vol 11 Sovereign header format.
# - Decoupled hardcoded harmonics (reads configs/harmonic_targets.json).
# - Direct ingest of z_scores_master.json (supports Chaos & Synthetic Z-scores).
# - Deprecated the legacy text-based log parser.
# - Dynamic color generation fallback for unknown harmonic registers.
# - FIX: Explicit NetworkX node initialization to prevent KeyError: 'size'.
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
import matplotlib.colors as mcolors
import networkx as nx
from pathlib import Path

PI = math.pi

REGISTER_COLORS = {
    "7/pi": "#9400D3", "12/pi": "#4B0082", "13/pi": "#8A2BE2", 
    "16/pi": "#0000FF", "17/pi": "#00FF00", "18/pi": "#32CD32", 
    "19/pi": "#FFD700", "20/pi": "#FFA500", "21/pi": "#FF8C00", 
    "22/pi": "#FF4500", "24/pi": "#FF0000", "25/pi": "#B22222"
}

def get_color_for_register(reg_str):
    if reg_str in REGISTER_COLORS:
        return REGISTER_COLORS[reg_str]
    cmap = plt.get_cmap('tab20')
    idx = hash(reg_str) % 20
    return mcolors.to_hex(cmap(idx))

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

def generate(context):
    out_dir = context.get("output_dir")
    root_path = out_dir.parents[3] 
    generated_files = []

    print("    -> Rendering Force-Directed Harmonic Bridge Map...")
    
    manifest = load_manifest(root_path / "reports")
    if not manifest: return generated_files

    configs = load_configs(root_path)
    harmonics_cfg = configs["harmonics"]
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

    if not z_scores_dict: return generated_files

    G = nx.Graph()
    active_registers = set()

    for dom_a, meta_a in manifest.items():
        if dom_a not in z_scores_dict: continue
        z_data_a = z_scores_dict[dom_a]
        z_scores_a = z_data_a.get("chaos_z", []) if isinstance(z_data_a, dict) else z_data_a
        if not z_scores_a: continue
        
        max_z_a = max(z_scores_a)
        if max_z_a < 5.0: continue 
        
        best_idx_a = z_scores_a.index(max_z_a)
        if best_idx_a >= len(HARMONICS): continue
        best_reg_a = HARMONICS[best_idx_a]
        
        if dom_a not in G:
            G.add_node(dom_a, size=max_z_a)
            
        for dom_b, meta_b in manifest.items():
            if dom_a == dom_b: continue
            if dom_b not in z_scores_dict: continue
            
            z_data_b = z_scores_dict[dom_b]
            z_scores_b = z_data_b.get("chaos_z", []) if isinstance(z_data_b, dict) else z_data_b
            if not z_scores_b: continue
            
            max_z_b = max(z_scores_b)
            if max_z_b < 5.0: continue
            
            best_idx_b = z_scores_b.index(max_z_b)
            if best_idx_b >= len(HARMONICS): continue
            best_reg_b = HARMONICS[best_idx_b]
            
            if best_reg_a == best_reg_b:
                # Explicitly add dom_b before drawing edge to ensure size is preserved
                if dom_b not in G:
                    G.add_node(dom_b, size=max_z_b)
                if not G.has_edge(dom_a, dom_b):
                    G.add_edge(dom_a, dom_b, weight=max_z_a + max_z_b, register=best_reg_a)
                    active_registers.add(best_reg_a)

    if G.number_of_nodes() == 0:
        return generated_files

    fig, ax = plt.subplots(figsize=(16, 16))
    pos = nx.spring_layout(G, k=0.45, iterations=60, seed=42)
    
    edges = G.edges(data=True)
    edge_colors = [get_color_for_register(d['register']) for u, v, d in edges]
    edge_widths = [max(1.0, math.log(d['weight'] + 1)) * 1.5 for u, v, d in edges]
    nx.draw_networkx_edges(G, pos, ax=ax, edgelist=edges, edge_color=edge_colors, width=edge_widths, alpha=0.6)
    
    nodes = G.nodes(data=True)
    # Added .get('size', 1.0) as a safe fallback
    sizes = [max(50, d.get('size', 1.0) * 50) for n, d in nodes]
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color='#333333', node_size=sizes, edgecolors='white', linewidths=1.5)
    
    labels = {n: n.replace('_', '\n') for n in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels=labels, ax=ax, font_size=9, font_color='black', font_weight='bold', 
                            bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, pad=0.5))

    import matplotlib.lines as mlines
    legend_handles = []
    sorted_active = sorted(list(active_registers), key=lambda x: int(x.split('/')[0]))
    for reg in sorted_active:
        color = get_color_for_register(reg)
        legend_handles.append(mlines.Line2D([], [], color=color, linewidth=4, label=f"{reg} Bridge"))
        
    if legend_handles:
        ax.legend(handles=legend_handles, loc='upper left', title="Kinematic Bridges", framealpha=0.9)

    ax.set_title("Volume 11 Harmonic Bridge Map\nForce-Directed Clustering of Unified Physical Domains", fontsize=18, fontweight='bold')
    ax.axis('off')
    
    props = dict(boxstyle='round,pad=0.6', facecolor='white', edgecolor='black', alpha=0.85)
    ax.text(0.98, 0.02, "Nodes: Physical Domains (Sized by Peak Z-Score)\nEdges: Shared Structural Resonance", 
            transform=ax.transAxes, fontsize=10, verticalalignment='bottom', horizontalalignment='right', 
            bbox=props, family='monospace')

    map_path = out_dir / "bridge_map_full.png"
    fig.tight_layout()
    fig.savefig(map_path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    generated_files.append(map_path)

    return generated_files