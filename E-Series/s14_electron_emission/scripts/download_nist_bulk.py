#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
download_nist_bulk.py — 403-proof NIST ASD downloader
Uses a browser-like session with cookies, referer, and user-agent.
"""

import os
import requests
import urllib.parse

OUT_DIR = "../nist_bulk"
os.makedirs(OUT_DIR, exist_ok=True)

ELEMENTS = [
    "H I", "He I", "Li I", "Be I", "B I", "C I",
    "N I", "O I", "F I", "Ne I", "Na I", "Mg I",
    "Al I", "Si I", "P I", "S I", "Cl I", "Ar I"
]

BASE = "https://physics.nist.gov/cgi-bin/ASD/lines1.pl"

PARAMS = (
    "&output_type=0"
    "&low_w=&upp_w=&unit=1"
    "&submit=Retrieve+Data"
    "&de=0&plot_out=0&I_scale_type=1"
    "&format=2"
    "&line_out=0"
    "&include_Ritz_E1=1"
    "&remove_js=on"
    "&en_unit=0"
    "&output=0"
    "&bibrefs=1"
    "&page_size=15"
    "&show_obs_wl=1"
    "&show_calc_wl=1"
    "&show_wn=1"
    "&unc_out=1"
    "&order_out=0"
    "&max_low_enrg=&show_av=2&max_upp_enrg="
    "&tsb_value=0"
    "&min_str=&A_out=0&intens_out=on&max_str="
    "&allowed_out=1&forbid_out=1"
    "&min_accur=&min_intens="
    "&conf_out=on&term_out=on&enrg_out=on&J_out=on&g_out=on"
)

def download_spectrum(spec):
    encoded = urllib.parse.quote_plus(spec)
    url = f"{BASE}?spectra={encoded}{PARAMS}"

    filename = f"{spec.replace(' ', '_')}_lines.ascii"
    path = os.path.join(OUT_DIR, filename)

    print(f"[DOWNLOAD] {spec} → {filename}")

    session = requests.Session()

    # Step 1: GET the form to obtain cookies
    session.get(
        "https://physics.nist.gov/PhysRefData/ASD/lines_form.html",
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://physics.nist.gov/PhysRefData/ASD/lines_form.html"
        }
    )

    # Step 2: GET the actual data using the cookie
    response = session.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://physics.nist.gov/PhysRefData/ASD/lines_form.html"
        }
    )

    if response.status_code == 200:
        with open(path, "w", encoding="utf-8") as f:
            f.write(response.text)
        print(f"[OK] Saved {filename}\n")
    else:
        print(f"[ERROR] {spec} → HTTP {response.status_code}\n")


def main():
    print("[BUILD] Downloading NIST ASD bulk files (neutral atoms)...\n")

    for spec in ELEMENTS:
        download_spectrum(spec)

    print("[BUILD] Complete.\n")


if __name__ == "__main__":
    main()
