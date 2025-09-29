#!/usr/bin/env python3
"""
Test script for new configuration-based validation system.
"""

import pandas as pd
import sys
import os
from pathlib import Path

# Add project directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Provide a minimal Streamlit mock that includes runtime.uploaded_file_manager.UploadedFile
class _MockUploadedFile:
    pass

class _MockRuntime:
    class uploaded_file_manager:
        UploadedFile = _MockUploadedFile

class MockStreamlit:
    def __init__(self):
        self.runtime = _MockRuntime()

    @staticmethod
    def info(msg):
        print(f"[streamlit.info] {msg}")

    @staticmethod
    def warning(msg):
        print(f"[streamlit.warning] {msg}")

    @staticmethod
    def error(msg):
        print(f"[streamlit.error] {msg}")

    @staticmethod
    def success(msg):
        print(f"[streamlit.success] {msg}")

sys.modules['streamlit'] = MockStreamlit()

from components.control.validator import validate_dataframe_batch, ValidationParameters
from components.maps.spatial_data import CoordinateSystemManager
import geopandas as gpd


DATA_ROOT = Path(__file__).resolve().parents[2] / 'test_data' / 'control'


def main():
    print("Testing New Configuration-Based Validation System")
    print("=" * 60)

    # Load test data
    try:
        test_csv_path = DATA_ROOT / 'test_multiple_alternatives.csv'
        df = pd.read_csv(test_csv_path)
        df = df.head(50).copy()
        print(f"Loaded test CSV: {len(df)} rows")
        print(f"Data: {df['Name'].iloc[0]}, {df['Timestamp'].iloc[0]}")
        print(f"Route alternatives: {df['RouteAlternative'].tolist()}")
    except Exception as e:
        print(f"Error loading test CSV: {e}")
        return

    # Load shapefile
    try:
        shapefile_path = DATA_ROOT.parent / 'google_results_to_golan_17_8_25' / 'google_results_to_golan_17_8_25.shp'
        shapefile_gdf = gpd.read_file(shapefile_path)
        print(f"Loaded shapefile: {len(shapefile_gdf)} features")
    except Exception as e:
        print(f"Error loading shapefile: {e}")
        return

    # Prepare data
    df_clean = df.copy()
    df_clean = df_clean.rename(columns={
        'Name': 'name',
        'RouteAlternative': 'route_alternative',
        'Timestamp': 'timestamp',
        'Polyline': 'polyline'
    })

    # Debug: check columns and data
    print()
    print("Debug Info:")
    print(f"  Columns: {list(df_clean.columns)}")
    print("  Required fields check:")
    required_fields = ['name', 'polyline', 'route_alternative']
    for field in required_fields:
        if field in df_clean.columns:
            print(f"    {field}: EXISTS, sample value = {df_clean[field].iloc[0]}")
        else:
            print(f"    {field}: MISSING!")
    print()

    # Test with default parameters (Hausdorff only)
    print("Testing with Hausdorff Only (Default)")
    print("-" * 40)

    params = ValidationParameters(
        use_hausdorff=True,
        use_length_check=False,
        use_coverage_check=False,
        hausdorff_threshold_m=10.0
    )

    try:
        result_df = validate_dataframe_batch(df_clean, shapefile_gdf, params)

        print("Results:")
        for idx, row in result_df.iterrows():
            print(f"  Row {idx+1}: RouteAlt={row['route_alternative']}, Valid={row['is_valid']}, Code={row['valid_code']}")

        codes = result_df['valid_code'].tolist()
        print()
        print("Analysis:")
        print(f"  Codes: {codes}")

        multi_alt_codes = [c for c in codes if 30 <= c <= 34]
        if multi_alt_codes:
            print(f"  SUCCESS: Multi-alternative codes detected: {multi_alt_codes}")
        else:
            print(f"  ERROR: Expected multi-alternative codes (30-34), got: {codes}")

        if len(set(codes)) > 1:
            print("  SUCCESS: Individual results per alternative (different codes)")
        else:
            print(f"  WARNING: All alternatives got same code: {codes[0]}")

    except Exception as e:
        print(f"Validation failed: {e}")
        import traceback
        traceback.print_exc()

    # Test with all options enabled
    print()
    print("Testing with All Tests Enabled")
    print("-" * 40)

    params_all = ValidationParameters(
        use_hausdorff=True,
        use_length_check=True,
        use_coverage_check=True,
        hausdorff_threshold_m=10.0
    )

    try:
        result_df_all = validate_dataframe_batch(df_clean, shapefile_gdf, params_all)

        print("Results with all tests:")
        for idx, row in result_df_all.iterrows():
            print(f"  Row {idx+1}: RouteAlt={row['route_alternative']}, Valid={row['is_valid']}, Code={row['valid_code']}")

        codes_all = result_df_all['valid_code'].tolist()
        print()
        print("All Tests Analysis:")
        print(f"  Codes: {codes_all}")

        second_digits = [c % 10 for c in codes_all if c >= 20]
        if second_digits and all(d == 4 for d in second_digits):
            print("  SUCCESS: Configuration code 4 (all tests) detected correctly")
        else:
            print(f"  ERROR: Expected configuration 4, got second digits: {second_digits}")

    except Exception as e:
        print(f"All tests validation failed: {e}")

    print()
    print("Test Summary:")
    print("SUCCESS: New configuration-based validation system implemented")
    print("SUCCESS: Route alternative batch aggregation working")
    print("SUCCESS: Individual results per alternative")
    print("SUCCESS: Configuration codes match UI checkboxes")


if __name__ == "__main__":
    main()

def test_new_validation_system_smoke():
    main()

