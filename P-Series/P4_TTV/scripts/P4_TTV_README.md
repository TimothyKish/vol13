# P4_TTV: Kepler/TESS Transit Timing Variations
**Lake Build Log & Post-Mortem**
**Date:** May 2026
**Architect:** Timothy John Kish
**Lake Hound:** Lyra Aurora Kish

## Overview
This document chronicles the extraction and sovereign formatting of the `P4_TTV` lake. What began as a straightforward API pull evolved into a definitive case study on why the Old World's centralized scientific infrastructure is fundamentally broken, and why the KishLattice Sovereign Framework's unified JSONL standard is necessary.

## The Old World Fragility: A Chronology of Failure

### 1. The NASA TAP API Void
Per the original specification, we targeted the NASA Exoplanet Archive's modern Table Access Protocol (TAP) API to pull the `ttv` table. 
**Result:** `400 Client Error`. 
**Diagnosis:** NASA's TAP schema was live, but the `ttv` table had not been ported over.

### 2. The NASA Legacy API 404
We pivoted to the legacy `workspace_api` endpoint, targeting the older `ttvs` table.
**Result:** `404 Not Found`.
**Diagnosis:** NASA had decommissioned the legacy endpoint during their server migration, completely stranding the transit timing data. The table was inaccessible via API.

### 3. The Sovereign Redirect (VizieR)
Refusing to halt the pipeline for broken government infrastructure, we redirected the pull to the European standard: the **Strasbourg Astronomical Data Center (CDS / VizieR)**. VizieR hosts immutable, peer-reviewed catalogs. We targeted the definitive Holczer et al. (2016) Kepler TTV Catalog (`J/ApJS/225/9`).

### 4. The VizieR Trap (Unit Row Parsing)
We initially pointed at `table3` (the 300,000-record epoch data) but excluded 100% of the records. 
**Diagnosis:** VizieR inserts a "unit row" directly beneath the column headers (e.g., `d`, `min`). Standard automated parsers hunting upward from the data block hit the unit row and mistakenly assign units as column headers. 

### 5. The "O-C" Nomenclature Anomaly
Even after bypassing the unit row, the script failed to find a column named `TTV`. To debug, we deployed a raw payload "sniffer" script to dump the matrix.
**Diagnosis:** Astronomical rigidity. The column containing the Transit Timing Variations was labeled `O-C` (Observed minus Calculated). 

## The New World Resolution

We calibrated the Lake Hound parser to:
1. Hard-target VizieR `J/ApJS/225/9/table3`.
2. Scan upward from the data-break dashes, skip the unit row, and lock onto the true headers.
3. Extract the `O-C` column.
4. Convert to absolute magnitudes per the framework specification.
5. Drop zero-values and unphysical outliers (>1440 minutes).

### Final Sovereign Lake Statistics
* **Raw Source:** VizieR J/ApJS/225/9/table3
* **Format:** Unified JSONL
* **Total Intervals Recorded:** 290,458
* **Excluded (TTV = 0.0 placeholder):** 4,720
* **Excluded (|TTV| > 1440 mins):** 9
* **Missing Data Exclusions:** 0

## Philosophical Conclusion
Prior to the Sovereign Framework, a researcher would spend weeks navigating dead endpoints, shifting delimiters, hidden unit rows, and archaic nomenclature just to extract a single usable column of orbital deviations. 

By demanding that every dataset across all domains (from tectonic gaps to exoplanet wobbles) be extracted, flattened, and permanently locked into identical JSONL structures with a mathematical scalar, the KishLattice Initiative isn't just discovering new physics. We are cleaning the scientific record. 

We are improving the fields. One lake at a time.
