"""
Tests for map data processing components.

This module tests the DataJoiner, FilterManager, and AggregationEngine classes
for the interactive map visualization feature.
"""

import pytest
import pandas as pd
import geopandas as gpd
from datetime import date, datetime
from shapely.geometry import LineString, Point
import numpy as np

from map_data import DataJoiner, FilterManager, AggregationEngine, MapDataProcessor


class TestDataJoiner:
    """Test cases for DataJoiner class."""
    
    @pytest.fixture
    def sample_shapefile(self):
        """Create sample shapefile GeoDataFrame."""
        data = {
            'Id': [1, 2, 3, 4],
            'From': ['A', 'B', 'C', 'D'],
            'To': ['B', 'C', 'D', 'A'],
            'geometry': [
                LineString([(0, 0), (1, 1)]),
                LineString([(1, 1), (2, 2)]),
                LineString([(2, 2), (3, 3)]),
                LineString([(3, 3), (0, 0)])
            ]
        }
        return gpd.GeoDataFrame(data, crs='EPSG:4326')
    
    @pytest.fixture
    def sample_results(self):
        """Create sample results DataFrame."""
        data = {
            'link_id': ['s_A-B', 's_B-C', 's_C-D', 's_E-F'],  # s_E-F doesn't exist in shapefile
            'date': ['2025-01-01', '2025-01-01', '2025-01-01', '2025-01-01'],
            'hour': [8, 8, 8, 8],
            'avg_duration_sec': [120, 150, 180, 200],
            'avg_speed_kmh': [50, 40, 35, 30],
            'n_valid': [10, 15, 12, 8]
        }
        return pd.DataFrame(data)
    
    def test_join_results_to_shapefile_basic(self, sample_shapefile, sample_results):
        """Test basic join functionality."""
        joiner = DataJoiner()
        result = joiner.join_results_to_shapefile(sample_shapefile, sample_results)
        
        # Check that join_key was created correctly
        expected_keys = ['s_A-B', 's_B-C', 's_C-D', 's_D-A']
        assert list(result['join_key']) == expected_keys
        
        # Check that results were joined correctly
        assert len(result) == 4  # Same as shapefile
        assert 'avg_duration_sec' in result.columns
        assert 'avg_speed_kmh' in result.columns
        
        # Check specific joins
        ab_row = result[result['join_key'] == 's_A-B'].iloc[0]
        assert ab_row['avg_duration_sec'] == 120
        assert ab_row['avg_speed_kmh'] == 50
        
        # Check that unmatched shapefile features have NaN values
        da_row = result[result['join_key'] == 's_D-A'].iloc[0]
        assert pd.isna(da_row['avg_duration_sec'])
    
    def test_join_rule_format(self):
        """Test that join rule follows s_From-To format."""
        joiner = DataJoiner()
        assert joiner.join_rule == "s_{From}-{To}"
    
    def test_validate_joins(self, sample_shapefile, sample_results):
        """Test join validation statistics."""
        joiner = DataJoiner()
        stats = joiner.validate_joins(sample_shapefile, sample_results)
        
        expected_stats = {
            'shapefile_features': 4,
            'results_records': 4,
            'unique_results_links': 4,
            'missing_in_shapefile': 1,  # s_E-F
            'missing_in_results': 1,    # s_D-A
            'successful_joins': 3       # s_A-B, s_B-C, s_C-D
        }
        
        assert stats == expected_stats
    
    def test_get_missing_links(self, sample_shapefile, sample_results):
        """Test identification of missing links."""
        joiner = DataJoiner()
        missing = joiner.get_missing_links(sample_shapefile, sample_results)
        
        assert missing == ['s_E-F']
    
    def test_join_with_numeric_from_to(self):
        """Test join with numeric From/To values."""
        # Create shapefile with numeric From/To
        shapefile_data = {
            'Id': [1, 2],
            'From': [100, 200],
            'To': [200, 300],
            'geometry': [
                LineString([(0, 0), (1, 1)]),
                LineString([(1, 1), (2, 2)])
            ]
        }
        gdf = gpd.GeoDataFrame(shapefile_data, crs='EPSG:4326')
        
        # Create results with corresponding link_ids
        results_data = {
            'link_id': ['s_100-200', 's_200-300'],
            'date': ['2025-01-01', '2025-01-01'],
            'hour': [8, 8],
            'avg_duration_sec': [120, 150],
            'avg_speed_kmh': [50, 40],
            'n_valid': [10, 15]
        }
        results_df = pd.DataFrame(results_data)
        
        joiner = DataJoiner()
        result = joiner.join_results_to_shapefile(gdf, results_df)
        
        # Check join keys are created correctly
        expected_keys = ['s_100-200', 's_200-300']
        assert list(result['join_key']) == expected_keys
        
        # Check all records joined successfully
        assert not result['avg_duration_sec'].isna().any()
    
    def test_join_with_empty_results(self, sample_shapefile):
        """Test join with empty results DataFrame."""
        empty_results = pd.DataFrame(columns=['link_id', 'date', 'hour', 'avg_duration_sec', 'avg_speed_kmh', 'n_valid'])
        
        joiner = DataJoiner()
        result = joiner.join_results_to_shapefile(sample_shapefile, empty_results)
        
        # Should still have all shapefile features
        assert len(result) == 4
        # But all result columns should be NaN
        assert result['avg_duration_sec'].isna().all()
    
    def test_join_preserves_geometry(self, sample_shapefile, sample_results):
        """Test that join preserves geometry column."""
        joiner = DataJoiner()
        result = joiner.join_results_to_shapefile(sample_shapefile, sample_results)
        
        assert isinstance(result, gpd.GeoDataFrame)
        assert 'geometry' in result.columns
        assert len(result.geometry) == len(sample_shapefile)


class TestFilterManager:
    """Test cases for FilterManager class."""
    
    @pytest.fixture
    def sample_hourly_data(self):
        """Create sample hourly data for filtering tests."""
        dates = ['2025-01-01', '2025-01-02', '2025-01-03'] * 8
        hours = [8, 9, 10, 11, 12, 13, 14, 15] * 3
        
        data = {
            'link_id': ['s_A-B'] * 24,
            'date': dates,
            'hour': hours,
            'avg_duration_sec': np.random.randint(60, 300, 24),
            'avg_speed_kmh': np.random.randint(20, 80, 24),
            'length_m': [1000] * 24,
            'n_valid': np.random.randint(5, 20, 24)
        }
        return pd.DataFrame(data)
    
    def test_apply_temporal_filters_date_range(self, sample_hourly_data):
        """Test temporal filtering by date range."""
        filter_manager = FilterManager()
        
        # Filter to single date
        filtered = filter_manager.apply_temporal_filters(
            sample_hourly_data,
            date_range=(date(2025, 1, 2), date(2025, 1, 2))
        )
        
        assert len(filtered) == 8  # 8 hours for one date
        assert all(filtered['date'] == '2025-01-02')
    
    def test_apply_temporal_filters_hour_range(self, sample_hourly_data):
        """Test temporal filtering by hour range."""
        filter_manager = FilterManager()
        
        # Filter to morning hours
        filtered = filter_manager.apply_temporal_filters(
            sample_hourly_data,
            hour_range=(8, 10)
        )
        
        expected_hours = [8, 9, 10]
        assert len(filtered) == 9  # 3 hours * 3 dates
        assert set(filtered['hour'].unique()) == set(expected_hours)
    
    def test_apply_temporal_filters_combined(self, sample_hourly_data):
        """Test combined date and hour filtering."""
        filter_manager = FilterManager()
        
        filtered = filter_manager.apply_temporal_filters(
            sample_hourly_data,
            date_range=(date(2025, 1, 1), date(2025, 1, 2)),
            hour_range=(9, 11)
        )
        
        assert len(filtered) == 6  # 3 hours * 2 dates
        assert set(filtered['date'].unique()) == {'2025-01-01', '2025-01-02'}
        assert set(filtered['hour'].unique()) == {9, 10, 11}
    
    def test_apply_attribute_filters_above(self, sample_hourly_data):
        """Test attribute filtering with 'above' operator."""
        filter_manager = FilterManager()
        
        # Set some known values for testing
        sample_hourly_data.loc[0, 'avg_speed_kmh'] = 60
        sample_hourly_data.loc[1, 'avg_speed_kmh'] = 40
        
        filters = {'avg_speed_kmh': {'operator': 'above', 'value': 50}}
        filtered = filter_manager.apply_attribute_filters(sample_hourly_data, filters)
        
        assert all(filtered['avg_speed_kmh'] > 50)
    
    def test_apply_attribute_filters_below(self, sample_hourly_data):
        """Test attribute filtering with 'below' operator."""
        filter_manager = FilterManager()
        
        filters = {'avg_duration_sec': {'operator': 'below', 'value': 150}}
        filtered = filter_manager.apply_attribute_filters(sample_hourly_data, filters)
        
        assert all(filtered['avg_duration_sec'] < 150)
    
    def test_apply_attribute_filters_between(self, sample_hourly_data):
        """Test attribute filtering with 'between' operator."""
        filter_manager = FilterManager()
        
        filters = {'avg_speed_kmh': {'operator': 'between', 'value': [30, 60]}}
        filtered = filter_manager.apply_attribute_filters(sample_hourly_data, filters)
        
        assert all((filtered['avg_speed_kmh'] >= 30) & (filtered['avg_speed_kmh'] <= 60))
    
    def test_apply_attribute_filters_multiple(self, sample_hourly_data):
        """Test multiple attribute filters."""
        filter_manager = FilterManager()
        
        filters = {
            'avg_speed_kmh': {'operator': 'above', 'value': 30},
            'avg_duration_sec': {'operator': 'below', 'value': 250}
        }
        filtered = filter_manager.apply_attribute_filters(sample_hourly_data, filters)
        
        assert all(filtered['avg_speed_kmh'] > 30)
        assert all(filtered['avg_duration_sec'] < 250)
    
    def test_apply_spatial_filters_no_selection(self):
        """Test spatial filtering with no selection (should return original data)."""
        # Create sample GeoDataFrame
        data = {
            'link_id': ['s_A-B', 's_B-C'],
            'geometry': [
                LineString([(0, 0), (1, 1)]),
                LineString([(1, 1), (2, 2)])
            ]
        }
        gdf = gpd.GeoDataFrame(data, crs='EPSG:4326')
        
        filter_manager = FilterManager()
        result = filter_manager.apply_spatial_filters(gdf, None)
        
        assert len(result) == len(gdf)
        assert result.equals(gdf)


class TestAggregationEngine:
    """Test cases for AggregationEngine class."""
    
    @pytest.fixture
    def sample_multi_day_data(self):
        """Create sample multi-day hourly data for aggregation tests."""
        data = []
        for day in range(1, 8):  # 7 days
            for hour in [8, 9, 10]:  # 3 hours
                data.append({
                    'link_id': 's_A-B',
                    'date': f'2025-01-{day:02d}',
                    'hour': hour,
                    'avg_duration_sec': 120 + day * 10 + hour,  # Varying values
                    'avg_speed_kmh': 50 - day + hour,
                    'n_valid': 10 + day
                })
        return pd.DataFrame(data)
    
    def test_compute_weekly_aggregation_median(self, sample_multi_day_data):
        """Test weekly aggregation using median."""
        engine = AggregationEngine()
        result = engine.compute_weekly_aggregation(sample_multi_day_data, method='median')
        
        # Should have 3 records (one for each hour)
        assert len(result) == 3
        assert set(result['hour'].unique()) == {8, 9, 10}
        
        # Check that aggregation was performed
        assert 'avg_duration_sec' in result.columns
        assert 'avg_speed_kmh' in result.columns
        assert 'n_valid' in result.columns
        
        # n_valid should be summed (not median)
        hour_8_data = sample_multi_day_data[sample_multi_day_data['hour'] == 8]
        expected_n_valid = hour_8_data['n_valid'].sum()
        actual_n_valid = result[result['hour'] == 8]['n_valid'].iloc[0]
        assert actual_n_valid == expected_n_valid
    
    def test_compute_weekly_aggregation_mean(self, sample_multi_day_data):
        """Test weekly aggregation using mean."""
        engine = AggregationEngine()
        result = engine.compute_weekly_aggregation(sample_multi_day_data, method='mean')
        
        assert len(result) == 3
        
        # Verify mean calculation for hour 8
        hour_8_data = sample_multi_day_data[sample_multi_day_data['hour'] == 8]
        expected_mean_duration = hour_8_data['avg_duration_sec'].mean()
        actual_mean_duration = result[result['hour'] == 8]['avg_duration_sec'].iloc[0]
        assert abs(actual_mean_duration - expected_mean_duration) < 0.01
    
    def test_compute_weekly_aggregation_invalid_method(self, sample_multi_day_data):
        """Test weekly aggregation with invalid method."""
        engine = AggregationEngine()
        
        with pytest.raises(ValueError, match="Method must be one of"):
            engine.compute_weekly_aggregation(sample_multi_day_data, method='invalid')
    
    def test_compute_weekly_aggregation_multiple_links(self):
        """Test weekly aggregation with multiple links."""
        data = []
        for link in ['s_A-B', 's_B-C']:
            for day in range(1, 4):  # 3 days
                for hour in [8, 9]:  # 2 hours
                    data.append({
                        'link_id': link,
                        'date': f'2025-01-{day:02d}',
                        'hour': hour,
                        'avg_duration_sec': 120,
                        'avg_speed_kmh': 50,
                        'n_valid': 10
                    })
        df = pd.DataFrame(data)
        
        engine = AggregationEngine()
        result = engine.compute_weekly_aggregation(df, method='median')
        
        # Should have 4 records (2 links * 2 hours)
        assert len(result) == 4
        assert set(result['link_id'].unique()) == {'s_A-B', 's_B-C'}
        assert set(result['hour'].unique()) == {8, 9}
    
    def test_calculate_date_span_context(self, sample_multi_day_data):
        """Test date span context calculation."""
        engine = AggregationEngine()
        context = engine.calculate_date_span_context(sample_multi_day_data)
        
        expected_context = {
            'start_date': date(2025, 1, 1),
            'end_date': date(2025, 1, 7),
            'n_days': 7,
            'date_range_str': '2025-01-01 to 2025-01-07'
        }
        
        assert context == expected_context
    
    def test_calculate_date_span_context_single_day(self):
        """Test date span context with single day."""
        data = pd.DataFrame({
            'link_id': ['s_A-B'],
            'date': ['2025-01-15'],
            'hour': [8],
            'avg_duration_sec': [120],
            'avg_speed_kmh': [50],
            'n_valid': [10]
        })
        
        engine = AggregationEngine()
        context = engine.calculate_date_span_context(data)
        
        assert context['start_date'] == date(2025, 1, 15)
        assert context['end_date'] == date(2025, 1, 15)
        assert context['n_days'] == 1
        assert context['date_range_str'] == '2025-01-15 to 2025-01-15'


class TestMapDataProcessor:
    """Test cases for MapDataProcessor integration."""
    
    @pytest.fixture
    def sample_shapefile(self):
        """Create sample shapefile GeoDataFrame."""
        data = {
            'Id': [1, 2],
            'From': ['A', 'B'],
            'To': ['B', 'C'],
            'geometry': [
                LineString([(0, 0), (1, 1)]),
                LineString([(1, 1), (2, 2)])
            ]
        }
        return gpd.GeoDataFrame(data, crs='EPSG:4326')
    
    @pytest.fixture
    def sample_results(self):
        """Create sample results DataFrame."""
        data = {
            'link_id': ['s_A-B', 's_B-C'],
            'date': ['2025-01-01', '2025-01-01'],
            'hour': [8, 8],
            'avg_duration_sec': [120, 150],
            'avg_speed_kmh': [50, 40],
            'n_valid': [10, 15]
        }
        return pd.DataFrame(data)
    
    def test_prepare_map_data_no_filters(self, sample_shapefile, sample_results):
        """Test data preparation without filters."""
        processor = MapDataProcessor()
        result = processor.prepare_map_data(sample_shapefile, sample_results)
        
        assert isinstance(result, gpd.GeoDataFrame)
        assert len(result) == 2
        assert 'avg_duration_sec' in result.columns
        assert not result['avg_duration_sec'].isna().any()
    
    def test_prepare_map_data_with_temporal_filters(self, sample_shapefile, sample_results):
        """Test data preparation with temporal filters."""
        # Add more data for filtering
        additional_data = pd.DataFrame({
            'link_id': ['s_A-B', 's_B-C'],
            'date': ['2025-01-02', '2025-01-02'],
            'hour': [9, 9],
            'avg_duration_sec': [130, 160],
            'avg_speed_kmh': [45, 35],
            'n_valid': [12, 18]
        })
        extended_results = pd.concat([sample_results, additional_data], ignore_index=True)
        
        filters = {
            'temporal': {
                'date_range': (date(2025, 1, 1), date(2025, 1, 1)),
                'hour_range': (8, 8)
            }
        }
        
        processor = MapDataProcessor()
        result = processor.prepare_map_data(sample_shapefile, extended_results, filters)
        
        # Should only have data from 2025-01-01 hour 8
        assert len(result) == 2
        # All non-NaN values should be from the filtered data
        non_nan_result = result.dropna(subset=['date'])
        assert all(non_nan_result['date'] == '2025-01-01')
        assert all(non_nan_result['hour'] == 8)
    
    def test_prepare_map_data_with_attribute_filters(self, sample_shapefile, sample_results):
        """Test data preparation with attribute filters."""
        filters = {
            'attributes': {
                'avg_speed_kmh': {'operator': 'above', 'value': 45}
            }
        }
        
        processor = MapDataProcessor()
        result = processor.prepare_map_data(sample_shapefile, sample_results, filters)
        
        # Should only have records with speed > 45
        non_nan_result = result.dropna(subset=['avg_speed_kmh'])
        assert all(non_nan_result['avg_speed_kmh'] > 45)