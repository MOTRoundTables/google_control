#!/usr/bin/env python3
"""
Final test of missing observations logic using proper datetime format
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


def test_final_gap_detection():
    """Test with proper datetime format matching real data"""
    print("FINAL GAP DETECTION TEST")
    print("=" * 40)

    # Use proper datetime format like the real data
    base_date = date(2025, 6, 29)

    # Create test data with intentional gap at 01:00
    test_data = []
    times_with_gap = [
        '00:00:00', '00:15:00', '00:30:00', '00:45:00',
        # Missing: '01:00:00'  <-- This should be detected
        '01:15:00', '01:30:00', '01:45:00', '02:00:00'
    ]

    for i, time_str in enumerate(times_with_gap):
        # Create proper Timestamp column like real data
        timestamp_str = f"29/06/2025 {time_str.split(':')[0]}:{time_str.split(':')[1]}"

        test_data.append({
            'DataID': f'test_{i}',
            'Name': 's_1000-2000',
            'RequestedTime': time_str,
            'Timestamp': timestamp_str,
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
    print(f"  RequestedTime values: {test_df['RequestedTime'].tolist()}")
    print(f"  Timestamp values: {test_df['Timestamp'].tolist()}")
    print(f"  Missing: 01:00:00 (should be detected)")

    # Test the logic
    print(f"\nRunning extract_missing_observations...")

    missing_df = extract_missing_observations(
        validated_df=test_df,
        completeness_params=completeness_params,
        shapefile_gdf=test_shapefile
    )

    print(f"Result: Found {len(missing_df)} missing observations")

    if len(missing_df) > 0:
        print("SUCCESS! Missing times found:")
        for _, row in missing_df.iterrows():
            print(f"  {row['RequestedTime']} (code: {row['valid_code']})")
    else:
        print("No missing observations detected")

    # Now test with the REAL test data format
    print(f"\n" + "=" * 40)
    print("TESTING WITH REAL DATA SAMPLE")

    # Load real data sample
    data_path = project_root / "test_data" / "control" / "data.csv"
    real_df = pd.read_csv(data_path, encoding='utf-8-sig', nrows=500)  # Just first 500 rows

    # Add validation columns
    real_df['is_valid'] = True
    real_df['valid_code'] = 0
    real_df['link_id'] = real_df['Name']

    # Create shapefile for the links in sample
    unique_links = real_df['Name'].unique()[:5]  # First 5 links
    shapefile_data = []
    geometries = []

    for i, link_name in enumerate(unique_links):
        parts = link_name[2:].split('-')
        from_id, to_id = parts
        shapefile_data.append({
            'From': int(from_id),
            'To': int(to_id),
            'Description': f'Real link {link_name}'
        })
        geometries.append(LineString([(i, i), (i+1, i+1)]))

    real_shapefile = gpd.GeoDataFrame(shapefile_data, geometry=geometries, crs='EPSG:4326')

    # Filter to just the links we have in shapefile
    test_real_df = real_df[real_df['Name'].isin(unique_links)].copy()

    print(f"Real data sample:")
    print(f"  Rows: {len(test_real_df)}")
    print(f"  Links: {test_real_df['Name'].nunique()}")
    print(f"  RequestedTime sample: {test_real_df['RequestedTime'].head().tolist()}")

    # Test with real data
    real_completeness_params = {
        'start_date': date(2025, 6, 29),
        'end_date': date(2025, 7, 1),  # 3 days as originally intended
        'interval_minutes': 15
    }

    missing_real_df = extract_missing_observations(
        validated_df=test_real_df,
        completeness_params=real_completeness_params,
        shapefile_gdf=real_shapefile
    )

    print(f"\nReal data test result:")
    print(f"  Found {len(missing_real_df)} missing observations")

    if len(missing_real_df) > 0:
        missing_by_link = missing_real_df.groupby('link_id').size()
        print(f"  Missing by link:")
        for link, count in missing_by_link.head().items():
            print(f"    {link}: {count} missing")


if __name__ == "__main__":
    test_final_gap_detection()