"""
Integration tests for dataset control and reporting feature.

These tests verify end-to-end functionality with realistic data scenarios.
"""

import pytest
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString
import tempfile
import os
from datetime import date

# Import modules under test (will fail until implemented)
from components.control.validator import validate_row, ValidationParameters
from components.control.report import generate_link_report


class TestProcessSampleCSV:
    """Integration test: Process sample CSV with default parameters."""

    def setup_method(self):
        """Set up test data for integration tests."""
        # Create sample CSV data that mimics real structure
        self.sample_csv_data = pd.DataFrame({
            'DataID': ['001', '002', '003', '004'],
            'Name': ['s_653-655', 's_653-655', 's_655-657', 's_655-657'],
            'SegmentID': ['1185048', '1185048', '1185049', '1185050'],
            'RouteAlternative': [1, 2, 1, 1],
            'RequestedTime': ['13:45:00', '13:50:00', '14:00:00', '14:15:00'],
            'Timestamp': [
                '2025-07-01 13:45:42',
                '2025-07-01 13:50:41',
                '2025-07-01 14:00:12',
                '2025-07-01 14:15:33'
            ],
            'DayInWeek': ['יום ב', 'יום ב', 'יום ב', 'יום ב'],
            'DayType': ['יום חול', 'יום חול', 'יום חול', 'יום חול'],
            'Duration': [2446.0, 2400.0, 1800.0, 2200.0],
            'Distance': [59428.0, 58900.0, 45000.0, 52000.0],
            'Speed': [87.465576, 88.25, 90.0, 85.0],
            'Url': ['https://example.com/1', 'https://example.com/2',
                   'https://example.com/3', 'https://example.com/4'],
            'Polyline': [
                '_oxwD{_wtEoAlCe@vFq@ha@c@~X_@fO',  # Valid encoded polyline
                '_oxwD{_wtEoAlCe@vFq@ha@c@~X_@fP',  # Slightly different
                'bpxwD}_wtEmBlDf@vFr@ha@d@~X_@fO',  # Different route
                'invalid_polyline_data'              # Invalid polyline
            ]
        })

        # Create reference shapefile
        self.reference_shapefile = gpd.GeoDataFrame({
            'Id': ['1', '2'],
            'From': ['653', '655'],
            'To': ['655', '657'],
            'geometry': [
                LineString([(34.8, 32.1), (34.81, 32.11), (34.82, 32.12)]),
                LineString([(34.82, 32.12), (34.83, 32.13), (34.84, 32.14)])
            ]
        }, crs='EPSG:4326')  # WGS84, will be reprojected

        self.default_params = ValidationParameters()

    def test_full_pipeline_with_default_parameters(self):
        """Test complete validation pipeline with default parameters."""
        # Process each row through validation
        validation_results = []

        for idx, row in self.sample_csv_data.iterrows():
            is_valid, valid_code = validate_row(
                row,
                self.reference_shapefile,
                self.default_params
            )
            validation_results.append({
                'is_valid': is_valid,
                'valid_code': valid_code
            })

        # Add validation results to dataframe
        validation_df = pd.DataFrame(validation_results)
        result_df = pd.concat([self.sample_csv_data, validation_df], axis=1)

        # Verify validation results
        assert len(result_df) == 4
        assert 'is_valid' in result_df.columns
        assert 'valid_code' in result_df.columns

        # Generate link report
        report_gdf = generate_link_report(result_df, self.reference_shapefile)

        # Verify report structure
        assert len(report_gdf) >= 2  # At least our reference links
        assert 'result_code' in report_gdf.columns
        assert 'result_label' in report_gdf.columns
        assert 'num' in report_gdf.columns

        # Check that we have results for both reference links
        link_ids = set(f"s_{row['From']}-{row['To']}"
                      for _, row in self.reference_shapefile.iterrows())
        assert len(link_ids) == 2

    def test_validation_code_distribution(self):
        """Test that various validation codes are generated as expected."""
        validation_results = []

        for idx, row in self.sample_csv_data.iterrows():
            is_valid, valid_code = validate_row(
                row,
                self.reference_shapefile,
                self.default_params
            )
            validation_results.append(valid_code)

        # Should have mix of codes
        unique_codes = set(validation_results)
        assert len(unique_codes) > 1  # Should have variety of validation results

        # Last row should fail due to invalid polyline (code 93)
        assert validation_results[-1] == 93  # POLYLINE_DECODE_FAILURE

    def test_report_code_generation(self):
        """Test that report codes are generated correctly."""
        # Create mixed validation scenario with different success patterns per link
        mixed_data = pd.DataFrame({
            'Name': ['s_653-655', 's_653-655', 's_655-657', 's_655-657'],  # Two different links
            'link_id': ['s_653-655', 's_653-655', 's_655-657', 's_655-657'],
            'timestamp': ['2025-01-01 10:00', '2025-01-01 11:00', '2025-01-01 10:00', '2025-01-01 11:00'],
            'is_valid': [True, True, True, False],  # First link: all valid, Second link: partial
            'valid_code': [2, 2, 2, 2]  # Valid context codes
        })

        report_gdf = generate_link_report(mixed_data, self.reference_shapefile)

        # Should have different result codes for the two links
        result_codes = report_gdf['result_code'].unique()
        assert len(result_codes) >= 1  # Should have at least one result code

        # First link should be all valid, second link should be partial
        link_653_655_result = report_gdf[report_gdf['From'] == '653']['result_code'].iloc[0]
        link_655_657_result = report_gdf[report_gdf['From'] == '655']['result_code'].iloc[0]

        # The codes should be different (all valid vs partial)
        assert link_653_655_result != link_655_657_result


class TestDateFiltering:
    """Integration test: Date filtering functionality."""

    def setup_method(self):
        """Set up test data with multiple dates."""
        # Create data spanning multiple dates
        self.multi_date_data = pd.DataFrame({
            'link_id': ['s_653-655'] * 6,
            'timestamp': [
                '2025-07-01 10:00:00',
                '2025-07-01 11:00:00',
                '2025-07-02 10:00:00',
                '2025-07-02 11:00:00',
                '2025-07-03 10:00:00',
                '2025-07-03 11:00:00'
            ],
            'polyline': ['poly1', 'poly2', 'poly3', 'poly4', 'poly5', 'poly6'],
            'route_alternative': [1, 1, 1, 1, 1, 1],
            'is_valid': [True, False, True, True, False, True],
            'valid_code': [1, 2, 1, 1, 2, 1]
        })

        self.reference_shapefile = gpd.GeoDataFrame({
            'Id': ['1'],
            'From': ['653'],
            'To': ['655'],
            'geometry': [LineString([(0, 0), (1, 1)])]
        })

    def test_single_day_filtering(self):
        """Test filtering to a single specific day."""
        date_filter = {'specific_day': '2025-07-01'}

        report_gdf = generate_link_report(
            self.multi_date_data,
            self.reference_shapefile,
            date_filter
        )

        # Should still have shapefile links in report
        assert len(report_gdf) >= 1

        # Verify filtering occurred (would need to check internal logic)
        # This test verifies the function accepts date filtering parameters

    def test_date_range_filtering(self):
        """Test filtering to a date range."""
        date_filter = {
            'start_date': '2025-07-01',
            'end_date': '2025-07-02'
        }

        report_gdf = generate_link_report(
            self.multi_date_data,
            self.reference_shapefile,
            date_filter
        )

        assert len(report_gdf) >= 1

    def test_no_date_filter(self):
        """Test processing without date filtering (all data)."""
        report_gdf = generate_link_report(
            self.multi_date_data,
            self.reference_shapefile
        )

        assert len(report_gdf) >= 1


class TestParameterSensitivity:
    """Integration test: Parameter sensitivity testing."""

    def setup_method(self):
        """Set up test data for parameter testing."""
        self.test_row = pd.Series({
            'Name': 's_653-655',
            'polyline': '_oxwD{_wtEoAlCe@vFq@ha@c@~X_@fO',
            'route_alternative': 1
        })

        self.reference_shapefile = gpd.GeoDataFrame({
            'Id': ['1'],
            'From': ['653'],
            'To': ['655'],
            'geometry': [LineString([(0, 0), (1, 1)])]
        })

    def test_hausdorff_threshold_sensitivity(self):
        """Test validation sensitivity to Hausdorff threshold changes."""
        # Strict threshold
        strict_params = ValidationParameters(hausdorff_threshold_m=1.0)
        strict_valid, strict_code = validate_row(
            self.test_row,
            self.reference_shapefile,
            strict_params
        )

        # Relaxed threshold
        relaxed_params = ValidationParameters(hausdorff_threshold_m=100.0)
        relaxed_valid, relaxed_code = validate_row(
            self.test_row,
            self.reference_shapefile,
            relaxed_params
        )

        # Results might differ based on geometry matching
        # At minimum, function should execute without errors
        assert isinstance(strict_valid, bool)
        assert isinstance(relaxed_valid, bool)
        assert isinstance(strict_code, int)
        assert isinstance(relaxed_code, int)

    def test_length_check_mode_sensitivity(self):
        """Test validation sensitivity to length check mode."""
        # Test different modes
        modes = ['off', 'ratio', 'exact']
        results = []

        for mode in modes:
            params = ValidationParameters(length_check_mode=mode)
            is_valid, valid_code = validate_row(
                self.test_row,
                self.reference_shapefile,
                params
            )
            results.append((is_valid, valid_code))

        # Should execute without errors for all modes
        assert len(results) == 3
        for is_valid, valid_code in results:
            assert isinstance(is_valid, bool)
            assert isinstance(valid_code, int)

    def test_coverage_parameters(self):
        """Test validation sensitivity to coverage parameters."""
        # Strict coverage
        strict_params = ValidationParameters(
            coverage_min=0.95,
            coverage_spacing_m=0.1
        )
        strict_valid, strict_code = validate_row(
            self.test_row,
            self.reference_shapefile,
            strict_params
        )

        # Relaxed coverage
        relaxed_params = ValidationParameters(
            coverage_min=0.5,
            coverage_spacing_m=2.0
        )
        relaxed_valid, relaxed_code = validate_row(
            self.test_row,
            self.reference_shapefile,
            relaxed_params
        )

        # Should execute without errors
        assert isinstance(strict_valid, bool)
        assert isinstance(relaxed_valid, bool)


# These tests will fail until implementation is complete
if __name__ == "__main__":
    pytest.main([__file__])