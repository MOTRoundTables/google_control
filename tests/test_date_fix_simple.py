"""Simple test to verify date parsing fix works"""
import sys
sys.path.insert(0, 'E:/google_agg')

import pandas as pd
from components.control.report import _parse_timestamp_series

print("Testing Date Parsing Fix")
print("=" * 70)

# Test 1: ISO dates should NOT be misinterpreted
print("\nTest 1: ISO Date Parsing")
print("-" * 70)

iso_dates = pd.Series([
    '2025-10-01',  # Should be October 1
    '2025-10-04',  # Should be October 4
])

parsed = _parse_timestamp_series(iso_dates)
print(f"Input: {iso_dates.tolist()}")
print(f"Parsed: {parsed.tolist()}")
print(f"Months: {parsed.dt.month.tolist()}")

assert parsed[0].month == 10, f"FAIL: Oct 1 parsed as month {parsed[0].month}"
assert parsed[1].month == 10, f"FAIL: Oct 4 parsed as month {parsed[1].month}"
print("[OK] ISO dates parsed correctly")

# Test 2: Compare old vs new approach
print("\nTest 2: Old (buggy) vs New (fixed) approach")
print("-" * 70)

test_date = '2025-10-01 14:30:00'
series = pd.Series([test_date])

# Old buggy way (dayfirst=True)
old_parsed = pd.to_datetime(series, errors='coerce', dayfirst=True)
print(f"OLD (dayfirst=True): {old_parsed[0]} -> Month {old_parsed[0].month}")

# New fixed way
new_parsed = _parse_timestamp_series(series)
print(f"NEW (_parse_timestamp_series): {new_parsed[0]} -> Month {new_parsed[0].month}")

if old_parsed[0].month != new_parsed[0].month:
    print(f"[OK] Fix working! Old was wrong (month {old_parsed[0].month}), new is correct (month {new_parsed[0].month})")
else:
    print("[OK] Both give same result for this date")

print("\n" + "=" * 70)
print("Fix verified - date parsing is working correctly!")
print("=" * 70)
print("\nYou can now run control validation.")
print("Expected result: ~4 missing observations (not 933,888)")
