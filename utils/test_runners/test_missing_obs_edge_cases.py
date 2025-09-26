#!/usr/bin/env python3
"""
Comprehensive edge case testing for missing observations logic.

Tests:
1. Route alternatives handling (why 289 vs 288 observations)
2. Links not in CSV vs links with actual temporal gaps
3. Expected missing observations count for full dataset
4. Various edge cases and scenarios
"""

import sys
import os
import pandas as pd
import geopandas as gpd
from pathlib import Path
from datetime import date, datetime, timedelta
import tempfile

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from components.control.report import extract_missing_observations, extract_no_data_links
from shapely.geometry import LineString


def analyze_route_alternatives():
    """Analyze route alternatives in the test data"""
    print("ROUTE ALTERNATIVES ANALYSIS")
    print("=" * 50)

    # Load the test data
    data_path = project_root / "test_data" / "control" / "data.csv"
    df = pd.read_csv(data_path, encoding='utf-8-sig')

    # Focus on s_10005-91 which had 289 observations
    link_data = df[df['Name'] == 's_10005-91'].copy()

    print(f"Link s_10005-91 analysis:")
    print(f"  Total rows: {len(link_data)}")
    print(f"  Unique RequestedTime values: {link_data['RequestedTime'].nunique()}")
    print(f"  Unique RouteAlternative values: {sorted(link_data['RouteAlternative'].unique())}")

    # Check for multiple route alternatives per timestamp
    route_alt_breakdown = link_data.groupby('RequestedTime')['RouteAlternative'].nunique()
    multi_alt_times = route_alt_breakdown[route_alt_breakdown > 1]

    print(f"  Times with multiple route alternatives: {len(multi_alt_times)}")
    if len(multi_alt_times) > 0:
        print(f"  Example multi-alternative times:")
        for time_val in list(multi_alt_times.index)[:5]:
            alts = link_data[link_data['RequestedTime'] == time_val]['RouteAlternative'].tolist()
            print(f"    {time_val}: alternatives {alts}")

    # Expected: 3 days * 96 intervals/day = 288 unique timestamps
    expected_unique_times = 3 * 96
    actual_unique_times = link_data['RequestedTime'].nunique()

    print(f"  Expected unique times (3 days * 96): {expected_unique_times}")
    print(f"  Actual unique times: {actual_unique_times}")
    print(f"  Difference: {actual_unique_times - expected_unique_times}")

    return link_data


def create_gap_test_data():
    """Create test data with intentional gaps"""
    print("\nCREATING GAP TEST DATA")
    print("=" * 50)

    base_time = datetime(2025, 6, 29, 0, 0)
    test_data = []

    # Link 1: Complete data (no gaps)
    link1_name = "s_1000-2000"
    for i in range(96):  # Full day
        test_data.append({
            'DataID': f'test_{i}',
            'Name': link1_name,
            'SegmentID': '1000',
            'RouteAlternative': 1,
            'RequestedTime': (base_time + timedelta(minutes=i*15)).strftime('%H:%M:%S'),
            'Timestamp': base_time + timedelta(minutes=i*15),
            'is_valid': True,
            'valid_code': 0,
            'link_id': link1_name
        })

    # Link 2: Data with 3 missing intervals (gaps)
    link2_name = "s_2000-3000"
    missing_intervals = [10, 25, 50]  # Missing 02:30, 06:15, 12:30

    for i in range(96):
        if i not in missing_intervals:
            test_data.append({
                'DataID': f'test_gap_{i}',
                'Name': link2_name,
                'SegmentID': '2000',
                'RouteAlternative': 1,
                'RequestedTime': (base_time + timedelta(minutes=i*15)).strftime('%H:%M:%S'),
                'Timestamp': base_time + timedelta(minutes=i*15),
                'is_valid': True,
                'valid_code': 0,
                'link_id': link2_name
            })

    # Link 3: Only partial data (first 50% of day)
    link3_name = "s_3000-4000"
    for i in range(48):  # Only first half of day
        test_data.append({
            'DataID': f'test_partial_{i}',
            'Name': link3_name,
            'SegmentID': '3000',
            'RouteAlternative': 1,
            'RequestedTime': (base_time + timedelta(minutes=i*15)).strftime('%H:%M:%S'),
            'Timestamp': base_time + timedelta(minutes=i*15),
            'is_valid': True,
            'valid_code': 0,
            'link_id': link3_name
        })

    # Create shapefile for all links
    shapefile_data = []
    geometries = []

    for i, link_name in enumerate([link1_name, link2_name, link3_name, "s_4000-5000"]):  # Extra link not in data
        parts = link_name[2:].split('-')
        from_id, to_id = parts
        shapefile_data.append({
            'From': int(from_id),
            'To': int(to_id),
            'Description': f'Test link {link_name}'
        })
        geometries.append(LineString([(i, i), (i+1, i+1)]))

    test_df = pd.DataFrame(test_data)
    test_shapefile = gpd.GeoDataFrame(shapefile_data, geometry=geometries, crs='EPSG:4326')

    print(f"Created test data:")
    print(f"  Link 1 ({link1_name}): {len(test_df[test_df['Name'] == link1_name])} observations (complete)")
    print(f"  Link 2 ({link2_name}): {len(test_df[test_df['Name'] == link2_name])} observations (3 gaps)")
    print(f"  Link 3 ({link3_name}): {len(test_df[test_df['Name'] == link3_name])} observations (partial)")
    print(f"  Shapefile has {len(test_shapefile)} links (including s_4000-5000 not in data)")

    return test_df, test_shapefile, missing_intervals


def test_missing_observations_edge_cases():
    """Test missing observations logic with edge cases"""
    print("\nTESTING MISSING OBSERVATIONS EDGE CASES")
    print("=" * 50)

    test_df, test_shapefile, expected_missing_intervals = create_gap_test_data()

    # Set up completeness parameters for single day test
    completeness_params = {
        'start_date': date(2025, 6, 29),
        'end_date': date(2025, 6, 29),  # Single day
        'interval_minutes': 15
    }

    print(f"Testing with date range: {completeness_params['start_date']} (single day)")
    print(f"Expected intervals per day: 96")

    # Test missing observations logic
    missing_df = extract_missing_observations(
        validated_df=test_df,
        completeness_params=completeness_params,
        shapefile_gdf=test_shapefile
    )

    print(f"\nMISSING OBSERVATIONS RESULTS:")
    print(f"  Found {len(missing_df)} missing observations")

    if len(missing_df) > 0:
        missing_by_link = missing_df.groupby('link_id').size()
        print(f"  Missing by link:")
        for link, count in missing_by_link.items():
            print(f"    {link}: {count} missing")

        print(f"\nExpected missing (Link 2 gaps): {len(expected_missing_intervals)}")
        print(f"Actual missing found: {len(missing_df)}")

        # Show the specific missing times
        if 's_2000-3000' in missing_df['link_id'].values:
            link2_missing = missing_df[missing_df['link_id'] == 's_2000-3000']['RequestedTime'].tolist()
            print(f"Link 2 missing times: {link2_missing}")

    # Test no-data links logic
    no_data_df = extract_no_data_links(
        validated_df=test_df,
        shapefile_gdf=test_shapefile
    )

    print(f"\nNO-DATA LINKS RESULTS:")
    print(f"  Found {len(no_data_df)} no-data links")
    if len(no_data_df) > 0:
        print(f"  No-data links: {no_data_df['link_id'].tolist()}")


def analyze_full_dataset_expectations():
    """Analyze why full dataset should have ~2 missing observations"""
    print("\nFULL DATASET ANALYSIS")
    print("=" * 50)

    # Load the full test data
    data_path = project_root / "test_data" / "control" / "data.csv"
    df = pd.read_csv(data_path, encoding='utf-8-sig')

    print(f"Full dataset overview:")
    print(f"  Total rows: {len(df):,}")
    print(f"  Unique links: {df['Name'].nunique():,}")
    print(f"  Date range: {df['RequestedTime'].min()} to {df['RequestedTime'].max()}")

    # Analyze completeness per link
    print(f"\nCompleteness analysis:")

    # Expected timestamps for 3 days
    expected_times_per_day = 96  # 24 hours * 4 intervals/hour
    expected_times_3_days = expected_times_per_day * 3

    link_completeness = []

    for link in df['Name'].unique():
        link_data = df[df['Name'] == link]
        unique_times = link_data['RequestedTime'].nunique()
        missing_count = expected_times_3_days - unique_times

        if missing_count > 0:
            link_completeness.append({
                'link': link,
                'actual_times': unique_times,
                'missing_count': missing_count
            })

    print(f"  Expected unique times per link (3 days): {expected_times_3_days}")
    print(f"  Links with missing data: {len(link_completeness)}")

    if len(link_completeness) > 0:
        total_missing = sum(lc['missing_count'] for lc in link_completeness)
        print(f"  Total missing observations: {total_missing}")
        print(f"  Links with most missing data:")

        sorted_incomplete = sorted(link_completeness, key=lambda x: x['missing_count'], reverse=True)
        for lc in sorted_incomplete[:5]:
            print(f"    {lc['link']}: {lc['actual_times']} times ({lc['missing_count']} missing)")
    else:
        print(f"  All links appear complete!")

    # Check for route alternatives impact
    print(f"\nRoute alternatives impact:")
    total_rows = len(df)
    unique_link_time_combinations = df.groupby(['Name', 'RequestedTime']).size().count()
    extra_observations = total_rows - unique_link_time_combinations

    print(f"  Total rows: {total_rows:,}")
    print(f"  Unique (link, time) combinations: {unique_link_time_combinations:,}")
    print(f"  Extra observations (route alternatives): {extra_observations:,}")


def main():
    """Run all edge case tests"""
    print("MISSING OBSERVATIONS EDGE CASE TESTING")
    print("=" * 60)

    # 1. Analyze route alternatives in real data
    link_data = analyze_route_alternatives()

    # 2. Test edge cases with synthetic gaps
    test_missing_observations_edge_cases()

    # 3. Analyze full dataset expectations
    analyze_full_dataset_expectations()

    print(f"\n" + "=" * 60)
    print("EDGE CASE TESTING COMPLETED")


if __name__ == "__main__":
    main()