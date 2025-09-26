"""
Test with more CSV data to see more links with actual validation results.
"""
import pandas as pd
import geopandas as gpd
import sys
import os
from pathlib import Path
sys.path.insert(0, r'E:\google_agg')

from components.control.validator import ValidationParameters, validate_dataframe_batch
from components.control.report import generate_link_report
import zipfile
import tempfile

REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_DATA_DIR = REPO_ROOT / 'test_data' / 'control'

CSV_CANDIDATES = sorted(TEST_DATA_DIR.glob('original_*data_test_control_s_9054-99_s_653-656.csv'))
SHAPEFILE_ZIP = TEST_DATA_DIR / 'google_results_to_golan_17_8_25.zip'


def run_more_links():
    if not CSV_CANDIDATES:
        raise FileNotFoundError("Could not locate the sample CSV with additional links")
    if not SHAPEFILE_ZIP.exists():
        raise FileNotFoundError(f"Missing shapefile ZIP at {SHAPEFILE_ZIP}")

    csv_file = CSV_CANDIDATES[0]

    print("=== TESTING WITH MORE LINKS ===")
    print(f"Loading CSV from {csv_file}")
    df = pd.read_csv(csv_file, encoding='cp1255')  # Hebrew-friendly encoding
    print(f"Loaded {len(df)} CSV records")

    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(SHAPEFILE_ZIP, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        shp_files = [f for f in os.listdir(temp_dir) if f.endswith('.shp')]
        shp_path = os.path.join(temp_dir, shp_files[0])
        gdf = gpd.read_file(shp_path)

    print(f"Loaded {len(gdf)} shapefile features")

    unique_csv_links = df['Name'].unique()
    print(f"Unique links in CSV: {len(unique_csv_links)}")
    print(f"Sample links: {list(unique_csv_links)[:10]}")

    params = ValidationParameters(hausdorff_threshold_m=5.0)
    result_df = validate_dataframe_batch(df, gdf, params)

    print(f"Validation completed: {len(result_df)} results")
    print(f"  Valid routes: {result_df['is_valid'].sum()}")
    print(f"  Invalid routes: {(~result_df['is_valid']).sum()}")

    print()
    print("=== GENERATING LINK REPORT ===")
    report_gdf = generate_link_report(result_df, gdf)

    links_with_data = report_gdf[report_gdf['total_observations'] > 0]
    print(f"Links with validation data: {len(links_with_data)} out of {len(report_gdf)}")

    if len(links_with_data) > 0:
        print()
        print("=== LINKS WITH ACTUAL VALIDATION RESULTS ===")
        print("Link_ID | Perfect% | Threshold% | Failed% | Success obs / Total obs")
        print("-" * 80)

        for _, row in links_with_data.head(10).iterrows():
            from_id = row.get('From')
            to_id = row.get('To')
            link_id = f"s_{from_id}-{to_id}"
            total_obs = row.get('total_observations', 0)
            success_obs = row.get('successful_observations', 0)
            perfect_pct = row.get('perfect_match_percent') or 0.0
            threshold_pct = row.get('threshold_pass_percent') or 0.0
            failed_pct = row.get('failed_percent') or 0.0

            print(
                f"{link_id:<12} | "
                f"{perfect_pct:>7.2f}% | "
                f"{threshold_pct:>9.2f}% | "
                f"{failed_pct:>7.2f}% | "
                f"{success_obs}/{total_obs}"
            )

        sample_row = links_with_data.iloc[0]
        sample_link_id = f"s_{sample_row['From']}-{sample_row['To']}"

        print()
        print(f"=== DETAILED BREAKDOWN FOR {sample_link_id} ===")
        print(
            f"  Perfect%: {sample_row.get('perfect_match_percent') or 0:.2f}% | "
            f"Threshold%: {sample_row.get('threshold_pass_percent') or 0:.2f}% | "
            f"Failed%: {sample_row.get('failed_percent') or 0:.2f}%"
        )
        print(
            f"  Observations: {sample_row.get('successful_observations')}/"
            f"{sample_row.get('total_observations')} (success/total)"
        )
        print(
            f"  Route alternatives: single={sample_row.get('single_route_observations')}, "
            f"multi={sample_row.get('multi_route_observations')}"
        )

        raw_data = result_df[result_df['Name'] == sample_link_id]
        print(f"  Raw Validation Data: {len(raw_data)} records")

        if len(raw_data) > 0:
            timestamp_groups = raw_data.groupby('Timestamp')
            print("  Timestamp Analysis (showing first 5):")

            for i, (timestamp, group) in enumerate(timestamp_groups):
                if i >= 5:
                    break
                valid_count = group['is_valid'].sum()
                total_count = len(group)
                timestamp_valid = group['is_valid'].any()
                alternatives = (
                    sorted(group['RouteAlternative'].unique())
                    if 'RouteAlternative' in group.columns else [1]
                )
                print(
                    f"    {timestamp}: Alt {alternatives} -> {valid_count}/{total_count} valid -> "
                    f"{'SUCCESS' if timestamp_valid else 'FAILED'}"
                )
    else:
        print("No links with validation data found!")

    print()
    print("=== SUMMARY ===")
    print(
        f"The report shows {len(links_with_data)} links with data out of {len(report_gdf)} total shapefile links."
    )
    print(
        "The remaining links have no observations and their percentage fields remain empty (NaN)."
    )


if __name__ == "__main__":
    run_more_links()


def test_more_links_smoke():
    run_more_links()
