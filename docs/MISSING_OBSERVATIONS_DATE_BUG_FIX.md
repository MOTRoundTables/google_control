# Missing Observations Date Parsing Bug Fix

**Date**: October 6, 2025
**Component**: Control Validation
**Severity**: Critical (933,888 false positives)

---

## Bug Description

The `extract_missing_observations()` function was using `dayfirst=True` for date parsing, causing ISO dates to be misinterpreted and creating hundreds of thousands of false "missing observations."

---

## Symptoms

**Expected**: 4 missing observations
**Actual**: 933,888 missing observations (233,472× more than expected!)

Each link+time combination was flagged as missing for ALL dates because date matching failed.

---

## Root Cause

**File**: `components/control/report.py:1166`

**Buggy Code**:
```python
timestamp_dates = pd.to_datetime(link_df[timestamp_col], errors='coerce', dayfirst=True).dt.date
```

**Problem**: ISO dates like `2025-10-01` were parsed as January 10 instead of October 1.

---

## Fix Applied

**Changed to**:
```python
parsed_timestamps = _parse_timestamp_series(link_df[timestamp_col])
timestamp_dates = parsed_timestamps.dt.date
```

Now uses the same ISO8601-priority parsing as the rest of the system.

---

## Other Locations Checked

### ✅ **No other bugs found in core components**

**Checked locations**:
1. ✅ `components/control/report.py:64` - Safe (only fills NaN values)
2. ⚠️ `utils/test_runners/test_comprehensive_missing_obs.py:43,66` - Test scripts only (non-critical)
3. ⚠️ `utils/debug/debug_timestamps.py:10` - Debug script only (non-critical)

**All production code is safe.** Only test/debug scripts have `dayfirst=True`, which won't affect actual data processing.

---

## Verification

After fix, re-run control validation and verify:
- `missing_observations.csv` has ~4 rows (not 933,888)
- `link_report.csv` shows `missing_observations` sum = 4
- Date ranges display correctly (Oct 1-4, not Jan 10 - Apr 10)
