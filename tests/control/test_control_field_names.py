"""
Test to verify field name preservation issue in control validation
"""
import pandas as pd
import sys
import os
sys.path.insert(0, r'E:\google_agg')

from components.control.validator import validate_dataframe_batch, ValidationParameters
import tempfile
from pathlib import Path

# Create test data with proper field names
test_data = pd.DataFrame({
    'DataID': ['001', '002'],
    'Name': ['s_653-655', 's_655-657'],
    'SegmentID': ['1185048', '1185049'],
    'RouteAlternative': [1, 1],
    'Timestamp': ['2025-01-07 13:45', '2025-01-07 14:00'],
    'Polyline': ['_oxwD{_wtEoAlCe@vFq@ha@', '_oxwD{_wtEoAlCe@vFq@ha@']
})

print("Input columns:", list(test_data.columns))
print("Input sample:")
print(test_data[['Name', 'RouteAlternative']].head())

# Create dummy shapefile data
import geopandas as gpd
from shapely.geometry import LineString

shapefile_data = gpd.GeoDataFrame({
    'Id': ['s_653-655', 's_655-657'],
    'From': [653, 655], 
    'To': [655, 657],
    'geometry': [
        LineString([(0, 0), (1, 1)]),
        LineString([(1, 1), (2, 2)])
    ]
}, crs='EPSG:2039')

# Create validation parameters - use correct field names
params = ValidationParameters(
    use_hausdorff=True,
    hausdorff_threshold_m=10.0,  # Fixed parameter name
    use_length_check=False,
    use_coverage_check=False
)

# Validate
result = validate_dataframe_batch(test_data, shapefile_data, params)

print("\nOutput columns:", list(result.columns))
print("Output sample:")
if 'Name' in result.columns and 'RouteAlternative' in result.columns:
    print(result[['Name', 'RouteAlternative', 'is_valid', 'valid_code']].head())
    print("\nSUCCESS: Field names preserved!")
else:
    print("Available columns:", list(result.columns))
    print("\nERROR: Field names not preserved!")
    # Show the actual data to see what's happening
    print("\nActual output data:")
    print(result.head())
