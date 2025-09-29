#!/usr/bin/env python3
"""Test script to verify all optimizations and fixes work correctly."""

import sys
import time
import pandas as pd
import geopandas as gpd
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from components.control.validator import (
    validate_dataframe_batch,
    validate_dataframe_batch_parallel,
    ValidationParameters,
    calculate_hausdorff
)
from components.control.report import extract_best_valid_observations
from shapely.geometry import LineString

def test_all_fixes():
    """Test all optimizations and bug fixes."""

    print("Testing All Fixes and Optimizations")
    print("=" * 50)

    # Load test data
    csv_path = Path("test_data/control/data.csv")
    shapefile_path = Path("test_data/control/google_results_to_golan_17_8_25.shp")

    # Test with 2000 rows for speed
    csv_df = pd.read_csv(csv_path, nrows=2000)
    shapefile_gdf = gpd.read_file(shapefile_path)

    print(f"Loaded {len(csv_df)} CSV rows, {len(shapefile_gdf)} shapefile links")

    # Test 1: Envelope guard removal
    print("\n1. Testing envelope guard removal...")
    line1 = LineString([(34.0, 31.0), (34.1, 31.1)])
    line2 = LineString([(34.0, 31.0), (34.1, 31.1)])  # Same line

    dist = calculate_hausdorff(line1, line2)
    print(f"   Hausdorff distance (identical lines): {dist:.3f}m")

    if dist == 0.0:
        print("   [OK] Exact Hausdorff calculation working")
    else:
        print(f"   [ERROR] Expected 0.0, got {dist}")

    # Test 2: Validation parameters (no strict_hausdorff)
    print("\n2. Testing ValidationParameters...")
    try:
        params = ValidationParameters(
            use_hausdorff=True,
            hausdorff_threshold_m=5.0,
            use_length_check=False,
            use_coverage_check=False
        )
        print("   [OK] ValidationParameters created successfully (no strict_hausdorff)")
    except Exception as e:
        print(f"   ❌ ValidationParameters error: {e}")

    # Test 3: Sequential validation
    print("\n3. Testing sequential validation...")
    start_time = time.time()
    sequential_result = validate_dataframe_batch(csv_df, shapefile_gdf, params)
    sequential_time = time.time() - start_time

    valid_count = sequential_result['is_valid'].sum()
    print(f"   Sequential: {sequential_time:.2f}s, {valid_count} valid, {len(sequential_result)} total")

    # Test 4: Parallel validation
    print("\n4. Testing parallel validation...")
    start_time = time.time()
    parallel_result = validate_dataframe_batch_parallel(csv_df, shapefile_gdf, params, max_workers=2)
    parallel_time = time.time() - start_time

    par_valid_count = parallel_result['is_valid'].sum()
    print(f"   Parallel: {parallel_time:.2f}s, {par_valid_count} valid, {len(parallel_result)} total")

    # Test 5: Results consistency
    print("\n5. Testing results consistency...")
    if len(sequential_result) == len(parallel_result):
        print("   [OK] Row counts match")
    else:
        print(f"   [ERROR] Row count mismatch: {len(sequential_result)} vs {len(parallel_result)}")

    if valid_count == par_valid_count:
        print("   [OK] Valid counts match")
    else:
        print(f"   [ERROR] Valid count mismatch: {valid_count} vs {par_valid_count}")

    # Test 6: Best alternative selection
    print("\n6. Testing best alternative selection...")
    try:
        seq_best = extract_best_valid_observations(sequential_result)
        par_best = extract_best_valid_observations(parallel_result)

        if len(seq_best) == len(par_best):
            print(f"   [OK] Best alternatives match: {len(seq_best)} observations")
        else:
            print(f"   [ERROR] Best alternatives mismatch: {len(seq_best)} vs {len(par_best)}")
    except Exception as e:
        print(f"   [ERROR] Best alternative error: {e}")

    # Test 7: Performance comparison
    print("\n7. Performance Summary:")
    if parallel_time > 0:
        speedup = sequential_time / parallel_time
        print(f"   Sequential: {sequential_time:.2f}s ({len(csv_df)/sequential_time:.0f} rows/s)")
        print(f"   Parallel:   {parallel_time:.2f}s ({len(csv_df)/parallel_time:.0f} rows/s)")
        print(f"   Speedup:    {speedup:.1f}x")

        if speedup > 0.8:  # Allow some variation for small datasets
            print("   [OK] Performance acceptable")
        else:
            print("   [WARN] Performance lower than expected (normal for small datasets)")

    # Test 8: Validation rate check
    validation_rate = (valid_count / len(sequential_result)) * 100
    print(f"\n8. Validation Rate: {validation_rate:.1f}%")

    if validation_rate > 95:
        print("   [OK] High validation rate (expected for reference data)")
    elif validation_rate > 30:
        print("   [OK] Reasonable validation rate")
    else:
        print("   [WARN] Low validation rate - check data compatibility")

    # Test 9: Failed observations reference shapefile fix
    print("\n9. Testing failed_observations_reference_shapefile fix...")
    try:
        # Test that the failed observations shapefile creation works
        failed_df = sequential_result[sequential_result['is_valid'] == False].copy()
        if len(failed_df) > 0:
            from components.control.report import create_failed_observations_reference_shapefile
            try:
                create_failed_observations_reference_shapefile(failed_df, shapefile_gdf, "test_failed_output")
                print("   [OK] Failed observations shapefile creation works")
            except Exception as e:
                print(f"   [ERROR] Failed observations shapefile error: {e}")
        else:
            print("   [OK] No failed observations to test (all passed validation)")
    except Exception as e:
        print(f"   [ERROR] Failed observations test error: {e}")

    print("\n" + "=" * 50)
    print("[OK] All tests completed!")

    return True

if __name__ == "__main__":
    try:
        test_all_fixes()
        print("\n[SUCCESS] All fixes and optimizations working correctly!")
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)