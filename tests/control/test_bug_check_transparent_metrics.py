"""
Comprehensive bug check for the new transparent metrics system.
Test edge cases, math consistency, and potential issues.
"""
import pandas as pd
import geopandas as gpd
import sys
import os
from pathlib import Path
sys.path.insert(0, r'E:\google_agg')

from components.control.validator import ValidationParameters, validate_dataframe_batch
from components.control.report import generate_link_report, aggregate_link_statistics
import zipfile
import tempfile

REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_DATA_DIR = REPO_ROOT / 'test_data' / 'control'

CSV_PATH = TEST_DATA_DIR / 'original_test_data_full.csv'
SHAPEFILE_ZIP = TEST_DATA_DIR / 'google_results_to_golan_17_8_25.zip'


def run_bug_check():
    print("=== COMPREHENSIVE BUG CHECK FOR TRANSPARENT METRICS ===")

    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Missing test CSV at {CSV_PATH}")
    if not SHAPEFILE_ZIP.exists():
        raise FileNotFoundError(f"Missing shapefile ZIP at {SHAPEFILE_ZIP}")

    df = pd.read_csv(CSV_PATH, encoding='latin-1')  # ISO-8859-1 encoding

    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(SHAPEFILE_ZIP, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        shp_files = [f for f in os.listdir(temp_dir) if f.endswith('.shp')]
        shp_path = os.path.join(temp_dir, shp_files[0])
        gdf = gpd.read_file(shp_path)

    print("=== BUG CHECK 1: Math Consistency ===")

    params = ValidationParameters(hausdorff_threshold_m=5.0)
    result_df = validate_dataframe_batch(df, gdf, params)
    report_gdf = generate_link_report(result_df, gdf)

    links_with_data = report_gdf[report_gdf['total_observations'] > 0]
    print(f"Links with data to check: {len(links_with_data)}")

    math_errors = 0
    for _, row in links_with_data.iterrows():
        total_obs = row['total_observations']
        success_obs = row['successful_observations']
        failed_obs = row['failed_observations']
        perfect_percent = row['perfect_match_percent'] or 0.0
        threshold_percent = row['threshold_pass_percent'] or 0.0
        failed_percent = row['failed_percent'] or 0.0

        if success_obs + failed_obs != total_obs:
            print(f"ERROR: Observation inconsistency for link {row['From']}-{row['To']}")
            print(f"  {success_obs} + {failed_obs} != {total_obs}")
            math_errors += 1

        if total_obs > 0 and abs((perfect_percent + threshold_percent + failed_percent) - 100.0) > 0.5:
            print(f"ERROR: Percentage breakdown does not sum to 100% for link {row['From']}-{row['To']}")
            print(f"  Perfect: {perfect_percent:.2f}, Threshold: {threshold_percent:.2f}, Failed: {failed_percent:.2f}")
            math_errors += 1

    print(f"Math consistency check: {math_errors} errors found")

    print()
    print("=== BUG CHECK 2: Data Type Issues ===")

    links_without_data = report_gdf[report_gdf['total_observations'] == 0]
    none_data_count = 0
    zero_fields_count = 0

    for _, row in links_without_data.head(5).iterrows():
        if all(pd.isna(row.get(field)) for field in ['perfect_match_percent', 'threshold_pass_percent', 'failed_percent']):
            none_data_count += 1

        fields_to_check = ['total_observations', 'successful_observations', 'failed_observations']
        if all(row[field] == 0 for field in fields_to_check):
            zero_fields_count += 1

    print(f"Links without data: {len(links_without_data)}")
    print(f"Links with None percentages: {none_data_count}/5 (should be 5)")
    print(f"Links with zero counts: {zero_fields_count}/5 (should be 5)")

    print()
    print("=== BUG CHECK 3: Edge Cases ===")

    try:
        empty_stats = aggregate_link_statistics(pd.DataFrame())
        print(f"Empty DataFrame test: {empty_stats}")

        required_fields = {
            'total_observations': 0,
            'successful_observations': 0,
            'failed_observations': 0,
            'single_route_observations': 0,
            'multi_route_observations': 0
        }

        all_correct = all(empty_stats.get(field) == expected for field, expected in required_fields.items())

        if all_correct:
            print("[OK] Empty DataFrame handled correctly")
        else:
            print("ERROR: Empty DataFrame not handled correctly")
            print(f"Expected fields: {required_fields}")
            print(f"Got: {empty_stats}")

    except Exception as e:
        print(f"ERROR: Empty DataFrame caused exception: {e}")

    print()
    print("=== BUG CHECK 4: Column Names for Shapefile Export ===")

    long_column_names = [col for col in report_gdf.columns if len(col) > 10]
    if long_column_names:
        print("WARNING: Long column names that might cause shapefile issues:")
        for col in long_column_names:
            print(f"  {col} ({len(col)} chars)")
    else:
        print("All column names are DBF-compatible")

    print()
    print("=== BUG CHECK 5: Multi-Alternative Logic ===")

    link_with_multi_alt = None
    for _, row in links_with_data.iterrows():
        if row['multi_route_observations'] > 0:
            link_with_multi_alt = f"s_{row['From']}-{row['To']}"
            break

    if link_with_multi_alt:
        print(f"Testing multi-alternative logic for {link_with_multi_alt}")

        raw_data = result_df[result_df['Name'] == link_with_multi_alt]
        timestamp_groups = raw_data.groupby('Timestamp')

        multi_alt_found = False
        for timestamp, group in timestamp_groups:
            if len(group) > 1:
                multi_alt_found = True
                any_valid = group['is_valid'].any()
                print(f"  Timestamp {timestamp}: {len(group)} alternatives, any_valid={any_valid}")
                break

        if multi_alt_found:
            print("[OK] Multi-alternative logic appears to be working")
        else:
            print("WARNING: No multi-alternative timestamps found to test")
    else:
        print("INFO: No links with multi-alternatives in test data")

    print()
    print("=== BUG CHECK 6: Data Integrity ===")

    total_validation_rows = len(result_df)
    sum_total_observations = links_with_data['total_observations'].sum()

    print(f"Total validation rows: {total_validation_rows}")
    print(f"Sum of total_observations: {sum_total_observations}")

    if total_validation_rows == sum_total_observations:
        print("total_observations accounting is correct")
    else:
        print("WARNING: total_observations accounting might have issues")

    print()
    print("=== SUMMARY ===")
    print("Comprehensive bug check completed. Review any ERROR or WARNING messages above.")
    print("Key areas checked:")
    print("- Observation consistency (successful + failed = total)")
    print("- Percentage breakdown accuracy")
    print("- Handling of links without data")
    print("- Empty DataFrame safeguards")
    print("- Shapefile field compatibility")
    print("- Multi-alternative aggregation logic")
    print("- Overall observation accounting")


if __name__ == "__main__":
    run_bug_check()


def test_transparent_metrics_smoke():
    run_bug_check()
