"""
Test current validation system before implementing the new simplified approach.
This ensures we understand exactly what we're changing.
"""
import pandas as pd
import geopandas as gpd
import sys
import os
sys.path.insert(0, r'E:\google_agg')

from components.control.validator import ValidationParameters, validate_dataframe_batch, ValidCode
import tempfile
import zipfile

print("=== TESTING CURRENT VALIDATION SYSTEM (BEFORE CHANGES) ===")

# Load test data
csv_file = r'test_data/control/original_‏‏‏‏data_test_control_s_9054-99_s_653-656.csv'
shapefile_zip = r'test_data/control/google_results_to_golan_17_8_25.zip'

df = pd.read_csv(csv_file, encoding='cp1255').head(10)  # Small sample
print(f"Loaded {len(df)} CSV records (sample)")

with tempfile.TemporaryDirectory() as temp_dir:
    with zipfile.ZipFile(shapefile_zip, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

    shp_files = [f for f in os.listdir(temp_dir) if f.endswith('.shp')]
    shp_path = os.path.join(temp_dir, shp_files[0])
    gdf = gpd.read_file(shp_path)

print(f"Loaded {len(gdf)} shapefile features")

print("\n=== TEST 1: Current System - Hausdorff Only ===")
params1 = ValidationParameters(
    hausdorff_threshold_m=5.0,
    use_hausdorff=True,
    use_length_check=False,
    use_coverage_check=False
)

result1 = validate_dataframe_batch(df, gdf, params1)
print(f"Results: {len(result1)} rows")
print("Current valid_codes:", result1['valid_code'].unique())
print("is_valid distribution:", result1['is_valid'].value_counts())

print("\n=== TEST 2: Current System - Hausdorff + Length ===")
params2 = ValidationParameters(
    hausdorff_threshold_m=5.0,
    use_hausdorff=True,
    use_length_check=True,
    use_coverage_check=False,
    length_check_mode="ratio"
)

result2 = validate_dataframe_batch(df, gdf, params2)
print("Current valid_codes:", result2['valid_code'].unique())
print("is_valid distribution:", result2['is_valid'].value_counts())

print("\n=== TEST 3: Current System - All Tests ===")
params3 = ValidationParameters(
    hausdorff_threshold_m=5.0,
    use_hausdorff=True,
    use_length_check=True,
    use_coverage_check=True
)

result3 = validate_dataframe_batch(df, gdf, params3)
print("Current valid_codes:", result3['valid_code'].unique())
print("is_valid distribution:", result3['is_valid'].value_counts())

print("\n=== CURRENT SYSTEM ANALYSIS ===")
print("Available columns in result:", list(result1.columns))

# Sample detailed results
print("\nSample current results (first 3 rows):")
for idx, row in result1.head(3).iterrows():
    print(f"Row {idx}:")
    print(f"  Name: {row['Name']}")
    print(f"  is_valid: {row['is_valid']}")
    print(f"  valid_code: {row['valid_code']}")
    print(f"  RouteAlternative: {row.get('RouteAlternative', 'N/A')}")

print(f"\n=== CURRENT VALID CODES USED ===")
all_codes = set()
all_codes.update(result1['valid_code'].unique())
all_codes.update(result2['valid_code'].unique())
all_codes.update(result3['valid_code'].unique())

for code in sorted(all_codes):
    try:
        code_name = ValidCode(code).name
        print(f"  {code}: {code_name}")
    except:
        print(f"  {code}: UNKNOWN CODE")

print(f"\n=== WHAT WE WANT TO CHANGE TO ===")
print("New system will have:")
print("  valid_code: 1, 2, 3 (context only)")
print("  hausdorff_distance: actual distance in meters")
print("  hausdorff_pass: True/False")
print("  length_ratio: actual ratio (if length test enabled)")
print("  length_pass: True/False (if length test enabled)")
print("  coverage_percent: actual % (if coverage test enabled)")
print("  coverage_pass: True/False (if coverage test enabled)")
print("  is_valid: True if ALL enabled tests pass")

print(f"\n=== READY TO IMPLEMENT NEW SYSTEM ===")
print("This test shows current system behavior to ensure compatibility after changes.")