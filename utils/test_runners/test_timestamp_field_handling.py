#!/usr/bin/env python3
"""
Test RequestedTime vs timestamp field handling to ensure no regression.

This test verifies that:
1. Missing observations specifically use RequestedTime field for output
2. Other functions continue to use timestamp fields correctly
3. Field detection logic works properly for different column name variations
4. No existing functionality was broken by RequestedTime changes

Run with: python utils/test_runners/test_timestamp_field_handling.py
"""

import sys
import os
import pandas as pd
import geopandas as gpd
from pathlib import Path
from datetime import datetime, timedelta
import tempfile

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from components.control.report import (
    extract_missing_observations,
    extract_failed_observations,
    extract_best_valid_observations
)


class TestTimestampFieldHandling:
    """Test timestamp vs RequestedTime field handling"""

    def __init__(self):
        self.test_results = []

    def log_test(self, test_name, passed, message=""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'message': message
        })
        print(f"{status}: {test_name}")
        if message:
            print(f"   {message}")

    def create_test_data_with_different_time_fields(self):
        """Create test data with different timestamp field variations"""
        base_time = datetime(2025, 1, 15, 10, 0)

        # Dataset 1: Has RequestedTime field (preferred)
        data1 = []
        for i in range(4):
            data1.append({
                'Name': 's_100-200',
                'link_id': 's_100-200',
                'RequestedTime': base_time + timedelta(minutes=i*15),
                'Timestamp': base_time + timedelta(minutes=i*15),  # Also has Timestamp
                'is_valid': True if i != 2 else False,  # Gap at i=2
                'valid_code': 0 if i != 2 else 1,
                'polyline': 'encoded_polyline',
                'RouteAlternative': 1,
            })

        # Dataset 2: Has only Timestamp field (fallback)
        data2 = []
        for i in range(4):
            if i != 1:  # Create gap
                data2.append({
                    'Name': 's_200-300',
                    'link_id': 's_200-300',
                    'Timestamp': base_time + timedelta(minutes=i*15),
                    'is_valid': True,
                    'valid_code': 0,
                    'polyline': 'encoded_polyline2',
                    'RouteAlternative': 1,
                })

        # Dataset 3: Has lowercase timestamp (fallback)
        data3 = []
        for i in range(4):
            if i != 3:  # Create gap
                data3.append({
                    'Name': 's_300-400',
                    'link_id': 's_300-400',
                    'timestamp': base_time + timedelta(minutes=i*15),
                    'is_valid': True,
                    'valid_code': 0,
                    'polyline': 'encoded_polyline3',
                    'RouteAlternative': 1,
                })

        return data1, data2, data3, base_time

    def create_simple_shapefile(self):
        """Create simple test shapefile"""
        from shapely.geometry import LineString

        shapefile_data = [
            {'From': 100, 'To': 200},
            {'From': 200, 'To': 300},
            {'From': 300, 'To': 400},
            {'From': 400, 'To': 500},  # No data in CSV
        ]

        geometries = [LineString([(i, i), (i+1, i+1)]) for i in range(4)]
        return gpd.GeoDataFrame(shapefile_data, geometry=geometries)

    def test_1_requested_time_field_priority(self):
        """Test that RequestedTime field takes priority when available"""
        data1, _, _, base_time = self.create_test_data_with_different_time_fields()
        shapefile_gdf = self.create_simple_shapefile()

        df = pd.DataFrame(data1)

        completeness_params = {
            'start_date': base_time.date(),
            'end_date': base_time.date(),
            'interval_minutes': 15
        }

        try:
            missing_df = extract_missing_observations(df, completeness_params, shapefile_gdf)

            if missing_df.empty:
                self.log_test("RequestedTime field priority", False, "No missing observations found")
                return

            # Check that output uses RequestedTime column
            if 'RequestedTime' not in missing_df.columns:
                self.log_test("RequestedTime field priority", False,
                             "RequestedTime not in output columns")
                return

            # Check that missing observations were detected correctly
            # We created a gap at i=2 for s_100-200
            missing_times = missing_df[missing_df['link_id'] == 's_100-200']['RequestedTime']
            expected_missing_time = base_time + timedelta(minutes=2*15)

            if expected_missing_time not in missing_times.values:
                self.log_test("RequestedTime field priority", False,
                             f"Expected missing time {expected_missing_time} not found")
                return

            self.log_test("RequestedTime field priority", True,
                         "RequestedTime field correctly prioritized and used")

        except Exception as e:
            self.log_test("RequestedTime field priority", False, f"Exception: {e}")

    def test_2_timestamp_fallback(self):
        """Test that function falls back to Timestamp when RequestedTime not available"""
        _, data2, _, base_time = self.create_test_data_with_different_time_fields()
        shapefile_gdf = self.create_simple_shapefile()

        df = pd.DataFrame(data2)

        completeness_params = {
            'start_date': base_time.date(),
            'end_date': base_time.date(),
            'interval_minutes': 15
        }

        try:
            missing_df = extract_missing_observations(df, completeness_params, shapefile_gdf)

            if missing_df.empty:
                self.log_test("Timestamp fallback", False, "No missing observations found")
                return

            # Should still output RequestedTime column even when input was Timestamp
            if 'RequestedTime' not in missing_df.columns:
                self.log_test("Timestamp fallback", False,
                             "RequestedTime not in output despite fallback")
                return

            # Check that missing observations were detected from Timestamp field
            # We created a gap at i=1 for s_200-300
            missing_times = missing_df[missing_df['link_id'] == 's_200-300']['RequestedTime']
            expected_missing_time = base_time + timedelta(minutes=1*15)

            if expected_missing_time not in missing_times.values:
                self.log_test("Timestamp fallback", False,
                             f"Expected missing time {expected_missing_time} not found")
                return

            self.log_test("Timestamp fallback", True,
                         "Correctly fell back to Timestamp field when RequestedTime not available")

        except Exception as e:
            self.log_test("Timestamp fallback", False, f"Exception: {e}")

    def test_3_lowercase_timestamp_fallback(self):
        """Test fallback to lowercase timestamp field"""
        _, _, data3, base_time = self.create_test_data_with_different_time_fields()
        shapefile_gdf = self.create_simple_shapefile()

        df = pd.DataFrame(data3)

        completeness_params = {
            'start_date': base_time.date(),
            'end_date': base_time.date(),
            'interval_minutes': 15
        }

        try:
            missing_df = extract_missing_observations(df, completeness_params, shapefile_gdf)

            if missing_df.empty:
                self.log_test("Lowercase timestamp fallback", False, "No missing observations found")
                return

            # Should still output RequestedTime column
            if 'RequestedTime' not in missing_df.columns:
                self.log_test("Lowercase timestamp fallback", False,
                             "RequestedTime not in output despite fallback")
                return

            # Check detection from lowercase timestamp
            # We created a gap at i=3 for s_300-400
            missing_times = missing_df[missing_df['link_id'] == 's_300-400']['RequestedTime']
            expected_missing_time = base_time + timedelta(minutes=3*15)

            if expected_missing_time not in missing_times.values:
                self.log_test("Lowercase timestamp fallback", False,
                             f"Expected missing time {expected_missing_time} not found")
                return

            self.log_test("Lowercase timestamp fallback", True,
                         "Correctly fell back to lowercase timestamp field")

        except Exception as e:
            self.log_test("Lowercase timestamp fallback", False, f"Exception: {e}")

    def test_4_other_functions_still_use_timestamp(self):
        """Test that other functions (not missing observations) still use timestamp correctly"""
        data1, data2, data3, _ = self.create_test_data_with_different_time_fields()

        # Combine all data with failed observations
        all_data = data1 + data2 + data3

        # Add some failed observations
        failed_data = [
            {
                'Name': 's_400-500',
                'link_id': 's_400-500',
                'Timestamp': datetime(2025, 1, 15, 11, 0),
                'is_valid': False,
                'valid_code': 2,
                'polyline': 'failed_polyline',
                'RouteAlternative': 1,
                'hausdorff_distance': 10.0,
            }
        ]

        combined_data = all_data + failed_data
        df = pd.DataFrame(combined_data)

        try:
            # Test extract_failed_observations - should work with any timestamp field
            failed_df = extract_failed_observations(df)

            if failed_df.empty:
                self.log_test("Other functions use timestamp", False, "No failed observations extracted")
                return

            # Should extract the failed observation
            failed_links = set(failed_df['link_id'].unique())
            if 's_400-500' not in failed_links:
                self.log_test("Other functions use timestamp", False,
                             "Failed to extract known failed observation")
                return

            # Test extract_best_valid_observations
            best_df = extract_best_valid_observations(df)

            if best_df.empty:
                self.log_test("Other functions use timestamp", False, "No best observations extracted")
                return

            self.log_test("Other functions use timestamp", True,
                         "Other functions still work correctly with timestamp fields")

        except Exception as e:
            self.log_test("Other functions use timestamp", False, f"Exception: {e}")

    def test_5_no_time_field_handling(self):
        """Test handling when no time fields are available"""
        shapefile_gdf = self.create_simple_shapefile()

        # Create data without any time fields
        no_time_data = [
            {
                'Name': 's_100-200',
                'link_id': 's_100-200',
                'is_valid': True,
                'valid_code': 0,
                'polyline': 'test_polyline',
            }
        ]

        df = pd.DataFrame(no_time_data)

        completeness_params = {
            'start_date': datetime(2025, 1, 15).date(),
            'end_date': datetime(2025, 1, 15).date(),
            'interval_minutes': 15
        }

        try:
            missing_df = extract_missing_observations(df, completeness_params, shapefile_gdf)

            # Should return empty DataFrame when no time field available
            if not missing_df.empty:
                self.log_test("No time field handling", False,
                             f"Expected empty result, got {len(missing_df)} rows")
                return

            self.log_test("No time field handling", True,
                         "Correctly handles missing time fields by returning empty")

        except Exception as e:
            self.log_test("No time field handling", False, f"Exception: {e}")

    def run_all_tests(self):
        """Run all timestamp field tests"""
        print("⏰ Running Timestamp Field Handling Tests")
        print("=" * 60)

        self.test_1_requested_time_field_priority()
        self.test_2_timestamp_fallback()
        self.test_3_lowercase_timestamp_fallback()
        self.test_4_other_functions_still_use_timestamp()
        self.test_5_no_time_field_handling()

        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)

        passed = sum(1 for r in self.test_results if r['passed'])
        total = len(self.test_results)

        for result in self.test_results:
            status = "✅" if result['passed'] else "❌"
            print(f"{status} {result['test']}")
            if result['message']:
                print(f"   → {result['message']}")

        print(f"\n📈 Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")

        if passed == total:
            print("🎉 All timestamp field tests passed!")
            return True
        else:
            print("⚠️  Some tests failed. Timestamp field handling may have issues.")
            return False


def main():
    """Run the timestamp field tests"""
    tester = TestTimestampFieldHandling()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())