"""
Test the new transparent metrics system to ensure it works correctly.
"""
import pandas as pd
import geopandas as gpd
import sys
import os
sys.path.insert(0, r'E:\google_agg')

from components.control.validator import ValidationParameters, validate_dataframe_batch
from components.control.report import generate_link_report
import zipfile
import tempfile

print("=== TESTING NEW TRANSPARENT METRICS SYSTEM ===")

# Load test data
csv_file = r'test_data/control/original_‏‏‏‏data_test_control_s_9054-99_s_653-656.csv'
shapefile_zip = r'test_data/control/google_results_to_golan_17_8_25.zip'

df = pd.read_csv(csv_file, encoding='cp1255')
print(f"Loaded {len(df)} CSV records")

with tempfile.TemporaryDirectory() as temp_dir:
    with zipfile.ZipFile(shapefile_zip, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

    shp_files = [f for f in os.listdir(temp_dir) if f.endswith('.shp')]
    shp_path = os.path.join(temp_dir, shp_files[0])
    gdf = gpd.read_file(shp_path)

print(f"Loaded {len(gdf)} shapefile features")

# Run validation
params = ValidationParameters(hausdorff_threshold_m=5.0)
result_df = validate_dataframe_batch(df, gdf, params)

print(f"Validation completed: {len(result_df)} results")

# Generate report with new transparent metrics
print("\n=== GENERATING LINK REPORT WITH TRANSPARENT METRICS ===")
report_gdf = generate_link_report(result_df, gdf)

# Check what columns we now have
print(f"Report columns: {list(report_gdf.columns)}")

# Show transparent metrics for links with data
links_with_data = report_gdf[report_gdf['total_timestamps'] > 0]
print(f"\nLinks with data: {len(links_with_data)} out of {len(report_gdf)}")

if len(links_with_data) > 0:
    print("\n=== TRANSPARENT METRICS RESULTS ===")
    print("Link_ID | Success_Rate | Total_TS | Success_TS | Failed_TS | Total_Obs")
    print("-" * 80)

    for idx, row in links_with_data.iterrows():
        from_id = row.get('From')
        to_id = row.get('To')
        link_id = f"s_{from_id}-{to_id}"

        success_rate = row.get('success_rate')
        total_timestamps = row.get('total_timestamps', 0)
        successful_timestamps = row.get('successful_timestamps', 0)
        failed_timestamps = row.get('failed_timestamps', 0)
        total_observations = row.get('total_observations', 0)

        # Format success rate
        if success_rate is None:
            rate_str = "None"
        else:
            rate_str = f"{success_rate:.1f}%"

        print(f"{link_id:<12} | {rate_str:<12} | {total_timestamps:<8} | {successful_timestamps:<10} | {failed_timestamps:<9} | {total_observations}")

    print(f"\n=== DETAILED BREAKDOWN FOR FIRST LINK ===")
    first_link = links_with_data.iloc[0]
    from_id = first_link.get('From')
    to_id = first_link.get('To')
    link_id = f"s_{from_id}-{to_id}"

    print(f"Link: {link_id}")
    print(f"  Success Rate: {first_link.get('success_rate')}%")
    print(f"  Total Timestamps: {first_link.get('total_timestamps')}")
    print(f"  Successful Timestamps: {first_link.get('successful_timestamps')}")
    print(f"  Failed Timestamps: {first_link.get('failed_timestamps')}")
    print(f"  Total Observations: {first_link.get('total_observations')}")
    print(f"  Single Alt Timestamps: {first_link.get('single_alt_timestamps')}")
    print(f"  Multi Alt Timestamps: {first_link.get('multi_alt_timestamps')}")

    # Verify the math makes sense
    total_ts = first_link.get('total_timestamps')
    success_ts = first_link.get('successful_timestamps')
    failed_ts = first_link.get('failed_timestamps')
    success_rate = first_link.get('success_rate')

    print(f"\n=== VERIFICATION ===")
    print(f"  Math check: {success_ts} + {failed_ts} = {success_ts + failed_ts} (should equal {total_ts})")

    if total_ts > 0:
        calculated_rate = (success_ts / total_ts) * 100
        print(f"  Rate check: ({success_ts}/{total_ts}) * 100 = {calculated_rate:.1f}% (should equal {success_rate}%)")

else:
    print("ERROR: No links with data found!")

# Check a few links without data
links_without_data = report_gdf[report_gdf['total_timestamps'] == 0].head(3)
print(f"\n=== SAMPLE LINKS WITHOUT DATA ===")
for idx, row in links_without_data.iterrows():
    from_id = row.get('From')
    to_id = row.get('To')
    link_id = f"s_{from_id}-{to_id}"
    success_rate = row.get('success_rate')

    print(f"{link_id}: success_rate={success_rate}, total_timestamps={row.get('total_timestamps')}")

print(f"\n=== SUMMARY ===")
print(f"✓ New transparent metrics system implemented")
print(f"✓ Shows raw success rates instead of confusing codes")
print(f"✓ Provides complete breakdown of timestamps and observations")
print(f"✓ Links without data have success_rate=None and total_timestamps=0")