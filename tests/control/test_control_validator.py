"""
Tests for control_validator module - Row-level validation logic.

These tests must be written first and must fail before implementation.
"""

import pytest
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString, Point
from datetime import datetime
from unittest.mock import Mock

# Import the functions we're testing (will fail until implemented)
from components.control.validator import (
    parse_link_name,
    decode_polyline,
    calculate_hausdorff,
    check_length_similarity,
    calculate_coverage,
    validate_row,
    ValidationParameters,
    ValidCode
)


class TestParseLinkName:
    """Test parse_link_name function with various input formats."""

    def test_parse_standard_format(self):
        """Test parsing standard s_from-to format."""
        from_id, to_id = parse_link_name("s_653-655")
        assert from_id == "653"
        assert to_id == "655"

    def test_parse_underscore_format(self):
        """Test parsing s_from_to format with underscore."""
        from_id, to_id = parse_link_name("s_653_655")
        assert from_id == "653"
        assert to_id == "655"

    def test_parse_mixed_case(self):
        """Test parsing with mixed case S instead of s."""
        from_id, to_id = parse_link_name("S_653-655")
        assert from_id == "653"
        assert to_id == "655"

    def test_parse_no_prefix(self):
        """Test parsing without s prefix."""
        from_id, to_id = parse_link_name("653-655")
        assert from_id == "653"
        assert to_id == "655"

    def test_parse_leading_zeros(self):
        """Test that leading zeros are preserved."""
        from_id, to_id = parse_link_name("s_053-655")
        assert from_id == "053"
        assert to_id == "655"

    def test_parse_failure_invalid_format(self):
        """Test parsing fails with invalid format."""
        from_id, to_id = parse_link_name("invalid_format")
        assert from_id is None
        assert to_id is None

    def test_parse_failure_empty_string(self):
        """Test parsing fails with empty string."""
        from_id, to_id = parse_link_name("")
        assert from_id is None
        assert to_id is None

    def test_parse_failure_none_input(self):
        """Test parsing fails with None input."""
        from_id, to_id = parse_link_name(None)
        assert from_id is None
        assert to_id is None


class TestDecodePolyline:
    """Test decode_polyline function with various encoded polylines."""

    def test_decode_valid_polyline(self):
        """Test decoding a valid Google Maps polyline."""
        # Simple encoded polyline for a short line
        encoded = "_p~iF~ps|U_ulLnnqC_mqNvxq`@"
        result = decode_polyline(encoded, precision=5)
        assert isinstance(result, LineString)
        assert len(result.coords) > 1

    def test_decode_precision_parameter(self):
        """Test decoding with different precision values."""
        encoded = "_p~iF~ps|U_ulLnnqC_mqNvxq`@"
        result_5 = decode_polyline(encoded, precision=5)
        result_6 = decode_polyline(encoded, precision=6)
        assert isinstance(result_5, LineString)
        assert isinstance(result_6, LineString)

    def test_decode_invalid_polyline(self):
        """Test decoding fails with invalid polyline."""
        result = decode_polyline("invalid_polyline")
        assert result is None

    def test_decode_empty_string(self):
        """Test decoding fails with empty string."""
        result = decode_polyline("")
        assert result is None

    def test_decode_none_input(self):
        """Test decoding fails with None input."""
        result = decode_polyline(None)
        assert result is None


class TestCalculateHausdorff:
    """Test calculate_hausdorff function for distance calculations."""

    def test_identical_lines(self):
        """Test Hausdorff distance for identical lines is zero."""
        line = LineString([(0, 0), (1, 1), (2, 2)])
        distance = calculate_hausdorff(line, line)
        assert distance == 0.0

    def test_parallel_lines(self):
        """Test Hausdorff distance for parallel lines."""
        line1 = LineString([(0, 0), (2, 0)])
        line2 = LineString([(0, 1), (2, 1)])
        distance = calculate_hausdorff(line1, line2)
        assert distance > 0
        assert isinstance(distance, float)

    def test_different_crs(self):
        """Test calculation with specified CRS."""
        line1 = LineString([(0, 0), (1, 1)])
        line2 = LineString([(0, 0.1), (1, 1.1)])
        distance = calculate_hausdorff(line1, line2, crs="EPSG:2039")
        assert isinstance(distance, float)
        assert distance >= 0


class TestCheckLengthSimilarity:
    """Test check_length_similarity function with different modes."""

    def test_mode_off(self):
        """Test length check with mode='off' always returns True."""
        line1 = LineString([(0, 0), (1, 0)])
        line2 = LineString([(0, 0), (2, 0)])
        params = ValidationParameters(length_check_mode="off")
        result = check_length_similarity(line1, line2, "off", params)
        assert result is True

    def test_mode_ratio_within_tolerance(self):
        """Test ratio mode with lengths within tolerance."""
        line1 = LineString([(0, 0), (1, 0)])  # length = 1
        line2 = LineString([(0, 0), (0.95, 0)])  # length = 0.95
        params = ValidationParameters(
            length_ratio_min=0.90,
            length_ratio_max=1.10
        )
        result = check_length_similarity(line1, line2, "ratio", params)
        assert result is True

    def test_mode_ratio_outside_tolerance(self):
        """Test ratio mode with lengths outside tolerance."""
        line1 = LineString([(0, 0), (1, 0)])  # length = 1
        line2 = LineString([(0, 0), (2, 0)])  # length = 2
        params = ValidationParameters(
            length_ratio_min=0.90,
            length_ratio_max=1.10
        )
        result = check_length_similarity(line1, line2, "ratio", params)
        assert result is False

    def test_mode_exact_within_epsilon(self):
        """Test exact mode with lengths within epsilon."""
        line1 = LineString([(0, 0), (1, 0)])
        line2 = LineString([(0, 0), (1.001, 0)])  # Very close
        params = ValidationParameters(epsilon_length_m=0.5)
        result = check_length_similarity(line1, line2, "exact", params)
        assert result is True

    def test_mode_exact_outside_epsilon(self):
        """Test exact mode with lengths outside epsilon."""
        line1 = LineString([(0, 0), (1, 0)])
        line2 = LineString([(0, 0), (2, 0)])  # Too different
        params = ValidationParameters(epsilon_length_m=0.5)
        result = check_length_similarity(line1, line2, "exact", params)
        assert result is False


class TestCalculateCoverage:
    """Test calculate_coverage function for overlap calculation."""

    def test_perfect_overlap(self):
        """Test coverage calculation with perfect overlap."""
        line1 = LineString([(0, 0), (1, 0)])
        line2 = LineString([(0, 0), (1, 0)])
        coverage = calculate_coverage(line1, line2, spacing=0.1)
        assert coverage == pytest.approx(1.0, rel=0.1)

    def test_partial_overlap(self):
        """Test coverage calculation with partial overlap."""
        polyline = LineString([(0, 0), (0.5, 0)])  # Half length
        reference = LineString([(0, 0), (1, 0)])
        coverage = calculate_coverage(polyline, reference, spacing=0.1)
        assert 0.4 < coverage < 0.6  # Approximately 50%

    def test_no_overlap(self):
        """Test coverage calculation with no overlap."""
        polyline = LineString([(2, 0), (3, 0)])  # Separate line
        reference = LineString([(0, 0), (1, 0)])
        coverage = calculate_coverage(polyline, reference, spacing=0.1)
        assert coverage < 0.1  # Minimal coverage

    def test_different_spacing(self):
        """Test coverage with different spacing parameters."""
        line1 = LineString([(0, 0), (1, 0)])
        line2 = LineString([(0, 0), (1, 0)])
        coverage_fine = calculate_coverage(line1, line2, spacing=0.1)
        coverage_coarse = calculate_coverage(line1, line2, spacing=0.5)
        # Both should be close to 1.0 for perfect overlap
        assert abs(coverage_fine - coverage_coarse) < 0.2


class TestValidateRow:
    """Test validate_row function with various scenarios."""

    def setup_method(self):
        """Set up test data for validate_row tests."""
        # Create a simple test shapefile
        self.shapefile_gdf = gpd.GeoDataFrame({
            'Id': ['1', '2'],
            'From': ['653', '655'],
            'To': ['655', '657'],
            'geometry': [
                LineString([(0, 0), (1, 1)]),
                LineString([(1, 1), (2, 2)])
            ]
        })
        self.params = ValidationParameters()

    def test_valid_code_90_missing_fields(self):
        """Test validation returns code 90 for missing required fields."""
        row = pd.Series({
            'name': 's_653-655',
            # Missing polyline and route_alternative
        })
        is_valid, valid_code = validate_row(row, self.shapefile_gdf, self.params)
        assert is_valid is False
        assert valid_code == ValidCode.REQUIRED_FIELDS_MISSING

    def test_valid_code_91_name_parse_failure(self):
        """Test validation returns code 91 for name parse failure."""
        row = pd.Series({
            'name': 'invalid_name_format',
            'polyline': '_p~iF~ps|U_ulLnnqC_mqNvxq`@',
            'route_alternative': 1
        })
        is_valid, valid_code = validate_row(row, self.shapefile_gdf, self.params)
        assert is_valid is False
        assert valid_code == ValidCode.NAME_PARSE_FAILURE

    def test_valid_code_92_link_not_in_shapefile(self):
        """Test validation returns code 92 for link not in shapefile."""
        row = pd.Series({
            'name': 's_999-888',  # Not in shapefile
            'polyline': '_p~iF~ps|U_ulLnnqC_mqNvxq`@',
            'route_alternative': 1
        })
        is_valid, valid_code = validate_row(row, self.shapefile_gdf, self.params)
        assert is_valid is False
        assert valid_code == ValidCode.LINK_NOT_IN_SHAPEFILE

    def test_valid_code_93_polyline_decode_failure(self):
        """Test validation returns code 93 for polyline decode failure."""
        row = pd.Series({
            'name': 's_653-655',
            'polyline': 'invalid_polyline',
            'route_alternative': 1
        })
        is_valid, valid_code = validate_row(row, self.shapefile_gdf, self.params)
        assert is_valid is False
        assert valid_code == ValidCode.POLYLINE_DECODE_FAILURE


# These tests will fail until implementation is complete
if __name__ == "__main__":
    pytest.main([__file__])