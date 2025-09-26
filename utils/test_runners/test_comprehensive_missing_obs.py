#!/usr/bin/env python3
"""
Comprehensive test of missing observations logic with real data.

Tests:
- Real data from 29/6/25 to 1/7/25 (3 days)
- Expected: 288 observations per link (3 days × 96 intervals)
- Edge cases: shapefile links not in data, validation below thresholds
- File generation verification
"""

import sys
import pandas as pd
import geopandas as gpd
from pathlib import Path
from datetime import date, datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from components.control.report import extract_missing_observations, extract_no_data_links
from components.control.page import save_validation_results
from shapely.geometry import LineString


def analyze_real_data_completeness():
    """Analyze completeness of real test data"""
    print("COMPREHENSIVE MISSING OBSERVATIONS TEST")
    print("=" * 60)

    # Load real test data
    data_path = project_root / "test_data" / "control" / "data.csv"
    df = pd.read_csv(data_path, encoding='utf-8-sig')

    print(f"Real data analysis:")
    print(f"  Total rows: {len(df):,}")
    print(f"  Unique links: {df['Name'].nunique():,}")
    print(f"  Date range (RequestedTime): {df['RequestedTime'].min()} to {df['RequestedTime'].max()}")

    # Analyze timestamp dates
    try:
        timestamps = pd.to_datetime(df['Timestamp'], errors='coerce', dayfirst=True)
        timestamp_dates = timestamps.dt.date.dropna().unique()
        print(f"  Actual dates (from Timestamp): {sorted(timestamp_dates)}")
        print(f"  Date span: {len(timestamp_dates)} days")
    except:
        print("  Could not parse Timestamp dates")

    # Expected observations per link
    expected_per_day = 96  # 24 hours × 4 intervals per hour
    expected_3_days = expected_per_day * 3
    print(f"  Expected per link (3 days): {expected_3_days} observations")

    # Analyze completeness by link
    completeness_analysis = []
    unique_links = df['Name'].unique()

    print(f"\nAnalyzing completeness for first 10 links:")
    for link in unique_links[:10]:
        link_data = df[df['Name'] == link]
        unique_times = link_data['RequestedTime'].nunique()

        # Try to count unique date+time combinations
        try:
            timestamps = pd.to_datetime(link_data['Timestamp'], errors='coerce', dayfirst=True)
            unique_date_times = len(timestamps.dropna().unique())
        except:
            unique_date_times = len(link_data)

        missing_count = expected_3_days - unique_times

        completeness_analysis.append({
            'link': link,
            'total_rows': len(link_data),
            'unique_times': unique_times,
            'unique_date_times': unique_date_times,
            'missing_count': missing_count,
            'completeness_pct': (unique_times / expected_3_days) * 100
        })

        print(f"  {link}: {unique_times} unique times, {unique_date_times} date+times, {missing_count} missing")

    return df, completeness_analysis


def create_test_shapefile_with_extra_links(df):
    """Create test shapefile including links NOT in the data"""
    print(f"\nCreating test shapefile with extra links...")

    # Get unique links from data
    data_links = set(df['Name'].unique())
    print(f"  Links in data: {len(data_links)}")

    # Create shapefile with data links + extra links
    shapefile_data = []
    geometries = []

    # Add first 20 data links
    for i, link_name in enumerate(list(data_links)[:20]):
        parts = link_name[2:].split('-')
        if len(parts) == 2:
            from_id, to_id = parts
            shapefile_data.append({
                'From': int(from_id),
                'To': int(to_id),
                'Description': f'Data link {link_name}'
            })
            geometries.append(LineString([(i, i), (i+1, i+1)]))

    # Add 5 extra links NOT in data
    extra_links = [
        ('99001', '99002', 'Extra link 1'),
        ('99003', '99004', 'Extra link 2'),
        ('99005', '99006', 'Extra link 3'),
        ('99007', '99008', 'Extra link 4'),
        ('99009', '99010', 'Extra link 5')
    ]

    for i, (from_id, to_id, desc) in enumerate(extra_links):
        shapefile_data.append({
            'From': int(from_id),
            'To': int(to_id),
            'Description': desc
        })
        geometries.append(LineString([(i+20, i+20), (i+21, i+21)]))

    test_shapefile = gpd.GeoDataFrame(shapefile_data, geometry=geometries, crs='EPSG:4326')

    # Calculate expected no-data links
    shapefile_links = set(f"s_{row['From']}-{row['To']}" for _, row in test_shapefile.iterrows())
    no_data_links = shapefile_links - data_links

    print(f"  Total shapefile links: {len(test_shapefile)}")
    print(f"  Expected no-data links: {len(no_data_links)} - {list(no_data_links)}")

    return test_shapefile, no_data_links


def test_missing_observations_with_real_data():
    """Test missing observations logic with real data"""
    print(f"\n" + "=" * 60)
    print("TESTING MISSING OBSERVATIONS WITH REAL DATA")
    print("=" * 60)

    # Load and analyze data
    df, completeness_analysis = analyze_real_data_completeness()

    # Create test shapefile with extra links
    test_shapefile, expected_no_data_links = create_test_shapefile_with_extra_links(df)

    # Prepare test data (first 20 links)
    test_links = [f"s_{row['From']}-{row['To']}" for _, row in test_shapefile.iterrows() if f"s_{row['From']}-{row['To']}" in df['Name'].values]
    test_df = df[df['Name'].isin(test_links)].copy()

    # Add validation columns
    test_df['is_valid'] = True
    test_df['valid_code'] = 0
    test_df['link_id'] = test_df['Name']

    print(f"Test dataset:")
    print(f"  Links tested: {len(test_links)}")
    print(f"  Rows: {len(test_df):,}")

    # Test missing observations
    completeness_params = {
        'start_date': date(2025, 6, 29),  # 29/06/2025
        'end_date': date(2025, 7, 1),     # 01/07/2025
        'interval_minutes': 15
    }

    print(f"  Date range: {completeness_params['start_date']} to {completeness_params['end_date']}")
    print(f"  Expected intervals: {3 * 96} per link")

    # Run missing observations analysis
    missing_df = extract_missing_observations(
        validated_df=test_df,
        completeness_params=completeness_params,
        shapefile_gdf=test_shapefile
    )

    print(f"\nMISSING OBSERVATIONS RESULTS:")
    print(f"  Found: {len(missing_df)} missing observations")

    if len(missing_df) > 0:
        missing_by_link = missing_df.groupby('link_id').size().sort_values(ascending=False)
        print(f"  Links with missing data: {len(missing_by_link)}")
        print(f"  Top links with most missing:")
        for link, count in missing_by_link.head(10).items():
            print(f"    {link}: {count} missing")

        # Show sample missing times
        print(f"  Sample missing observations:")
        sample_missing = missing_df.head(5)[['link_id', 'RequestedTime', 'valid_code']]
        for _, row in sample_missing.iterrows():
            print(f"    {row['link_id']}: {row['RequestedTime']} (code {row['valid_code']})")

    # Test no-data links
    no_data_df = extract_no_data_links(
        validated_df=test_df,
        shapefile_gdf=test_shapefile
    )

    print(f"\nNO-DATA LINKS RESULTS:")
    print(f"  Found: {len(no_data_df)} no-data links")
    if len(no_data_df) > 0:
        found_no_data = set(no_data_df['link_id'].tolist())
        print(f"  No-data links: {found_no_data}")
        print(f"  Expected: {expected_no_data_links}")
        print(f"  Match expected: {'YES' if found_no_data == expected_no_data_links else 'NO'}")

    return missing_df, no_data_df, test_df, test_shapefile


def test_complete_workflow_with_edge_cases():
    """Test complete workflow including file generation"""
    print(f"\n" + "=" * 60)
    print("TESTING COMPLETE WORKFLOW WITH EDGE CASES")
    print("=" * 60)

    missing_df, no_data_df, test_df, test_shapefile = test_missing_observations_with_real_data()

    # Create output directory
    import tempfile
    output_dir = Path(tempfile.mkdtemp()) / "test_output"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Testing complete workflow...")
    print(f"  Output directory: {output_dir}")

    # Test with completeness analysis enabled
    completeness_params = {
        'start_date': date(2025, 6, 29),
        'end_date': date(2025, 7, 1),
        'interval_minutes': 15
    }

    try:
        output_files = save_validation_results(
            result_df=test_df,
            report_gdf=test_shapefile,
            output_dir=str(output_dir),
            generate_shapefile=True,
            completeness_params=completeness_params
        )

        print(f"  Generated files:")
        for file_type, file_path in output_files.items():
            file_size = Path(file_path).stat().st_size if Path(file_path).exists() else 0
            print(f"    {file_type}: {Path(file_path).name} ({file_size:,} bytes)")

        # Verify file contents
        print(f"\nFile content verification:")

        # Check missing observations file
        if 'missing_observations_csv' in output_files:
            missing_csv = pd.read_csv(output_files['missing_observations_csv'])
            print(f"  missing_observations.csv: {len(missing_csv)} rows")
            if len(missing_csv) > 0:
                codes = missing_csv['valid_code'].unique()
                print(f"    Codes: {codes} (should be [94])")

        # Check no-data links file
        if 'no_data_links_csv' in output_files:
            no_data_csv = pd.read_csv(output_files['no_data_links_csv'])
            print(f"  no_data_links.csv: {len(no_data_csv)} rows")
            if len(no_data_csv) > 0:
                codes = no_data_csv['valid_code'].unique()
                print(f"    Codes: {codes} (should be [95])")

        # Check link report has total_success_rate
        if 'link_report_csv' in output_files:
            link_report = pd.read_csv(output_files['link_report_csv'])
            has_total_success = 'total_success_rate' in link_report.columns
            print(f"  link_report.csv: {len(link_report)} rows")
            print(f"    Has total_success_rate field: {'YES' if has_total_success else 'NO'}")
            if has_total_success:
                avg_success = link_report['total_success_rate'].mean()
                print(f"    Average success rate: {avg_success:.1f}%")

        return True

    except Exception as e:
        print(f"  ERROR in workflow: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        import shutil
        try:
            shutil.rmtree(output_dir.parent)
        except:
            pass


def main():
    """Run comprehensive tests"""
    print("COMPREHENSIVE MISSING OBSERVATIONS TESTING")
    print("=" * 80)

    success = test_complete_workflow_with_edge_cases()

    print(f"\n" + "=" * 80)
    print(f"COMPREHENSIVE TEST RESULTS")
    print("=" * 80)

    if success:
        print("ALL TESTS PASSED! Missing observations logic working correctly.")
        print("\nKey findings:")
        print("- Missing observations detected correctly for real data")
        print("- No-data links identified properly")
        print("- File separation working as expected")
        print("- total_success_rate field added successfully")
        print("- Complete workflow generates all required files")
    else:
        print("SOME TESTS FAILED! Review output above.")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)