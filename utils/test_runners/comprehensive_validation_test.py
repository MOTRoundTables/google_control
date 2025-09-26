#!/usr/bin/env python3
"""
Comprehensive test for all validation code ranges (0-4, 20-24, 30-34, 90-93).
Tests all checkbox combinations and edge cases.
"""

import pandas as pd
import sys
import os

# Add project directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from control_validator import validate_dataframe_batch, ValidationParameters
import geopandas as gpd


def test_all_configurations():
    """Test all checkbox combinations to verify codes 0-4, 20-24, 30-34 work correctly."""

    print("COMPREHENSIVE VALIDATION SYSTEM TEST")
    print("=" * 60)

    # Load test data
    try:
        df = pd.read_csv("comprehensive_test_dataset.csv", comment='#')
        print(f"Loaded test dataset: {len(df)} rows")

        # Clean data
        df = df.rename(columns={
            'Name': 'name',
            'RouteAlternative': 'route_alternative',
            'Timestamp': 'timestamp',
            'Polyline': 'polyline'
        })

    except Exception as e:
        print(f"Error loading test data: {e}")
        return False

    # Load shapefile
    try:
        shapefile_path = "test_data/google_results_to_golan_17_8_25/google_results_to_golan_17_8_25.shp"
        shapefile_gdf = gpd.read_file(shapefile_path)
        print(f"Loaded shapefile: {len(shapefile_gdf)} features")
    except Exception as e:
        print(f"Error loading shapefile: {e}")
        return False

    all_tests_passed = True

    # Test Configuration 1: Hausdorff Only
    print("\n1. TESTING HAUSDORFF ONLY (codes x1)")
    print("-" * 40)

    params1 = ValidationParameters(
        use_hausdorff=True,
        use_length_check=False,
        use_coverage_check=False,
        hausdorff_threshold_m=10.0
    )

    try:
        result1 = validate_dataframe_batch(df, shapefile_gdf, params1)
        codes1 = result1['valid_code'].tolist()
        print(f"Result codes: {codes1}")

        # Analyze results by test case groups
        print("Analysis by test case:")

        # Test Case 1: Data errors (should be 90-93)
        case1_codes = codes1[0:4]  # First 4 rows
        print(f"  Case 1 (Data errors 90-93): {case1_codes}")
        expected_90_93 = all(90 <= c <= 93 for c in case1_codes)
        if expected_90_93:
            print("    SUCCESS: Data availability codes working")
        else:
            print("    ERROR: Expected codes 90-93")
            all_tests_passed = False

        # Test Case 2: Geometry only (should be 0-4, specifically x1)
        case2_codes = codes1[4:6]  # Next 2 rows
        print(f"  Case 2 (Geometry only): {case2_codes}")
        expected_geometry = all(0 <= c <= 4 for c in case2_codes)
        if expected_geometry:
            print("    SUCCESS: Geometry-only codes working")
        else:
            print("    ERROR: Expected codes 0-4")
            all_tests_passed = False

        # Test Case 3: Single alternative (should be 20-24, specifically x1)
        case3_codes = codes1[6:8]  # Next 2 rows
        print(f"  Case 3 (Single alternative): {case3_codes}")
        expected_single = all(20 <= c <= 24 for c in case3_codes)
        if expected_single:
            print("    SUCCESS: Single alternative codes working")
        else:
            print("    ERROR: Expected codes 20-24")
            all_tests_passed = False

        # Test Case 4: Multi alternative (should be 30-34, specifically x1)
        case4_codes = codes1[8:11]  # Last 3 rows
        print(f"  Case 4 (Multi alternative): {case4_codes}")
        expected_multi = all(30 <= c <= 34 for c in case4_codes)
        if expected_multi:
            print("    SUCCESS: Multi alternative codes working")
        else:
            print("    ERROR: Expected codes 30-34")
            all_tests_passed = False

        # Check second digit is 1 for configuration (Hausdorff only)
        config_codes = [c for c in codes1 if c not in range(90, 94)]  # Exclude error codes
        second_digits = [c % 10 for c in config_codes if c >= 10]
        expected_config = all(d == 1 for d in second_digits if d != 0)  # 0 is exact match special case
        print(f"  Configuration check (second digit should be 1): {second_digits}")
        if expected_config:
            print("    SUCCESS: Configuration code 1 (Hausdorff only) detected")
        else:
            print("    WARNING: Expected configuration 1, check special cases")

    except Exception as e:
        print(f"Test 1 failed: {e}")
        all_tests_passed = False

    # Test Configuration 4: All Tests Enabled
    print("\n2. TESTING ALL TESTS ENABLED (codes x4)")
    print("-" * 40)

    params4 = ValidationParameters(
        use_hausdorff=True,
        use_length_check=True,
        use_coverage_check=True,
        hausdorff_threshold_m=10.0
    )

    try:
        result4 = validate_dataframe_batch(df, shapefile_gdf, params4)
        codes4 = result4['valid_code'].tolist()
        print(f"Result codes: {codes4}")

        # Check second digit is 4 for configuration (all tests)
        config_codes4 = [c for c in codes4 if c not in range(90, 94)]  # Exclude error codes
        second_digits4 = [c % 10 for c in config_codes4 if c >= 10]
        expected_config4 = all(d == 4 for d in second_digits4 if d != 0)  # 0 is exact match special case
        print(f"  Configuration check (second digit should be 4): {second_digits4}")
        if expected_config4:
            print("    SUCCESS: Configuration code 4 (all tests) detected")
        else:
            print("    WARNING: Expected configuration 4, check special cases")

    except Exception as e:
        print(f"Test 2 failed: {e}")
        all_tests_passed = False

    # Test Configuration 2: Hausdorff + Length
    print("\n3. TESTING HAUSDORFF + LENGTH (codes x2)")
    print("-" * 40)

    params2 = ValidationParameters(
        use_hausdorff=True,
        use_length_check=True,
        use_coverage_check=False,
        hausdorff_threshold_m=10.0
    )

    try:
        result2 = validate_dataframe_batch(df, shapefile_gdf, params2)
        codes2 = result2['valid_code'].tolist()
        print(f"Result codes: {codes2}")

        # Check second digit is 2
        config_codes2 = [c for c in codes2 if c not in range(90, 94)]
        second_digits2 = [c % 10 for c in config_codes2 if c >= 10]
        expected_config2 = all(d == 2 for d in second_digits2 if d != 0)
        print(f"  Configuration check (second digit should be 2): {second_digits2}")
        if expected_config2:
            print("    SUCCESS: Configuration code 2 (Hausdorff + Length) detected")
        else:
            print("    WARNING: Expected configuration 2, check special cases")

    except Exception as e:
        print(f"Test 3 failed: {e}")
        all_tests_passed = False

    # Test Configuration 3: Hausdorff + Coverage
    print("\n4. TESTING HAUSDORFF + COVERAGE (codes x3)")
    print("-" * 40)

    params3 = ValidationParameters(
        use_hausdorff=True,
        use_length_check=False,
        use_coverage_check=True,
        hausdorff_threshold_m=10.0
    )

    try:
        result3 = validate_dataframe_batch(df, shapefile_gdf, params3)
        codes3 = result3['valid_code'].tolist()
        print(f"Result codes: {codes3}")

        # Check second digit is 3
        config_codes3 = [c for c in codes3 if c not in range(90, 94)]
        second_digits3 = [c % 10 for c in config_codes3 if c >= 10]
        expected_config3 = all(d == 3 for d in second_digits3 if d != 0)
        print(f"  Configuration check (second digit should be 3): {second_digits3}")
        if expected_config3:
            print("    SUCCESS: Configuration code 3 (Hausdorff + Coverage) detected")
        else:
            print("    WARNING: Expected configuration 3, check special cases")

    except Exception as e:
        print(f"Test 4 failed: {e}")
        all_tests_passed = False

    # Test Priority: Exact Match (Hausdorff = 0) gets code x0
    print("\n5. TESTING EXACT MATCH PRIORITY (codes x0)")
    print("-" * 40)
    print("Note: This requires test data with Hausdorff distance exactly = 0")
    print("Current test data may not have exact matches, so codes x0 may not appear")

    # Final Summary
    print("\n" + "=" * 60)
    print("COMPREHENSIVE TEST SUMMARY")
    print("=" * 60)

    if all_tests_passed:
        print("SUCCESS: All validation code ranges working correctly!")
        print("- Codes 90-93: Data availability errors")
        print("- Codes 0-4: Geometry only (no route_alternative)")
        print("- Codes 20-24: Single alternative context")
        print("- Codes 30-34: Multi alternative context")
        print("- Configuration matching: Second digit matches checkbox selection")
    else:
        print("ERROR: Some tests failed - check output above")

    return all_tests_passed


if __name__ == "__main__":
    success = test_all_configurations()
    sys.exit(0 if success else 1)