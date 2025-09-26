"""Minimal test to verify validation works"""
import pandas as pd
import geopandas as gpd
import zipfile
import tempfile
import os
import sys

sys.path.insert(0, r'E:\google_agg')

from components.control.validator import validate_dataframe_batch, ValidationParameters

print("MINIMAL VALIDATION TEST")
print("="*40)

# Load just 100 rows
df = pd.read_csv(r'E:\google_agg\test_data\control\data.csv', encoding='utf-8', nrows=100)
print(f"Loaded {len(df)} rows")

# Load shapefile
with tempfile.TemporaryDirectory() as temp_dir:
    with zipfile.ZipFile(r'E:\google_agg\test_data\control\google_results_to_golan_17_8_25.zip', 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    shp_path = os.path.join(temp_dir, [f for f in os.listdir(temp_dir) if f.endswith('.shp')][0])
    gdf = gpd.read_file(shp_path)
    print(f"Loaded {len(gdf)} shapefile features")

    # Validate
    df.columns = df.columns.str.lower()
    params = ValidationParameters(hausdorff_threshold_m=5.0)
    result = validate_dataframe_batch(df, gdf, params)

    # Check results
    if 'is_valid' in result.columns:
        nan_count = result['is_valid'].isna().sum()
        print(f"NaN in is_valid: {nan_count}")

        result['is_valid'] = result['is_valid'].fillna(False)
        valid = result['is_valid'].sum()
        print(f"Valid: {valid}/{len(result)}")
        print("SUCCESS!")
    else:
        print("ERROR: No is_valid column")

print("="*40)