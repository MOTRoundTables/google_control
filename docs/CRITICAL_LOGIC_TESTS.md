# Critical Logic Tests - Data Correctness Validation

**Purpose**: Identify bugs that cause **incorrect output data**, not performance issues.
**Focus**: Logic errors that silently produce wrong results, data loss, or corrupted files.

---

## 1. Control Validation Component

### 1.1 Unique Polylines Deduplication Logic

**Test Case**: Verify deduplication removes temporal duplicates but keeps unique routes per link

**Critical Bug Risk**: Wrong deduplication key could remove valid route alternatives

```python
# Test Setup
# Link s_1119-9150 with:
# - Timestamp 2025-10-01 08:00: Polyline "ABC123" (Route A)
# - Timestamp 2025-10-01 09:00: Polyline "ABC123" (Route A) - DUPLICATE
# - Timestamp 2025-10-01 10:00: Polyline "XYZ789" (Route B) - UNIQUE
# - Timestamp 2025-10-02 08:00: Polyline "ABC123" (Route A) - DUPLICATE

# Expected Output: 2 features (Route A once, Route B once)
# Bug if: 1 feature (wrongly removed Route B) OR 4 features (no deduplication)
```

**Verification Steps**:
1. Create test CSV with 1000 observations, 50 links, 3 route alternatives each
2. Each route alternative repeated at 10 different timestamps
3. Expected: 150 unique routes (50 links × 3 routes)
4. Run control validation with spatial export
5. Count features in `failed_observations_unique_polylines_shapefile.zip`
6. **FAIL if**: Feature count ≠ 150

**Code Location**: `components/control/report.py:1478-1486`

**Potential Bug**: If deduplication uses `(Name + Timestamp + Polyline)` instead of `(Name + Polyline)`, it won't deduplicate temporal duplicates.

---

### 1.2 Date Parsing - ISO vs Day-First Format

**Test Case**: Verify dates parsed correctly regardless of format

**Critical Bug Risk**: Dates misinterpreted (Oct 1 becomes Jan 10)

```python
# Test Dates
test_dates = [
    "2025-10-01",      # ISO format - Expected: Oct 1, 2025
    "2025-01-10",      # ISO format - Expected: Jan 10, 2025
    "01/10/2025",      # Ambiguous - Could be Oct 1 or Jan 10
    "10/01/2025",      # Ambiguous - Could be Jan 10 or Oct 1
]

# Expected Behavior:
# ISO format (YYYY-MM-DD) should ALWAYS parse correctly
# Ambiguous formats should use ISO priority, then fallback
```

**Verification Steps**:
1. Create test CSV with ISO dates: 2025-10-01, 2025-10-02, 2025-10-03, 2025-10-04
2. Run control validation
3. Check `performance_and_parameters_log.txt` for date range detection
4. **FAIL if**: Shows "2025-01-10 to 2025-04-10" instead of "2025-10-01 to 2025-10-04"

**Code Location**: `components/control/report.py:49-72` (`_parse_timestamp_series`)

**Potential Bug**: Using `dayfirst=True` as default instead of ISO8601 priority.

**Fix Verification**:
```python
# Correct implementation should:
# 1. Try ISO8601 format first
# 2. If >50% fail, try standard parsing
# 3. If still NaN, try dayfirst=True
# This ensures ISO dates are never misinterpreted
```

---

### 1.3 Column Name Preservation

**Test Case**: Verify output files preserve exact input column names

**Critical Bug Risk**: Column names changed = data processing pipelines break

```python
# Input CSV columns (exact case):
input_columns = [
    "DataID", "Name", "SegmentID", "RouteAlternative",
    "Timestamp", "Duration (seconds)", "Static Duration (seconds)",
    "Distance (meters)", "Speed (km/h)", "Polyline"
]

# Expected: ALL output CSVs and shapefiles preserve these names
# Bug if: Lowercased, stripped, or renamed
```

**Verification Steps**:
1. Create test CSV with mixed-case column names
2. Run control validation
3. Check ALL output files for exact column name matches
4. **FAIL if**: Any column renamed (e.g., "Duration (seconds)" → "duration_seconds")

**Code Location**: `components/control/report.py` (CSV writing functions)

**Potential Bug**: Using `df.columns.str.lower()` or automatic column normalization.

---

### 1.4 Failed Observations Reference Shapefile - Time Period Aggregation

**Test Case**: Verify time period boundaries are correct (left-inclusive, right-exclusive)

**Critical Bug Risk**: Wrong hour assignments = wrong time-of-day analysis

```python
# Time Period Definitions (from methodology)
periods = {
    "Night":     (0, 6),   # 00:00-05:59 (excludes 06:00)
    "Morning":   (6, 11),  # 06:00-10:59 (excludes 11:00)
    "Midday":    (11, 15), # 11:00-14:59 (excludes 15:00)
    "Afternoon": (15, 20), # 15:00-19:59 (excludes 20:00)
    "Evening":   (20, 24), # 20:00-23:59 (excludes 24:00/00:00)
}

# Test Data
test_failures = [
    {"hour": 5, "count": 1},   # Should be Night
    {"hour": 6, "count": 1},   # Should be Morning (boundary)
    {"hour": 11, "count": 1},  # Should be Midday (boundary)
    {"hour": 15, "count": 1},  # Should be Afternoon (boundary)
    {"hour": 20, "count": 1},  # Should be Evening (boundary)
    {"hour": 23, "count": 1},  # Should be Evening
]

# Expected field values in failed_observations_reference_shapefile:
# 00_06_f_cn = 1 (hour 5)
# 06_11_f_cn = 1 (hour 6)
# 11_15_f_cn = 1 (hour 11)
# 15_20_f_cn = 1 (hour 15)
# 20_00_f_cn = 2 (hours 20, 23)
```

**Verification Steps**:
1. Create test CSV with failures at exact boundary hours (5, 6, 11, 15, 20, 23)
2. Run control validation with spatial export
3. Check `failed_observations_reference_shapefile.zip` field values
4. **FAIL if**: Boundary hour assigned to wrong period

**Code Location**: `components/control/report.py` (time period aggregation)

**Potential Bug**: Using `<=` instead of `<` for right boundaries.

---

## 2. Aggregation Component

### 2.1 Static Duration Field Ordering

**Test Case**: Verify static duration fields appear RIGHT AFTER regular duration fields

**Critical Bug Risk**: Wrong column order = data misalignment in downstream tools

```python
# Expected Column Order in hourly_agg.csv
expected_order = [
    "link_id", "date", "hour_of_day", "daytype",
    "n_total", "n_valid", "valid_hour", "no_valid_hour",
    "avg_duration_sec",         # Regular duration
    "std_duration_sec",         # Regular duration
    "avg_static_duration_sec",  # Static duration (RIGHT AFTER)
    "std_static_duration_sec",  # Static duration (RIGHT AFTER)
    "avg_distance_m",           # Distance (AFTER static duration)
    "avg_speed_kmh"             # Speed (AFTER distance)
]

# Bug if: Static duration fields at the end instead
wrong_order = [..., "avg_distance_m", "avg_speed_kmh",
               "avg_static_duration_sec", "std_static_duration_sec"]
```

**Verification Steps**:
1. Create test CSV WITH "Static Duration (seconds)" column
2. Run aggregation
3. Check `hourly_agg.csv` column order
4. **FAIL if**: Static duration fields not immediately after regular duration fields

**Code Location**: `components/aggregation/pipeline.py:1863-1878`

**Potential Bug**: Using `.append()` instead of `.insert()` for static duration columns.

---

### 2.2 Null Handling for Hours with No Valid Data

**Test Case**: Verify hours with n_valid=0 have NULL metrics, not zeros

**Critical Bug Risk**: Zeros instead of NULL = false data that looks valid

```python
# Test Data for Link s_123-456 on 2025-10-01 at hour 14:
# - 10 total observations
# - 0 valid observations (all failed validation)

# Expected Output in hourly_agg.csv:
{
    "link_id": "s_123-456",
    "date": "2025-10-01",
    "hour_of_day": 14,
    "n_total": 10,
    "n_valid": 0,
    "valid_hour": False,
    "no_valid_hour": 1,
    "avg_duration_sec": NULL,      # NOT 0
    "std_duration_sec": NULL,      # NOT 0
    "avg_static_duration_sec": NULL,  # NOT 0
    "avg_distance_m": NULL,        # NOT 0
    "avg_speed_kmh": NULL          # NOT 0
}
```

**Verification Steps**:
1. Create test CSV with some hours having all invalid observations
2. Run aggregation
3. Load `hourly_agg.csv` and filter rows where `n_valid = 0`
4. **FAIL if**: ANY metric column has 0 instead of NULL/NaN

**Code Location**: `components/aggregation/pipeline.py` (aggregation logic)

**Potential Bug**: Using `fillna(0)` instead of leaving as NULL for invalid hours.

---

### 2.3 Weekly Profile Exclusion of Invalid Hours

**Test Case**: Verify weekly profile ONLY includes hours where valid_hour=True

**Critical Bug Risk**: Including invalid hours = corrupted weekly patterns

```python
# Test Data
# Link s_123-456:
# - Day 1, Hour 14: n_valid=5 (valid_hour=True)
# - Day 2, Hour 14: n_valid=0 (valid_hour=False)
# - Day 3, Hour 14: n_valid=8 (valid_hour=True)

# Expected in weekly_hourly_profile.csv:
# Should average ONLY Days 1 and 3 (valid hours)
# avg_n_valid = (5 + 8) / 2 = 6.5
# n_days = 2 (not 3!)

# Bug if: Includes Day 2 with n_valid=0
# Wrong result: avg_n_valid = (5 + 0 + 8) / 3 = 4.33
```

**Verification Steps**:
1. Create test CSV with mixed valid/invalid hours for same link+hour
2. Run aggregation
3. Check `weekly_hourly_profile.csv`
4. **FAIL if**: `n_days` includes days with `valid_hour=False`

**Code Location**: `components/aggregation/pipeline.py` (weekly profile generation)

**Potential Bug**: Not filtering by `valid_hour=True` before weekly aggregation.

---

### 2.4 Timestamp/RequestedTime Column Priority

**Test Case**: Verify Timestamp used first, RequestedTime as fallback

**Critical Bug Risk**: Wrong time column = wrong temporal analysis

```python
# Test Case 1: Both columns present
csv_data_1 = {
    "Timestamp": "2025-10-01 14:30:00",
    "RequestedTime": "2025-10-01 14:00:00"  # Different time
}
# Expected: Use Timestamp (14:30:00)
# Bug if: Uses RequestedTime

# Test Case 2: Only RequestedTime present
csv_data_2 = {
    "RequestedTime": "2025-10-01 14:00:00"
}
# Expected: Use RequestedTime (14:00:00)
# Bug if: Fails or uses wrong column
```

**Verification Steps**:
1. Create two test CSVs (one with both, one with only RequestedTime)
2. Run aggregation on both
3. Check hourly assignments in output
4. **FAIL if**: Wrong time column used when both present

**Code Location**: `components/aggregation/pipeline.py` (timestamp column detection)

**Potential Bug**: Hardcoded column name instead of priority-based selection.

---

### 2.5 Chunk Processing Consistency

**Test Case**: Verify chunked reading produces same results as full file read

**Critical Bug Risk**: Chunk boundaries = data loss or double-counting

```python
# Test Setup
# Create CSV with 150,000 rows
# Process with chunk_size = 50,000 (3 chunks)

# Expected:
# - Sum of all n_total across all hours = 150,000
# - No duplicates in output
# - No missing records

# Compare:
# Result A: Process with chunk_size=50000
# Result B: Process with chunk_size=150000 (single chunk)
# Both should be IDENTICAL
```

**Verification Steps**:
1. Create large test CSV (150K rows)
2. Run aggregation with `chunk_size=50000`
3. Run aggregation with `chunk_size=150000`
4. Compare both outputs row-by-row
5. **FAIL if**: ANY difference in results

**Code Location**: `components/aggregation/pipeline.py` (chunked reading logic)

**Potential Bug**: Not properly handling chunk boundaries, duplicate processing.

---

### 2.6 Hebrew Encoding Preservation

**Test Case**: Verify Hebrew text (DayInWeek, DayType) preserved correctly

**Critical Bug Risk**: Encoding corruption = unreadable data

```python
# Input Hebrew Values
hebrew_input = {
    "DayInWeek": "ראשון",  # Sunday
    "DayType": "חול"       # Weekday
}

# Expected Output (same Hebrew characters, UTF-8 with BOM)
# Bug if: Greek characters, question marks, or corrupted text
```

**Verification Steps**:
1. Create test CSV with Hebrew characters (CP1255 or UTF-8)
2. Run aggregation
3. Open output CSVs in Excel/Notepad
4. **FAIL if**: Hebrew text corrupted or shows as Greek

**Code Location**: `components/aggregation/pipeline.py` (encoding detection and CSV writing)

**Potential Bug**: Not using UTF-8 BOM for output or wrong encoding detection.

---

## 3. Maps Component

### 3.1 Link ID Join Logic

**Test Case**: Verify correct join between aggregation data and shapefile

**Critical Bug Risk**: Wrong join = data assigned to wrong links

```python
# Shapefile has links:
shapefile_links = ["s_100-200", "s_200-300", "s_300-400"]

# Aggregation CSV has data for:
agg_links = ["s_100-200", "s_200-300", "s_400-500"]  # s_400-500 NOT in shapefile

# Expected Behavior:
# - s_100-200: Show data (matched)
# - s_200-300: Show data (matched)
# - s_300-400: Show no data (in shapefile, not in CSV)
# - s_400-500: Warning about missing link (in CSV, not in shapefile)

# Bug if:
# - Data from s_400-500 assigned to s_300-400 (wrong join)
# - Silent data loss (no warning)
# - All links shown as "no data"
```

**Verification Steps**:
1. Create shapefile with links A, B, C
2. Create CSV with data for links B, C, D
3. Load both in maps
4. Check which links show data
5. **FAIL if**: Link A shows data OR link D data missing without warning

**Code Location**: `components/maps/map_data.py` (data joining logic)

**Potential Bug**: Using wrong join type (inner vs left vs right).

---

### 3.2 Hour Filtering - Inclusive vs Exclusive

**Test Case**: Verify hour range filtering includes both start and end hours

**Critical Bug Risk**: Off-by-one errors in hour selection

```python
# User selects hour range: 6-9

# Expected behavior: Include hours 6, 7, 8, 9 (4 hours)
# Bug if: Include hours 6, 7, 8 (excludes 9) - off by one
# Bug if: Include hours 7, 8, 9 (excludes 6) - off by one
```

**Verification Steps**:
1. Load test data with exactly 1 observation per hour (0-23)
2. Filter to hours 6-9
3. Count displayed observations
4. **FAIL if**: Count ≠ 4

**Code Location**: `components/maps/map_data.py` (hour filtering)

**Potential Bug**: Using `<` instead of `<=` for end hour.

---

### 3.3 Date Multi-Select Aggregation

**Test Case**: Verify multi-date selection aggregates correctly

**Critical Bug Risk**: Wrong aggregation = misleading visualizations

```python
# Test Data for Link s_123-456, Hour 14:
dates_data = {
    "2025-10-01": {"avg_duration_sec": 120, "n_valid": 10},
    "2025-10-02": {"avg_duration_sec": 150, "n_valid": 8},
    "2025-10-03": {"avg_duration_sec": 90, "n_valid": 12}
}

# User selects all 3 dates

# Expected aggregation:
# avg_duration = (120*10 + 150*8 + 90*12) / (10+8+12)
#              = (1200 + 1200 + 1080) / 30
#              = 3480 / 30
#              = 116 seconds

# Bug if:
# - Simple mean: (120 + 150 + 90) / 3 = 120 (WRONG - ignores weights)
# - Only shows last date: 90 (WRONG - data loss)
```

**Verification Steps**:
1. Create test CSV with different durations and observation counts per date
2. Select multiple dates in Map A
3. Check displayed duration value
4. **FAIL if**: Not weighted by n_valid

**Code Location**: `components/maps/map_data.py` (multi-date aggregation)

**Potential Bug**: Using simple mean instead of weighted average.

---

### 3.4 Metric Toggle - Duration vs Speed

**Test Case**: Verify metric toggle changes symbology correctly

**Critical Bug Risk**: Wrong colors = misinterpreted data

```python
# Link with:
# avg_duration_sec = 300 (5 minutes) - SLOW (should be RED)
# avg_speed_kmh = 60 - FAST (should be GREEN)

# When showing Duration:
# Expected: Link colored RED (high duration = slow = bad)

# When showing Speed:
# Expected: Link colored GREEN (high speed = fast = good)

# Bug if: Colors don't invert when switching metrics
```

**Verification Steps**:
1. Load data with known slow links (high duration, low speed)
2. Toggle between Duration and Speed metrics
3. Check link colors
4. **FAIL if**: Color palette doesn't invert

**Code Location**: `components/maps/symbology.py` (color scheme selection)

**Potential Bug**: Using same color scheme for both metrics.

---

### 3.5 Shapefile ZIP Extraction - Temp Directory Handling

**Test Case**: Verify shapefile data persists after temp directory deletion

**Critical Bug Risk**: Data loss when temp directory cleaned up

```python
# User uploads shapefile ZIP
# System extracts to temp directory
# System loads shapefile from temp directory
# Temp directory is deleted (Python's TemporaryDirectory context exit)

# Expected: GeoDataFrame stored in session state (data persists)
# Bug if: Path stored instead of data (file not found errors)
```

**Verification Steps**:
1. Upload shapefile ZIP through UI
2. Click "Load Shapefile"
3. Wait 1 minute (ensure temp cleanup)
4. Try to use map features
5. **FAIL if**: "File not found" or "No such directory" errors

**Code Location**: `components/maps/maps_page.py:240-283`

**Potential Bug**: Storing file path instead of loaded GeoDataFrame.

**Fixed**: Now stores `shapefile_data` directly in session state within temp context.

---

## 4. Cross-Component Integration

### 4.1 Control → Aggregation Folder Traceability

**Test Case**: Verify aggregation output folder correctly links to control source

**Critical Bug Risk**: Wrong folder = data traceability lost

```python
# Control output: runs/1_10_25/output/control/05_10_25_16_36/
# Contains: best_valid_observations.csv

# User uploads: best_valid_observations.csv + log file to aggregation
# Log file contains: "Run Date: 2025-10-05", "Start Time: 16:36:28"

# Expected aggregation output folder:
# runs/1_10_25/output/aggregation/from_control_05_10_25_16_36/

# Bug if: Different timestamp OR generic folder name
```

**Verification Steps**:
1. Run control validation (note timestamp)
2. Upload control output + log to aggregation
3. Check created aggregation folder name
4. **FAIL if**: Folder name doesn't match control timestamp

**Code Location**: `app.py` (aggregation folder creation logic)

**Potential Bug**: Not extracting timestamp correctly from log file.

---

### 4.2 Maps Auto-Detection of Aggregation Output

**Test Case**: Verify maps finds latest aggregation results

**Critical Bug Risk**: Loading wrong data version

```python
# Folder structure:
# runs/1_10_25/output/aggregation/
#   ├── from_control_05_10_25_16_36/  (older)
#   └── from_control_05_10_25_18_51/  (newer)

# User navigates to Maps page

# Expected: Auto-detect newest folder (18_51)
# Bug if: Loads older folder OR doesn't detect any folder
```

**Verification Steps**:
1. Create multiple aggregation output folders with different timestamps
2. Navigate to Maps page
3. Check which folder's data is suggested/loaded
4. **FAIL if**: Not the most recent folder

**Code Location**: `components/maps/maps_page.py` (folder detection)

**Note**: Currently all files must be uploaded - no auto-detection implemented.

---

## 5. Data Integrity Cross-Checks

### 5.1 Row Count Conservation

**Test Case**: Verify no data loss through pipeline

```python
# Input CSV: 100,000 rows
# Control validation: Should process all 100,000 rows
# Aggregation: Sum of all n_total should equal processed rows

# Checks:
# 1. validated_data.csv row count = input row count
# 2. Sum(hourly_agg.n_total) = number of valid rows processed
# 3. failed_observations.csv + best_valid_observations.csv = validated_data.csv
```

**Verification Steps**:
1. Create test CSV with known row count
2. Run full pipeline
3. Count rows in all outputs
4. **FAIL if**: Any data loss detected

---

### 5.2 Temporal Continuity

**Test Case**: Verify no missing hours in hourly aggregation

```python
# Input: Data for Link s_123-456 from 2025-10-01 to 2025-10-03
# Expected hourly_agg.csv: 24 hours × 3 days = 72 rows for this link

# Even hours with n_valid=0 should exist with NULL metrics
# Bug if: Hours with no data completely missing from output
```

**Verification Steps**:
1. Create test CSV with sparse data (some hours missing)
2. Run aggregation
3. Check hourly_agg.csv for complete hour coverage
4. **FAIL if**: Any hour missing from output

---

### 5.3 Shapefile-CSV Link ID Consistency

**Test Case**: Verify link_id format matches between control and aggregation

```python
# Control output: link_id = "s_653-655"
# Shapefile: From=653, To=655
# Aggregation input: Uses control output
# Maps: Joins on link_id

# All components should use: "s_" + From + "-" + To
# Bug if: Inconsistent format breaks joins
```

**Verification Steps**:
1. Run control validation
2. Check link_id format in outputs
3. Run aggregation with control output
4. Load in maps with shapefile
5. **FAIL if**: Join failures due to format mismatch

---

## 6. Edge Cases and Boundary Conditions

### 6.1 Empty/Minimal Data Handling

**Test Cases**:
- CSV with 0 rows
- CSV with 1 row
- Link with only 1 observation
- Hour with only 1 valid observation
- Week with data for only 1 day

**Expected**: Graceful handling with warnings, not crashes or wrong calculations.

---

### 6.2 Extreme Values

**Test Cases**:
- Duration = 0 seconds (instantaneous)
- Duration = 7200 seconds (2 hours - maximum)
- Speed = 0 km/h (stopped)
- Speed = 200 km/h (very fast)
- Hausdorff distance = 0 (perfect match)
- Hausdorff distance >> threshold (complete mismatch)

**Expected**: All values processed correctly within validation ranges.

---

### 6.3 Missing Optional Fields

**Test Cases**:
- CSV without "Static Duration (seconds)" column
- CSV without "is_valid" column
- CSV without "RouteAlternative" column

**Expected**: Processing continues, optional features disabled, no errors.

---

## Test Execution Priority

### Priority 1 (Critical - Data Correctness)
1. Unique polylines deduplication (1.1)
2. Date parsing ISO format (1.2)
3. Null handling for invalid hours (2.2)
4. Weekly profile invalid hour exclusion (2.3)
5. Link ID join logic (3.1)
6. Static duration field ordering (2.1)

### Priority 2 (Important - Data Quality)
7. Time period boundaries (1.4)
8. Column name preservation (1.3)
9. Chunk processing consistency (2.5)
10. Multi-date aggregation (3.3)
11. Shapefile ZIP temp handling (3.5)

### Priority 3 (Integration)
12. Control→Aggregation traceability (4.1)
13. Row count conservation (5.1)
14. Temporal continuity (5.2)
15. Link ID consistency (5.3)

---

## Automated Test Script Template

```python
import pandas as pd
import geopandas as gpd
from pathlib import Path

def test_unique_polylines_deduplication():
    """Test 1.1 - Unique polylines removes temporal duplicates"""
    # Create test data: 50 links × 3 routes × 10 timestamps = 1500 rows
    # Expected output: 150 unique routes

    test_csv = create_test_csv_with_duplicates(
        n_links=50,
        n_routes_per_link=3,
        n_timestamps=10
    )

    # Run control validation
    run_control_validation(test_csv)

    # Check unique polylines shapefile
    unique_shp = gpd.read_file("output/failed_observations_unique_polylines.shp")

    assert len(unique_shp) == 150, \
        f"Expected 150 unique routes, got {len(unique_shp)}"

def test_null_handling_invalid_hours():
    """Test 2.2 - Hours with n_valid=0 have NULL metrics"""

    test_csv = create_csv_with_invalid_hours()

    # Run aggregation
    run_aggregation(test_csv)

    # Check hourly output
    hourly = pd.read_csv("output/hourly_agg.csv")
    invalid_hours = hourly[hourly['n_valid'] == 0]

    # All metric columns should be NULL, not 0
    metric_cols = ['avg_duration_sec', 'std_duration_sec',
                   'avg_distance_m', 'avg_speed_kmh']

    for col in metric_cols:
        assert invalid_hours[col].isna().all(), \
            f"Column {col} has values instead of NULL for invalid hours"

# Add more tests following this pattern...
```

---

## Summary

**Total Critical Tests**: 14 priority-1 and priority-2 tests
**Focus**: Data correctness, not performance
**Goal**: Catch silent logic errors that produce wrong outputs

**Most Critical Bugs to Watch**:
1. ✅ Unique polylines deduplication (VERIFIED - uses Name+Polyline only, ignores timestamps)
2. ✅ Date parsing ISO priority (FIXED - ISO8601 first)
3. ⚠️ Null handling for invalid hours (NEEDS VERIFICATION)
4. ⚠️ Weekly profile filtering (NEEDS VERIFICATION)
5. ⚠️ Link ID joins in maps (NEEDS VERIFICATION)
6. ✅ Shapefile ZIP temp handling (FIXED - stores GeoDataFrame directly)

**Next Steps**:
1. Implement automated test suite for Priority 1 tests
2. Create test data generators for each scenario
3. Run full regression test before each release
4. Document any bugs found and fixes applied
