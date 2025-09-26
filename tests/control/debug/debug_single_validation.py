"""
Debug a single validation for s_653-655 to see the exact error.
"""
import pandas as pd
import geopandas as gpd
import sys
import os
sys.path.insert(0, r'E:\google_agg')

from components.control.validator import ValidationParameters, validate_row
from shapely.geometry import LineString
import zipfile
import tempfile

print("=== DEBUGGING SINGLE VALIDATION FOR S_653-655 ===")

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

# Get single record for s_653-655
target_row = df[df['Name'] == 's_653-655'].iloc[0]
print(f"Target record:")
print(f"  Name: {target_row['Name']}")
print(f"  Timestamp: {target_row['Timestamp']}")
print(f"  RouteAlternative: {target_row['RouteAlternative']}")
print(f"  Polyline (first 50 chars): {target_row['Polyline'][:50]}...")

# Run single validation
params = ValidationParameters(hausdorff_threshold_m=5.0)

print(f"\nRunning single validation with params:")
print(f"  hausdorff_threshold_m: {params.hausdorff_threshold_m}")

try:
    result = validate_row(target_row, gdf, params)
    print(f"\nValidation result:")
    print(f"  Result type: {type(result)}")
    print(f"  Result value: {result}")

    # Handle tuple result
    if isinstance(result, tuple):
        is_valid, valid_code = result
        print(f"  is_valid: {is_valid}")
        print(f"  valid_code: {valid_code}")
    else:
        print(f"  is_valid: {result['is_valid']}")
        print(f"  valid_code: {result['valid_code']}")
        if 'error_msg' in result:
            print(f"  error_msg: {result['error_msg']}")

except Exception as e:
    print(f"\nValidation FAILED with error:")
    print(f"  Error type: {type(e).__name__}")
    print(f"  Error message: {str(e)}")

    # Print full traceback for debugging
    import traceback
    print(f"\nFull traceback:")
    traceback.print_exc()

print(f"\n=== CONCLUSION ===")
print(f"This should show us the exact error happening during validation.")