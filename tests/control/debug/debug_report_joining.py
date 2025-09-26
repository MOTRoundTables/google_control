"""
Debug why the link report only shows 'not recorded' links instead of actual validation results.
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

print("=== DEBUGGING LINK REPORT JOINING ===")

# Load test data
csv_file = r'test_data/control/original_‏‏‏‏data_test_control_s_9054-99_s_653-656.csv'
shapefile_zip = r'test_data/control/google_results_to_golan_17_8_25.zip'

df = pd.read_csv(csv_file, encoding='cp1255').head(20)  # Small test sample
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

# Check what links we have in the CSV data
print("\n=== CSV LINK ANALYSIS ===")
csv_links = result_df['Name'].unique()[:10]
print(f"CSV links (first 10): {list(csv_links)}")

# Check what the validation results look like
print(f"\nValidation results summary:")
print(f"  Valid: {result_df['is_valid'].sum()}")
print(f"  Invalid: {(~result_df['is_valid']).sum()}")
print(f"  Total: {len(result_df)}")

# Check shapefile link format
print("\n=== SHAPEFILE LINK ANALYSIS ===")
print(f"Shapefile columns: {list(gdf.columns)}")

# Create the join keys as the report system does
gdf_sample = gdf.head(10).copy()
gdf_sample['join_key'] = 's_' + gdf_sample['From'].astype(str) + '-' + gdf_sample['To'].astype(str)
print(f"Shapefile join keys (first 10): {list(gdf_sample['join_key'])}")

# Check if there's any overlap
csv_links_set = set(csv_links)
shp_links_set = set(gdf_sample['join_key'])
overlap = csv_links_set.intersection(shp_links_set)
print(f"\nJoin key overlap: {len(overlap)} matches found")
if overlap:
    print(f"Matching links: {list(overlap)[:5]}")

# Now let's debug the actual report generation step by step
print("\n=== DEBUGGING REPORT GENERATION ===")

# Check what happens in the report generation
report_gdf = generate_link_report(result_df, gdf)

# Count results by type
result_code_counts = report_gdf['result_code'].value_counts()
print(f"Result code counts:")
for code, count in result_code_counts.items():
    print(f"  Code {code}: {count} links")

# Find some links that should have data
links_with_data = report_gdf[report_gdf['result_code'] != 999]
print(f"\nLinks with actual data: {len(links_with_data)}")

if len(links_with_data) > 0:
    print("\nSample links with data:")
    for idx, row in links_with_data.head(3).iterrows():
        from_id = row.get('From')
        to_id = row.get('To')
        link_id = f"s_{from_id}-{to_id}"
        result_code = row.get('result_code')
        result_label = row.get('result_label')

        print(f"  {link_id}: code={result_code}, label={result_label}")

# Let's manually check the joining logic
print("\n=== MANUAL JOIN CHECK ===")

# Take the first CSV link and see if we can find it in the shapefile
test_csv_link = csv_links[0]
print(f"Testing CSV link: {test_csv_link}")

# Look for this link in the shapefile
matching_shp_rows = gdf[gdf['From'].astype(str) + '-' + gdf['To'].astype(str) == test_csv_link.replace('s_', '')]
print(f"Matching shapefile rows: {len(matching_shp_rows)}")

if len(matching_shp_rows) > 0:
    print("Match found! The joining should work.")

    # Check if the CSV data has the right format for this link
    csv_data_for_link = result_df[result_df['Name'] == test_csv_link]
    print(f"CSV data for {test_csv_link}: {len(csv_data_for_link)} rows")
    print(f"  Valid: {csv_data_for_link['is_valid'].sum()}")
    print(f"  Invalid: {(~csv_data_for_link['is_valid']).sum()}")
else:
    print("No match found - there's a joining problem!")

print("\n=== CONCLUSION ===")
print("If links_with_data is 0, there's a joining problem in generate_link_report()")
print("If links_with_data > 0, the function is working but maybe just not visible in your test")