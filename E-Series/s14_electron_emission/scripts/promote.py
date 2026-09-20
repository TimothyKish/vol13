#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
promote.py — KLGHS promotion step
Aligned with Atlas Aurora Kish architecture.
"""

import json
import os

RAW_PATH = "../lake/raw/nist_asd_emission_Z1_to_Z18.jsonl"
PROMOTED_PATH = "../lake/promoted/nist_asd_promoted.jsonl"

C_CM_PER_S = 2.99792458e10
CM1_TO_EV = 1 / 8065.54429

VERTEX_CLASS = {
    "H I": 2, "He I": 2, "Li I": 4, "Be I": 4, "B I": 4, "C I": 4,
    "N I": 4, "O I": 4, "F I": 4, "Ne I": 4, "Na I": 8, "Mg I": 8,
    "Al I": 8, "Si I": 8, "P I": 8, "S I": 8, "Cl I": 8, "Ar I": 8
}

def clean_numeric(value):
    """Clean NIST numeric strings like =""0.0000"", ""[109610.2232]"", etc."""
    if value is None:
        return None

    v = str(value)

    # Remove NIST artifacts
    for junk in ["=", "\"", "'", "[", "]"]:
        v = v.replace(junk, "")

    v = v.strip()

    if v == "":
        return None

    try:
        return float(v)
    except ValueError:
        return None


def promote_record(raw):
    spec = raw["element"]

    # Clean Ei/Ek
    ei = clean_numeric(raw.get("Ei(cm-1)"))
    ek = clean_numeric(raw.get("Ek(cm-1)"))

    if ei is None or ek is None:
        return None

    delta_wn = ek - ei
    if delta_wn <= 0:
        return None

    # Correct physics path: wavenumber → Hz
    freq_hz = delta_wn * C_CM_PER_S

    # Convenience: eV
    energy_eV = delta_wn * CM1_TO_EV

    # Vertex class
    if spec not in VERTEX_CLASS:
        return None

    vertex_class = VERTEX_CLASS[spec]

    promoted = {
        "element": spec,
        "Z": raw["Z"],
        "raw_row_index": raw["raw_row_index"],
        "source": raw["source"],
        "source_access_date": raw["source_access_date"],

        "Ei_cm1": ei,
        "Ek_cm1": ek,
        "delta_wavenumber_cm1": delta_wn,

        "klghs_transition_freq_Hz": freq_hz,
        "klghs_transition_energy_eV": energy_eV,
        "klghs_vertex_class": vertex_class,
        "klghs_natural_unit": "Hz",
        "klghs_transform": "log_standard",
        "klghs_domain": "electron_transitional",
        "predicted_register": "25/pi",

        "obs_wl_vac_nm": raw.get("obs_wl_vac(nm)"),
        "ritz_wl_vac_nm": raw.get("ritz_wl_vac(nm)"),
        "conf_i": raw.get("conf_i"),
        "term_i": raw.get("term_i"),
        "conf_k": raw.get("conf_k"),
        "term_k": raw.get("term_k"),
        "Aki_s^-1": raw.get("Aki(s^-1)"),
        "intens": raw.get("intens"),
        "Acc": raw.get("Acc"),
        "tp_ref": raw.get("tp_ref"),
        "line_ref": raw.get("line_ref"),
    }

    return promoted


def promote_lake():
    print("[PROMOTE] Starting promotion step...\n")

    os.makedirs(os.path.dirname(PROMOTED_PATH), exist_ok=True)

    total_raw = 0
    total_promoted = 0
    total_excluded = 0

    with open(RAW_PATH, "r", encoding="utf-8") as raw_file, \
         open(PROMOTED_PATH, "w", encoding="utf-8") as out:

        for line in raw_file:
            total_raw += 1
            raw = json.loads(line)

            promoted = promote_record(raw)
            if promoted is None:
                total_excluded += 1
                continue

            out.write(json.dumps(promoted) + "\n")
            total_promoted += 1

    print(f"[PROMOTE] Raw records:      {total_raw}")
    print(f"[PROMOTE] Promoted records: {total_promoted}")
    print(f"[PROMOTE] EXCLUDED:         {total_excluded}")
    print("\n[PROMOTE] Complete.\n")


if __name__ == "__main__":
    promote_lake()
