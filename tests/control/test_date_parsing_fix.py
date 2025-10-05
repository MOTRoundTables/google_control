"""
Quick test to verify the date parsing fix works correctly.
"""

import pandas as pd
from components.control.report import _parse_timestamp_series
from datetime import datetime

def test_iso_format_dates():
    """Test that ISO format dates (YYYY-MM-DD) are parsed correctly"""

    # Sample data matching your CSV format
    timestamps = pd.Series([
        '2025-10-02 00:45:52',
        '2025-10-01 00:45:55',
        '2025-10-01 01:31:22',
        '2025-10-01 07:16:02',
        '2025-10-03 00:15:48',
        '2025-10-04 23:31:26',
    ])

    print("Testing date parsing with ISO format (YYYY-MM-DD)...")
    print(f"Sample timestamps:\n{timestamps}\n")

    # Parse timestamps
    parsed = _parse_timestamp_series(timestamps)

    print(f"Parsed timestamps:\n{parsed}\n")

    # Check results
    min_date = parsed.min().date()
    max_date = parsed.max().date()

    print(f"Min date: {min_date}")
    print(f"Max date: {max_date}")
    print(f"Duration: {(max_date - min_date).days + 1} days")

    # Verify the dates are correct
    expected_min = datetime(2025, 10, 1).date()  # October 1, 2025
    expected_max = datetime(2025, 10, 4).date()  # October 4, 2025

    if min_date == expected_min and max_date == expected_max:
        print("\n[OK] SUCCESS: Dates parsed correctly!")
        print(f"  Expected: October 1-4, 2025")
        print(f"  Got:      {min_date.strftime('%B %d, %Y')} - {max_date.strftime('%B %d, %Y')}")

        # Calculate expected observations
        duration_days = (max_date - min_date).days + 1
        observations_per_day = 24 * 60 // 15  # 96 observations per day (15 min intervals)
        expected_observations = duration_days * observations_per_day

        print(f"\n  Duration: {duration_days} days")
        print(f"  Expected observations (15 min intervals, 24/7): {expected_observations}")
        print(f"  This should be 384, not 8,736!")

        return True
    else:
        print("\n[FAIL] Dates parsed incorrectly!")
        print(f"  Expected: October 1-4, 2025")
        print(f"  Got:      {min_date} - {max_date}")
        return False

def test_european_format_dates():
    """Test that European format dates (DD/MM/YYYY) still work"""

    timestamps = pd.Series([
        '01/10/2025 00:45:52',  # Should be October 1, 2025
        '02/10/2025 00:45:55',
        '03/10/2025 01:31:22',
        '04/10/2025 07:16:02',
    ])

    print("\n" + "="*60)
    print("Testing date parsing with European format (DD/MM/YYYY)...")
    print(f"Sample timestamps:\n{timestamps}\n")

    parsed = _parse_timestamp_series(timestamps)

    print(f"Parsed timestamps:\n{parsed}\n")

    min_date = parsed.min().date()
    max_date = parsed.max().date()

    print(f"Min date: {min_date}")
    print(f"Max date: {max_date}")

    expected_min = datetime(2025, 10, 1).date()
    expected_max = datetime(2025, 10, 4).date()

    if min_date == expected_min and max_date == expected_max:
        print("\n[OK] SUCCESS: European format dates parsed correctly!")
        return True
    else:
        print("\n[FAIL] European format dates not working as expected")
        print(f"  Expected: {expected_min} - {expected_max}")
        print(f"  Got:      {min_date} - {max_date}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("Date Parsing Fix Verification")
    print("="*60 + "\n")

    test1 = test_iso_format_dates()
    test2 = test_european_format_dates()

    print("\n" + "="*60)
    if test1 and test2:
        print("ALL TESTS PASSED [OK]")
    else:
        print("SOME TESTS FAILED [FAIL]")
    print("="*60)
