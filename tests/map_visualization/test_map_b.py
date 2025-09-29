"""
Tests for Map B (Weekly View) implementation.

This module tests the weekly map interface, aggregation aggregation, 
and interactions for the interactive map visualization feature.
"""

import pytest
import pandas as pd
import geopandas as gpd
import streamlit as st
from datetime import date, timedelta
from unittest.mock import Mock, patch, MagicMock
import numpy as np

# Import the module under test
from map_b_weekly import WeeklyMapInterface, render_map_b_page


class TestWeeklyMapInterface:
    """Test cases for WeeklyMapInterface class."""
    
    @pytest.fixture
    def weekly_interface(self):
        """Create WeeklyMapInterface instance for testing."""
        return WeeklyMapInterface()
    
    @pytest.fixture
    def sample_shapefile_data(self):
        """Create sample shapefile data for testing."""
        from shapely.geometry import LineString
        
        data = {
            'Id': ['link_1', 'link_2', 'link_3'],
            'From': ['A', 'B', 'C'],
            'To': ['B', 'C', 'D'],
            'geometry': [
                LineString([(0, 0), (1, 1)]),
                LineString([(1, 1), (2, 2)]),
                LineString([(2, 2), (3, 3)])
            ]
        }
        
        return gpd.GeoDataFrame(data, crs="EPSG:4326")
    
    @pytest.fixture
    def sample_results_data(self):
        """Create sample results data for testing."""
        dates = [date(2025, 1, 1), date(2025, 1, 2), date(2025, 1, 3)]
        hours = [7, 8, 9, 17, 18, 19]
        
        data = []
        for link_id in ['s_A-B', 's_B-C', 's_C-D']:
            for test_date in dates:
                for hour in hours:
                    data.append({
                        'link_id': link_id,
                        'date': test_date,
                        'hour': hour,
                        'avg_duration_sec': np.random.uniform(300, 1800),  # 5-30 minutes
                        'avg_speed_kmh': np.random.uniform(20, 80),
                        'n_valid': np.random.randint(5, 50),
                        'length_m': np.random.uniform(500, 2000)
                    })
        
        return pd.DataFrame(data)
    
    def test_init(self, weekly_interface):
        """Test WeeklyMapInterface initialization."""
        assert weekly_interface.controls is not None
        assert weekly_interface.renderer is not None
        assert weekly_interface.data_processor is not None
        assert weekly_interface.symbology is not None
    
    @patch('streamlit.title')
    @patch('streamlit.markdown')
    @patch('streamlit.warning')
    def test_render_weekly_map_page_no_data(self, mock_warning, mock_markdown, mock_title, weekly_interface):
        """Test rendering weekly map page with no data."""
        empty_gdf = gpd.GeoDataFrame()
        empty_df = pd.DataFrame()
        
        weekly_interface.render_weekly_map_page(empty_gdf, empty_df)
        
        mock_title.assert_called_once()
        mock_markdown.assert_called_once()
        mock_warning.assert_called_once_with("⚠️ No data available. Please load shapefile and results data first.")
    
    def test_calculate_data_bounds(self, weekly_interface, sample_results_data):
        """Test calculation of data bounds for weekly view."""
        bounds = weekly_interface._calculate_data_bounds(sample_results_data)
        
        # Should have hour bounds but no date bounds
        assert 'min_hour' in bounds
        assert 'max_hour' in bounds
        assert 'min_date' not in bounds  # Weekly view doesn't use dates
        assert 'max_date' not in bounds
        
        # Should have numeric attribute bounds
        assert 'avg_speed_kmh' in bounds
        assert 'avg_duration_sec' in bounds
        assert 'length_m' in bounds
        
        # Check hour bounds
        assert bounds['min_hour'] == 7
        assert bounds['max_hour'] == 19
    
    def test_apply_hour_filters(self, weekly_interface, sample_results_data):
        """Test applying hour filters (no date filters for weekly view)."""
        temporal_filters = {
            'hour_range': (8, 18)
        }
        
        filtered_data = weekly_interface._apply_hour_filters(sample_results_data, temporal_filters)
        
        # Should only include hours 8-18
        assert filtered_data['hour'].min() >= 8
        assert filtered_data['hour'].max() <= 18
        
        # Should have fewer records than original
        assert len(filtered_data) < len(sample_results_data)
    
    def test_apply_attribute_filters(self, weekly_interface, sample_results_data):
        """Test applying attribute filters to aggregated data."""
        attribute_filters = {
            'avg_speed_kmh': {
                'operator': 'above',
                'value': 50.0
            },
            'avg_duration_sec': {
                'operator': 'below',
                'value': 1200.0  # 20 minutes
            }
        }
        
        filtered_data = weekly_interface._apply_attribute_filters(sample_results_data, attribute_filters)
        
        # Should only include records meeting filter criteria
        assert all(filtered_data['avg_speed_kmh'] > 50.0)
        assert all(filtered_data['avg_duration_sec'] < 1200.0)
        
        # Should have fewer records than original
        assert len(filtered_data) <= len(sample_results_data)
    
    def test_apply_attribute_filters_between(self, weekly_interface, sample_results_data):
        """Test applying attribute filters with 'between' operator."""
        attribute_filters = {
            'avg_speed_kmh': {
                'operator': 'between',
                'value': (30.0, 60.0)
            }
        }
        
        filtered_data = weekly_interface._apply_attribute_filters(sample_results_data, attribute_filters)
        
        # Should only include records within range
        assert all(filtered_data['avg_speed_kmh'] >= 30.0)
        assert all(filtered_data['avg_speed_kmh'] <= 60.0)
    
    @patch('streamlit.info')
    def test_display_date_context(self, mock_info, weekly_interface):
        """Test displaying date context for weekly aggregation."""
        date_context = {
            'start_date': date(2025, 1, 1),
            'end_date': date(2025, 1, 31),
            'n_days': 31,
            'date_range_str': '2025-01-01 to 2025-01-31',
            'aggregation_method': 'median'
        }
        
        control_state = {
            'filters': {
                'temporal': {
                    'hour_range': (7, 19)
                }
            }
        }
        
        weekly_interface._display_date_context(date_context, control_state)
        
        # Should display context information
        mock_info.assert_called()
        call_args = mock_info.call_args[0][0]
        assert 'Median aggregation' in call_args
        assert '2025-01-01 to 2025-01-31' in call_args
        assert 'N = 31 days' in call_args
    
    def test_format_active_filters_weekly(self, weekly_interface):
        """Test formatting active filters for weekly view."""
        control_state = {
            'filters': {
                'temporal': {
                    'hour_range': (8, 17)
                },
                'metrics': {
                    'aggregation_method': 'mean'
                },
                'attributes': {
                    'avg_speed_kmh': {
                        'operator': 'above',
                        'value': 40.0
                    }
                }
            }
        }
        
        filters = weekly_interface._format_active_filters(control_state)
        
        # Should include hour range, aggregation method, and attribute filters
        filter_strings = ' '.join(filters)
        assert 'Hours: 8:00-17:00' in filter_strings
        assert 'Aggregation: Mean' in filter_strings
        assert 'Speed above: 40.0 km/h' in filter_strings
    
    def test_format_active_filters_single_hour(self, weekly_interface):
        """Test formatting active filters with single hour."""
        control_state = {
            'filters': {
                'temporal': {
                    'hour_range': (9, 9)
                },
                'metrics': {
                    'aggregation_method': 'median'
                }
            }
        }
        
        filters = weekly_interface._format_active_filters(control_state)
        
        # Should show single hour format
        filter_strings = ' '.join(filters)
        assert 'Hour: 9:00' in filter_strings
    
    @patch('streamlit.metric')
    @patch('streamlit.subheader')
    def test_display_map_statistics(self, mock_subheader, mock_metric, weekly_interface):
        """Test displaying map statistics for weekly view."""
        # Create sample data with required columns
        data = {
            'Id': ['link_1', 'link_2'],
            'avg_duration_min': [15.5, 22.3],
            'avg_speed_kmh': [45.2, 38.7],
            'n_valid': [25, 18],
            'length_m': [1200, 1800],
            'geometry': [None, None]  # Placeholder
        }
        
        sample_data = gpd.GeoDataFrame(data)
        
        control_state = {
            'filters': {
                'metrics': {
                    'metric_type': 'duration',
                    'aggregation_method': 'median'
                }
            }
        }
        
        date_context = {
            'n_days': 15,
            'aggregation_method': 'median'
        }
        
        weekly_interface._display_map_statistics(sample_data, control_state, date_context)
        
        # Should display statistics
        mock_subheader.assert_called_with("📊 Map Statistics")
        assert mock_metric.call_count >= 3  # At least 3 metrics displayed
    
    @patch('streamlit.warning')
    def test_display_map_statistics_empty_data(self, mock_warning, weekly_interface):
        """Test displaying map statistics with empty data."""
        empty_data = gpd.GeoDataFrame()
        control_state = {}
        date_context = {}
        
        weekly_interface._display_map_statistics(empty_data, control_state, date_context)
        
        mock_warning.assert_called_once_with("⚠️ No data to display after applying filters and aggregation")
    
    def test_find_closest_link(self, weekly_interface, sample_shapefile_data):
        """Test finding closest link to click point."""
        # Test with valid coordinates
        closest_link = weekly_interface._find_closest_link(0.5, 0.5, sample_shapefile_data)
        
        assert closest_link is not None
        assert 'Id' in closest_link
        
        # Test with empty data
        empty_gdf = gpd.GeoDataFrame()
        closest_link_empty = weekly_interface._find_closest_link(0.5, 0.5, empty_gdf)
        
        assert closest_link_empty is None
    
    @patch('streamlit.metric')
    @patch('streamlit.subheader')
    def test_display_aggregation_summary(self, mock_subheader, mock_metric, weekly_interface):
        """Test displaying aggregation summary."""
        aggregation_stats = {
            'total_observations': 150,
            'unique_dates': 10,
            'unique_hours': 12,
            'data_quality': 'good',
            'weekly_patterns': {
                'duration': {
                    'peak_hour': 8,
                    'off_peak_hour': 14,
                    'min_value': 300,
                    'max_value': 1800,
                    'mean_value': 900,
                    'std_value': 200,
                    'variation_coefficient': 0.22,
                    'hourly_values': {7: 600, 8: 1200, 9: 800}
                }
            },
            'date_coverage': ['2025-01-01', '2025-01-02'],
            'hour_coverage': [7, 8, 9, 17, 18, 19]
        }
        
        weekly_interface._display_aggregation_summary(aggregation_stats, 'median')
        
        # Should display summary information
        mock_subheader.assert_called()
        assert mock_metric.call_count >= 4  # At least 4 metrics displayed
    
    @patch('streamlit.warning')
    def test_display_aggregation_summary_no_stats(self, mock_warning, weekly_interface):
        """Test displaying aggregation summary with no statistics."""
        weekly_interface._display_aggregation_summary({}, 'median')
        
        mock_warning.assert_called_once_with("⚠️ No aggregation statistics available for this link")


class TestWeeklyMapIntegration:
    """Integration tests for weekly map functionality."""
    
    @pytest.fixture
    def mock_session_state(self):
        """Mock Streamlit session state."""
        with patch.object(st, 'session_state', {}) as mock_state:
            yield mock_state
    
    @patch('streamlit.warning')
    def test_render_map_b_page_no_session_data(self, mock_warning, mock_session_state):
        """Test rendering Map B page without session data."""
        render_map_b_page()
        
        mock_warning.assert_called_once_with("⚠️ Please load shapefile and results data first.")
    
    @patch('map_b_weekly.WeeklyMapInterface')
    def test_render_map_b_page_with_data(self, mock_interface_class, mock_session_state):
        """Test rendering Map B page with session data."""
        # Setup session state with data
        mock_session_state['shapefile_data'] = gpd.GeoDataFrame({'Id': ['test']})
        mock_session_state['hourly_results'] = pd.DataFrame({'link_id': ['test']})
        
        # Mock the interface
        mock_interface = Mock()
        mock_interface_class.return_value = mock_interface
        
        render_map_b_page()
        
        # Should create interface and render page
        mock_interface_class.assert_called_once()
        mock_interface.render_weekly_map_page.assert_called_once()


class TestWeeklyMapAggregation:
    """Test weekly aggregation functionality."""
    
    @pytest.fixture
    def weekly_interface(self):
        """Create WeeklyMapInterface instance for testing."""
        return WeeklyMapInterface()
    
    @pytest.fixture
    def multi_day_hourly_data(self):
        """Create multi-day hourly data for aggregation testing."""
        dates = [date(2025, 1, 1), date(2025, 1, 2), date(2025, 1, 3)]
        hours = [7, 8, 9]
        
        data = []
        for link_id in ['s_A-B', 's_B-C']:
            for test_date in dates:
                for hour in hours:
                    data.append({
                        'link_id': link_id,
                        'date': test_date,
                        'hour': hour,
                        'avg_duration_sec': 600 + hour * 60,  # Varies by hour
                        'avg_speed_kmh': 50 - hour * 2,       # Varies by hour
                        'n_valid': 10
                    })
        
        return pd.DataFrame(data)
    
    def test_weekly_aggregation_aggregation(self, weekly_interface, multi_day_hourly_data):
        """Test weekly aggregation aggregation with filters."""
        # Mock shapefile data
        from shapely.geometry import LineString
        shapefile_data = gpd.GeoDataFrame({
            'Id': ['link_1', 'link_2'],
            'From': ['A', 'B'],
            'To': ['B', 'C'],
            'geometry': [LineString([(0, 0), (1, 1)]), LineString([(1, 1), (2, 2)])]
        })
        
        # Mock control state
        control_state = {
            'filters': {
                'temporal': {'hour_range': (7, 9)},
                'metrics': {'aggregation_method': 'median'},
                'attributes': {}
            },
            'spatial': {}
        }
        
        # Test aggregation
        filtered_data, date_context = weekly_interface._apply_filters_and_aggregate(
            shapefile_data, multi_day_hourly_data, control_state
        )
        
        # Should have aggregated data
        assert not filtered_data.empty
        assert 'aggregation_method' in date_context
        assert date_context['aggregation_method'] == 'median'
        assert date_context['n_days'] == 3  # 3 unique dates
    
    def test_aggregation_statistics_computation(self, weekly_interface, multi_day_hourly_data):
        """Test computation of aggregation statistics for link details."""
        link_id = 's_A-B'
        
        # Compute statistics
        stats = weekly_interface.data_processor.aggregation_engine.compute_aggregation_statistics(
            multi_day_hourly_data, link_id, method='median'
        )
        
        # Should have computed statistics
        assert stats['total_observations'] > 0
        assert stats['unique_dates'] == 3
        assert stats['unique_hours'] == 3
        assert stats['aggregation_method'] == 'median'
        assert 'weekly_patterns' in stats
        assert 'data_quality' in stats
    
    def test_weekly_pattern_analysis(self, weekly_interface, multi_day_hourly_data):
        """Test weekly pattern analysis in aggregation statistics."""
        link_id = 's_A-B'
        
        # Compute statistics
        stats = weekly_interface.data_processor.aggregation_engine.compute_aggregation_statistics(
            multi_day_hourly_data, link_id, method='median'
        )
        
        # Should have weekly patterns
        weekly_patterns = stats.get('weekly_patterns', {})
        assert 'duration' in weekly_patterns
        assert 'speed' in weekly_patterns
        
        # Check duration pattern
        duration_pattern = weekly_patterns['duration']
        assert 'hourly_values' in duration_pattern
        assert 'peak_hour' in duration_pattern
        assert 'off_peak_hour' in duration_pattern
        assert 'variation_coefficient' in duration_pattern


if __name__ == "__main__":
    pytest.main([__file__])