"""
Tests for no_data_links functionality to ensure files are always created.
"""

import pytest
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString

from components.control.report import extract_no_data_links


class TestNoDataLinks:
    """Test that no_data_links is always created even when empty."""

    def test_empty_no_data_links_returns_proper_structure(self):
        """Test that extract_no_data_links returns DataFrame with proper structure even when all links have data."""
        # Create validated data where all shapefile links have data
        validated_df = pd.DataFrame({
            'Name': ['s_653-655', 's_655-657'],
            'link_id': ['s_653-655', 's_655-657'],
            'timestamp': ['2025-01-01 10:00', '2025-01-01 11:00'],
            'is_valid': [True, True],
            'valid_code': [2, 2]
        })

        # Create shapefile with the same links
        shapefile_gdf = gpd.GeoDataFrame({
            'Id': ['1', '2'],
            'From': ['653', '655'],
            'To': ['655', '657'],
            'geometry': [
                LineString([(0, 0), (1, 1)]),
                LineString([(1, 1), (2, 2)])
            ]
        })

        # Extract no-data links - should be empty but with proper structure
        result = extract_no_data_links(validated_df, shapefile_gdf)

        # Should return empty DataFrame with expected columns
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0  # No missing links

        # Check expected columns are present
        expected_columns = ['Name', 'link_id', 'timestamp', 'is_valid', 'valid_code',
                          'hausdorff_distance', 'hausdorff_pass']
        for col in expected_columns:
            assert col in result.columns

    def test_no_data_links_with_missing_links(self):
        """Test that extract_no_data_links properly identifies missing links."""
        # Create validated data with only one link
        validated_df = pd.DataFrame({
            'Name': ['s_653-655'],
            'link_id': ['s_653-655'],
            'timestamp': ['2025-01-01 10:00'],
            'is_valid': [True],
            'valid_code': [2],
            'RouteAlternative': [1],
            'polyline': ['encoded_poly'],
            'SegmentID': ['123'],
            'DataID': ['001']
        })

        # Create shapefile with two links
        shapefile_gdf = gpd.GeoDataFrame({
            'Id': ['1', '2'],
            'From': ['653', '655'],
            'To': ['655', '657'],
            'geometry': [
                LineString([(0, 0), (1, 1)]),
                LineString([(1, 1), (2, 2)])
            ]
        })

        # Extract no-data links
        result = extract_no_data_links(validated_df, shapefile_gdf)

        # Should identify s_655-657 as missing
        assert len(result) == 1
        assert result.iloc[0]['link_id'] == 's_655-657'
        assert result.iloc[0]['valid_code'] == 95
        assert result.iloc[0]['is_valid'] == False

        # Should include columns from validated_df structure
        assert 'RouteAlternative' in result.columns
        assert 'polyline' in result.columns
        assert 'SegmentID' in result.columns
        assert 'DataID' in result.columns

    def test_empty_inputs(self):
        """Test handling of empty inputs."""
        empty_df = pd.DataFrame()
        empty_gdf = gpd.GeoDataFrame()

        result = extract_no_data_links(empty_df, empty_gdf)

        # Should return empty DataFrame with expected structure
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
        expected_columns = ['Name', 'link_id', 'timestamp', 'is_valid', 'valid_code',
                          'hausdorff_distance', 'hausdorff_pass']
        for col in expected_columns:
            assert col in result.columns