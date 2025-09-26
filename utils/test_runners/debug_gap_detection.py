#!/usr/bin/env python3
"""
Debug gap detection in missing observations logic
"""

import sys
import pandas as pd
import geopandas as gpd
from pathlib import Path
from datetime import date, datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from components.control.report import extract_missing_observations
from shapely.geometry import LineString


def debug_gap_detection():
    """Debug why gaps aren't being detected"""
    print("DEBUG GAP DETECTION")
    print("=" * 40)

    # Create very simple test case with obvious gap
    base_date = date(2025, 6, 29)
    base_time = datetime.combine(base_date, datetime.min.time())

    # Link with obvious gap at 01:00
    test_data = []
    times = ['00:00:00', '00:15:00', '00:30:00', '00:45:00',
             # GAP: missing 01:00:00
             '01:15:00', '01:30:00', '01:45:00']

    for i, time_str in enumerate(times):
        test_data.append({
            'DataID': f'test_{i}',
            'Name': 's_1000-2000',
            'RequestedTime': time_str,
            'is_valid': True,
            'valid_code': 0,
            'link_id': 's_1000-2000'
        })

    test_df = pd.DataFrame(test_data)

    # Create minimal shapefile
    shapefile_data = [{
        'From': 1000,
        'To': 2000,
        'Description': 'Test link'
    }]
    test_shapefile = gpd.GeoDataFrame(
        shapefile_data,
        geometry=[LineString([(0, 0), (1, 1)])],
        crs='EPSG:4326'
    )

    completeness_params = {
        'start_date': base_date,
        'end_date': base_date,  # Single day
        'interval_minutes': 15
    }

    print(f"Test data:")
    print(f"  Link: s_1000-2000")
    print(f"  Times: {test_df['RequestedTime'].tolist()}")
    print(f"  Missing: 01:00:00 (should be detected)")

    # Generate expected timestamps for comparison
    start_dt = datetime.combine(base_date, datetime.min.time())
    end_dt = start_dt + timedelta(days=1)

    expected_timestamps = []
    current_dt = start_dt
    while current_dt < end_dt:
        expected_timestamps.append(current_dt)
        current_dt += timedelta(minutes=15)

    print(f"\nExpected first 8 timestamps:")
    for i, ts in enumerate(expected_timestamps[:8]):
        missing_marker = " <-- MISSING" if ts.strftime('%H:%M:%S') == '01:00:00' else ""
        print(f"  {ts.strftime('%H:%M:%S')}{missing_marker}")

    # Test the logic
    print(f"\nRunning extract_missing_observations...")

    missing_df = extract_missing_observations(
        validated_df=test_df,
        completeness_params=completeness_params,
        shapefile_gdf=test_shapefile
    )

    print(f"Result: Found {len(missing_df)} missing observations")

    if len(missing_df) > 0:
        print("Missing times found:")
        for _, row in missing_df.iterrows():
            print(f"  {row['RequestedTime']} (code: {row['valid_code']})")
    else:
        print("No missing observations detected")

    # Debug the internal logic step by step
    print(f"\nDEBUGGING INTERNAL LOGIC...")

    # Mimic the internal processing exactly as in the function
    df = test_df.copy()
    df['requested_time'] = df['RequestedTime']

    # Test the parsing logic step by step
    print(f"Before parsing:")
    print(f"  is_datetime: {pd.api.types.is_datetime64_any_dtype(df['requested_time'])}")

    if not pd.api.types.is_datetime64_any_dtype(df['requested_time']):
        print("Applying _parse_timestamp_series...")
        from components.control.report import _parse_timestamp_series
        df['requested_time'] = _parse_timestamp_series(df['requested_time'])
        print(f"  After _parse_timestamp_series: {pd.api.types.is_datetime64_any_dtype(df['requested_time'])}")

        if not pd.api.types.is_datetime64_any_dtype(df['requested_time']):
            print("Applying time + date combination...")
            try:
                df['requested_time'] = pd.to_datetime(
                    base_date.strftime('%Y-%m-%d') + ' ' + df['requested_time'].astype(str),
                    errors='coerce'
                )
                print(f"  After date combination: {pd.api.types.is_datetime64_any_dtype(df['requested_time'])}")
            except Exception as e:
                print(f"  Error in date combination: {e}")

    # Check if times are parsed correctly
    print(f"RequestedTime after all parsing:")
    for val in df['requested_time']:
        print(f"  {val} (type: {type(val)})")

    # Test the range restriction logic
    link_data = df[df['link_id'] == 's_1000-2000']['requested_time'].dropna()
    if not link_data.empty:
        link_start = link_data.min()
        link_end = link_data.max()
        print(f"\nLink time range:")
        print(f"  Start: {link_start}")
        print(f"  End: {link_end}")

        # Extended range check
        extended_start = link_start - timedelta(minutes=15)
        extended_end = link_end + timedelta(minutes=15)
        print(f"  Extended start: {extended_start}")
        print(f"  Extended end: {extended_end}")

        # Expected 01:00:00 timestamp
        expected_missing = datetime(2025, 6, 29, 1, 0, 0)
        in_range = extended_start <= expected_missing <= extended_end
        print(f"  Expected missing time (01:00:00): {expected_missing}")
        print(f"  Is in extended range: {in_range}")

    # Check normalization
    interval_minutes = 15
    def normalize_to_interval(ts, interval_minutes):
        """Test normalization function"""
        if pd.isna(ts):
            return ts
        if isinstance(ts, str):
            # Try to parse time string
            try:
                dt = datetime.strptime(ts, '%H:%M:%S')
                dt = dt.replace(year=2025, month=6, day=29)  # Add date
            except:
                return ts
        else:
            dt = ts

        minutes = dt.minute
        normalized_minutes = (minutes // interval_minutes) * interval_minutes
        return dt.replace(minute=normalized_minutes, second=0, microsecond=0)

    print(f"\nNormalization test:")
    for val in df['requested_time']:
        normalized = normalize_to_interval(val, interval_minutes)
        print(f"  {val} -> {normalized}")


if __name__ == "__main__":
    debug_gap_detection()