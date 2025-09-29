"""
Debug route alternatives issue - different polylines should give different results
"""
import pandas as pd
import geopandas as gpd
import sys
import os
sys.path.insert(0, r'E:\google_agg')

from components.control.validator import decode_polyline, calculate_hausdorff
import zipfile
import tempfile

# Load data
csv_file = r'test_data/control/original_‏‏‏‏data_test_control_s_9054-99_s_653-656.csv'
shapefile_zip = r'test_data/control/google_results_to_golan_17_8_25.zip'

df = pd.read_csv(csv_file, encoding='cp1255')

# Check the specific case mentioned by user
link_name = 's_11430-1321'
test_data = df[df['Name'] == link_name].copy()

print(f"Found {len(test_data)} records for {link_name}")
print("Route alternatives:", test_data['RouteAlternative'].unique())

# Show sample data
for idx, row in test_data.head(3).iterrows():
    polyline = row['Polyline']
    alt = row['RouteAlternative']
    print(f"\nRoute Alternative {alt}:")
    print(f"  Polyline (first 50 chars): {polyline[:50]}")
    print(f"  Polyline length: {len(polyline)} characters")

# Load shapefile and check matching
with tempfile.TemporaryDirectory() as temp_dir:
    with zipfile.ZipFile(shapefile_zip, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    
    shp_files = [f for f in os.listdir(temp_dir) if f.endswith('.shp')]
    shp_path = os.path.join(temp_dir, shp_files[0])
    gdf = gpd.read_file(shp_path)

    print(f"\nShapefile columns: {list(gdf.columns)}")
    
    # Create the expected link format as user described: s_ + From + - + To
    if 'From' in gdf.columns and 'To' in gdf.columns:
        gdf['link_id'] = 's_' + gdf['From'].astype(str) + '-' + gdf['To'].astype(str)
        print("Created link_id format: s_FROM-TO")
        
        # Check if we have a match for s_11430-1321
        matching_row = gdf[gdf['link_id'] == link_name]
        if len(matching_row) > 0:
            print(f"FOUND match in shapefile for {link_name}")
            ref_geom = matching_row.geometry.iloc[0]
            print(f"Reference geometry length: {ref_geom.length:.6f}")
            
            # Test each route alternative
            for idx, row in test_data.head(3).iterrows():
                alt = row['RouteAlternative']
                polyline = row['Polyline']
                
                try:
                    google_geom = decode_polyline(polyline)
                    distance = calculate_hausdorff(ref_geom, google_geom, crs='EPSG:2039')
                    
                    print(f"\nRoute Alternative {alt}:")
                    print(f"  Google geometry length: {google_geom.length:.6f}")
                    print(f"  Hausdorff distance: {distance:.6f} meters")
                    
                    if distance <= 5.0:
                        print(f"  Result: VALID (≤ 5m)")
                    else:
                        print(f"  Result: INVALID (> 5m)")
                    
                except Exception as e:
                    print(f"  Error aggregation alternative {alt}: {e}")
                    
        else:
            print(f"NO MATCH found in shapefile for {link_name}")
            print("Available link IDs (first 10):", gdf['link_id'].head(10).tolist())
    
    else:
        print("Shapefile missing From/To columns")
        
print("\nCONCLUSION:")
print("If route alternatives have different polylines but same Hausdorff distance,")
print("it could mean they're all equally close/far from the reference geometry.")
print("This would be the correct behavior of the validation system.")

