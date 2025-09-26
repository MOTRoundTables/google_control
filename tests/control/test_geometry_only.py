#!/usr/bin/env python3
"""
Test geometry-only validation codes (0-4).
"""

import pandas as pd
import sys
import os

# Add project directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from components.control.validator import validate_dataframe_batch, ValidationParameters
import geopandas as gpd


def test_geometry_only_codes():
    """Test that geometry-only data (no route_alternative column) gets codes 0-4."""
    print("TESTING GEOMETRY-ONLY CODES (0-4)")
    print("=" * 50)

    try:
        # Load geometry-only test data (no route_alternative column)
        geom_df = pd.read_csv("geometry_only_complete_test.csv")
        print(f"Loaded geometry-only data: {len(geom_df)} rows")
        print(f"Columns: {list(geom_df.columns)}")

        # Verify no route_alternative column
        if 'route_alternative' in geom_df.columns:
            print("ERROR: Test data still has route_alternative column!")
            return False

        # Rename columns to match expected format
        geom_df = geom_df.rename(columns={
            'Name': 'name',
            'Timestamp': 'timestamp',
            'Polyline': 'polyline'
        })

        shapefile_path = "test_data/google_results_to_golan_17_8_25/google_results_to_golan_17_8_25.shp"
        shapefile_gdf = gpd.read_file(shapefile_path)
        print(f"Loaded shapefile: {len(shapefile_gdf)} features")

        # Test with different configurations
        configs = [
            ("Hausdorff only", ValidationParameters(use_hausdorff=True, use_length_check=False, use_coverage_check=False), 1),
            ("Hausdorff + Length", ValidationParameters(use_hausdorff=True, use_length_check=True, use_coverage_check=False), 2),
            ("Hausdorff + Coverage", ValidationParameters(use_hausdorff=True, use_length_check=False, use_coverage_check=True), 3),
            ("All tests", ValidationParameters(use_hausdorff=True, use_length_check=True, use_coverage_check=True), 4)
        ]

        all_passed = True

        for name, params, expected_config in configs:
            print(f"\n--- {name} (expected config {expected_config}) ---")

            result = validate_dataframe_batch(geom_df, shapefile_gdf, params)
            codes = result['valid_code'].tolist()

            print(f"Result codes: {codes}")

            # Check that all codes are in 0-4 range (geometry-only context)
            geometry_only_codes = all(0 <= c <= 4 for c in codes)

            # Check configuration digits for non-zero codes
            config_check = True
            for code in codes:
                if code > 0:  # Skip exact match (code 0)
                    if code != expected_config:
                        config_check = False
                        print(f"  ERROR: Expected config {expected_config}, got {code}")

            if geometry_only_codes and config_check:
                print(f"  SUCCESS: Geometry-only codes with config {expected_config}")
            else:
                print(f"  ERROR: Expected codes 0-4 with config {expected_config}")
                all_passed = False

        return all_passed

    except Exception as e:
        print(f"Error in geometry-only test: {e}")
        return False


if __name__ == "__main__":
    success = test_geometry_only_codes()
    if success:
        print("\n✅ GEOMETRY-ONLY VALIDATION WORKING CORRECTLY!")
    else:
        print("\n❌ GEOMETRY-ONLY VALIDATION FAILED!")

    sys.exit(0 if success else 1)