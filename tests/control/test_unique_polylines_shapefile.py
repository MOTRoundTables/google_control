"""
Test unique polylines shapefile functionality.

This tests that:
1. Duplicate geometries are properly deduplicated
2. Unique combinations of (Timestamp + Name + Geometry) are preserved
3. The function doesn't break the existing control workflow
"""

import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString
from pathlib import Path
import tempfile
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from components.control.report import create_failed_observations_unique_polylines_shapefile


def test_unique_polylines_deduplication():
    """Test that duplicate polylines are properly deduplicated"""
    print("="*60)
    print("Test: Unique Polylines Deduplication")
    print("="*60)

    # Create test data with duplicate polylines
    # Scenario: 3 route alternatives, but alt 1 and 3 have identical geometries
    test_data = pd.DataFrame({
        'Name': ['s_7025-10764'] * 6,
        'Timestamp': [
            '2025-10-01 00:45:00', '2025-10-01 00:45:00', '2025-10-01 00:45:00',
            '2025-10-01 01:00:00', '2025-10-01 01:00:00', '2025-10-01 01:00:00'
        ],
        'RouteAlternative': [1, 2, 3, 1, 2, 3],
        # Encoded polylines (alt 1 and 3 are identical, alt 2 is different)
        'Polyline': [
            'gydbE_glvEpBn@',  # Alt 1
            'hydbE`glvErCo@',  # Alt 2 (different)
            'gydbE_glvEpBn@',  # Alt 3 (same as alt 1)
            'gydbE_glvEpBn@',  # Alt 1 (timestamp 01:00)
            'hydbE`glvErCo@',  # Alt 2 (timestamp 01:00)
            'gydbE_glvEpBn@',  # Alt 3 (timestamp 01:00)
        ],
        'is_valid': [False] * 6,
        'validation_code': [1] * 6,
        'hausdorff_distance': [5.5, 6.0, 5.5, 5.5, 6.0, 5.5]
    })

    # Create reference shapefile
    ref_geom = LineString([(34.8, 32.0), (34.81, 32.01)])
    ref_gdf = gpd.GeoDataFrame(
        {'From': ['7025'], 'To': ['10764']},
        geometry=[ref_geom],
        crs='EPSG:4326'
    )

    # Create temporary output
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_unique.shp"

        # Call the function
        create_failed_observations_unique_polylines_shapefile(
            test_data,
            ref_gdf,
            str(output_path)
        )

        # Check results
        if output_path.exists():
            result_gdf = gpd.read_file(output_path)

            print(f"\n[Results]")
            print(f"  Input rows: {len(test_data)}")
            print(f"  Output rows (unique polylines): {len(result_gdf)}")
            print(f"  Expected: 4 (2 unique geometries × 2 timestamps)")

            # We expect 4 rows:
            # - Timestamp 00:45, geometry 1 (from alt 1 or 3)
            # - Timestamp 00:45, geometry 2 (from alt 2)
            # - Timestamp 01:00, geometry 1 (from alt 1 or 3)
            # - Timestamp 01:00, geometry 2 (from alt 2)

            if len(result_gdf) == 4:
                print("\n[OK] Deduplication works correctly!")
                print("  - 6 input rows reduced to 4 unique polylines")
                print("  - Duplicates (alt 1 & 3) correctly removed")
                return True
            else:
                print(f"\n[FAIL] Expected 4 unique rows, got {len(result_gdf)}")
                return False
        else:
            print("\n[FAIL] Shapefile not created")
            return False


def test_backward_compatibility():
    """Test that function doesn't break with missing columns"""
    print("\n" + "="*60)
    print("Test: Backward Compatibility")
    print("="*60)

    # Test with minimal data (no RequestedTime, no RouteAlternative)
    test_data = pd.DataFrame({
        'Name': ['s_100-200'],
        'Polyline': ['gydbE_glvEpBn@'],
        'is_valid': [False],
        'validation_code': [1]
    })

    ref_geom = LineString([(34.8, 32.0), (34.81, 32.01)])
    ref_gdf = gpd.GeoDataFrame(
        {'From': ['100'], 'To': ['200']},
        geometry=[ref_geom],
        crs='EPSG:4326'
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_minimal.shp"

        try:
            create_failed_observations_unique_polylines_shapefile(
                test_data,
                ref_gdf,
                str(output_path)
            )

            if output_path.exists():
                result_gdf = gpd.read_file(output_path)
                print(f"\n[OK] Works with minimal columns")
                print(f"  - Created shapefile with {len(result_gdf)} feature(s)")
                return True
            else:
                print("\n[FAIL] Shapefile not created with minimal data")
                return False
        except Exception as e:
            print(f"\n[FAIL] Error with minimal data: {e}")
            return False


def test_empty_input():
    """Test that function handles empty dataframe gracefully"""
    print("\n" + "="*60)
    print("Test: Empty Input Handling")
    print("="*60)

    test_data = pd.DataFrame(columns=['Name', 'Polyline', 'is_valid'])

    ref_geom = LineString([(34.8, 32.0), (34.81, 32.01)])
    ref_gdf = gpd.GeoDataFrame(
        {'From': ['100'], 'To': ['200']},
        geometry=[ref_geom],
        crs='EPSG:4326'
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_empty.shp"

        try:
            create_failed_observations_unique_polylines_shapefile(
                test_data,
                ref_gdf,
                str(output_path)
            )
            print(f"\n[OK] Handles empty input gracefully (no crash)")
            return True
        except Exception as e:
            print(f"\n[FAIL] Crashed on empty input: {e}")
            return False


def main():
    print("\n" + "="*60)
    print("Unique Polylines Shapefile - Test Suite")
    print("="*60)

    test1 = test_unique_polylines_deduplication()
    test2 = test_backward_compatibility()
    test3 = test_empty_input()

    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    print(f"Test 1 - Deduplication Logic: {'[OK]' if test1 else '[FAIL]'}")
    print(f"Test 2 - Backward Compatibility: {'[OK]' if test2 else '[FAIL]'}")
    print(f"Test 3 - Empty Input Handling: {'[OK]' if test3 else '[FAIL]'}")
    print()

    if all([test1, test2, test3]):
        print("[OK] All tests passed!")
        print()
        print("Implementation Summary:")
        print("  - Deduplicates by (Timestamp + Name + Geometry)")
        print("  - Reduces file size when multiple alternatives have identical geometries")
        print("  - Works with minimal columns (backward compatible)")
        print("  - Handles empty input gracefully")
        print("  - New file: failed_observations_unique_polylines_shapefile.zip")
        return 0
    else:
        print("[FAIL] Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
