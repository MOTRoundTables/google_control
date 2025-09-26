#!/usr/bin/env python3
"""
Test missing observations logic with real test data from test_data/control/data.csv

This tests the fixed missing observations logic using:
- Date range: 2025-06-29 to 2025-07-01 (3 days)
- 15-minute intervals
- Real data with 2,432 links and 714,385 observations

Expected behavior: Should find only actual temporal gaps, not generate false positives.
"""

import sys
import os
import pandas as pd
import geopandas as gpd
from pathlib import Path
from datetime import date
import tempfile
import shutil

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from components.control.report import extract_missing_observations
from shapely.geometry import LineString


def create_test_shapefile(unique_links):
    """Create a minimal test shapefile with the links from the data"""
    shapefile_data = []
    geometries = []

    for i, link_name in enumerate(unique_links[:10]):  # Just test first 10 links
        # Extract From-To from link name like s_10005-91
        if link_name.startswith('s_'):
            parts = link_name[2:].split('-')
            if len(parts) == 2:
                from_id, to_id = parts
                shapefile_data.append({
                    'From': int(from_id),
                    'To': int(to_id),
                    'Description': f'Test link {link_name}'
                })
                # Create simple line geometry
                geometries.append(LineString([(i, i), (i+1, i+1)]))

    return gpd.GeoDataFrame(shapefile_data, geometry=geometries, crs='EPSG:4326')


def analyze_real_data_gaps():
    """Test missing observations logic with real test data"""

    print("Testing Missing Observations Logic with Real Data")
    print("=" * 60)

    # Load the real test data
    data_path = project_root / "test_data" / "control" / "data.csv"
    print(f"Loading data from: {data_path}")

    try:
        # Read CSV with proper encoding handling
        df = pd.read_csv(data_path, encoding='utf-8-sig')
        print(f"Loaded {len(df):,} rows with columns: {list(df.columns)}")

        # Analyze data structure
        print(f"\nData Analysis:")
        print(f"   Date range: {df['RequestedTime'].min()} to {df['RequestedTime'].max()}")
        unique_links = df['Name'].unique()
        print(f"   Unique links: {len(unique_links):,}")
        print(f"   Sample links: {list(unique_links[:5])}")

        # Create minimal test shapefile
        print(f"\nCreating test shapefile for first 10 links...")
        test_shapefile = create_test_shapefile(unique_links)
        print(f"   Shapefile has {len(test_shapefile)} links")

        # Set up completeness parameters (exact range from data)
        completeness_params = {
            'start_date': date(2025, 6, 29),  # 29/06/2025
            'end_date': date(2025, 7, 1),     # 01/07/2025
            'interval_minutes': 15
        }

        print(f"\nTesting completeness parameters:")
        print(f"   Start date: {completeness_params['start_date']}")
        print(f"   End date: {completeness_params['end_date']}")
        print(f"   Interval: {completeness_params['interval_minutes']} minutes")

        # Calculate expected intervals
        from datetime import datetime, timedelta
        start_dt = datetime.combine(completeness_params['start_date'], datetime.min.time())
        end_dt = datetime.combine(completeness_params['end_date'] + timedelta(days=1), datetime.min.time())

        expected_intervals = []
        current_dt = start_dt
        while current_dt < end_dt:
            expected_intervals.append(current_dt)
            current_dt += timedelta(minutes=15)

        print(f"   Expected intervals per link: {len(expected_intervals)}")
        print(f"   Total expected observations: {len(unique_links[:10]) * len(expected_intervals):,}")

        # Test with only first 10 links to make it manageable
        test_df = df[df['Name'].isin(unique_links[:10])].copy()
        print(f"\nTesting with subset: {len(test_df):,} rows from first 10 links")

        # Add validation fields that missing observations logic expects
        test_df['is_valid'] = True  # Assume all observations are valid
        test_df['valid_code'] = 0   # Valid code
        test_df['link_id'] = test_df['Name']  # Ensure link_id column exists

        # Run the missing observations logic
        print(f"\nRunning extract_missing_observations...")

        try:
            missing_df = extract_missing_observations(
                validated_df=test_df,
                completeness_params=completeness_params,
                shapefile_gdf=test_shapefile
            )

            print(f"Missing observations analysis completed!")
            print(f"   Found {len(missing_df)} missing observations")

            if len(missing_df) > 0:
                print(f"\nMissing observations details:")
                print(f"   Links with missing data: {missing_df['link_id'].nunique()}")
                print(f"   Date range of missing: {missing_df['RequestedTime'].min()} to {missing_df['RequestedTime'].max()}")

                # Show breakdown by link
                missing_by_link = missing_df.groupby('link_id').size()
                print(f"\nMissing observations by link:")
                for link, count in missing_by_link.head(10).items():
                    print(f"   {link}: {count} missing")

                # Sample missing observations
                print(f"\nSample missing observations:")
                print(missing_df[['link_id', 'RequestedTime', 'valid_code']].head())

            else:
                print("No missing observations found - all expected data is present!")

            # Analyze actual data gaps for first few links
            print(f"\nAnalyzing actual gaps in first 3 links:")
            for link in unique_links[:3]:
                link_data = test_df[test_df['link_id'] == link]['RequestedTime'].sort_values()
                if len(link_data) > 0:
                    # Convert to datetime for analysis
                    link_data_dt = pd.to_datetime(link_data, format='%H:%M:%S', errors='coerce')
                    link_data_dt = link_data_dt.dropna()

                    print(f"   {link}: {len(link_data)} observations")
                    if len(link_data) > 1:
                        print(f"      Range: {link_data.iloc[0]} to {link_data.iloc[-1]}")
                        # Check for gaps > 15 minutes
                        gaps = []
                        for i in range(1, len(link_data)):
                            # Simple string comparison for time gaps
                            pass  # Skip complex gap analysis for now

        except Exception as e:
            print(f"Error during missing observations analysis: {e}")
            import traceback
            traceback.print_exc()

    except Exception as e:
        print(f"Error loading data: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    analyze_real_data_gaps()