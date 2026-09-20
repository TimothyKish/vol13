"""
TEMPLATE: How to write a KishLattice Reporting Plugin.
Drop this into vol10/reports/ and the engine will run it automatically.
"""
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

def generate(context):
    """
    The engine passes a 'context' dictionary containing:
      - context["pinch_table"] (dict)
      - context["sweep_results"] (dict)
      - context["output_dir"] (Path object)
      - context["unified_master_path"] (Path object)
    """
    
    # 1. Extract what you need
    pinch = context["pinch_table"]
    out_dir = context["output_dir"]
    
    generated_files = []
    
    # 2. DO YOUR PLOTTING HERE (Matplotlib, Seaborn, etc.)
    # fig = plt.figure()
    
    # 3. Save to the isolated output directory
    # filepath = out_dir / "my_custom_chart.pdf"
    # fig.savefig(filepath)
    # generated_files.append(filepath)
    
    # 4. Return the list of created files so the engine can log them
    return generated_files