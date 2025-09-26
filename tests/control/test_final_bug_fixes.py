"""
Test the final bug fixes: DBF column name compatibility and updated system functionality.
"""
import pandas as pd
import geopandas as gpd
import sys
import os
sys.path.insert(0, r'E:\google_agg')

from components.control.validator import ValidationParameters, validate_dataframe_batch
from components.control.report import generate_link_report, write_shapefile_with_results
import zipfile
import tempfile
import shutil

print("=== TESTING FINAL BUG FIXES ===")

# Load test data
csv_file = r'test_data/control/original_‏‏‏‏data_test_control_s_9054-99_s_653-656.csv'
shapefile_zip = r'test_data/control/google_results_to_golan_17_8_25.zip'

df = pd.read_csv(csv_file, encoding='cp1255')

with tempfile.TemporaryDirectory() as temp_dir:
    with zipfile.ZipFile(shapefile_zip, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

    shp_files = [f for f in os.listdir(temp_dir) if f.endswith('.shp')]
    shp_path = os.path.join(temp_dir, shp_files[0])
    gdf = gpd.read_file(shp_path)

# Run validation and generate report
params = ValidationParameters(hausdorff_threshold_m=5.0)
result_df = validate_dataframe_batch(df, gdf, params)
report_gdf = generate_link_report(result_df, gdf)

print(f"Report generated with {len(report_gdf)} links")
print(f"Links with data: {len(report_gdf[report_gdf['total_timestamps'] > 0])}")

print("\n=== TEST 1: CSV Report Column Names ===")
csv_columns = list(report_gdf.columns)
print(f"CSV columns: {csv_columns}")

# Check for transparent metrics columns
required_columns = ['success_rate', 'total_timestamps', 'successful_timestamps', 'failed_timestamps']
missing_columns = [col for col in required_columns if col not in csv_columns]

if missing_columns:
    print(f"ERROR: Missing required columns: {missing_columns}")
else:
    print("SUCCESS: All required transparent metrics columns present")

print("\n=== TEST 2: Shapefile Export with DBF-Compatible Names ===")

# Test shapefile export - create a separate temp directory for output
output_temp_dir = tempfile.mkdtemp()
output_path = os.path.join(output_temp_dir, "test_output.shp")

try:
    write_shapefile_with_results(report_gdf, output_path)
    print(f"SUCCESS: Shapefile written to {output_path}")

    # Read the shapefile back to check column names
    test_gdf = gpd.read_file(output_path)
    shp_columns = list(test_gdf.columns)
    print(f"Shapefile columns: {shp_columns}")

    # Check that column names are DBF-compatible (max 10 chars)
    long_columns = [col for col in shp_columns if len(col) > 10]
    if long_columns:
        print(f"ERROR: Long column names in shapefile: {long_columns}")
    else:
        print("SUCCESS: All shapefile column names are DBF-compatible (<=10 chars)")

    # Check that the expected shortened columns are present
    expected_short_columns = ['suc_rate', 'total_ts', 'success_ts', 'failed_ts']
    missing_short_columns = [col for col in expected_short_columns if col not in shp_columns]

    if missing_short_columns:
        print(f"WARNING: Missing expected short columns: {missing_short_columns}")
    else:
        print("SUCCESS: All expected shortened columns present in shapefile")

except Exception as e:
    print(f"ERROR: Shapefile export failed: {e}")
    import traceback
    traceback.print_exc()

finally:
    # Clean up temp directory
    if 'output_temp_dir' in locals():
        shutil.rmtree(output_temp_dir, ignore_errors=True)

print("\n=== TEST 3: Data Integrity Check ===")

# Test a specific link's data
links_with_data = report_gdf[report_gdf['total_timestamps'] > 0]
if len(links_with_data) > 0:
    test_link = links_with_data.iloc[0]

    print(f"Testing link s_{test_link['From']}-{test_link['To']}:")
    print(f"  success_rate: {test_link['success_rate']}")
    print(f"  total_timestamps: {test_link['total_timestamps']}")
    print(f"  successful_timestamps: {test_link['successful_timestamps']}")
    print(f"  failed_timestamps: {test_link['failed_timestamps']}")

    # Verify math
    total_check = test_link['successful_timestamps'] + test_link['failed_timestamps']
    if total_check == test_link['total_timestamps']:
        print("SUCCESS: Math consistency check passed")
    else:
        print(f"ERROR: Math inconsistency: {test_link['successful_timestamps']} + {test_link['failed_timestamps']} != {test_link['total_timestamps']}")

print("\n=== TEST 4: GUI Column Compatibility ===")

# Test the columns that the GUI expects
gui_columns = ['From', 'To', 'success_rate', 'total_timestamps', 'successful_timestamps', 'failed_timestamps']
gui_available = [col for col in gui_columns if col in report_gdf.columns]

print(f"GUI expects: {gui_columns}")
print(f"Available: {gui_available}")

if len(gui_available) == len(gui_columns):
    print("SUCCESS: All GUI-expected columns are available")
else:
    missing_gui_cols = [col for col in gui_columns if col not in gui_available]
    print(f"ERROR: Missing GUI columns: {missing_gui_cols}")

print("\n=== SUMMARY ===")
print("Final bug fixes tested:")
print("1. DBF column name compatibility (max 10 chars)")
print("2. CSV report maintains full column names")
print("3. Shapefile export uses shortened column names")
print("4. Math consistency in transparent metrics")
print("5. GUI compatibility with new column names")
print("\nReview any ERROR messages above. SUCCESS messages indicate fixes are working.")