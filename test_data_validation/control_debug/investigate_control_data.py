"""
Investigate why control validation shows all valid
"""
import pandas as pd
import sys
import os
sys.path.insert(0, r'E:\google_agg')

# Load the problematic data
csv_file = r'test_data/control/original_‏‏‏‏data_test_control_s_9054-99_s_653-656.csv'
df = pd.read_csv(csv_file, encoding='cp1255')

print(f"Loaded {len(df)} rows")
print(f"Columns: {list(df.columns)}")

# Check unique values in key columns
print(f"\nUnique Names: {df['Name'].unique()}")
print(f"Unique RouteAlternatives: {df['RouteAlternative'].unique()}")

# Check polylines
polylines = df['Polyline'].unique()
print(f"\nNumber of unique polylines: {len(polylines)}")

if len(polylines) <= 3:
    print("Polyline samples:")
    for i, poly in enumerate(polylines):
        print(f"  {i+1}: {poly[:100]}...")

# Check if all polylines are the same
if len(polylines) == 1:
    print("\n🔍 ISSUE FOUND: All rows have the SAME polyline!")
    print("This means all routes are identical, so Hausdorff distance = 0")
    print("That's why all validation results show as 'valid'")

# Check the shapefile too
import zipfile
import tempfile
import geopandas as gpd

shapefile_zip = r'test_data/control/google_results_to_golan_17_8_25.zip'
with tempfile.TemporaryDirectory() as temp_dir:
    with zipfile.ZipFile(shapefile_zip, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    
    # Find the .shp file
    shp_files = [f for f in os.listdir(temp_dir) if f.endswith('.shp')]
    if shp_files:
        shp_path = os.path.join(temp_dir, shp_files[0])
        gdf = gpd.read_file(shp_path)
        
        print(f"\nShapefile has {len(gdf)} features")
        print(f"Shapefile columns: {list(gdf.columns)}")
        
        # Check if s_653-655 exists
        if 'Id' in gdf.columns:
            matching_links = gdf[gdf['Id'].isin(df['Name'].unique())]
            print(f"Found {len(matching_links)} matching links in shapefile")
            
            if len(matching_links) > 0:
                print("Matching link IDs:", matching_links['Id'].tolist())
            else:
                print("❌ NO MATCHING LINKS FOUND!")
                print("CSV has:", df['Name'].unique())
                print("Shapefile has:", gdf['Id'].unique()[:10], "...")

print("\n" + "="*60)
print("ANALYSIS COMPLETE")
