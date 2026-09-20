#!/usr/bin/env python3
# ==============================================================================
# build_universal_energy.py
# 
# THEORETICAL CONTEXT & THE "ECHOES OF THE CONTAINER" POSTULATE:
# ------------------------------------------------------------------------------
# In previous runs, the 1D Period Engine detected a dense harmonic chord (12/pi) 
# across 28 decades of angular frequency (Hertz). However, unstructured scalar 
# aggregation washed out into background noise. 
#
# This script constructs the "Universal Energy Lake". It tests the postulate that
# the lattice signature is not an artifact of angular frequency alone, but is 
# fundamentally etched into the energy density thresholds of the universe.
#
# By leveraging E = mc^2 = hf, we can map distinct physical state transitions 
# onto a single dimensionally invariant axis: Electron-Volts (eV). 
# 
# If the period engine detects the 16/pi or 12/pi harmonics in this pure-eV 
# manifold, it strongly supports the hypothesis that human mathematical normalizations
# (Form C) do not "inject" structure, but rather "mirror" the inherent geometry 
# of the physical container they are attempting to describe.
# ==============================================================================
import os
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IN_DIR = ROOT / "lakes" / "inputs_promoted"
OUT_DIR = ROOT / "lakes1d_period" / "inputs_promoted"
OUT_FILE = OUT_DIR / "L_universal_energy_promoted.jsonl"

# The targeted schema map. We only extract specific thermodynamic thresholds,
# ensuring we compare apples to apples across the quantum and macro domains.
ENERGY_SOURCES = [
    # --- BASELINE EV (Multiplier: 1.0) ---
    {"file": "q8_ionisation_promoted.jsonl", "key": "ionisation_energy_ev", "mult": 1.0, "desc": "Atomic Ionisation"},
    {"file": "L_emission_nist_promoted.jsonl", "key": "klghs_transition_energy_eV", "mult": 1.0, "desc": "NIST Quantum Transitions"},
    {"file": "L_fermi_extended_promoted.jsonl", "key": "fermi_energy_ev", "mult": 1.0, "desc": "Solid-State Fermi Levels"},
    {"file": "L_auger_electrons_promoted.jsonl", "key": "energy_ev", "mult": 1.0, "desc": "Auger Electron Emissions"},
    {"file": "L_compton_electrons_promoted.jsonl", "key": "energy_ev", "mult": 1.0, "desc": "Compton Scattering Thresholds"},
    {"file": "L_conversion_electrons_promoted.jsonl", "key": "energy_ev", "mult": 1.0, "desc": "Internal Conversion Electrons"},
    
    # --- KILO-EV (Multiplier: 10^3) ---
    {"file": "L_beta_decay_promoted.jsonl", "key": "beta_endpoint_kev", "mult": 1e3, "desc": "Nuclear Beta Decay Endpoints"},
    
    # --- MEGA-EV (Multiplier: 10^6) ---
    {"file": "q4_nuclear_promoted.jsonl", "key": "binding_energy_mev_per_A", "mult": 1e6, "desc": "Nuclear Binding Energy per Nucleon"},
    
    # --- GIGA-EV (Multiplier: 10^9) ---
    # Using E=mc^2 to equate invariant mass to energy states
    {"file": "h1_cern_lhc_promoted.jsonl", "key": "invariant_mass_gev", "mult": 1e9, "desc": "LHC Invariant Mass Thresholds"}
]

def safe_extract(record, key):
    """Checks top-level and common payload nesting for the targeted key."""
    if key in record:
        return record[key]
    if "_raw_payload" in record and key in record["_raw_payload"]:
        return record["_raw_payload"][key]
    if "geometry_payload" in record and key in record["geometry_payload"]:
        return record["geometry_payload"][key]
    return None

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not IN_DIR.exists():
        print(f"[!] Promoted inputs directory not found: {IN_DIR}")
        return

    print("================================================================")
    print(" BUILDING UNIVERSAL ENERGY LAKE (eV)")
    print("================================================================")
    
    total_records = 0
    energy_values = []
    
    with open(OUT_FILE, "w", encoding="utf-8") as out_f:
        for src in ENERGY_SOURCES:
            src_path = IN_DIR / src["file"]
            if not src_path.exists():
                print(f"[!] Skipping {src['file']} - not found.")
                continue
                
            domain_records = 0
            original_domain = src["file"].replace("_promoted.jsonl", "")
            
            with open(src_path, "r", encoding="utf-8") as in_f:
                for line in in_f:
                    line = line.strip()
                    if not line: continue
                    
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                        
                    raw_val = safe_extract(rec, src["key"])
                    
                    if raw_val is None:
                        continue
                        
                    try:
                        val = float(raw_val)
                    except (ValueError, TypeError):
                        continue
                        
                    if val <= 0 or not math.isfinite(val):
                        continue
                        
                    # Apply multiplier to convert everything to pure eV
                    ev_value = val * src["mult"]
                    
                    master_rec = {
                        "entity_id": rec.get("entity_id", rec.get("id", f"energy_{total_records}")),
                        "domain": "universal_energy",  # Unified for the logifier
                        "lake_id": "L_universal_energy",
                        "klghs_x": ev_value,
                        "meta": {
                            "original_domain": original_domain,
                            "source_file": src["file"],
                            "extracted_field": src["key"],
                            "raw_value": val,
                            "multiplier": src["mult"],
                            "description": src["desc"]
                        }
                    }
                    
                    out_f.write(json.dumps(master_rec) + "\n")
                    energy_values.append(ev_value)
                    total_records += 1
                    domain_records += 1
                    
            print(f"  -> {original_domain}: {domain_records:,} records ({src['desc']})")

    if energy_values:
        log_ev = [math.log(x) for x in energy_values]
        span = max(log_ev) - min(log_ev)
        
        print("\n================================================================")
        print(f"[*] SUCCESS: Compiled {total_records:,} records into Universal Energy Lake.")
        print(f"[*] Energy Bounds: {min(energy_values):.4e} eV to {max(energy_values):.4e} eV")
        print(f"[*] Log-Span: {span:.2f} units ({(span/math.log(10)):.2f} decades)")
        print(f"[*] Saved to: {OUT_FILE}")
        print("================================================================\n")

if __name__ == "__main__":
    main()