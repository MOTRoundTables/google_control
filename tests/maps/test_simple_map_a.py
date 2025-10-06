"""
Tests for simple Map A implementation.
"""

import pytest
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString
from datetime import datetime
import streamlit as st
from unittest.mock import Mock, patch


@pytest.fixture
def sample_hourly_data():
    """Create sample hourly data for testing."""
    return pd.DataFrame({
        'link_id': ['s_1-2', 's_2-3', 's_1-2'],
        'date': ['2025-01-01', '2025-01-01', '2025-01-02'],
        'hour': [8, 8, 8],
        'avg_duration_sec': [180, 240, 200],
        'avg_speed_kmh': [50, 40, 45],
        'avg_static_dur': [150, 200, 180],
        'avg_dist': [2500, 2000, 2500]
    })


@pytest.fixture
def sample_shapefile():
    """Create sample shapefile for testing."""
    gdf = gpd.GeoDataFrame({
        'From': ['1', '2'],
        'To': ['2', '3'],
        'geometry': [
            LineString([(34.8, 31.5), (34.81, 31.51)]),
            LineString([(34.81, 31.51), (34.82, 31.52)])
        ]
    }, crs='EPSG:2039')

    return gdf


class TestSimpleMapA:
    """Test cases for simple Map A implementation."""

    def test_map_a_data_filtering(self, sample_hourly_data, sample_shapefile):
        """Test that Map A correctly filters data by date and hour."""
        # Filter for specific date and hour
        selected_date = '2025-01-01'
        selected_hour = 8

        df_filtered = sample_hourly_data[
            (sample_hourly_data['date'] == selected_date) &
            (sample_hourly_data['hour'] == selected_hour)
        ]

        assert len(df_filtered) == 2
        assert all(df_filtered['date'] == selected_date)
        assert all(df_filtered['hour'] == selected_hour)

    def test_map_a_data_join(self, sample_hourly_data, sample_shapefile):
        """Test that Map A correctly joins data with shapefile."""
        # Add link_id to shapefile
        gdf = sample_shapefile.copy()
        gdf['link_id'] = gdf.apply(lambda row: f"s_{row['From']}-{row['To']}", axis=1)

        # Filter data
        df_filtered = sample_hourly_data[sample_hourly_data['date'] == '2025-01-01']

        # Join
        gdf_joined = gdf.merge(df_filtered, on='link_id', how='inner')

        assert len(gdf_joined) == 2
        assert 'avg_duration_sec' in gdf_joined.columns
        assert 'geometry' in gdf_joined.columns

    def test_map_a_color_assignment_duration(self, sample_hourly_data):
        """Test color assignment for duration metric."""
        import numpy as np

        df = sample_hourly_data.copy()
        df['duration_min'] = df['avg_duration_sec'] / 60

        # Test duration-based coloring
        durations = df['duration_min'].values
        colors = np.select([durations < 3, durations < 5], ['green', 'orange'], default='red')

        # 180sec=3min should be orange (not < 3)
        # 240sec=4min should be orange
        # 200sec=3.33min should be orange
        assert colors[0] == 'orange'  # 3 min
        assert colors[1] == 'orange'  # 4 min
        assert colors[2] == 'orange'  # 3.33 min

    def test_map_a_color_assignment_speed(self, sample_hourly_data):
        """Test color assignment for speed metric."""
        import numpy as np

        df = sample_hourly_data.copy()

        # Test speed-based coloring
        speeds = df['avg_speed_kmh'].values
        colors = np.select([speeds < 30, speeds < 50], ['red', 'orange'], default='green')

        # 50 km/h should be green (not < 50)
        # 40 km/h should be orange
        # 45 km/h should be orange
        assert colors[0] == 'green'   # 50 km/h
        assert colors[1] == 'orange'  # 40 km/h
        assert colors[2] == 'orange'  # 45 km/h

    def test_map_a_crs_conversion(self, sample_shapefile):
        """Test CRS conversion from EPSG:2039 to EPSG:4326."""
        gdf = sample_shapefile.copy()

        # Convert to WGS84
        gdf_wgs84 = gdf.to_crs('EPSG:4326')

        assert gdf_wgs84.crs.to_string() == 'EPSG:4326'
        assert len(gdf_wgs84) == len(gdf)
        assert gdf_wgs84.geometry.is_valid.all()

    def test_map_a_geojson_serialization(self, sample_shapefile, sample_hourly_data):
        """Test GeoJSON serialization for caching."""
        import json

        # Prepare data
        gdf = sample_shapefile.copy()
        gdf['link_id'] = gdf.apply(lambda row: f"s_{row['From']}-{row['To']}", axis=1)

        df_filtered = sample_hourly_data[sample_hourly_data['date'] == '2025-01-01'].copy()
        df_filtered['duration_min'] = df_filtered['avg_duration_sec'] / 60
        df_filtered['color'] = 'green'

        gdf_joined = gdf.merge(df_filtered, on='link_id', how='inner')
        gdf_display = gpd.GeoDataFrame(gdf_joined, geometry='geometry', crs='EPSG:4326')

        # Convert timestamps to strings
        for col in gdf_display.columns:
            if pd.api.types.is_datetime64_any_dtype(gdf_display[col]):
                gdf_display[col] = gdf_display[col].astype(str)

        # Serialize to GeoJSON
        geojson_str = gdf_display.to_json()
        geojson_dict = json.loads(geojson_str)

        assert 'type' in geojson_dict
        assert geojson_dict['type'] == 'FeatureCollection'
        assert 'features' in geojson_dict
        assert len(geojson_dict['features']) > 0

    def test_map_a_empty_data_handling(self, sample_shapefile):
        """Test handling of empty filtered data."""
        gdf = sample_shapefile.copy()
        gdf['link_id'] = gdf.apply(lambda row: f"s_{row['From']}-{row['To']}", axis=1)

        # Empty dataframe
        df_empty = pd.DataFrame(columns=['link_id', 'date', 'hour', 'avg_duration_sec'])

        # Join should result in empty
        gdf_joined = gdf.merge(df_empty, on='link_id', how='inner')

        assert len(gdf_joined) == 0

    def test_map_a_date_list_generation(self, sample_hourly_data):
        """Test available dates list generation."""
        dates = sorted(sample_hourly_data['date'].unique())

        assert len(dates) == 2
        assert '2025-01-01' in dates
        assert '2025-01-02' in dates

    def test_map_a_cache_key_generation(self):
        """Test cache key generation for map."""
        import hashlib

        selected_date = '2025-01-01'
        selected_hour = 8
        current_metric = 'duration'
        data_length = 100

        map_data_hash = hashlib.md5(
            f'{selected_date}_{selected_hour}_{current_metric}_{data_length}'.encode()
        ).hexdigest()

        assert isinstance(map_data_hash, str)
        assert len(map_data_hash) == 32  # MD5 hash length

        # Same inputs should produce same hash
        map_data_hash2 = hashlib.md5(
            f'{selected_date}_{selected_hour}_{current_metric}_{data_length}'.encode()
        ).hexdigest()

        assert map_data_hash == map_data_hash2

        # Different inputs should produce different hash
        map_data_hash3 = hashlib.md5(
            f'{selected_date}_{selected_hour}_speed_{data_length}'.encode()
        ).hexdigest()

        assert map_data_hash != map_data_hash3


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
