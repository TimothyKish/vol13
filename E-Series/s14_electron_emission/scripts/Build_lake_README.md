# 📘 **build_lake_README.md**

## **Overview**
This directory contains the tools for building the **NIST ASD Sovereign Spectral Lake** used in the *Geometric Electron* and *Geometric Harmonic Spectroscopy* pipelines.

Because the NIST Atomic Spectra Database (ASD) does **not** provide a stable API, the lake must be built using **manual exports** from the ASD Lines Form:

🔗 **NIST ASD Lines Form:**  
[https://physics.nist.gov/PhysRefData/ASD/lines_form.html](https://physics.nist.gov/PhysRefData/ASD/lines_form.html)

This README explains **exactly how to fill out the form**, **how to export each element**, and **how to save the files** so the pipeline can parse them.

---

# ⚠️ **Important Note About the ASD Form**
The ASD form is a **stateful CGI interface**, not an API.

This means:

- The form generates a **session token** each time you load it.
- The “Retrieve Data” button uses that session token.
- URLs copied from one session **do not always work** in the next session.
- Some elements (H, He, Li…) may work via URL, while others (Cl, S, Ar…) may fail unless the form is reloaded.

This is why you experienced:

> “Hydrogen worked, but the next element failed unless I went back to the form.”

This is normal behavior for NIST ASD.

The **correct workflow** is:

1. Load the form fresh  
2. Select the correct options  
3. Enter the element  
4. Click **Retrieve Data**  
5. Save the output page as `ELEMENT_lines.ascii`

Repeat for each element.

---

# 🧭 **How to Fill Out the ASD Lines Form**

Open:  
[https://physics.nist.gov/PhysRefData/ASD/lines_form.html](https://physics.nist.gov/PhysRefData/ASD/lines_form.html)

Then set the following options:

---

## **1. Spectrum**
Enter the element symbol:

```
H
He
Li
Be
B
C
N
O
F
Ne
Na
Mg
Al
Si
P
S
Cl
Ar
```

---

## **2. Search For**
Choose:

```
Wavelength
```

This keeps output consistent with the lake parser.

---

## **3. Wavelength Range**
Leave **Lower** and **Upper** blank to retrieve *all* transitions.

---

## **4. Output Options**
Set:

- **Format output:** `CSV (text)`
- **No JavaScript:** ✔
- **No spaces in values:** ✔
- **Energy Level Units:** `cm⁻¹`
- **Display output:** `in its entirety`
- **Page size:** `15`
- **Output ordering:** `Wavelength`

---

## **5. Wavelength Data**
Check:

- ✔ Observed  
- ✔ Ritz  
- ✔ Wavenumber (in cm⁻¹)  
- ✔ Uncertainties  

---

## **6. Transition Type**
Check:

- ✔ Allowed (E1)  
- ✔ Forbidden (M1, E2, …)  
- ✔ Relative Intensity  

---

## **7. Level Information**
Check:

- ✔ Configurations  
- ✔ Terms  
- ✔ Energies  
- ✔ J  
- ✔ g  

---

## **8. Additional Criteria**
Leave all fields blank unless you want filtering.

---

## **9. Click “Retrieve Data”**
This will open a plain‑text page containing the ASCII/CSV table.

---

# 💾 **Saving the File**
After clicking **Retrieve Data**, save the resulting page as:

```
H_lines.ascii
He_lines.ascii
Li_lines.ascii
...
Ar_lines.ascii
```

Place all files in:

```
nist_bulk/
```

Your directory should look like:

```
nist_bulk/
    H_lines.ascii
    He_lines.ascii
    Li_lines.ascii
    ...
    Ar_lines.ascii
```

---

# 🔍 **Why URLs Sometimes Work and Sometimes Fail**
Your working URLs for Cl and S:

```
https://physics.nist.gov/cgi-bin/ASD/lines1.pl?spectra=Cl&...
https://physics.nist.gov/cgi-bin/ASD/lines1.pl?spectra=S&...
```

match the form output **for that session only**.

But the ASD server:

- rotates session tokens  
- rejects stale tokens  
- rejects requests without a fresh form load  
- sometimes requires a new cookie  

This is why:

- Hydrogen worked  
- Helium failed  
- You reloaded the form  
- Helium worked  
- Lithium failed  
- You reloaded the form  
- Lithium worked  

This is **expected behavior**.

The README instructs users to **always use the form**, not rely on URLs.

---

# 🧱 **Building the Lake**
Once all `.ascii` files are saved:

Run:

```
python build_lake.py
```

The parser will:

- read each ASCII file  
- extract Ei, Ek, configurations, terms, intensities  
- compute transition energies  
- write JSON lines into:

```
../lake/raw/nist_asd_emission_Z1_to_Z18.jsonl
```

---

# 🎉 **You Now Have a Complete Sovereign NIST Spectral Lake**
This lake is:

- offline  
- reproducible  
- stable  
- independent of NIST rate limits  
- independent of CGI session tokens  
- compatible with your harmonic register extractor  
- compatible with your vertex‑mapping pipeline  
