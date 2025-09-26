"""
Calculate the actual Hausdorff distance for s_653-655 to see why it exceeds 5.0m.
"""
import pandas as pd
import geopandas as gpd
import sys
import os
sys.path.insert(0, r'E:\google_agg')

from components.control.validator import decode_polyline, calculate_hausdorff
from shapely.geometry import LineString
import zipfile
import tempfile

print("=== CALCULATING ACTUAL HAUSDORFF DISTANCE FOR S_653-655 ===")

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

# Get the reference geometry for s_653-655
matching_shp = gdf[(gdf['From'].astype(str) == '653') & (gdf['To'].astype(str) == '655')]
ref_geometry = matching_shp.iloc[0]['geometry']

print(f"Reference geometry info:")
print(f"  Type: {ref_geometry.geom_type}")
print(f"  Length in degrees: {ref_geometry.length:.6f}")
print(f"  Bounds: {ref_geometry.bounds}")

# Get the first Google polyline for s_653-655
target_row = df[df['Name'] == 's_653-655'].iloc[0]
polyline = target_row['Polyline']

print(f"\nGoogle polyline info:")
print(f"  Polyline (first 80 chars): {polyline[:80]}...")

# Decode the polyline
try:
    result = decode_polyline(polyline)
    print(f"  Decode result type: {type(result)}")

    if isinstance(result, LineString):
        google_line = result
        print(f"  Returned LineString directly")
        print(f"  Google geometry length in degrees: {google_line.length:.6f}")
        print(f"  Google geometry bounds: {google_line.bounds}")
        print(f"  Number of coordinate points: {len(google_line.coords)}")
    else:
        google_coords = result
        print(f"  Decoded coordinates: {len(google_coords)} points")
        print(f"  First point (lat, lon): {google_coords[0]}")
        print(f"  Last point (lat, lon): {google_coords[-1]}")

        # Create LineString (note: polyline is (lat, lon) but LineString expects (lon, lat))
        google_line = LineString([(p[1], p[0]) for p in google_coords])
        print(f"  Google geometry length in degrees: {google_line.length:.6f}")
        print(f"  Google geometry bounds: {google_line.bounds}")

    # Now calculate the Hausdorff distance using our fixed function
    print(f"\nCalculating Hausdorff distance...")
    hausdorff_dist = calculate_hausdorff(google_line, ref_geometry)
    print(f"  Hausdorff distance: {hausdorff_dist:.2f} meters")
    print(f"  Threshold: 5.0 meters")
    print(f"  Pass/Fail: {'PASS' if hausdorff_dist <= 5.0 else 'FAIL'}")

    # Let's also check the coordinate systems being used
    print(f"\nCoordinate system analysis:")
    print(f"  Reference bounds: {ref_geometry.bounds}")
    print(f"  Google bounds:    {google_line.bounds}")

    # Check if they overlap at all
    ref_bounds = ref_geometry.bounds
    google_bounds = google_line.bounds

    x_overlap = not (google_bounds[2] < ref_bounds[0] or ref_bounds[2] < google_bounds[0])
    y_overlap = not (google_bounds[3] < ref_bounds[1] or ref_bounds[3] < google_bounds[1])

    print(f"  X coordinates overlap: {x_overlap}")
    print(f"  Y coordinates overlap: {y_overlap}")

    if x_overlap and y_overlap:
        print("  ✓ Geometries overlap spatially")
    else:
        print("  ✗ Geometries do NOT overlap - major problem!")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

print(f"\n=== SUMMARY ===")
print(f"This shows the actual Hausdorff distance calculation")
print(f"and whether the geometries are in the right coordinate system.")