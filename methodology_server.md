# Dataset Control — Methodology (Implementation‑accurate)

This document explains **exactly** what the validator does, the **inputs** it expects, the **tests** it runs, and the **files** it writes. It’s written for someone deploying the code on a server (not necessarily GIS‑savvy).

---

## 1) Inputs

### A. CSV with Google routes
Required columns (case‑insensitive aliases supported):
- **Name** — link id in the form `s_FROM-TO` (e.g. `s_653-655`). `s`/`S`, `_`/`-` prefixes are tolerated (e.g. `S653-655`, `s_653-655`).  
- **Polyline** — Google encoded polyline string.  
- **RouteAlternative** — integer route option *per timestamp*. If missing, the row is still tested geometrically but marked with context code **1** (NO_ROUTE_ALTERNATIVE).  
Recommended / optional:
- **Timestamp** — observation time (datetime). Used for link‑level stats and completeness.  
- **RequestedTime** — time‑of‑day string like `17:00:00`. Used only for **completeness** checks.

### B. Reference shapefile (lines)
- Must contain **From**, **To**, and **geometry** (LineString).  
- Join key is `s_{From}-{To}` (string form).

---

## 2) Parameters (defaults)

- Tests enabled: **Hausdorff ON**, **Length OFF**, **Coverage OFF**
- Hausdorff threshold: **5.0 m**
- Length mode: **ratio** with **0.90 – 1.10** bounds; epsilon for “exact” mode: **0.5 m**; min link length for length check: **20.0 m**
- Coverage: **min 0.85 (85%)**, **spacing 1.0 m** (used as the buffer width in the fallback overlap calculation)
- System: **polyline precision 5**, metric CRS **EPSG:2039** (WGS84 → 2039 for all metric calculations)
- Completeness (optional): **off** by default; interval **15 min**, date range blank

These are fully configurable in the UI or via parameters when calling the core functions.

---

## 3) What happens per CSV row

1) **Required fields check** (Name, Polyline; RouteAlternative if grouping by alternatives).  
2) **Parse link id** from `Name` → `(From, To)`.  
3) **Join** to the shapefile geometry using `s_{From}-{To}`.  
4) **Decode** the Google **Polyline** to a LineString (lon/lat).  
5) **Transform** both decoded polyline and reference geometry to **EPSG:2039** for metric work.  
6) **Run tests** in order:
   - **Hausdorff** (always evaluated): pass if `distance ≤ threshold`.
   - **Length** (if enabled): either **ratio** is within `[0.90, 1.10]` or **exact** within `±0.5 m` (links shorter than **20 m** skip the length check).
   - **Coverage** (if enabled): compute overlap of the decoded line with the reference; if strict overlap is zero, use a **buffer around the decoded line** with width = **spacing** to allow near‑miss coverage; require **≥ 85%**.
7) **is_valid** is **True only if all enabled tests pass**.  
8) **valid_code** is a **context code**, not a test result:
   - **1** NO_ROUTE_ALTERNATIVE (no RouteAlternative column)  
   - **2** SINGLE_ROUTE_ALTERNATIVE  
   - **3** MULTI_ROUTE_ALTERNATIVE  
   Data issues are encoded as:
   - **90** REQUIRED_FIELDS_MISSING, **91** NAME_PARSE_FAILURE, **92** LINK_NOT_IN_SHAPEFILE, **93** POLYLINE_DECODE_FAILURE

The per‑row output keeps your original fields and adds: `is_valid`, `valid_code`, `hausdorff_distance`, `hausdorff_pass` and (if enabled) `length_ratio/length_pass` or `coverage_percent/coverage_pass`.

---

## 4) Route alternatives & timestamps (how link stats are computed)

- Alternatives are **not separate measurements** — they are options for the **same request at the same timestamp**.  
- For each pair **(link_id, timestamp)**:
  - If **any** alternative is valid → the **timestamp is successful**.  
  - If **all** alternatives fail → the **timestamp fails**.  
- Link‑level metrics are then computed from **successful vs. total timestamps** (plus counts of observations and alternatives).

---

## 5) Outputs (file list & meaning)

Core CSVs (always written):
- **validated_data.csv** — every row with test results and codes; sorted by Name → Timestamp → RouteAlternative when present.  
- **link_report.csv** — per‑link aggregation with clear fields (see below).  
Core shapefile:
- **link_report_shapefile.zip** — the spatial version of the link report (same field order; DBF names ≤10 chars).

Analysis CSVs (always written):
- **failed_observations.csv** — only geometric failures (**codes 1–3** with `is_valid=False`).  
- **best_valid_observations.csv** — one **best** route per timestamp (favoring smaller Hausdorff).  
- **no_data_links.csv** — links present in the shapefile with **zero** CSV observations (**code 95**).

Conditional (when **completeness** is enabled and a date range is provided):
- **missing_observations.csv** — expected `(RequestedTime + Date)` combinations that are **missing** for links that do have some data (**code 94**).

Optional shapefiles (when spatial export is toggled):
- **failed_observations_shapefile.zip** — failed rows using **decoded polylines**.  
- **failed_observations_reference_shapefile.zip** — failure counts by time‑period on **reference geometries**.  
- **missing_observations_shapefile.zip** — missing observations on **reference geometries**.  
- **no_data_links_shapefile.zip** — no‑data links on **reference geometries**.

> Note: large CSVs may also be provided as ZIPs alongside the raw files.

---

## 6) Link report fields (what you’ll see per link)

Percentages are raw, transparent metrics (no bins):
- **perfect_match_percent** — share of observations with **Hausdorff = 0**  
- **threshold_pass_percent** — share with `0 < Hausdorff ≤ threshold`  
- **failed_percent** — share with `Hausdorff > threshold` or other test failures  
- **total_success_rate** — share of **successful timestamps** (per §4)
- **total_observations**, **successful_observations**, **failed_observations**
- **total_routes** — count of alternatives observed
- **single_route_observations**, **multi_route_observations**
- **expected_observations**, **missing_observations**, **data_coverage_percent** (only when completeness is enabled)

Shapefile DBF field names are automatically trimmed to ≤10 characters but keep the **same column order** as the CSV.

---

## 7) Completeness logic (optional)

If you provide a **date range** and an **interval** (e.g. 15 minutes):
- **Expected observations** = every interval within the inclusive date range.  
- For each link that has **some data**, the system looks for **missing (RequestedTime + Date)** combinations. Those become **code 94** rows in `missing_observations.csv`.  
- Links with **no observations at all** become **code 95** in `no_data_links.csv`.

---

## 8) Operational tips

- Keep `Name` strictly parseable (`s_FROM-TO`).  
- Ensure the shapefile’s `From/To` match the `Name` pairs.  
- If you enable **Coverage**, expect longer runtimes (uses buffered overlap when there’s no strict intersection).  
- All metric calculations (Hausdorff, length, coverage) are done in **EPSG:2039**.

---

## 9) Minimal example of pass/fail

- **Pass (Hausdorff only)**: `hausdorff_distance ≤ 5.0` → `is_valid=True`.  
- **Fail with all tests on**: Hausdorff fails even if length/coverage pass → `is_valid=False`.

---

## 10) File names (output directory)

- CSV: `validated_data.csv`, `best_valid_observations.csv`, `failed_observations.csv`, `missing_observations.csv`, `no_data_links.csv`, `link_report.csv`  
- Shapefile ZIPs: `link_report_shapefile.zip`, `failed_observations_shapefile.zip`, `failed_observations_reference_shapefile.zip`, `missing_observations_shapefile.zip`, `no_data_links_shapefile.zip`

