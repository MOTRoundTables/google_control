"""
Properly check the different route alternatives
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

# Get the specific records mentioned by user
link_name = 's_11430-1321'
timestamp = '01/07/2025 17:00'

# Filter to get the exact records
test_records = df[(df['Name'] == link_name) & (df['Timestamp'] == timestamp)].copy()
test_records = test_records.sort_values('RouteAlternative')

print(f"Found {len(test_records)} records for {link_name} at {timestamp}")

for idx, row in test_records.iterrows():
    alt = row['RouteAlternative']
    polyline = row['Polyline']
    data_id = row['DataID']
    
    print(f"\nDataID {data_id} - Route Alternative {alt}:")
    print(f"  Polyline (first 80 chars): {polyline[:80]}...")
    print(f"  Polyline length: {len(polyline)} chars")
    
    # Check if polylines are actually different
    if alt == 1:
        polyline_1 = polyline
    elif alt == 2:
        if 'polyline_1' in locals():
            if polyline == polyline_1:
                print("  WARNING: Same as Alternative 1!")
            else:
                print("  DIFFERENT from Alternative 1")
    elif alt == 3:
        if 'polyline_1' in locals():
            if polyline == polyline_1:
                print("  WARNING: Same as Alternative 1!")
            else:
                print("  DIFFERENT from Alternative 1")

# Load shapefile and test validation
with tempfile.TemporaryDirectory() as temp_dir:
    with zipfile.ZipFile(shapefile_zip, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    
    shp_files = [f for f in os.listdir(temp_dir) if f.endswith('.shp')]
    shp_path = os.path.join(temp_dir, shp_files[0])
    gdf = gpd.read_file(shp_path)

    # Create link IDs
    gdf['link_id'] = 's_' + gdf['From'].astype(str) + '-' + gdf['To'].astype(str)
    
    # Get reference geometry
    ref_row = gdf[gdf['link_id'] == link_name]
    if len(ref_row) > 0:
        ref_geom = ref_row.geometry.iloc[0]
        
        print(f"\nReference geometry from shapefile:")
        print(f"  Length: {ref_geom.length:.6f}")
        print(f"  From: {ref_row['From'].iloc[0]}")
        print(f"  To: {ref_row['To'].iloc[0]}")
        
        # Test each alternative
        for idx, row in test_records.iterrows():
            alt = row['RouteAlternative']
            polyline = row['Polyline']
            
            try:
                google_geom = decode_polyline(polyline)
                distance = calculate_hausdorff(ref_geom, google_geom, crs='EPSG:2039')
                
                print(f"\nAlternative {alt} validation:")
                print(f"  Google length: {google_geom.length:.6f}")
                print(f"  Hausdorff distance: {distance:.6f} meters")
                
                # Test with 5m threshold
                if distance <= 5.0:
                    print(f"  5m threshold: PASS")
                else:
                    print(f"  5m threshold: FAIL")
                
                # Test with 1m threshold
                if distance <= 1.0:
                    print(f"  1m threshold: PASS")
                else:
                    print(f"  1m threshold: FAIL")
                
            except Exception as e:
                print(f"  Error: {e}")

print("\nANALYSIS:")
print("This will show if the different route alternatives actually have")
print("different geometries and different Hausdorff distances.")

