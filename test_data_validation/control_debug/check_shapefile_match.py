"""
Check if shapefile has matching links for validation
"""
import pandas as pd
import sys
import os
sys.path.insert(0, r'E:\google_agg')

import zipfile
import tempfile
import geopandas as gpd

# Check the shapefile structure
shapefile_zip = r'test_data/control/google_results_to_golan_17_8_25.zip'
csv_file = r'test_data/control/original_‏‏‏‏data_test_control_s_9054-99_s_653-656.csv'

df = pd.read_csv(csv_file, encoding='cp1255')

with tempfile.TemporaryDirectory() as temp_dir:
    with zipfile.ZipFile(shapefile_zip, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    
    # Find the .shp file
    shp_files = [f for f in os.listdir(temp_dir) if f.endswith('.shp')]
    if shp_files:
        shp_path = os.path.join(temp_dir, shp_files[0])
        gdf = gpd.read_file(shp_path)
        
        print("CSV unique Names:", df['Name'].unique())
        print(f"Shapefile columns: {list(gdf.columns)}")
        
        # The validator expects 'Id' column but shapefile has 'id'
        if 'id' in gdf.columns:
            print(f"Shapefile 'id' samples: {gdf['id'].head(10).tolist()}")
            
            # Check if we need to create the expected format s_FROM-TO
            if 'From' in gdf.columns and 'To' in gdf.columns:
                # Create expected link IDs
                gdf['expected_link_id'] = 's_' + gdf['From'].astype(str) + '-' + gdf['To'].astype(str)
                
                matching_by_expected = gdf[gdf['expected_link_id'].isin(df['Name'].unique())]
                print(f"\nMatching by s_FROM-TO format: {len(matching_by_expected)}")
                if len(matching_by_expected) > 0:
                    print("Found matches:", matching_by_expected['expected_link_id'].tolist())
                    
                    # Check geometry types
                    print(f"Geometry types: {matching_by_expected.geometry.geom_type.value_counts()}")
                else:
                    print("No matches found with s_FROM-TO format")
                    print("Sample expected format:", gdf['expected_link_id'].head(5).tolist())

        # Also check if direct 'id' column matches
        if 'id' in gdf.columns:
            direct_matches = gdf[gdf['id'].isin(df['Name'].unique())]
            print(f"\nDirect 'id' matches: {len(direct_matches)}")

print("\n" + "="*50)

# Now test actual validation on a small sample
from components.control.validator import validate_dataframe_batch, ValidationParameters

# Take just first few rows for testing
test_df = df.head(3).copy()
print(f"\nTesting validation on {len(test_df)} rows...")

# Test with very strict threshold to see what happens
params = ValidationParameters(
    use_hausdorff=True,
    hausdorff_threshold_m=1.0,  # Very strict - 1 meter
    use_length_check=False,
    use_coverage_check=False
)

try:
    result = validate_dataframe_batch(test_df, gdf, params)
    print(f"Validation completed. Results:")
    print(f"Valid count: {result['is_valid'].sum()}")
    print(f"Invalid count: {(~result['is_valid']).sum()}")
    print(f"Valid codes: {result['valid_code'].value_counts().to_dict()}")
    
    if 'is_valid' in result.columns:
        for idx, row in result.iterrows():
            print(f"Row {idx}: {row['Name']} -> valid={row['is_valid']}, code={row['valid_code']}")

except Exception as e:
    print(f"Validation error: {e}")
    import traceback
    traceback.print_exc()

