"""
Tests for control_report module - Link-level reporting and shapefile generation.

These tests must be written first and must fail before implementation.
"""

import pytest
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString
from datetime import date
import tempfile
import os

# Import the functions we're testing (will fail until implemented)
from components.control.report import (
    deduplicate_observations,
    aggregate_link_statistics,
    determine_result_code,
    generate_link_report,
    write_shapefile_with_results,
    ResultCode
)


class TestDeduplicateObservations:
    """Test deduplicate_observations function."""

    def test_no_duplicates(self):
        """Test that data without duplicates remains unchanged."""
        df = pd.DataFrame({
            'link_id': ['s_653-655', 's_655-657'],
            'timestamp': ['2025-01-01 10:00:00', '2025-01-01 10:05:00'],
            'polyline': ['poly1', 'poly2'],
            'is_valid': [True, False]
        })
        result = deduplicate_observations(df)
        assert len(result) == 2
        assert list(result['link_id']) == ['s_653-655', 's_655-657']

    def test_exact_duplicates(self):
        """Test removal of exact duplicates by link_id + timestamp + polyline."""
        df = pd.DataFrame({
            'link_id': ['s_653-655', 's_653-655', 's_655-657'],
            'timestamp': ['2025-01-01 10:00:00', '2025-01-01 10:00:00', '2025-01-01 10:05:00'],
            'polyline': ['poly1', 'poly1', 'poly2'],
            'is_valid': [True, True, False]
        })
        result = deduplicate_observations(df)
        assert len(result) == 2  # One duplicate removed
        assert 's_653-655' in result['link_id'].values
        assert 's_655-657' in result['link_id'].values

    def test_same_timestamp_different_polyline(self):
        """Test that same timestamp with different polyline is kept."""
        df = pd.DataFrame({
            'link_id': ['s_653-655', 's_653-655'],
            'timestamp': ['2025-01-01 10:00:00', '2025-01-01 10:00:00'],
            'polyline': ['poly1', 'poly2'],  # Different polylines
            'is_valid': [True, False]
        })
        result = deduplicate_observations(df)
        assert len(result) == 2  # Both kept


class TestAggregateLinkStatistics:
    """Test aggregate_link_statistics function."""

    def test_single_alternative_all_valid(self):
        """Test aggregation for single alternative with all valid observations."""
        link_data = pd.DataFrame({
            'route_alternative': [1, 1, 1],
            'is_valid': [True, True, True],
            'valid_code': [1, 1, 1]
        })
        stats = aggregate_link_statistics(link_data)
        assert stats['total_observations'] == 3
        assert stats['valid_observations'] == 3
        assert stats['invalid_observations'] == 0
        assert stats['single_alternative_count'] == 3
        assert stats['multi_alternative_count'] == 0

    def test_multiple_alternatives_mixed_validity(self):
        """Test aggregation for multiple alternatives with mixed validity."""
        link_data = pd.DataFrame({
            'route_alternative': [1, 2, 1, 2],
            'is_valid': [True, False, True, True],
            'valid_code': [1, 2, 1, 1]
        })
        stats = aggregate_link_statistics(link_data)
        assert stats['total_observations'] == 4
        assert stats['valid_observations'] == 3
        assert stats['invalid_observations'] == 1
        assert stats['multi_alternative_count'] == 4

    def test_empty_data(self):
        """Test aggregation with empty data."""
        link_data = pd.DataFrame(columns=['route_alternative', 'is_valid', 'valid_code'])
        stats = aggregate_link_statistics(link_data)
        assert stats['total_observations'] == 0
        assert stats['valid_observations'] == 0


class TestDetermineResultCode:
    """Test determine_result_code function for all result codes."""

    def test_result_code_0_all_valid(self):
        """Test result code 0: All observations valid (100%)."""
        stats = {
            'total_observations': 10,
            'valid_observations': 10,
            'invalid_observations': 0,
            'single_alternative_count': 10,
            'multi_alternative_count': 0
        }
        result_code, result_label, num = determine_result_code(stats)
        assert result_code == ResultCode.ALL_VALID
        assert result_label == "valid"
        assert num == 100.0

    def test_result_code_1_single_alt_partial(self):
        """Test result code 1: Single alternative, some invalid."""
        stats = {
            'total_observations': 10,
            'valid_observations': 7,
            'invalid_observations': 3,
            'single_alternative_count': 10,
            'multi_alternative_count': 0
        }
        result_code, result_label, num = determine_result_code(stats)
        assert result_code == ResultCode.SINGLE_ALT_PARTIAL
        assert result_label == "no RouteAlternative"
        assert num == 70.0

    def test_result_code_2_single_alt_all_invalid(self):
        """Test result code 2: Single alternative, all invalid (0%)."""
        stats = {
            'total_observations': 10,
            'valid_observations': 0,
            'invalid_observations': 10,
            'single_alternative_count': 10,
            'multi_alternative_count': 0
        }
        result_code, result_label, num = determine_result_code(stats)
        assert result_code == ResultCode.SINGLE_ALT_ALL_INVALID
        assert result_label == "no RouteAlternative and all invalid"
        assert num == 0.0

    def test_result_code_30_multi_alt_all_valid(self):
        """Test result code 30: Multiple alternatives, all valid (100%)."""
        stats = {
            'total_observations': 10,
            'valid_observations': 10,
            'invalid_observations': 0,
            'single_alternative_count': 0,
            'multi_alternative_count': 10
        }
        result_code, result_label, num = determine_result_code(stats)
        assert result_code == ResultCode.MULTI_ALT_ALL_VALID
        assert result_label == "RouteAlternative greater than one"
        assert num == 100.0

    def test_result_code_31_multi_alt_partial(self):
        """Test result code 31: Multiple alternatives, mixed validity."""
        stats = {
            'total_observations': 10,
            'valid_observations': 6,
            'invalid_observations': 4,
            'single_alternative_count': 0,
            'multi_alternative_count': 10
        }
        result_code, result_label, num = determine_result_code(stats)
        assert result_code == ResultCode.MULTI_ALT_PARTIAL
        assert result_label == "RouteAlternative greater than one"
        assert num == 60.0

    def test_result_code_32_multi_alt_all_invalid(self):
        """Test result code 32: Multiple alternatives, all invalid (0%)."""
        stats = {
            'total_observations': 10,
            'valid_observations': 0,
            'invalid_observations': 10,
            'single_alternative_count': 0,
            'multi_alternative_count': 10
        }
        result_code, result_label, num = determine_result_code(stats)
        assert result_code == ResultCode.MULTI_ALT_ALL_INVALID
        assert result_label == "RouteAlternative greater than one"
        assert num == 0.0

    def test_result_code_41_not_recorded(self):
        """Test result code 41: Link not recorded in dataset."""
        stats = {
            'total_observations': 0,
            'valid_observations': 0,
            'invalid_observations': 0,
            'single_alternative_count': 0,
            'multi_alternative_count': 0
        }
        result_code, result_label, num = determine_result_code(stats)
        assert result_code == ResultCode.NOT_RECORDED
        assert result_label == "did not record"
        assert num is None


class TestGenerateLinkReport:
    """Test generate_link_report function - full pipeline."""

    def setup_method(self):
        """Set up test data for report generation."""
        # Create test validated data
        self.validated_df = pd.DataFrame({
            'link_id': ['s_653-655', 's_653-655', 's_655-657', 's_655-657'],
            'timestamp': ['2025-01-01 10:00:00', '2025-01-01 11:00:00',
                         '2025-01-01 10:00:00', '2025-01-01 11:00:00'],
            'polyline': ['poly1', 'poly2', 'poly3', 'poly4'],
            'route_alternative': [1, 1, 2, 2],
            'is_valid': [True, False, True, True],
            'valid_code': [1, 2, 1, 1]
        })

        # Create test shapefile
        self.shapefile_gdf = gpd.GeoDataFrame({
            'Id': ['1', '2', '3'],
            'From': ['653', '655', '999'],
            'To': ['655', '657', '888'],
            'geometry': [
                LineString([(0, 0), (1, 1)]),
                LineString([(1, 1), (2, 2)]),
                LineString([(3, 3), (4, 4)])  # No data for this link
            ]
        })

    def test_full_report_generation(self):
        """Test full report generation pipeline."""
        report_gdf = generate_link_report(self.validated_df, self.shapefile_gdf)

        # Check that all shapefile links are in report
        assert len(report_gdf) == len(self.shapefile_gdf)

        # Check that result fields were added
        expected_columns = ['result_code', 'result_label', 'num']
        for col in expected_columns:
            assert col in report_gdf.columns

        # Check specific results
        # Link s_653-655: 1 valid, 1 invalid -> result_code 1
        link_653_655 = report_gdf[report_gdf['From'] == '653']
        assert len(link_653_655) == 1
        assert link_653_655.iloc[0]['result_code'] == ResultCode.SINGLE_ALT_PARTIAL

        # Link s_655-657: 2 valid, 0 invalid -> result_code 30
        link_655_657 = report_gdf[report_gdf['From'] == '655']
        assert len(link_655_657) == 1
        assert link_655_657.iloc[0]['result_code'] == ResultCode.MULTI_ALT_ALL_VALID

        # Link s_999-888: no data -> result_code 41
        link_999_888 = report_gdf[report_gdf['From'] == '999']
        assert len(link_999_888) == 1
        assert link_999_888.iloc[0]['result_code'] == ResultCode.NOT_RECORDED

    def test_date_filtering(self):
        """Test report generation with date filtering."""
        date_filter = {
            'start_date': '2025-01-01',
            'end_date': '2025-01-01'
        }
        report_gdf = generate_link_report(
            self.validated_df,
            self.shapefile_gdf,
            date_filter
        )
        assert len(report_gdf) == len(self.shapefile_gdf)

    def test_specific_day_filtering(self):
        """Test report generation for specific day."""
        date_filter = {
            'specific_day': '2025-01-01'
        }
        report_gdf = generate_link_report(
            self.validated_df,
            self.shapefile_gdf,
            date_filter
        )
        assert len(report_gdf) == len(self.shapefile_gdf)


class TestWriteShapefileWithResults:
    """Test write_shapefile_with_results function."""

    def test_write_shapefile(self):
        """Test writing shapefile with results."""
        # Create test GeoDataFrame with results
        gdf = gpd.GeoDataFrame({
            'Id': ['1', '2'],
            'From': ['653', '655'],
            'To': ['655', '657'],
            'result_code': [1, 30],
            'result_label': ['partial', 'all valid'],
            'num': [75.0, 100.0],
            'geometry': [
                LineString([(0, 0), (1, 1)]),
                LineString([(1, 1), (2, 2)])
            ]
        })

        # Write to temporary file
        with tempfile.NamedTemporaryFile(suffix='.shp', delete=False) as tmp:
            output_path = tmp.name

        try:
            write_shapefile_with_results(gdf, output_path)

            # Verify file was created
            assert os.path.exists(output_path)

            # Verify we can read it back
            read_gdf = gpd.read_file(output_path)
            assert len(read_gdf) == 2
            # Verify that only desired fields are kept (From, To, geometry)
            # result_code, result_label, num should have been removed
            assert 'From' in read_gdf.columns
            assert 'To' in read_gdf.columns
            assert 'geometry' in read_gdf.columns
            # These should NOT be in the output (removed as unwanted fields)
            assert 'result_code' not in read_gdf.columns
            assert 'result_labe' not in read_gdf.columns
            assert 'num' not in read_gdf.columns

        finally:
            # Clean up temporary files
            for ext in ['.shp', '.shx', '.dbf', '.prj', '.cpg']:
                temp_file = output_path.replace('.shp', ext)
                if os.path.exists(temp_file):
                    os.unlink(temp_file)

    def test_write_shapefile_io_error(self):
        """Test handling of IO errors during shapefile writing."""
        gdf = gpd.GeoDataFrame({
            'Id': ['1'],
            'geometry': [LineString([(0, 0), (1, 1)])]
        })

        # Try to write to invalid path
        with pytest.raises(Exception):  # Should raise IOError or similar
            write_shapefile_with_results(gdf, "/invalid/path/file.shp")


# These tests will fail until implementation is complete
if __name__ == "__main__":
    pytest.main([__file__])