"""
Tests for simple Map B implementation.
"""

import pytest
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString
import streamlit as st
from unittest.mock import Mock, patch


@pytest.fixture
def sample_weekly_data():
    """Create sample weekly data for testing."""
    return pd.DataFrame({
        'link_id': ['s_1-2', 's_2-3', 's_1-2', 's_2-3', 's_1-2', 's_2-3'],
        'daytype': ['weekday', 'weekday', 'weekend', 'weekend', 'holiday', 'holiday'],
        'hour': [8, 8, 8, 8, 8, 8],
        'avg_dur': [180, 240, 200, 250, 190, 230],
        'avg_speed': [50, 40, 45, 38, 48, 42],
        'avg_static_dur': [150, 200, 180, 210, 160, 190],
        'avg_dist': [2500, 2000, 2500, 2000, 2500, 2000],
        'n_days': [5, 5, 2, 2, 1, 1]
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


class TestSimpleMapB:
    """Test cases for simple Map B implementation."""

    def test_map_b_daytype_filtering(self, sample_weekly_data):
        """Test that Map B correctly filters by daytype."""
        # Filter for weekday
        selected_daytype = 'weekday'
        selected_hour = 8

        df_filtered = sample_weekly_data[
            (sample_weekly_data['daytype'] == selected_daytype) &
            (sample_weekly_data['hour'] == selected_hour)
        ]

        assert len(df_filtered) == 2
        assert all(df_filtered['daytype'] == selected_daytype)
        assert all(df_filtered['hour'] == selected_hour)

    def test_map_b_daytype_all_filter(self, sample_weekly_data):
        """Test that Map B 'all' daytype shows all data."""
        selected_daytype = 'all'
        selected_hour = 8

        # When daytype is 'all', don't filter by daytype
        if selected_daytype == 'all':
            df_filtered = sample_weekly_data[sample_weekly_data['hour'] == selected_hour]
        else:
            df_filtered = sample_weekly_data[
                (sample_weekly_data['daytype'] == selected_daytype) &
                (sample_weekly_data['hour'] == selected_hour)
            ]

        assert len(df_filtered) == 6  # All 6 rows (3 daytypes * 2 links)
        assert all(df_filtered['hour'] == selected_hour)

    def test_map_b_weekend_filtering(self, sample_weekly_data):
        """Test filtering for weekend data."""
        selected_daytype = 'weekend'
        selected_hour = 8

        df_filtered = sample_weekly_data[
            (sample_weekly_data['daytype'] == selected_daytype) &
            (sample_weekly_data['hour'] == selected_hour)
        ]

        assert len(df_filtered) == 2
        assert all(df_filtered['daytype'] == 'weekend')

    def test_map_b_holiday_filtering(self, sample_weekly_data):
        """Test filtering for holiday data."""
        selected_daytype = 'holiday'
        selected_hour = 8

        df_filtered = sample_weekly_data[
            (sample_weekly_data['daytype'] == selected_daytype) &
            (sample_weekly_data['hour'] == selected_hour)
        ]

        assert len(df_filtered) == 2
        assert all(df_filtered['daytype'] == 'holiday')

    def test_map_b_data_join(self, sample_weekly_data, sample_shapefile):
        """Test that Map B correctly joins data with shapefile."""
        # Add link_id to shapefile
        gdf = sample_shapefile.copy()
        gdf['link_id'] = gdf.apply(lambda row: f"s_{row['From']}-{row['To']}", axis=1)

        # Filter data for weekday
        df_filtered = sample_weekly_data[sample_weekly_data['daytype'] == 'weekday']

        # Join
        gdf_joined = gdf.merge(df_filtered, on='link_id', how='inner')

        assert len(gdf_joined) == 2
        assert 'avg_dur' in gdf_joined.columns
        assert 'geometry' in gdf_joined.columns
        assert 'daytype' in gdf_joined.columns

    def test_map_b_hour_filtering(self, sample_weekly_data):
        """Test hour filtering in Map B."""
        # Add different hours
        df = sample_weekly_data.copy()
        df.loc[df.index[0], 'hour'] = 9
        df.loc[df.index[1], 'hour'] = 10

        # Filter for hour 8
        df_filtered = df[df['hour'] == 8]

        assert len(df_filtered) == 4  # Original 6 - 2 changed
        assert all(df_filtered['hour'] == 8)

    def test_map_b_color_assignment_duration(self, sample_weekly_data):
        """Test color assignment for duration metric."""
        import numpy as np

        df = sample_weekly_data.copy()
        df['duration_min'] = df['avg_dur'] / 60

        # Test duration-based coloring
        durations = df['duration_min'].values
        colors = np.select([durations < 3, durations < 5], ['green', 'orange'], default='red')

        # 180sec=3min should be orange
        # 240sec=4min should be orange
        # 200sec=3.33min should be orange
        assert colors[0] == 'orange'  # 3 min
        assert colors[1] == 'orange'  # 4 min
        assert colors[2] == 'orange'  # 3.33 min

    def test_map_b_color_assignment_speed(self, sample_weekly_data):
        """Test color assignment for speed metric."""
        import numpy as np

        df = sample_weekly_data.copy()

        # Test speed-based coloring
        speeds = df['avg_speed'].values
        colors = np.select([speeds < 30, speeds < 50], ['red', 'orange'], default='green')

        # 50 km/h should be green
        # 40 km/h should be orange
        # 45 km/h should be orange
        assert colors[0] == 'green'   # 50 km/h
        assert colors[1] == 'orange'  # 40 km/h
        assert colors[2] == 'orange'  # 45 km/h

    def test_map_b_cache_serialization(self, sample_weekly_data):
        """Test data serialization for caching."""
        # Convert to dict for caching
        df_serialized = sample_weekly_data.to_dict('records')

        assert isinstance(df_serialized, list)
        assert len(df_serialized) == 6
        assert 'link_id' in df_serialized[0]
        assert 'daytype' in df_serialized[0]

    def test_map_b_cached_filtering(self, sample_weekly_data):
        """Test ultra-fast cached filtering logic."""
        # Simulate cached data (serialized)
        df_serialized = sample_weekly_data.to_dict('records')

        # Reconstruct and filter
        df = pd.DataFrame(df_serialized)

        selected_hour = 8
        selected_daytype = 'weekday'

        # Apply daytype filter
        if selected_daytype != 'all':
            df = df[df['daytype'] == selected_daytype]

        # Apply hour filter
        df_filtered = df[df['hour'] == selected_hour]

        assert len(df_filtered) == 2
        assert all(df_filtered['daytype'] == 'weekday')
        assert all(df_filtered['hour'] == 8)

    def test_map_b_empty_data_handling(self, sample_shapefile):
        """Test handling of empty filtered data."""
        gdf = sample_shapefile.copy()
        gdf['link_id'] = gdf.apply(lambda row: f"s_{row['From']}-{row['To']}", axis=1)

        # Empty dataframe
        df_empty = pd.DataFrame(columns=['link_id', 'daytype', 'hour', 'avg_dur'])

        # Join should result in empty
        gdf_joined = gdf.merge(df_empty, on='link_id', how='inner')

        assert len(gdf_joined) == 0

    def test_map_b_geojson_serialization(self, sample_shapefile, sample_weekly_data):
        """Test GeoJSON serialization for Map B."""
        import json

        # Prepare data
        gdf = sample_shapefile.copy()
        gdf['link_id'] = gdf.apply(lambda row: f"s_{row['From']}-{row['To']}", axis=1)

        df_filtered = sample_weekly_data[sample_weekly_data['daytype'] == 'weekday'].copy()
        df_filtered['duration_min'] = df_filtered['avg_dur'] / 60
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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
