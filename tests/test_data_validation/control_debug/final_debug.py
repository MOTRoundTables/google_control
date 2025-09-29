"""
Final debug of Hausdorff distances
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

# Test each unique link
unique_links = df['Name'].unique()
for link_name in unique_links:
    print(f"\nTesting {link_name}")
    print("-" * 30)
    
    # Get reference geometry
    ref_geom = gdf[gdf['link_id'] == link_name].geometry.iloc[0]
    
    # Get a sample polyline for this link
    polyline = df[df['Name'] == link_name]['Polyline'].iloc[0]
    
    try:
        google_geom = decode_polyline(polyline)
        
        # Calculate Hausdorff distance with correct parameter name
        distance = calculate_hausdorff(ref_geom, google_geom, crs='EPSG:2039')
        print(f"Hausdorff distance: {distance:.3f} meters")
        
        # Test against common thresholds
        results = {
            '1m': distance <= 1.0,
            '5m': distance <= 5.0,
            '10m': distance <= 10.0
        }
        
        for threshold, passes in results.items():
            status = 'PASS' if passes else 'FAIL'
            print(f"  {threshold}: {status}")
        
    except Exception as e:
        print(f"Error: {e}")

print("\nSUMMARY:")
print("If all distances are < 5m, then Hausdorff validation with 5m threshold")
print("will show everything as valid, which explains your observation.")
print("\nTo see failures, try using a threshold of 1m or 0.5m")

