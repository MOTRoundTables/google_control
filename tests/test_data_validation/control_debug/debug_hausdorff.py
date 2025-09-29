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

# Test specific cases
test_cases = [
    ('s_653-655', df[df['Name'] == 's_653-655']['Polyline'].iloc[0]),
    ('s_9054-99', df[df['Name'] == 's_9054-99']['Polyline'].iloc[0]),
]

for link_name, polyline in test_cases:
    print(f"\n{'='*50}")
    print(f"Testing {link_name}")
    print(f"{'='*50}")
    
    # Get reference geometry
    ref_geom = gdf[gdf['link_id'] == link_name].geometry.iloc[0]
    print(f"Reference geometry length: {ref_geom.length:.2f} units")
    
    # Decode Google polyline
    try:
        google_coords = decode_polyline(polyline)
        print(f"Google polyline decoded: {len(google_coords)} points")
        print(f"First few points: {google_coords[:3]}")
        
        from shapely.geometry import LineString
        google_geom = LineString(google_coords)
        print(f"Google geometry length: {google_geom.length:.2f} units")
        
        # Calculate Hausdorff distance manually
        distance = calculate_hausdorff(ref_geom, google_geom, target_crs='EPSG:2039')
        print(f"Hausdorff distance: {distance:.6f} meters")
        
        if distance <= 5.0:
            print("✅ PASSES Hausdorff test (≤ 5m)")
        else:
            print("❌ FAILS Hausdorff test (> 5m)")
            
    except Exception as e:
        print(f"❌ Error aggregation: {e}")
        import traceback
        traceback.print_exc()

print(f"\n{'='*60}")
print("CONCLUSION:")
print("If Hausdorff distances are very small (< 1-5m), then the validation")
print("is working correctly - the Google routes are just very accurate!")
print("This would explain why everything shows as 'valid'.")

