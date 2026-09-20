#!/usr/bin/env python3
# ==============================================================================
# COPYRIGHT: (c) 2026 KishLattice 16/pi Initiative LLC. FOUNDER: Timothy John Kish
# Open for scientific testing / peer review. Cite "KishLattice 16/pi Initiative".
# ==============================================================================
#
# report_01_support_shapes.py  --  STARTER PLUGIN for Vera.
#
# The first period-engine figure: a grid of support histograms, one per lake,
# each annotated with its shape verdict (FILLED / TAIL-INFLATED / SPARSE-TAIL /
# SPIKED) and effective span. This is the picture Timothy noticed by eye -- how
# many lakes are heavily spiked -- made into a single publishable panel.
#
# It reads the portrait for verdicts and streams each logified lake for its
# distribution. Matplotlib only; no seaborn, no exotic deps -- runs on a potato.
#
# TEMPLATE NOTES for Vera: a plugin implements generate(context) -> [Path,...].
# The context carries: portrait (verdicts), logified_dir, output_dir, load_lnx
# (cap-aware streaming loader), registers, kg, container, run_timestamp.
# Return the list of files you created so the index records them.
# ==============================================================================
import math
from pathlib import Path

def generate(context):
    try:
        import matplotlib
        matplotlib.use("Agg")            # headless: works over SSH / no display
        import matplotlib.pyplot as plt
        import numpy as np
    except Exception as e:
        # graceful: if matplotlib absent, write a text fallback so the run still
        # produces SOMETHING rather than failing.
        out = Path(context["output_dir"]) / "support_shapes_FALLBACK.txt"
        out.write_text(f"matplotlib unavailable ({e}); install it for the figure.\n")
        return [out]

    portrait = context["portrait"]
    logified = Path(context["logified_dir"])
    load_lnx = context["load_lnx"]
    out_dir = Path(context["output_dir"])

    lakes = [k for k, v in portrait.items() if not v.get("skipped")]
    if not lakes:
        p = out_dir / "support_shapes_EMPTY.txt"
        p.write_text("no scoreable lakes in portrait.\n")
        return [p]

    # color by shape verdict -- the reader sees the artifact class at a glance
    colors = {"FILLED": "#2c7", "TAIL-INFLATED": "#fb3",
              "SPARSE-TAIL-ARTIFACT": "#e63", "SPIKED": "#c33",
              "EMPTY-OR-DEGENERATE": "#999"}

    ncol = 3
    nrow = math.ceil(len(lakes) / ncol)
    fig, axes = plt.subplots(nrow, ncol, figsize=(4*ncol, 2.6*nrow))
    axes = np.array(axes).reshape(-1)

    created = []
    for ax, lake in zip(axes, lakes):
        f = logified / f"{lake}_logified.jsonl"
        if not f.exists():
            ax.set_visible(False); continue
        lnx = load_lnx(f)
        if len(lnx) < 20:
            ax.set_visible(False); continue
        d = portrait[lake]
        shape = d.get("shape", "?")
        eff = d.get("support", {}).get("eff_span", 0.0)
        ax.hist(lnx, bins=40, color=colors.get(shape, "#68a"), edgecolor="none")
        ax.set_title(f"{lake}\n{shape}  ({eff/math.log(10):.1f} dec)", fontsize=8)
        ax.set_yticks([]); ax.tick_params(labelsize=6)
        ax.set_xlabel("ln x", fontsize=6)

    for ax in axes[len(lakes):]:
        ax.set_visible(False)

    fig.suptitle("KishLattice Period Engine -- Support Shapes by Lake\n"
                 "colour = shape verdict; green FILLED is honest single-population support",
                 fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    png = out_dir / "support_shapes.png"
    fig.savefig(png, dpi=130)
    plt.close(fig)
    created.append(png)
    return created
