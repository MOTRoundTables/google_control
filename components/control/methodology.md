
This document explains **exactly** what the validator does, the **inputs** it expects, the **tests** it runs, and the **files** it writes. It's written for someone deploying the code on a server (not necessarily GIS‑savvy).

---

## 1) Inputs

### A. CSV with Google routes

**Required columns** (case‑insensitive aliases supported):
- **Name** — link id in the form `s_FROM-TO` (e.g. `s_653-655`). `s`/`S`, `_`/`-` prefixes are tolerated (e.g. `S653-655`, `s_653-655`)
- **Polyline** — Google encoded polyline string
- **RouteAlternative** — integer route option *per timestamp*. If missing, the row is still tested geometrically but marked with context code **1** (NO_ROUTE_ALTERNATIVE)

**Recommended / optional:**
- **Timestamp** — observation time (datetime). Used for link‑level stats and completeness
- **RequestedTime** — time‑of‑day string like `17:00:00`. Used only for **completeness** checks

### B. Reference shapefile (lines)

- Must contain **From**, **To**, and **geometry** (LineString)
- Join key is `s_{From}-{To}` (string form)

---

## 2) Parameters (defaults)

**Test Configuration:**
- Tests enabled: **Hausdorff ON**, **Length OFF**, **Coverage OFF**
- Hausdorff threshold: **5.0 m**

**Length Test Settings:**
- Length mode: **ratio** with **0.90 – 1.10** bounds
- Epsilon for "exact" mode: **0.5 m**
- Min link length for length check: **20.0 m**

**Coverage Test Settings:**
- Coverage: **min 0.85 (85%)**
- Spacing: **1.0 m** (used as the buffer width in the fallback overlap calculation)

**System Settings:**
- Polyline precision: **5**
- Metric CRS: **EPSG:2039** (WGS84 → 2039 for all metric calculations)

**Completeness (optional):**
- Default: **off**
- Interval: **15 min**
- Date range: blank

*These are fully configurable in the UI or via parameters when calling the core functions.*

---

## 3) What happens per CSV row

**Processing Steps:**
1. **Required fields check** (Name, Polyline; RouteAlternative if grouping by alternatives)
2. **Parse link id** from `Name` → `(From, To)`
3. **Join** to the shapefile geometry using `s_{From}-{To}`
4. **Decode** the Google **Polyline** to a LineString (lon/lat)
5. **Transform** both decoded polyline and reference geometry to **EPSG:2039** for metric work
6. **Run tests** in order:
   - **Hausdorff** (always evaluated): pass if `distance ≤ threshold`
   - **Length** (if enabled): either **ratio** is within `[0.90, 1.10]` or **exact** within `±0.5 m` (links shorter than **20 m** skip the length check)
   - **Coverage** (if enabled): compute overlap of the decoded line with the reference; if strict overlap is zero, use a **buffer around the decoded line** with width = **spacing** to allow near‑miss coverage; require **≥ 85%**
7. **is_valid** is **True only if all enabled tests pass**

**Context Codes:**
8. **valid_code** is a **context code**, not a test result:
   - **1** NO_ROUTE_ALTERNATIVE (no RouteAlternative column)
   - **2** SINGLE_ROUTE_ALTERNATIVE
   - **3** MULTI_ROUTE_ALTERNATIVE

**Data Issue Codes:**
   - **90** REQUIRED_FIELDS_MISSING
   - **91** NAME_PARSE_FAILURE
   - **92** LINK_NOT_IN_SHAPEFILE
   - **93** POLYLINE_DECODE_FAILURE

**Output Fields:**
The per‑row output keeps your original fields and adds: `is_valid`, `valid_code`, `hausdorff_distance`, `hausdorff_pass` and (if enabled) `length_ratio/length_pass` or `coverage_percent/coverage_pass`.

---

## 4) Route alternatives & timestamps (how link stats are computed)

**Key Concept:**
- Alternatives are **not separate measurements** — they are options for the **same request at the same timestamp**

**Timestamp Evaluation:**
- For each pair **(link_id, timestamp)**:
  - If **any** alternative is valid → the **timestamp is successful**
  - If **all** alternatives fail → the **timestamp fails**

**Link-Level Metrics:**
- Link‑level metrics are then computed from **successful vs. total timestamps** (plus counts of observations and alternatives)

---

## 5) Outputs (file list & meaning)

### Output folder structure

All control validation outputs are saved in **timestamped folders** with the format `DD_MM_YY_HH_MM`:

```
runs/
└── 1_10_25/                    # Run batch identifier
    └── output/
        ├── control/            # Control validation outputs
        │   ├── 05_10_25_16_36/ # Timestamped folder (5 Oct 2025, 16:36)
        │   │   ├── validated_data.csv
        │   │   ├── link_report.csv
        │   │   ├── failed_observations.csv
        │   │   ├── best_valid_observations.csv
        │   │   ├── failed_observations_shapefile.zip
        │   │   ├── failed_observations_unique_polylines_shapefile.zip
        │   │   └── performance_and_parameters_log.txt
        │   ├── 05_10_25_18_51/ # Another run
        │   └── ...
        │
        └── aggregation/        # Aggregation outputs (linked to control)
            ├── from_control_05_10_25_16_36/ # Traced to control folder
            ├── from_control_05_10_25_18_51/
            └── ...
```

**Key points:**
- **Timestamped folders**: Each validation run creates a new folder with timestamp `DD_MM_YY_HH_MM`
- **Traceability**: Aggregation folders use `from_control_[timestamp]` naming to link back to the control run
- **Multiple versions**: You can have multiple control and aggregation runs side-by-side
- **Log file**: `performance_and_parameters_log.txt` contains run metadata including the timestamp

### Core CSVs (always written)
- **validated_data.csv** — every row with test results and codes; sorted by Name → Timestamp → RouteAlternative when present
- **link_report.csv** — per‑link aggregation with clear fields (see below)

### Core shapefile
- **link_report_shapefile.zip** — the spatial version of the link report (same field order; DBF names ≤10 chars)

### Analysis CSVs (always written)
- **failed_observations.csv** — only geometric failures (**codes 1–3** with `is_valid=False`)
- **best_valid_observations.csv** — one **best** route per timestamp (favoring smaller Hausdorff)
- **no_data_links.csv** — links present in the shapefile with **zero** CSV observations (**code 95**)

### Conditional files
**When completeness is enabled and a date range is provided:**
- **missing_observations.csv** — expected `(RequestedTime + Date)` combinations that are **missing** for links that do have some data (**code 94**)

**Optional shapefiles (when spatial export is toggled):**
- **failed_observations_shapefile.zip** — all failed rows using **decoded polylines** (see §12.1)
- **failed_observations_unique_polylines_shapefile.zip** — **unique route geometries per link** (deduplicated across all timestamps by Name+Polyline, see §12.2)
- **failed_observations_reference_shapefile.zip** — failure counts by time‑period on **reference geometries** (see §12.3)
- **missing_observations_shapefile.zip** — missing observations on **reference geometries**
- **no_data_links_shapefile.zip** — no‑data links on **reference geometries**

> **Note:** Large CSVs may also be provided as ZIPs alongside the raw files. See **§12** for detailed shapefile specifications and deduplication logic.

---

## 6) Link report fields (what you'll see per link)

**Performance Metrics (raw percentages, no bins):**
- **perfect_match_percent** — share of observations with **Hausdorff = 0**
- **threshold_pass_percent** — share with `0 < Hausdorff ≤ threshold`
- **failed_percent** — share with `Hausdorff > threshold` or other test failures
- **total_success_rate** — share of **successful timestamps** (per §4)

**Observation Counts:**
- **total_observations**, **successful_observations**, **failed_observations**
- **total_routes** — count of alternatives observed
- **single_route_observations**, **multi_route_observations**

**Completeness Metrics (only when completeness is enabled):**
- **expected_observations**, **missing_observations**, **data_coverage_percent**

> **Note:** Shapefile DBF field names are automatically trimmed to ≤10 characters but keep the **same column order** as the CSV.

---

## 7) Completeness logic (optional)

**When you provide a date range and interval (e.g. 15 minutes):**

- **Expected observations** = every interval within the inclusive date range
- For each link that has **some data**, the system looks for **missing (RequestedTime + Date)** combinations. Those become **code 94** rows in `missing_observations.csv`
- Links with **no observations at all** become **code 95** in `no_data_links.csv`

---

## 8) Operational tips

**Data Preparation:**
- Keep `Name` strictly parseable (`s_FROM-TO`)
- Ensure the shapefile's `From/To` match the `Name` pairs

**Performance Considerations:**
- If you enable **Coverage**, expect longer runtimes (uses buffered overlap when there's no strict intersection)
- All metric calculations (Hausdorff, length, coverage) are done in **EPSG:2039**

---

## 9) Minimal example of pass/fail

**Pass (Hausdorff only):**
- `hausdorff_distance ≤ 5.0` → `is_valid=True`

**Fail with all tests on:**
- Hausdorff fails even if length/coverage pass → `is_valid=False`

---

## 10) File names (output directory)

- CSV: `validated_data.csv`, `best_valid_observations.csv`, `failed_observations.csv`, `missing_observations.csv`, `no_data_links.csv`, `link_report.csv`
- Shapefile ZIPs: `link_report_shapefile.zip`, `failed_observations_shapefile.zip`, `failed_observations_unique_polylines_shapefile.zip`, `failed_observations_reference_shapefile.zip`, `missing_observations_shapefile.zip`, `no_data_links_shapefile.zip`

---

## 11) Field reference — CSV outputs

### 11.1 validated_data.csv
| Field | Type | Meaning | Calculation or source |
| --- | --- | --- | --- |
| Name | string | Original link name | As received |
| link_id | string | Canonical id `s_{From}-{To}` | Parsed from Name |
| Timestamp | datetime | Observation time, if provided | As received |
| RouteAlternative | integer | Alternative index, if provided | As received |
| is_valid | boolean | True only if all enabled tests pass | From tests below |
| valid_code | integer | Context or data issue code | 1 no RouteAlternative, 2 single alternative, 3 multiple alternatives, 90–93 data issues |
| hausdorff_distance | float meters | Max nearest distance from observation to reference | Directed Hausdorff after projecting to EPSG:2039 |
| hausdorff_pass | boolean | Hausdorff threshold pass | `hausdorff_distance ≤ hausdorff_threshold_m` |
| length_ratio | float | Observation length divided by reference length (ratio mode) | Null if length check disabled |
| length_pass | boolean | Length test pass | Ratio within `[min,max]` or absolute diff ≤ epsilon in exact mode |
| coverage_percent | float percent | Share of reference covered by observation | `overlap_length / reference_length × 100` with buffered near-miss when needed |
| coverage_pass | boolean | Coverage test pass | `coverage_percent ≥ coverage_min × 100` |

Plain explanations  
1. **hausdorff_distance** — worst‑case mismatch between the two lines in meters (after EPSG:2039 projection).  
2. **coverage_percent** — how much of the reference is overlapped by the observation. If there is no strict intersection, a buffer of width `coverage_spacing_m` around the observed line is used to allow near‑miss coverage.  
3. **length_ratio** — 1.00 means equal lengths; below 1.00 shorter; above 1.00 longer.

### 11.2 link_report.csv
| Field | Type | Meaning | Calculation |
| --- | --- | --- | --- |
| link_id | string | Canonical id `s_{From}-{To}` | From shapefile join |
| perfect_match_percent | float percent | Observations with `Hausdorff = 0` | `count(h=0)/total × 100` |
| threshold_pass_percent | float percent | Observations with `0 < Hausdorff ≤ threshold` | `count(0<h≤thr)/total × 100` |
| failed_percent | float percent | Observations that failed | `count(failed)/total × 100` |
| total_success_rate | float percent | Successful timestamps share | `successful_timestamps/total_timestamps × 100` |
| total_observations | integer | Observation rows for link | Count |
| successful_observations | integer | Rows with `is_valid=True` | Count |
| failed_observations | integer | Rows with `is_valid=False` | Count |
| total_routes | integer | Route alternatives observed | Count |
| single_route_observations | integer | Timestamps with one alternative | Count |
| multi_route_observations | integer | Timestamps with multiple alternatives | Count |
| expected_observations | integer | With completeness enabled | Number of expected intervals |
| missing_observations | integer | With completeness enabled | Expected minus actual |
| data_coverage_percent | float percent | With completeness enabled | `(expected - missing)/expected × 100` |

### 11.3 best_valid_observations.csv
| Field | Type | Meaning | Calculation |
| --- | --- | --- | --- |
| link_id | string | Canonical id | Parsed or joined |
| Timestamp | datetime | Request time | As received |
| RouteAlternative | integer | Alternative index | As received |
| hausdorff_distance | float meters | Best passing distance | Minimum Hausdorff among valid alternatives at the timestamp |
| is_valid | boolean | Always True | By construction |

### 11.4 failed_observations.csv
| Field | Type | Meaning | Calculation |
| --- | --- | --- | --- |
| Name | string | Original link name | As received |
| link_id | string | Canonical id | Parsed |
| Timestamp | datetime | Observation time | As received |
| RouteAlternative | integer | Alternative index | As received |
| is_valid | boolean | Always False | By construction |
| valid_code | integer | Context code with failure | From validator |
| hausdorff_distance | float meters | Distance result | Calculated |
| length_ratio | float | Length result when enabled | Calculated or null |
| coverage_percent | float percent | Coverage result when enabled | Calculated or null |

### 11.5 missing_observations.csv  (only with completeness)
| Field | Type | Meaning | Calculation |
| --- | --- | --- | --- |
| link_id | string | Canonical id | From shapefile |
| RequestedTime | time | Expected time of day | From completeness setup |
| Date | date | Expected date | From completeness setup |
| valid_code | integer | Always 94 | Missing observation code |
| is_valid | boolean | Always False | By construction |

### 11.6 no_data_links.csv
| Field | Type | Meaning | Calculation |
| --- | --- | --- | --- |
| link_id | string | Canonical id | From shapefile |
| valid_code | integer | Always 95 | No‑data link code |
| is_valid | boolean | Always False | By construction |

---

## 12) Shapefile geometry and CRS per product

All shapefiles are written as **LineString** layers by default, with CRS set to match the reference shapefile (commonly `EPSG:2039`). Internal decoding starts in `EPSG:4326` and is reprojected to the shapefile CRS when saving.

| Shapefile ZIP | Geometry source | Geometry type | CRS on disk | Notes |
| --- | --- | --- | --- | --- |
| link_report_shapefile.zip | Reference shapefile | LineString | Reference CRS (e.g., EPSG:2039) | Attributes mirror link_report.csv and field order is the same |
| failed_observations_shapefile.zip | **Decoded polylines** from CSV | LineString | Reference CRS (reprojected from WGS84) | One row per failed observation; geometry equals the observed route (see §12.1) |
| failed_observations_unique_polylines_shapefile.zip | **Decoded polylines** from CSV (deduplicated) | LineString | Reference CRS (reprojected from WGS84) | Unique polylines only - deduplicated by Timestamp+Name+Polyline string (see §12.2) |
| failed_observations_reference_shapefile.zip | **Reference** geometry | LineString | Reference CRS | Aggregated by link and time periods; shows failure patterns on the expected geometry (see §12.3) |
| missing_observations_shapefile.zip | **Reference** geometry | LineString | Reference CRS | Produced only when completeness is enabled |
| no_data_links_shapefile.zip | **Reference** geometry | LineString | Reference CRS | One row per link that had zero observations |

DBF note: field names are trimmed to ≤ 10 characters in the shapefile, but the **column order** matches the CSVs. Keep the CSVs as the authoritative schemas.

### 12.1) Failed observations shapefile (decoded polylines - all observations)

The **failed_observations_shapefile.zip** contains **all failed validation observations** with their actual Google Maps polyline geometries decoded and reprojected.

**Purpose:**
- Visualize every failed observation with its actual observed route
- Compare observed routes against reference geometry
- Analyze spatial patterns of validation failures

**Characteristics:**
- **One row per failed observation** (codes 1-3 with `is_valid=False`)
- **Geometry source**: Decoded from `Polyline` column in CSV using Google Maps polyline encoding
- **Coordinate transformation**: Decoded in EPSG:4326 (WGS84) → reprojected to reference CRS
- **Attributes**: All columns from `failed_observations.csv` including validation codes, Hausdorff distances, route alternatives

**Typical use cases:**
- Visual inspection of why specific observations failed
- Route alternative comparison for multi-route timestamps
- Quality control and validation debugging

**Example counts:**
- Input: 5,060 failed observations
- Output: 5,060 polyline features (one per observation)

### 12.2) Failed observations unique polylines shapefile (deduplicated)

The **failed_observations_unique_polylines_shapefile.zip** provides a **deduplicated version** of the failed observations, keeping only unique route geometries per link across all timestamps.

**Purpose:**
- Show unique route variations without temporal repetition
- Reduce file size dramatically (e.g., 5,060 → 60 features)
- Focus on spatial route diversity rather than observation counts
- Ideal for route pattern analysis and alternative path visualization

**Deduplication logic:**
1. **Group by**: `(Name + Polyline string)` — **link + route geometry only, ignoring timestamps**
2. **Keep**: First occurrence of each unique (link, route) combination
3. **Result**: One feature per unique route geometry for each link, **regardless of when it was observed**

**Characteristics:**
- **Geometry source**: Same as §12.1 (decoded polylines from failed observations)
- **Deduplication basis**: Link name + original encoded polyline string (before decoding)
- **Attributes**: Preserved from first temporal occurrence of each unique route
- **Time independence**: If the same route appears at 100 different timestamps → output contains 1 feature
- **Route alternatives**: If a link has multiple route alternatives with different geometries → all unique routes are kept

**Important notes:**
- **Multiple routes per link is normal**: Links can have 1-3 route alternatives (different paths for the same origin-destination)
- **Not an error indicator**: Having multiple routes doesn't mean the link is "broken" — it's just Google Maps finding alternative paths
- **Distribution varies**: Some links may have 1 route, others 2-3 routes, depending on road network topology
- **Total count**: Represents total unique failed route geometries across all links (not per-link counts)

**Example scenario:**
```
Link s_1119-9150 observed 394 times across all timestamps:
- 384 observations: Polyline "abc123..." (route A) at various times
- 10 observations: Polyline "xyz789..." (route B) at various times

Result: 2 features output (one for route A, one for route B)

Link s_1753-3930 observed 15 times:
- All 15 observations: Polyline "def456..." (single route)

Result: 1 feature output (only one unique route for this link)
```

**Typical use cases:**
- Route alternative catalog per link
- Visual comparison of different paths between same origin-destination
- Cleaner maps showing route diversity without time-based clutter
- Understanding spatial variation in failed routes across the network

**Example counts:**
- Input: 5,060 failed observations (same routes repeated across timestamps)
- Output: 60 unique route geometries across all links (5,000 temporal duplicates removed)
- Interpretation: 60 distinct failed route patterns exist in the dataset, regardless of how many times each was observed

### 12.3) Failed observations reference shapefile (time-period aggregation)

The **failed_observations_reference_shapefile.zip** provides time-of-day failure pattern analysis with one row per unique link and aggregated failure counts across time periods.

**Time period structure (left-inclusive, right-exclusive):**
- **Night**: 00:00–06:00 (excludes 06:00)
- **Morning**: 06:00–11:00 (excludes 11:00)
- **Midday**: 11:00–15:00 (excludes 15:00)
- **Afternoon**: 15:00–20:00 (excludes 20:00)
- **Evening**: 20:00–00:00 (includes 20:00, excludes 00:00)

**Averaging logic:**
- Formula: `period_failure_count = total_failures_in_period ÷ total_days_analyzed`
- Example: Link s_653-655 across 3 days with morning failures (Day1=2, Day2=1, Day3=3) → 6 total ÷ 3 days = 2.0 average → field `06_11_f_cn = 2.0`

**Output fields (DBF 10-char limit):**

| Field | Description |
| --- | --- |
| **link_id** | Link identifier |
| **data_sourc** | Data source identifier (always "reference_shapefile") |
| **valid_code** | Validation code from failed observations |
| **avg_hausdo** | Average Hausdorff distance across all failures |
| **best_hausd** | Best (minimum) Hausdorff distance |
| **worst_haus** | Worst (maximum) Hausdorff distance |
| **00_06_f_cn** | Average failures per day in night period |
| **06_11_f_cn** | Average failures per day in morning period |
| **11_15_f_cn** | Average failures per day in midday period |
| **15_20_f_cn** | Average failures per day in afternoon period |
| **20_00_f_cn** | Average failures per day in evening period |
| **avg_len_rt** | Average length ratio (conditional: when length check enabled) |
| **best_len** | Best length ratio (conditional: when length check enabled) |
| **worst_len** | Worst length ratio (conditional: when length check enabled) |
| **avg_cover** | Average coverage percentage (conditional: when coverage enabled) |
| **best_cov** | Best coverage percentage (conditional: when coverage enabled) |
| **worst_cov** | Worst coverage percentage (conditional: when coverage enabled) |
| **total_days** | Number of unique days analyzed |
| **total_fail** | Total failed observations for this link |

**Field naming convention:**
- `f_cn` suffix = "failure count"
- `00_06` format clearly shows time range (hours in 24h format)
- All names fit DBF 10-character limit
