"""
Check actual Hausdorff distances for s_653-655 to see why all validations are failing.
"""
import pandas as pd
import geopandas as gpd
import sys
import os
sys.path.insert(0, r'E:\google_agg')

from components.control.validator import ValidationParameters, validate_row, decode_polyline
from shapely.geometry import LineString
import zipfile
import tempfile

print("=== CHECKING ACTUAL HAUSDORFF DISTANCES FOR S_653-655 ===")

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

# Focus on s_653-655 link
target_link = 's_653-655'
link_data = df[df['Name'] == target_link].copy()

# Get the reference geometry
matching_shp = gdf[(gdf['From'].astype(str) == '653') & (gdf['To'].astype(str) == '655')]
ref_geometry = matching_shp.iloc[0]['geometry']

print(f"Reference geometry for s_653-655:")
print(f"  Type: {ref_geometry.geom_type}")
print(f"  Length: {ref_geometry.length:.6f} degrees")
print(f"  Bounds: {ref_geometry.bounds}")

# Check a few sample polylines and their Hausdorff distances
params = ValidationParameters(hausdorff_threshold_m=5.0)

print(f"\nChecking first 5 observations:")
print("Timestamp | RouteAlt | Hausdorff Distance (m) | Valid?")
print("-" * 60)

for idx, row in link_data.head(5).iterrows():
    timestamp = row['Timestamp']
    route_alt = row.get('RouteAlternative', 1)
    polyline = row['Polyline']

    # Decode the polyline
    try:
        google_coords = decode_polyline(polyline)
        google_geometry = gpd.points_from_xy([p[1] for p in google_coords],
                                           [p[0] for p in google_coords])

        # Create LineString from points
        if len(google_coords) >= 2:
            google_line = LineString([(p[1], p[0]) for p in google_coords])

            # Calculate Hausdorff distance using our fixed function
            from components.control.validator import calculate_hausdorff
            try:
                hausdorff_dist = calculate_hausdorff(google_line, ref_geometry)
                is_valid = hausdorff_dist <= params.hausdorff_threshold_m
                print(f"{timestamp} | {route_alt:8} | {hausdorff_dist:15.2f} | {is_valid}")
            except Exception as e:
                print(f"{timestamp} | {route_alt:8} | ERROR: {str(e)} | False")

        else:
            print(f"{timestamp} | {route_alt:8} | ERROR: < 2 points | False")

    except Exception as e:
        print(f"{timestamp} | {route_alt:8} | ERROR: {str(e)[:20]} | False")

# Let's also check if the polylines are actually different or same
print(f"\nChecking if polylines are identical:")
unique_polylines = link_data['Polyline'].nunique()
total_polylines = len(link_data)
print(f"Unique polylines: {unique_polylines}")
print(f"Total records: {total_polylines}")

if unique_polylines < total_polylines:
    print("WARNING: Some polylines are duplicated!")

# Sample a few different polylines if available
if unique_polylines > 1:
    print(f"\nSampling different polylines:")
    unique_data = link_data.drop_duplicates(subset=['Polyline']).head(3)

    for idx, row in unique_data.iterrows():
        polyline = row['Polyline']
        try:
            google_coords = decode_polyline(polyline)
            if len(google_coords) >= 2:
                google_line = LineString([(p[1], p[0]) for p in google_coords])
                hausdorff_dist = calculate_hausdorff(ref_geometry, google_line)
                print(f"  Polyline {idx}: Hausdorff = {hausdorff_dist:.2f}m")
        except Exception as e:
            print(f"  Polyline {idx}: ERROR = {e}")

# Let's also examine the coordinate ranges
print(f"\nAnalyzing coordinate ranges:")
try:
    # Reference geometry bounds
    ref_bounds = ref_geometry.bounds
    print(f"Reference bounds: {ref_bounds}")

    # Sample Google geometry bounds
    sample_polyline = link_data.iloc[0]['Polyline']
    google_coords = decode_polyline(sample_polyline)
    google_line = LineString([(p[1], p[0]) for p in google_coords])
    google_bounds = google_line.bounds
    print(f"Google bounds:    {google_bounds}")

    # Check coordinate differences
    print(f"Coordinate differences:")
    print(f"  X range overlap: {max(ref_bounds[0], google_bounds[0])} to {min(ref_bounds[2], google_bounds[2])}")
    print(f"  Y range overlap: {max(ref_bounds[1], google_bounds[1])} to {min(ref_bounds[3], google_bounds[3])}")

except Exception as e:
    print(f"Error analyzing coordinates: {e}")

print(f"\n=== SUMMARY ===")
print(f"This analysis should show us the actual Hausdorff distances")
print(f"and help determine why all s_653-655 validations are failing.")