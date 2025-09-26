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
        # Load the existing geometry-only test data
        geom_df = pd.read_csv("geometry_only_test.csv")
        print(f"Loaded geometry-only data: {len(geom_df)} rows")
        print(f"Columns: {list(geom_df.columns)}")

        # Verify no route_alternative column
        if 'RouteAlternative' in geom_df.columns:
            print("WARNING: Test data has RouteAlternative column, removing it")
            geom_df = geom_df.drop('RouteAlternative', axis=1)

        if 'route_alternative' in geom_df.columns:
            print("WARNING: Test data has route_alternative column, removing it")
            geom_df = geom_df.drop('route_alternative', axis=1)

        # Rename columns to match expected format
        geom_df = geom_df.rename(columns={
            'Name': 'name',
            'Timestamp': 'timestamp',
            'Polyline': 'polyline'
        })

        print(f"Final columns: {list(geom_df.columns)}")
        print("Sample data:")
        print(geom_df.head(2))

        shapefile_path = "test_data/google_results_to_golan_17_8_25/google_results_to_golan_17_8_25.shp"
        shapefile_gdf = gpd.read_file(shapefile_path)
        print(f"Loaded shapefile: {len(shapefile_gdf)} features")

        # Test with Hausdorff only first
        print(f"\n--- Hausdorff only (expected config 1) ---")
        params = ValidationParameters(use_hausdorff=True, use_length_check=False, use_coverage_check=False)

        result = validate_dataframe_batch(geom_df, shapefile_gdf, params)
        codes = result['valid_code'].tolist()

        print(f"Result codes: {codes}")

        # Check that all codes are in 0-4 range (geometry-only context)
        geometry_only_codes = all(0 <= c <= 4 for c in codes if c < 90)  # Exclude error codes

        if geometry_only_codes:
            print(f"  SUCCESS: Geometry-only codes detected (0-4 range)")

            # Count exact matches and threshold matches
            exact_matches = sum(1 for c in codes if c == 0)
            threshold_matches = sum(1 for c in codes if c == 1)
            failures = sum(1 for c in codes if c > 1 and c <= 4)
            errors = sum(1 for c in codes if c >= 90)

            print(f"  Analysis: {exact_matches} exact matches (code 0)")
            print(f"           {threshold_matches} threshold matches (code 1)")
            print(f"           {failures} validation failures (codes 2-4)")
            print(f"           {errors} data errors (codes 90+)")
            return True
        else:
            print(f"  ERROR: Expected codes 0-4, got non-geometry codes")
            return False

    except Exception as e:
        print(f"Error in geometry-only test: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_geometry_only_codes()
    if success:
        print("\nSUCCESS: GEOMETRY-ONLY VALIDATION WORKING CORRECTLY!")
    else:
        print("\nERROR: GEOMETRY-ONLY VALIDATION FAILED!")

    sys.exit(0 if success else 1)