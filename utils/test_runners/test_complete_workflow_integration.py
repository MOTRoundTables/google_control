#!/usr/bin/env python3
"""
Complete workflow integration test for all missing observations fixes.

Tests the complete end-to-end workflow including:
1. File separation in save_validation_results
2. Conditional missing observations based on completeness_params
3. Correct shapefile generation for each file type
4. Proper output file structure

This simulates the complete user workflow from validation to file generation.

Run with: python utils/test_runners/test_complete_workflow_integration.py
"""

import sys
import os
import pandas as pd
import geopandas as gpd
from pathlib import Path
from datetime import datetime, timedelta
import tempfile
import shutil

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import the complete workflow
from components.control.page import save_validation_results
from components.control.report import (
    generate_link_report,
    extract_missing_observations,
    extract_failed_observations,
    extract_no_data_links
)


class TestCompleteWorkflowIntegration:
    """Test complete workflow integration"""

    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.output_dir = Path(self.temp_dir) / "control_output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.test_results = []

    def cleanup(self):
        """Clean up temporary files"""
        try:
            shutil.rmtree(self.temp_dir)
        except:
            pass

    def log_test(self, test_name, passed, message=""):
        """Log test result"""
        status = "PASS" if passed else "FAIL"
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'message': message
        })
        print(f"{status}: {test_name}")
        if message:
            print(f"   {message}")

    def create_comprehensive_test_data(self):
        """Create comprehensive test data covering all scenarios"""
        base_time = datetime(2025, 1, 15, 10, 0)

        # Validation results data with all code types
        validation_data = []

        # Links with validation failures (codes 1-3)
        for code in [1, 2, 3]:
            validation_data.append({
                'Name': f's_100-{200+code}',
                'link_id': f's_100-{200+code}',
                'RequestedTime': base_time,
                'Timestamp': base_time,
                'is_valid': False,
                'valid_code': code,
                'polyline': f'encoded_polyline_for_code_{code}',
                'RouteAlternative': 1,
                'hausdorff_distance': 10.0 + code,
                'DataID': f'data_{code}',
                'SegmentID': f'segment_{code}',
                'Duration': 300.0,
                'Distance': 1000.0,
                'Speed': 50.0,
            })

        # Links with valid data but temporal gaps (for missing observations)
        for i in range(5):
            if i != 2:  # Create gap at i=2
                validation_data.append({
                    'Name': 's_300-400',
                    'link_id': 's_300-400',
                    'RequestedTime': base_time + timedelta(minutes=i*15),
                    'Timestamp': base_time + timedelta(minutes=i*15),
                    'is_valid': True,
                    'valid_code': 0,
                    'polyline': 'valid_polyline',
                    'RouteAlternative': 1,
                    'hausdorff_distance': 2.0,
                    'DataID': f'data_valid_{i}',
                    'SegmentID': 'segment_valid',
                    'Duration': 250.0,
                    'Distance': 800.0,
                    'Speed': 60.0,
                })

        # Another link with gaps
        for i in [0, 3]:  # Missing i=1,2
            validation_data.append({
                'Name': 's_400-500',
                'link_id': 's_400-500',
                'RequestedTime': base_time + timedelta(minutes=i*15),
                'Timestamp': base_time + timedelta(minutes=i*15),
                'is_valid': True,
                'valid_code': 0,
                'polyline': 'another_valid_polyline',
                'RouteAlternative': 1,
                'hausdorff_distance': 1.5,
                'DataID': f'data_valid2_{i}',
                'SegmentID': 'segment_valid2',
                'Duration': 200.0,
                'Distance': 600.0,
                'Speed': 70.0,
            })

        result_df = pd.DataFrame(validation_data)

        # Create shapefile with additional links (some not in CSV)
        from shapely.geometry import LineString

        shapefile_data = []
        geometries = []

        link_configs = [
            (100, 201, 'Link with code 1 failure'),
            (100, 202, 'Link with code 2 failure'),
            (100, 203, 'Link with code 3 failure'),
            (300, 400, 'Link with valid data and gaps'),
            (400, 500, 'Another link with gaps'),
            (500, 600, 'No data link 1'),  # Not in CSV
            (600, 700, 'No data link 2'),  # Not in CSV
        ]

        for i, (from_id, to_id, desc) in enumerate(link_configs):
            shapefile_data.append({
                'From': from_id,
                'To': to_id,
                'Description': desc
            })
            # Create simple line geometries
            geometries.append(LineString([(i, i), (i+1, i+1)]))

        report_gdf = gpd.GeoDataFrame(shapefile_data, geometry=geometries)

        return result_df, report_gdf, base_time

    def test_1_file_separation_with_completeness(self):
        """Test file separation when completeness analysis is ENABLED"""
        result_df, report_gdf, base_time = self.create_comprehensive_test_data()

        # Enable completeness analysis
        completeness_params = {
            'start_date': base_time.date(),
            'end_date': base_time.date(),
            'interval_minutes': 15
        }

        try:
            # Run complete save_validation_results workflow
            output_files = save_validation_results(
                result_df=result_df,
                report_gdf=report_gdf,
                output_dir=str(self.output_dir),
                generate_shapefile=False,  # Skip shapefile for now
                completeness_params=completeness_params
            )

            # Check that all expected files were generated
            expected_files = [
                'validated_csv',
                'best_valid_observations_csv',
                'failed_observations_csv',
                'missing_observations_csv',  # Should be generated because completeness enabled
                'no_data_links_csv',
                'link_report_csv'
            ]

            missing_files = []
            for file_key in expected_files:
                if file_key not in output_files:
                    missing_files.append(file_key)

            if missing_files:
                self.log_test("File generation with completeness", False,
                             f"Missing files: {missing_files}")
                return

            # Verify file contents
            # 1. Failed observations should only have codes 1-3
            failed_path = Path(output_files['failed_observations_csv'])
            failed_df = pd.read_csv(failed_path)

            if not failed_df.empty:
                failed_codes = set(failed_df['valid_code'].unique())
                expected_failed_codes = {1, 2, 3}
                if not failed_codes.issubset(expected_failed_codes):
                    self.log_test("Failed observations content", False,
                                 f"Expected codes ⊆ {expected_failed_codes}, got {failed_codes}")
                    return

            # 2. Missing observations should only have code 94
            missing_path = Path(output_files['missing_observations_csv'])
            missing_df = pd.read_csv(missing_path)

            if not missing_df.empty:
                missing_codes = set(missing_df['valid_code'].unique())
                if missing_codes != {94}:
                    self.log_test("Missing observations content", False,
                                 f"Expected {{94}}, got {missing_codes}")
                    return

                # Should have RequestedTime column
                if 'RequestedTime' not in missing_df.columns:
                    self.log_test("Missing observations RequestedTime", False,
                                 "RequestedTime column missing from missing observations")
                    return

            # 3. No-data links should only have code 95
            no_data_path = Path(output_files['no_data_links_csv'])
            no_data_df = pd.read_csv(no_data_path)

            if not no_data_df.empty:
                no_data_codes = set(no_data_df['valid_code'].unique())
                if no_data_codes != {95}:
                    self.log_test("No-data links content", False,
                                 f"Expected {{95}}, got {no_data_codes}")
                    return

            self.log_test("File separation with completeness", True,
                         "All files generated correctly with completeness analysis enabled")

        except Exception as e:
            self.log_test("File separation with completeness", False, f"Exception: {e}")

    def test_2_file_separation_without_completeness(self):
        """Test file separation when completeness analysis is DISABLED"""
        result_df, report_gdf, base_time = self.create_comprehensive_test_data()

        # Disable completeness analysis (None)
        completeness_params = None

        try:
            # Create output directory
            no_completeness_dir = Path(str(self.output_dir) + "_no_completeness")
            no_completeness_dir.mkdir(parents=True, exist_ok=True)

            # Run save_validation_results without completeness
            output_files = save_validation_results(
                result_df=result_df,
                report_gdf=report_gdf,
                output_dir=str(no_completeness_dir),
                generate_shapefile=False,
                completeness_params=completeness_params
            )

            # Missing observations file should NOT be generated
            if 'missing_observations_csv' in output_files:
                self.log_test("No missing obs when completeness disabled", False,
                             "Missing observations file generated when completeness disabled")
                return

            # Other files should still be generated
            expected_files = [
                'validated_csv',
                'best_valid_observations_csv',
                'failed_observations_csv',
                'no_data_links_csv',
                'link_report_csv'
            ]

            missing_files = []
            for file_key in expected_files:
                if file_key not in output_files:
                    missing_files.append(file_key)

            if missing_files:
                self.log_test("File generation without completeness", False,
                             f"Missing files: {missing_files}")
                return

            self.log_test("File separation without completeness", True,
                         "Correct files generated when completeness analysis disabled")

        except Exception as e:
            self.log_test("File separation without completeness", False, f"Exception: {e}")

    def test_3_shapefile_generation_workflow(self):
        """Test complete shapefile generation workflow"""
        result_df, report_gdf, base_time = self.create_comprehensive_test_data()

        completeness_params = {
            'start_date': base_time.date(),
            'end_date': base_time.date(),
            'interval_minutes': 15
        }

        try:
            # Create output directory
            shapefiles_dir = Path(str(self.output_dir) + "_shapefiles")
            shapefiles_dir.mkdir(parents=True, exist_ok=True)

            # Run with shapefile generation enabled
            output_files = save_validation_results(
                result_df=result_df,
                report_gdf=report_gdf,
                output_dir=str(shapefiles_dir),
                generate_shapefile=True,  # Enable shapefile generation
                completeness_params=completeness_params
            )

            # Check for shapefile ZIP files
            expected_shapefile_keys = [
                'link_report_zip',
                'failed_observations_zip',  # Should be generated if failed observations exist
                'missing_observations_zip',  # Should be generated if missing observations exist
                'no_data_links_zip',  # Should be generated if no-data links exist
            ]

            generated_shapefiles = []
            for key in expected_shapefile_keys:
                if key in output_files:
                    shapefile_path = Path(output_files[key])
                    if shapefile_path.exists():
                        generated_shapefiles.append(key)

            if len(generated_shapefiles) == 0:
                self.log_test("Shapefile generation", False, "No shapefiles generated")
                return

            self.log_test("Shapefile generation workflow", True,
                         f"Generated shapefiles: {generated_shapefiles}")

        except Exception as e:
            self.log_test("Shapefile generation workflow", False, f"Exception: {e}")

    def test_4_data_consistency_across_files(self):
        """Test that data is consistent across different output files"""
        result_df, report_gdf, base_time = self.create_comprehensive_test_data()

        completeness_params = {
            'start_date': base_time.date(),
            'end_date': base_time.date(),
            'interval_minutes': 15
        }

        try:
            # Create output directory
            consistency_dir = Path(str(self.output_dir) + "_consistency")
            consistency_dir.mkdir(parents=True, exist_ok=True)

            output_files = save_validation_results(
                result_df=result_df,
                report_gdf=report_gdf,
                output_dir=str(consistency_dir),
                generate_shapefile=False,
                completeness_params=completeness_params
            )

            # Load all CSV files
            validated_df = pd.read_csv(output_files['validated_csv'])
            failed_df = pd.read_csv(output_files['failed_observations_csv'])
            missing_df = pd.read_csv(output_files['missing_observations_csv'])
            no_data_df = pd.read_csv(output_files['no_data_links_csv'])

            # Check no overlap in link+timestamp combinations between files
            # (except for validated_data.csv which contains everything)

            # Get identifiers from each file
            failed_ids = set()
            if not failed_df.empty:
                failed_ids = set(zip(failed_df.get('Name', []), failed_df.get('Timestamp', failed_df.get('RequestedTime', []))))

            missing_ids = set()
            if not missing_df.empty:
                missing_ids = set(zip(missing_df.get('Name', []), missing_df.get('RequestedTime', [])))

            no_data_ids = set()
            if not no_data_df.empty:
                no_data_ids = set(no_data_df.get('Name', []))

            # Check for overlaps (there shouldn't be any)
            if failed_ids & missing_ids:
                self.log_test("Data consistency", False,
                             f"Overlap between failed and missing: {len(failed_ids & missing_ids)}")
                return

            # Verify code distribution
            all_codes = set()
            if not failed_df.empty:
                all_codes.update(failed_df['valid_code'].unique())
            if not missing_df.empty:
                all_codes.update(missing_df['valid_code'].unique())
            if not no_data_df.empty:
                all_codes.update(no_data_df['valid_code'].unique())

            expected_codes = {1, 2, 3, 94, 95}
            if not expected_codes.issubset(all_codes):
                missing_codes = expected_codes - all_codes
                self.log_test("Data consistency", False,
                             f"Missing expected codes: {missing_codes}")
                return

            self.log_test("Data consistency across files", True,
                         "All files have consistent, non-overlapping data")

        except Exception as e:
            self.log_test("Data consistency across files", False, f"Exception: {e}")

    def run_all_tests(self):
        """Run all integration tests"""
        print("Running Complete Workflow Integration Tests")
        print("=" * 60)

        try:
            self.test_1_file_separation_with_completeness()
            self.test_2_file_separation_without_completeness()
            self.test_3_shapefile_generation_workflow()
            self.test_4_data_consistency_across_files()

        finally:
            self.cleanup()

        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)

        passed = sum(1 for r in self.test_results if r['passed'])
        total = len(self.test_results)

        for result in self.test_results:
            status = "PASS" if result['passed'] else "FAIL"
            print(f"{status}: {result['test']}")
            if result['message']:
                print(f"   -> {result['message']}")

        print(f"\nResults: {passed}/{total} tests passed ({passed/total*100:.1f}%)")

        if passed == total:
            print("All integration tests passed! Complete workflow is working correctly.")
            return True
        else:
            print("Some integration tests failed. Review the complete workflow.")
            return False


def main():
    """Run the complete workflow integration tests"""
    tester = TestCompleteWorkflowIntegration()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())