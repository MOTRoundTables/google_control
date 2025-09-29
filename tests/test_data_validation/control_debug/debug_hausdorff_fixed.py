"""
Debug actual Hausdorff distances being calculated
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

with tempfile.TemporaryDirectory() as temp_dir:
    with zipfile.ZipFile(shapefile_zip, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    
    shp_files = [f for f in os.listdir(temp_dir) if f.endswith('.shp')]
    shp_path = os.path.join(temp_dir, shp_files[0])
    gdf = gpd.read_file(shp_path)

# Create expected link IDs
gdf['link_id'] = 's_' + gdf['From'].astype(str) + '-' + gdf['To'].astype(str)

# Test specific case
link_name = 's_653-655'
polyline = df[df['Name'] == link_name]['Polyline'].iloc[0]

print("Testing", link_name)
print("=" * 50)

# Get reference geometry
ref_geom = gdf[gdf['link_id'] == link_name].geometry.iloc[0]
print(f"Reference geometry length: {ref_geom.length:.2f} units")

# Decode Google polyline
try:
    google_geom = decode_polyline(polyline)
    
    from shapely.geometry import LineString
    if isinstance(google_geom, LineString):
        google_coords = list(google_geom.coords)
        print(f"Google polyline decoded: {len(google_coords)} points")
        print(f"Google geometry length: {google_geom.length:.2f} units")
    else:
        print(f"Google geometry type: {type(google_geom)}")
        print(f"Google geometry length: {google_geom.length:.2f} units")
    
    # Calculate Hausdorff distance manually
    distance = calculate_hausdorff(ref_geom, google_geom, target_crs='EPSG:2039')
    print(f"Hausdorff distance: {distance:.6f} meters")
    
    if distance <= 5.0:
        print("PASSES Hausdorff test (≤ 5m)")
    else:
        print("FAILS Hausdorff test (> 5m)")
        
    # Check coordinate systems
    print(f"Reference CRS: {gdf.crs}")
    
    # Try with different thresholds
    test_thresholds = [0.1, 1.0, 5.0, 10.0, 50.0]
    for threshold in test_thresholds:
        passes = distance <= threshold
        print(f"Threshold {threshold:4.1f}m: {'PASS' if passes else 'FAIL'}")
        
except Exception as e:
    print(f"Error aggregation: {e}")

print("\nCONCLUSION:")
print("If distance is very small, validation is working correctly.")
print("Google routes are just very accurate to the reference!")

