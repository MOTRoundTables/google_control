"""
Debug why s_653-655 is showing 0% success rate when it should have some valid results.
Let's examine the raw data and validation process step by step.
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

print("=== DEBUGGING S_653-655 FAILURE ===")

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

# Focus on s_653-655 link
target_link = 's_653-655'
link_data = df[df['Name'] == target_link].copy()
print(f"\nFound {len(link_data)} records for {target_link}")

if len(link_data) > 0:
    print("\nFirst few records:")
    print(link_data[['Name', 'Timestamp', 'RouteAlternative', 'Polyline']].head())

    # Check if shapefile has this link
    matching_shp = gdf[(gdf['From'].astype(str) == '653') & (gdf['To'].astype(str) == '655')]
    print(f"\nShapefile match for From=653, To=655: {len(matching_shp)} records found")

    if len(matching_shp) > 0:
        print("Shapefile geometry found - link should be validatable")
        ref_geometry = matching_shp.iloc[0]['geometry']
        print(f"Reference geometry type: {ref_geometry.geom_type}")
        print(f"Reference geometry length: {ref_geometry.length:.6f} degrees")

        # Run validation with detailed output
        print("\n=== RUNNING VALIDATION ===")
        params = ValidationParameters(hausdorff_threshold_m=5.0)
        result_df = validate_dataframe_batch(df, gdf, params)

        # Filter results for our target link
        target_results = result_df[result_df['Name'] == target_link]
        print(f"\nValidation results for {target_link}: {len(target_results)} records")

        if len(target_results) > 0:
            print("\nDetailed validation results:")
            print("Timestamp | RouteAlt | is_valid | valid_code | Hausdorff_distance")
            print("-" * 70)

            for idx, row in target_results.head(10).iterrows():
                timestamp = row['Timestamp']
                route_alt = row.get('RouteAlternative', 'N/A')
                is_valid = row['is_valid']
                valid_code = row['valid_code']

                print(f"{timestamp} | {route_alt:8} | {is_valid:8} | {valid_code:10} | (checking...)")

            # Check the aggregation
            print(f"\nAggregation Analysis:")
            print(f"  Total records: {len(target_results)}")
            print(f"  Valid records: {target_results['is_valid'].sum()}")
            print(f"  Invalid records: {(~target_results['is_valid']).sum()}")

            # Check timestamp-based aggregation manually
            timestamp_groups = target_results.groupby('Timestamp')
            successful_timestamps = 0
            total_timestamps = len(timestamp_groups)

            print(f"\nTimestamp-based analysis (first 10 timestamps):")
            for i, (timestamp, group) in enumerate(timestamp_groups):
                if i >= 10:  # Only show first 10
                    break

                any_valid = group['is_valid'].any()
                valid_count = group['is_valid'].sum()
                total_count = len(group)

                if any_valid:
                    successful_timestamps += 1

                print(f"  {timestamp}: {valid_count}/{total_count} valid -> {'SUCCESS' if any_valid else 'FAILED'}")

            print(f"\nFinal aggregation:")
            print(f"  Successful timestamps: {successful_timestamps}")
            print(f"  Total timestamps: {total_timestamps}")
            print(f"  Success rate: {(successful_timestamps/total_timestamps*100):.1f}%")

        else:
            print("ERROR: No validation results found for target link!")

    else:
        print("ERROR: Link not found in shapefile!")

else:
    print(f"ERROR: No data found for {target_link} in CSV!")

# Let's also check what the report generation produces
print("\n=== CHECKING REPORT GENERATION ===")
params = ValidationParameters(hausdorff_threshold_m=5.0)
result_df = validate_dataframe_batch(df, gdf, params)
report_gdf = generate_link_report(result_df, gdf)

# Find our target link in the report
report_link = report_gdf[report_gdf['From'].astype(str) + '-' + report_gdf['To'].astype(str) == '653-655']
if len(report_link) > 0:
    link_row = report_link.iloc[0]
    print(f"Report shows for s_653-655:")
    print(f"  Result Code: {link_row['result_code']}")
    print(f"  Result Label: {link_row['result_label']}")
    print(f"  Success Rate: {link_row.get('success_rate', 'N/A')}%")
    print(f"  Total Timestamps: {link_row.get('total_timestamps', 'N/A')}")
    print(f"  Valid Timestamps: {link_row.get('valid_timestamps', 'N/A')}")
    print(f"  Total Observations: {link_row.get('total_observations', 'N/A')}")
else:
    print("ERROR: Link s_653-655 not found in report!")

print("\n=== CONCLUSION ===")
print("This should help us identify why s_653-655 is showing 0% success rate")
print("when we expect at least some validation to pass.")