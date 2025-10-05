"""
Test for missing observations date parsing fix.

Verifies that ISO dates are parsed correctly and don't create false missing observations.
"""

import pandas as pd
import geopandas as gpd
from datetime import date, datetime
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from components.control.report import extract_missing_observations, _parse_timestamp_series


def test_parse_timestamp_series_iso_dates():
    """Test that ISO dates are parsed correctly (not misinterpreted)."""

    # Test ISO dates that would be misinterpreted with dayfirst=True
    test_dates = pd.Series([
        '2025-10-01',  # October 1 (not January 10!)
        '2025-01-10',  # January 10 (not October 1!)
        '2025-10-04',  # October 4 (not April 10!)
    ])

    parsed = _parse_timestamp_series(test_dates)

    # Verify months are correct
    assert parsed[0].month == 10, f"October 1 parsed incorrectly! Got month {parsed[0].month}"
    assert parsed[1].month == 1, f"January 10 parsed incorrectly! Got month {parsed[1].month}"
    assert parsed[2].month == 10, f"October 4 parsed incorrectly! Got month {parsed[2].month}"

    print("[OK] ISO date parsing test PASSED")


def test_missing_observations_date_matching():
    """Test that missing observations correctly matches dates (not creating false positives)."""

    # Create test data with ISO dates
    # Period: Oct 1-3, 2025, every 15 minutes
    # We'll have data for all times EXCEPT one specific time

    test_data = []
    for day in [1, 2, 3]:
        for hour in [0, 1, 2]:
            for minute in [0, 15, 30, 45]:
                # Skip one specific observation to create a real missing observation
                if day == 2 and hour == 1 and minute == 30:
                    continue  # This will be missing

                test_data.append({
                    'Name': 's_123-456',
                    'link_id': 's_123-456',
                    'Timestamp': f'2025-10-0{day} {hour:02d}:{minute:02d}:00',
                    'RequestedTime': f'{hour:02d}:{minute:02d}:00',
                    'is_valid': True,
                    'valid_code': 0,
                    'hausdorff_distance': 0.5,
                    'hausdorff_pass': True,
                })

    validated_df = pd.DataFrame(test_data)

    # Create dummy shapefile
    from shapely.geometry import LineString
    shapefile_gdf = gpd.GeoDataFrame({
        'Id': ['123-456'],
        'From': [123],
        'To': [456],
        'geometry': [LineString([(0, 0), (1, 1)])]
    }, crs='EPSG:4326')

    # Completeness parameters
    completeness_params = {
        'start_date': date(2025, 10, 1),
        'end_date': date(2025, 10, 3),
        'interval_minutes': 15
    }

    # Extract missing observations
    missing_df = extract_missing_observations(
        validated_df,
        completeness_params,
        shapefile_gdf
    )

    print(f"\nTotal observations in test data: {len(validated_df)}")
    print(f"Missing observations found: {len(missing_df)}")

    # Should find exactly 1 missing observation (Oct 2, 01:30:00)
    assert len(missing_df) == 1, f"Expected 1 missing observation, found {len(missing_df)}"

    # Verify it's the correct missing observation
    missing_time = missing_df.iloc[0]['RequestedTime']
    assert missing_time == '01:30:00', f"Wrong missing time: {missing_time}"

    print(f"[OK] Missing observation correctly identified: {missing_time}")
    print("[OK] Date matching test PASSED (no false positives)")


def test_no_false_positives_with_iso_dates():
    """Test that ISO dates don't create false missing observations."""

    # Create complete data for one link across 4 days
    # If date parsing is broken, it will create false missing observations

    test_data = []
    for day in [1, 2, 3, 4]:
        for hour in range(24):
            for minute in [0, 15, 30, 45]:
                test_data.append({
                    'Name': 's_789-101',
                    'link_id': 's_789-101',
                    'Timestamp': f'2025-10-0{day} {hour:02d}:{minute:02d}:00',
                    'RequestedTime': f'{hour:02d}:{minute:02d}:00',
                    'is_valid': True,
                    'valid_code': 0,
                    'hausdorff_distance': 1.0,
                    'hausdorff_pass': True,
                })

    validated_df = pd.DataFrame(test_data)

    # Create dummy shapefile
    from shapely.geometry import LineString
    shapefile_gdf = gpd.GeoDataFrame({
        'Id': ['789-101'],
        'From': [789],
        'To': [101],
        'geometry': [LineString([(0, 0), (1, 1)])]
    }, crs='EPSG:4326')

    # Completeness parameters
    completeness_params = {
        'start_date': date(2025, 10, 1),
        'end_date': date(2025, 10, 4),
        'interval_minutes': 15
    }

    # Extract missing observations
    missing_df = extract_missing_observations(
        validated_df,
        completeness_params,
        shapefile_gdf
    )

    print(f"\nComplete dataset test:")
    print(f"Total observations: {len(validated_df)}")
    print(f"Missing observations found: {len(missing_df)}")

    # Should find ZERO missing observations (all data present)
    assert len(missing_df) == 0, f"Expected 0 missing observations, found {len(missing_df)} (FALSE POSITIVES!)"

    print("[OK] No false positives test PASSED")


if __name__ == '__main__':
    print("=" * 70)
    print("Testing Missing Observations Date Parsing Fix")
    print("=" * 70)

    try:
        # Test 1: ISO date parsing
        print("\nTest 1: ISO Date Parsing")
        print("-" * 70)
        test_parse_timestamp_series_iso_dates()

        # Test 2: Correct missing observation detection
        print("\nTest 2: Correct Missing Observation Detection")
        print("-" * 70)
        test_missing_observations_date_matching()

        # Test 3: No false positives with complete data
        print("\nTest 3: No False Positives with Complete Data")
        print("-" * 70)
        test_no_false_positives_with_iso_dates()

        print("\n" + "=" * 70)
        print("ALL TESTS PASSED [OK]")
        print("=" * 70)
        print("\nThe fix is working correctly!")
        print("You can now run control validation - missing observations should be accurate.")

    except AssertionError as e:
        print("\n" + "=" * 70)
        print("TEST FAILED [FAIL]")
        print("=" * 70)
        print(f"\nError: {e}")
        print("\nThe fix needs adjustment before running control validation.")
        sys.exit(1)
    except Exception as e:
        print("\n" + "=" * 70)
        print("TEST ERROR [ERROR]")
        print("=" * 70)
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
