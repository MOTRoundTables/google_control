# Dataset Control Methodology

## Overview

The Dataset Control system validates Google Maps polyline data against reference shapefiles using geometric similarity analysis. It provides transparent metrics and generates comprehensive link-level reports.

## Algorithm Explanation: Google Maps vs Reference Shapefile

### The Two Data Sources

**1. Reference Shapefile** (Your Upload)
- Contains "ground truth" road network geometry
- Structure: Links with `From`→`To` node IDs and LineString geometries
- Purpose: Defines the **expected** route for each link
- Example: Link `s_653-655` should follow a specific geometric path

**2. Google Maps Observations** (CSV Data)
- Contains real-world travel observations with encoded polylines
- Structure: Each row has `name`, `polyline`, `route_alternative`, timestamps
- Purpose: Shows the **actual** route Google Maps suggested/took
- Example: Same link `s_653-655` but with Google's encoded polyline

## Validation Pipeline Architecture

The validation process follows a hierarchical structure with specific exit points:

### Phase 1: Data Preparation
1. Load reference shapefile → Create join keys (s_From-To)
2. Load CSV observations → Parse link names to extract From/To IDs
3. Create matching pairs: CSV observation ↔ Shapefile reference

### Phase 2: Geometric Validation (Per Observation)

**Step 1: Data Availability Check** (Codes 90-93)
- ✓ Required fields present? (name, polyline, route_alternative)
- ✓ Link name parseable? (s_653-655 → From:653, To:655)
- ✓ Link exists in shapefile?
- ✓ Polyline decodeable?

**Step 2: Geometric Similarity Tests**

**A) Coordinate System Conversion**
- Convert both geometries to metric CRS (EPSG:2039)
- Google route: decode_polyline(observation.polyline)
- Reference route: from shapefile geometry
- Both now in meters for accurate distance calculations

**B) Hausdorff Distance Test**
- Measures maximum distance between the two routes
- If distance ≤ threshold: Routes are geometrically similar
- If distance > threshold: Code 2 (DISTANCE_FAILURE)

**C) Length Similarity Test** (Optional)
- When `length_check_mode` = "ratio": Check if lengths are within ratio bounds
- When `length_check_mode` = "exact": Check absolute length difference
- When `length_check_mode` = "off": **Skip this test entirely**

**D) Coverage Analysis**
- Densify reference route into points every 1.0 meter
- For each reference point, check if Google route comes close (≤ 1.0m)
- Calculate percentage: covered_length / reference_route.length
- If coverage ≥ 0.85 (85%): Sufficient coverage
- If coverage < 0.85: Code 4 (COVERAGE_FAILURE)

### Phase 3: Transparent Result System with Individual Test Metrics

Context-Only Codes:

- **Code 1**: NO_ROUTE_ALTERNATIVE (when RouteAlternative column is missing)
- **Code 2**: SINGLE_ROUTE_ALTERNATIVE (one alternative for link+timestamp)
- **Code 3**: MULTI_ROUTE_ALTERNATIVE (multiple alternatives for link+timestamp)

Route Alternative Processing:

The system groups observations by (link_id, timestamp) and provides individual test results:

Single Alternative Batch (only one row for link+timestamp):
- Gets `valid_code: 2` (context indicator only)
- Individual test results in dedicated fields

Multiple Alternative Batch (2+ rows for same link+timestamp):
- Each alternative gets `valid_code: 3` (context indicator only)
- Each alternative gets individual test results in dedicated fields

Example Multi-Alternative Scenario:
```
s_653-655, 13:45, RouteAlternative=1:
  valid_code=3, is_valid=False, hausdorff_distance=6.94, hausdorff_pass=False

s_653-655, 13:45, RouteAlternative=2:
  valid_code=3, is_valid=True, hausdorff_distance=2.1, hausdorff_pass=True

s_653-655, 13:45, RouteAlternative=3:
  valid_code=3, is_valid=False, hausdorff_distance=8.3, hausdorff_pass=False
```

Link-Level Reporting: Aggregates by unique timestamp first (any passing alternative marks that timestamp as successful) and publishes legacy ResultCode values for compatibility.

- Result labels surfaced to users/UI mirror the legacy meanings: `valid` (all timestamps succeed), `no RouteAlternative` (single-alternative links with mixed success), `no RouteAlternative and all invalid` (single-alternative links entirely failing), and `RouteAlternative greater than one` for any multi-alternative scenario.
- When RouteAlternative values are present but timestamps remain unique, the aggregator falls back on the alternative IDs so links with indices >1 are still classified as multi-alternative for reporting.

## Validation Codes Reference

### Simplified Context-Only Code System

The validation system now uses simplified context codes with individual test result fields:

### Context Codes (1-3)
*Indicate data structure context only*

| Code | Name | Context |
|------|------|---------|
| 1 | NO_ROUTE_ALTERNATIVE | RouteAlternative column missing from input data |
| 2 | SINGLE_ROUTE_ALTERNATIVE | One alternative exists for link+timestamp |
| 3 | MULTI_ROUTE_ALTERNATIVE | Multiple alternatives exist for link+timestamp |

### Data Completeness Codes (94-95)
*Appear in separate files when Data Completeness Analysis is enabled*

| Code | Name | Description | File Location |
|------|------|-------------|---------------|
| 94 | MISSING_OBSERVATION | Expected RequestedTime missing for links with data | missing_observations.csv |
| 95 | NO_DATA_LINK | Link exists in shapefile but has zero observations in CSV | no_data_links.csv |

**Notes:**
- Code 94: Links with some data but missing specific RequestedTime intervals
- Code 95: Links in shapefile but no observations in CSV data
- These codes appear in separate output files, not in validated_data.csv
- Code 94 uses RequestedTime field to indicate when observations were expected
- Code 95 has NULL RequestedTime values since the entire link lacks data
- Code 94 only generated when "Data Completeness Analysis" checkbox is enabled

### Individual Test Result Fields

Instead of encoding test configuration in codes, each test has dedicated result fields:

Always Present:
- `is_valid`: True if ALL enabled tests pass, False otherwise
- `valid_code`: Context code (1, 2, or 3)
- `hausdorff_distance`: Actual distance in meters (e.g., 6.94)
- `hausdorff_pass`: True/False for Hausdorff test

Present Only If Length Test Enabled:
- `length_ratio`: Actual length ratio (e.g., 0.999)
- `length_pass`: True/False for length test

Present Only If Coverage Test Enabled:
- `coverage_percent`: Actual coverage percentage (e.g., 97.3)
- `coverage_pass`: True/False for coverage test

### Example Results

Hausdorff Only Configuration:
```
is_valid=False, valid_code=2, hausdorff_distance=6.94, hausdorff_pass=False
```

All Tests Enabled Configuration:
```
is_valid=False, valid_code=2,
hausdorff_distance=6.94, hausdorff_pass=False,
length_ratio=0.999, length_pass=True,
coverage_percent=97.3, coverage_pass=True
```
(is_valid=False because Hausdorff failed despite length and coverage passing)

### Data Availability Codes (90-93)
*Error codes for validation data issues only*

| Code | Name | Meaning | is_valid |
|------|------|---------|----------|
| 90 | REQUIRED_FIELDS_MISSING | Missing required fields: name, polyline, route_alternative | False |
| 91 | NAME_PARSE_FAILURE | Cannot parse link name format (expected: s_FROM-TO) | False |
| 92 | LINK_NOT_IN_SHAPEFILE | Link exists in CSV but not found in reference shapefile | False |
| 93 | POLYLINE_DECODE_FAILURE | Invalid Google Maps polyline encoding | False |

**Note**: These codes only appear in validated_data.csv for actual CSV observations that have data issues. Synthetic data (codes 94-95) are handled separately in dedicated files.

## Validation Parameters

### Geometric Analysis
- **Hausdorff Distance Threshold**: Default 5.0 meters
- **Length Check Mode**: off/ratio/exact
- **Length Ratio Bounds**: 0.90-1.10 (90%-110% of reference)
- **Coverage Analysis**: 0.85 minimum (85% overlap required)
- **Coverage Spacing**: 1.0 meter for densification

### Processing Settings
- **Polyline Precision**: 5 (Google Maps standard)
- **Coordinate System**: WGS84 → EPSG:2039 conversion
- **Minimum Link Length**: 20.0 meters (short links bypass length checks)

### Technical Implementation Details

#### **Coordinate Reference System**
- **Input Data**: WGS84 (EPSG:4326) for Google Maps polylines
- **Processing CRS**: EPSG:2039 (Israel TM Grid) for metric calculations
- **Implementation**: Direct transformation using cached coordinate transformers

#### **Geometry Processing**
- **Shapefile Lookups**: Precomputed dictionary mapping for efficient link-to-geometry resolution
- **Polyline Decoding**: Google Maps encoded polylines decoded to coordinate sequences
- **Distance Calculations**: All geometric tests performed in metric coordinate system

#### **Data Quality Assurance**
- **Exception Handling**: Comprehensive error handling with `is_valid = False` fallback for problematic data
- **Data Type Consistency**: Proper numeric dtypes for all metric fields
- **Field Validation**: Required field presence verification before processing

## Link-Level Transparent Metrics

Route alternatives are alternatives for the same routing request, not independent observations.

Algorithm:
1. Timestamp-Level Evaluation: For each (link_id, timestamp), check if ANY alternative is valid
   - If ANY alternative passes validation → Timestamp is SUCCESSFUL
   - If ALL alternatives fail validation → Timestamp is FAILED

2. Link-Level Metrics: Calculate transparent statistics
   - `success_rate = (successful_timestamps / total_timestamps) × 100`
   - `failed_timestamps = total_timestamps - successful_timestamps`

Example:
```
Link s_653-655 at 17:00:
- Alternative 1: INVALID (Hausdorff 514m > 5m threshold)
- Alternative 2: INVALID (Hausdorff 195m > 5m threshold)
- Alternative 3: VALID (Hausdorff 0m ≤ 5m threshold)

RESULT: Timestamp SUCCESSFUL (≥1 valid alternative provided good route)
```

### Transparent Metrics Fields

| Field | Description | Example |
|-------|-------------|---------|
| `success_rate` | Raw percentage of successful timestamps | 99.3% |
| `total_success_rate` | Combined exact match + threshold pass percentages | 99.3% |
| `total_timestamps` | Number of unique time periods observed | 288 |
| `successful_timestamps` | Time periods with ≥1 valid alternative | 286 |
| `failed_timestamps` | Time periods with all alternatives invalid | 2 |
| `total_observations` | Total validation rows (all alternatives) | 409 |
| `single_alt_timestamps` | Time periods with one alternative | 200 |
| `multi_alt_timestamps` | Time periods with multiple alternatives | 88 |

## Real-World Examples

### Row-Level Validation Examples

Successful Single Alternative:
- Reference: A→B→C→D→E (5km highway segment)
- Google Alt 1: A→B→C→D→E (same route, slight GPS noise)
- Results: Hausdorff 3.2m < 5m PASS
- Row Result: `is_valid=True`, `valid_code=2`, `hausdorff_distance=3.2`, `hausdorff_pass=True`

Failed Single Alternative:
- Reference: A→B→C→D→E (main highway)
- Google Alt 1: A→F→G→H→E (alternative route via side roads)
- Results: Hausdorff 45m > 5m FAIL
- Row Result: `is_valid=False`, `valid_code=2`, `hausdorff_distance=45.0`, `hausdorff_pass=False`

Multi-Alternative Scenario:
- Reference: Highway route between nodes 1321-1430
- Google Alt 1: Primary highway (Hausdorff 0.0m, Length 0.985, Coverage 100%) → VALID
- Google Alt 2: Alternative route (Hausdorff 514.7m, Length 1.203, Coverage 78%) → INVALID
- Google Alt 3: Side roads route (Hausdorff 195.3m, Length 0.934, Coverage 65%) → INVALID
- Timestamp Result: SUCCESSFUL (≥1 valid alternative available)

### Link-Level Examples

High-Performance Link:
```
s_11430-1321: success_rate=99.3%, total_observations=288, successful_observations=286,
              failed_observations=2, total_routes=409, multi_route_observations=88
```

Perfect Performance Link:
```
s_9054-99: success_rate=100.0%, total_observations=54, successful_observations=54,
           failed_observations=0, total_routes=54, single_route_observations=54
```

Failed Link:
```
s_653-655: success_rate=0.0%, total_observations=245, successful_observations=0,
           failed_observations=245, total_routes=245, single_route_observations=245
```

Link with No Data:
```
s_999-888: success_rate=None, total_observations=0, successful_observations=0,
           failed_observations=0, total_routes=0
```

## Output Files

The validation system generates **6-11 output files** organized into three logical categories:

### **Core Output Files** (Always Generated)

#### **1. validated_data.csv**
- **Content**: Original data with added validation results for all observations
- **Added Columns**: `is_valid`, `valid_code`, `hausdorff_distance`, `hausdorff_pass`, plus optional length/coverage fields
- **Sorting**: Name → Timestamp → RouteAlternative for consistent analysis
- **Purpose**: Complete validation dataset with individual test metrics

#### **2. link_report.csv**
- **Content**: Per-link aggregation with transparent performance metrics
- **Key Fields**: Performance percentages, observation counts, completeness data (if enabled)
- **Logic**: Timestamp-based aggregation (≥1 valid alternative = successful timestamp)
- **Purpose**: Link-level summary statistics for network analysis

#### **3. link_report_shapefile.zip**
- **Content**: Complete spatial package with validation statistics matching CSV field order exactly
- **Components**: .shp, .shx, .dbf, .prj, .cpg files with standardized field ordering
- **Geometry**: Original reference shapefile LineString features
- **Purpose**: GIS-compatible spatial visualization of link performance

- **Field Order Guarantee**: Fields are structured in exact order to match CSV report:
  `From, To, perfect_match_percent, threshold_pass_percent, failed_percent, total_success_rate, total_observations, successful_observations, failed_observations, total_routes, single_route_observations, multi_route_observations, expected_observations, missing_observations, data_coverage_percent`

- **DBF Compatibility**: Field names are automatically truncated to 10 characters for shapefile DBF compatibility while preserving field order and data integrity

### **Analysis Files** (Always Generated)

#### **4. failed_observations.csv**
- **Content**: Only geometric validation failures (codes 1-3 with `is_valid=False`)
- **Logic**: Observations where actual geometric tests failed
- **Purpose**: Focus analysis on systematic validation failures for quality control

#### **5. best_valid_observations.csv**
- **Content**: One best route per timestamp using weighted geometric scoring
- **Logic**: Geometric accuracy prioritized (Hausdorff × -1000) over length and coverage
- **Purpose**: Clean dataset without duplicate timestamps for time-series analysis

#### **6. no_data_links.csv**
- **Content**: Links from shapefile missing entirely from CSV data (code 95)
- **Logic**: Spatial gaps - no observations exist for these links
- **Purpose**: Identify which shapefile links have zero CSV observations

### **Conditional Files** (Generated Based on User Settings)

#### **7. missing_observations.csv** *(Only if "Data Completeness Analysis (Optional)" enabled)*
- **Content**: Missing (RequestedTime + Date) combinations for links with existing data (code 94)
- **Logic**: Finds temporal gaps by checking for missing date+time combinations, not just time gaps
- **Key Feature**: Combines `RequestedTime` field with actual dates from date range to detect missing observations
- **Scope**: Only checks links that have actual data in CSV, ignoring links with zero observations
- **Accuracy**: Prevents false positives by checking within each link's actual temporal range
- **Purpose**: Identify specific missing time periods in data collection schedule

#### **8-12. Spatial Shapefiles** *(Only if shapefile generation enabled)*
- **failed_observations_shapefile.zip**: Validation failures with **decoded polyline geometries** from Google observations
- **failed_observations_reference_shapefile.zip**: Time-period aggregated failure analysis with **original shapefile geometries**
- **missing_observations_shapefile.zip**: Missing data with **original shapefile geometries** *(conditional on completeness analysis)*
- **no_data_links_shapefile.zip**: No-data links with **original shapefile geometries**
- **link_report.shp + components**: Individual shapefile files (also packaged in ZIP above)

### **File Structure Logic**

**Geometry Sources by File Type:**
- **Validation Failures (codes 1-3)**: Use decoded Google polylines to show actual routing differences
- **Failed Observations Reference**: Use original shapefile geometry with time-period aggregation for pattern analysis
- **Missing/No-Data (codes 94-95)**: Use original shapefile geometry since no Google data exists

## Failed Observations Reference Time-Period Aggregation

### Overview

The failed observations reference shapefile provides time-of-day failure pattern analysis with one row per unique link and aggregated failure counts across time periods.

### Time Period Structure

**5 Time Periods (Left-Inclusive, Right-Exclusive):**
1. **Night**: 00:00-06:00 (excludes 06:00)
2. **Morning**: 06:00-11:00 (excludes 11:00)
3. **Midday**: 11:00-15:00 (excludes 15:00)
4. **Afternoon**: 15:00-20:00 (excludes 20:00)
5. **Evening**: 20:00-00:00 (includes both 20:00 and 00:00)

### Averaging Logic

**Formula**: `period_failure_count = total_failures_in_period / total_days_analyzed`

**Example Calculation**:
- Link s_653-655 analyzed across 3 days
- Morning failures: Day1=2, Day2=1, Day3=3 = 6 total
- Morning average: 6 failures ÷ 3 days = 2.0 failures per day
- Output field: `06_11_f_cn = 2.0`

### Output Field Structure

**Core Fields (Always Present):**
- `link_id`: Link identifier
- `data_sourc`: Data source identifier
- `valid_code`: Validation code from failed observations
- `avg_hausdo`: Average Hausdorff distance across all failures
- `best_hausd`: Best (minimum) Hausdorff distance
- `worst_haus`: Worst (maximum) Hausdorff distance

**Time Period Fields (Always Present):**
- `00_06_f_cn`: Average failures per day in night period (00:00-06:00)
- `06_11_f_cn`: Average failures per day in morning period (06:00-11:00)
- `11_15_f_cn`: Average failures per day in midday period (11:00-15:00)
- `15_20_f_cn`: Average failures per day in afternoon period (15:00-20:00)
- `20_00_f_cn`: Average failures per day in evening period (20:00-00:00)

**Conditional Fields (When Length Check Enabled):**
- `avg_len_rt`: Average length ratio across all failures
- `best_len`: Best length ratio
- `worst_len`: Worst length ratio

**Conditional Fields (When Coverage Check Enabled):**
- `avg_cover`: Average coverage percentage across all failures
- `best_cov`: Best coverage percentage
- `worst_cov`: Worst coverage percentage

**Metadata Fields:**
- `total_days`: Number of unique days analyzed
- `total_fail`: Total failed observations for this link

### Analytical Benefits

- Identify rush hour vs off-peak failure rates
- Compare morning vs evening validation performance
- Symbolize links by dominant failure period
- 95%+ reduction in shapefile size

### Field Naming Convention

Field names are limited to 10 characters for DBF compatibility:
- `f_cn` suffix indicates "failure count"
- `00_06` format clearly shows time range
- All names designed for immediate recognition in GIS attribute tables

**Conditional Generation Rules:**
- **missing_observations.csv**: Only when "Data Completeness Analysis (Optional)" checkbox is enabled
- **All shapefiles**: Only when shapefile generation is enabled in settings
- **RequestedTime Field**: Used specifically for missing observations output (preserves timestamp for other functions), with the pipeline mirroring between `RequestedTime` and `requested_time` automatically so snake_case CSVs do not trigger KeyErrors.

## Validation Logic Summary

### Core Validation Approach

The validation system provides comprehensive geometric analysis with transparent metrics and clear file separation:

#### **Geometric Accuracy Testing**
- **Hausdorff Distance**: Primary geometric similarity test comparing Google routes to reference geometry
- **Optional Tests**: Length similarity and coverage analysis for detailed validation
- **Threshold-Based**: Configurable distance threshold (default 5.0m) for pass/fail determination

#### **Data Completeness Analysis (Optional)**
- **Temporal Gap Detection**: Combines RequestedTime with date range to identify missing (time + date) combinations
- **Conditional Generation**: Only creates missing observations file when checkbox is enabled
- **Link-Specific Logic**: Only checks for gaps in links that have actual data, not all shapefile links
- **Date-Time Combination**: Properly handles RequestedTime (HH:MM:SS) across multiple dates in the analysis period
- **False Positive Prevention**: Avoids generating missing observations for every possible timestamp across all shapefile links

#### **File Structure Benefits**
- **Clean Separation**: Different failure types in separate files for focused analysis
- **Appropriate Geometries**: Decoded polylines for validation failures, original shapefile geometry for gaps
- **Transparent Results**: Individual test metrics instead of confusing configuration codes

The system handles diverse validation scenarios with reliable geometric analysis and comprehensive reporting capabilities.

## Failed Observations Reference Shapefile

### Visual Comparison Analysis

The system generates two complementary shapefiles for GIS overlay analysis:
1. `failed_observations.shp` - Shows actual Google polyline geometries
2. `failed_observations_reference.shp` - Shows reference shapefile geometries

### Field Structure

**Core Identifiers:**
- `link_id`: Link identifier (e.g., "s_653-655")
- `timestamp`: When the failure occurred
- `num_alternatives`: How many alternatives were attempted

**Aggregated Failure Metrics:**
- `worst_hausdorff`, `best_hausdorff`, `avg_hausdorff`: Distance metrics
- `worst_length_ratio`, `best_length_ratio`, `avg_length_ratio`: Length metrics (when enabled)
- `worst_coverage`, `best_coverage`, `avg_coverage`: Coverage metrics (when enabled)

**Context Information:**
- `valid_code`: Validation context (2=single alternative, 3=multiple alternatives)
- `data_source`: Always "reference_shapefile" for provenance

## Enhanced Data Completeness Analysis

### Auto-Date Detection

The system automatically detects the analysis period from uploaded CSV files:

**Process:**
1. Searches for timestamp columns (timestamp, datetime, date, time)
2. Handles multiple date formats using robust parsing
3. Extracts minimum and maximum dates from valid timestamps
4. Automatically populates analysis period with detected dates

**Benefits:**
- No manual date entry required
- Eliminates errors from wrong date ranges
- Analysis period matches actual data coverage