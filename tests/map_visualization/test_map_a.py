"""
Tests for Map A (Hourly View) interface, filtering controls, and interactions.

This module tests the hourly map interface, filtering controls, and click interactions
as specified in task 6.3.
"""

import pytest
import pandas as pd
import geopandas as gpd
import streamlit as st
from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from shapely.geometry import LineString, Point

# Import modules to test
from map_a_hourly import HourlyMapInterface
from link_details_panel import LinkDetailsPanel
from controls import FilterControls, InteractiveControls


class TestHourlyMapInterface:
    """Test the main hourly map interface functionality."""
    
    @pytest.fixture
    def sample_shapefile_data(self):
        """Create sample shapefile data for testing."""
        # Create sample geometries
        geometries = [
            LineString([(0, 0), (1, 1)]),
            LineString([(1, 1), (2, 2)]),
            LineString([(2, 2), (3, 3)])
        ]
        
        return gpd.GeoDataFrame({
            'Id': ['LINK_001', 'LINK_002', 'LINK_003'],
            'From': ['NODE_A', 'NODE_B', 'NODE_C'],
            'To': ['NODE_B', 'NODE_C', 'NODE_D'],
            'length_m': [1000, 1500, 2000],
            'geometry': geometries
        }, crs='EPSG:4326')
    
    @pytest.fixture
    def sample_results_data(self):
        """Create sample hourly results data for testing."""
        dates = [date(2025, 1, 15), date(2025, 1, 16), date(2025, 1, 17)]
        hours = list(range(24))
        link_ids = ['s_NODE_A-NODE_B', 's_NODE_B-NODE_C', 's_NODE_C-NODE_D']
        
        data = []
        for link_id in link_ids:
            for test_date in dates:
                for hour in hours:
                    data.append({
                        'link_id': link_id,
                        'date': test_date,
                        'hour': hour,
                        'avg_duration_sec': 120 + hour * 5 + (hash(link_id) % 60),
                        'avg_speed_kmh': 40 - hour * 0.5 + (hash(link_id) % 20),
                        'n_valid': 10 + (hour % 5),
                        'median_duration_sec': 115 + hour * 5,
                        'p10_duration_sec': 100 + hour * 4,
                        'p90_duration_sec': 140 + hour * 6,
                        'median_speed_kmh': 38 - hour * 0.4,
                        'p10_speed_kmh': 30 - hour * 0.3,
                        'p90_speed_kmh': 50 - hour * 0.6
                    })
        
        return pd.DataFrame(data)
    
    @pytest.fixture
    def hourly_interface(self):
        """Create HourlyMapInterface instance for testing."""
        return HourlyMapInterface()
    
    def test_interface_initialization(self, hourly_interface):
        """Test that the interface initializes correctly."""
        assert hourly_interface.controls is not None
        assert hourly_interface.renderer is not None
        assert hourly_interface.data_processor is not None
        assert hourly_interface.symbology is not None
    
    def test_calculate_data_bounds(self, hourly_interface, sample_results_data):
        """Test data bounds calculation for controls."""
        bounds = hourly_interface._calculate_data_bounds(sample_results_data)
        
        # Check date bounds
        assert 'min_date' in bounds
        assert 'max_date' in bounds
        assert bounds['min_date'] == date(2025, 1, 15)
        assert bounds['max_date'] == date(2025, 1, 17)
        
        # Check hour bounds
        assert 'min_hour' in bounds
        assert 'max_hour' in bounds
        assert bounds['min_hour'] == 0
        assert bounds['max_hour'] == 23
        
        # Check numeric bounds
        assert 'avg_speed_kmh' in bounds
        assert 'avg_duration_sec' in bounds
        assert bounds['avg_speed_kmh']['min'] > 0
        assert bounds['avg_speed_kmh']['max'] > bounds['avg_speed_kmh']['min']
    
    def test_temporal_filters(self, hourly_interface, sample_results_data):
        """Test temporal filtering functionality."""
        temporal_filters = {
            'date_range': (date(2025, 1, 15), date(2025, 1, 16)),
            'hour_range': (8, 18)
        }
        
        filtered_data = hourly_interface._apply_temporal_filters(
            sample_results_data, temporal_filters
        )
        
        # Check date filtering
        dates = pd.to_datetime(filtered_data['date']).dt.date
        assert dates.min() >= date(2025, 1, 15)
        assert dates.max() <= date(2025, 1, 16)
        
        # Check hour filtering
        assert filtered_data['hour'].min() >= 8
        assert filtered_data['hour'].max() <= 18
        
        # Ensure we have data
        assert len(filtered_data) > 0
    
    def test_attribute_filters(self, hourly_interface, sample_results_data):
        """Test attribute filtering functionality."""
        attribute_filters = {
            'avg_speed_kmh': {
                'operator': 'above',
                'value': 30
            },
            'avg_duration_sec': {
                'operator': 'between',
                'value': (100, 200)
            }
        }
        
        filtered_data = hourly_interface._apply_attribute_filters(
            sample_results_data, attribute_filters
        )
        
        # Check speed filter
        assert filtered_data['avg_speed_kmh'].min() > 30
        
        # Check duration filter
        assert filtered_data['avg_duration_sec'].min() >= 100
        assert filtered_data['avg_duration_sec'].max() <= 200
        
        # Ensure we have data
        assert len(filtered_data) > 0
    
    @patch('streamlit.rerun')
    def test_apply_filters_integration(self, mock_rerun, hourly_interface, 
                                     sample_shapefile_data, sample_results_data):
        """Test complete filter application and data joining."""
        control_state = {
            'filters': {
                'temporal': {
                    'date_range': (date(2025, 1, 15), date(2025, 1, 16)),
                    'hour_range': (9, 17)
                },
                'metrics': {
                    'metric_type': 'duration'
                },
                'attributes': {
                    'avg_speed_kmh': {
                        'operator': 'above',
                        'value': 25
                    }
                }
            },
            'spatial': {
                'type': 'none'
            }
        }
        
        # Mock the data processor
        with patch.object(hourly_interface.data_processor, 'join_results_to_shapefile') as mock_join:
            mock_join.return_value = sample_shapefile_data.copy()
            
            filtered_data = hourly_interface._apply_filters(
                sample_shapefile_data, sample_results_data, control_state
            )
            
            # Verify join was called
            mock_join.assert_called_once()
            
            # Check that duration minutes column was added
            assert 'avg_duration_min' in filtered_data.columns
    
    def test_format_active_filters(self, hourly_interface):
        """Test active filter formatting for display."""
        control_state = {
            'filters': {
                'temporal': {
                    'date_range': (date(2025, 1, 15), date(2025, 1, 16)),
                    'hour_range': (9, 17)
                },
                'attributes': {
                    'avg_speed_kmh': {
                        'operator': 'above',
                        'value': 30
                    },
                    'avg_duration_sec': {
                        'operator': 'between',
                        'value': (120, 300)
                    }
                }
            }
        }
        
        filters = hourly_interface._format_active_filters(control_state)
        
        assert len(filters) >= 3  # Date, hour, speed filters minimum
        
        # Check specific filter formats
        date_filter = next((f for f in filters if 'Dates:' in f), None)
        assert date_filter is not None
        
        hour_filter = next((f for f in filters if 'Hours:' in f), None)
        assert hour_filter is not None
        
        speed_filter = next((f for f in filters if 'Speed above:' in f), None)
        assert speed_filter is not None
    
    def test_find_closest_link(self, hourly_interface, sample_shapefile_data):
        """Test finding closest link to click point."""
        # Convert to WGS84 for testing
        data_wgs84 = sample_shapefile_data.to_crs('EPSG:4326')
        
        # Click near the first link
        click_lat, click_lon = 0.5, 0.5
        
        closest_link = hourly_interface._find_closest_link(
            click_lat, click_lon, data_wgs84
        )
        
        assert closest_link is not None
        assert closest_link['Id'] in ['LINK_001', 'LINK_002', 'LINK_003']
    
    def test_get_date_context(self, hourly_interface):
        """Test date context calculation for KPIs."""
        control_state = {
            'filters': {
                'temporal': {
                    'date_range': (date(2025, 1, 15), date(2025, 1, 20))
                }
            }
        }
        
        context = hourly_interface._get_date_context(control_state)
        
        assert 'n_days' in context
        assert context['n_days'] == 6  # 5 days inclusive


class TestFilterControls:
    """Test the filter controls functionality."""
    
    @pytest.fixture
    def filter_controls(self):
        """Create FilterControls instance for testing."""
        return FilterControls()
    
    @pytest.fixture
    def sample_data_bounds(self):
        """Create sample data bounds for testing."""
        return {
            'min_date': date(2025, 1, 1),
            'max_date': date(2025, 1, 31),
            'min_hour': 0,
            'max_hour': 23,
            'avg_speed_kmh': {'min': 10.0, 'max': 80.0},
            'avg_duration_sec': {'min': 60.0, 'max': 600.0},
            'length_m': {'min': 500.0, 'max': 5000.0}
        }
    
    @patch('streamlit.subheader')
    @patch('streamlit.columns')
    @patch('streamlit.date_input')
    @patch('streamlit.slider')
    def test_render_temporal_controls(self, mock_slider, mock_date_input, 
                                    mock_columns, mock_subheader, 
                                    filter_controls, sample_data_bounds):
        """Test temporal controls rendering."""
        # Mock Streamlit components
        mock_columns.return_value = [Mock(), Mock()]
        mock_date_input.return_value = (date(2025, 1, 15), date(2025, 1, 20))
        mock_slider.return_value = (8, 18)
        
        result = filter_controls.render_temporal_controls(sample_data_bounds, "test")
        
        assert 'date_range' in result
        assert 'hour_range' in result
        assert result['date_range'] == (date(2025, 1, 15), date(2025, 1, 20))
        assert result['hour_range'] == (8, 18)
    
    @patch('streamlit.subheader')
    @patch('streamlit.columns')
    @patch('streamlit.selectbox')
    def test_render_metric_controls(self, mock_selectbox, mock_columns, 
                                  mock_subheader, filter_controls):
        """Test metric controls rendering."""
        # Mock Streamlit components
        mock_columns.return_value = [Mock(), Mock()]
        mock_selectbox.side_effect = ['duration', 'median']
        
        result = filter_controls.render_metric_controls("test")
        
        assert 'metric_type' in result
        assert 'aggregation_method' in result
        assert result['metric_type'] == 'duration'
        assert result['aggregation_method'] == 'median'
    
    @patch('streamlit.subheader')
    @patch('streamlit.expander')
    def test_render_attribute_filters(self, mock_expander, mock_subheader, 
                                    filter_controls, sample_data_bounds):
        """Test attribute filters rendering."""
        # Mock expander context manager
        mock_expander_context = Mock()
        mock_expander.return_value.__enter__ = Mock(return_value=mock_expander_context)
        mock_expander.return_value.__exit__ = Mock(return_value=None)
        
        with patch('streamlit.checkbox', return_value=True), \
             patch('streamlit.selectbox', return_value='above'), \
             patch('streamlit.number_input', return_value=50.0), \
             patch('streamlit.caption'):
            
            result = filter_controls.render_attribute_filters(sample_data_bounds, "test")
            
            # Should have filters for all available attributes
            assert len(result) <= 3  # length, speed, duration
            
            # Check filter structure
            for filter_config in result.values():
                assert 'operator' in filter_config
                assert 'value' in filter_config
                assert 'enabled' in filter_config


class TestLinkDetailsPanel:
    """Test the link details panel functionality."""
    
    @pytest.fixture
    def details_panel(self):
        """Create LinkDetailsPanel instance for testing."""
        return LinkDetailsPanel()
    
    @pytest.fixture
    def sample_link_data(self):
        """Create sample link data for testing."""
        return pd.Series({
            'Id': 'TEST_LINK_001',
            'From': 'NODE_A',
            'To': 'NODE_B',
            'length_m': 1500,
            'avg_speed_kmh': 35.5,
            'avg_duration_sec': 152,
            'n_valid': 25,
            'date': '2025-01-15',
            'hour': 8,
            'median_duration_sec': 145,
            'p10_duration_sec': 120,
            'p90_duration_sec': 180,
            'median_speed_kmh': 37.0,
            'p10_speed_kmh': 25.0,
            'p90_speed_kmh': 45.0
        })
    
    @pytest.fixture
    def sample_hourly_data(self):
        """Create sample hourly data for testing."""
        return pd.DataFrame({
            'hour': list(range(24)),
            'avg_duration_sec': [120 + i * 5 for i in range(24)],
            'avg_speed_kmh': [40 - i * 0.5 for i in range(24)],
            'n_valid': [10 + (i % 5) for i in range(24)]
        })
    
    def test_calculate_link_statistics(self, details_panel, sample_hourly_data):
        """Test link statistics calculation."""
        stats = details_panel._calculate_link_statistics(sample_hourly_data)
        
        assert 'duration_stats' in stats
        assert 'speed_stats' in stats
        
        # Check duration statistics
        dur_stats = stats['duration_stats']
        assert 'mean' in dur_stats
        assert 'median' in dur_stats
        assert 'std' in dur_stats
        assert 'p10' in dur_stats
        assert 'p90' in dur_stats
        
        # Check speed statistics
        speed_stats = stats['speed_stats']
        assert 'mean' in speed_stats
        assert 'median' in speed_stats
        assert 'std' in speed_stats
        assert 'p10' in speed_stats
        assert 'p90' in speed_stats
    
    @patch('streamlit.subheader')
    @patch('streamlit.markdown')
    @patch('streamlit.columns')
    @patch('streamlit.metric')
    def test_render_basic_info(self, mock_metric, mock_columns, mock_markdown, 
                              mock_subheader, details_panel, sample_link_data):
        """Test basic info rendering."""
        # Mock columns
        mock_columns.return_value = [Mock(), Mock(), Mock()]
        
        details_panel._render_basic_info(sample_link_data)
        
        # Verify that metrics were called
        mock_metric.assert_called()
        
        # Verify structure calls
        mock_subheader.assert_called_with("### 📋 Basic Information")
        mock_columns.assert_called_with(3)
    
    @patch('streamlit.markdown')
    @patch('streamlit.columns')
    @patch('streamlit.metric')
    def test_render_current_metrics(self, mock_metric, mock_columns, mock_markdown,
                                   details_panel, sample_link_data):
        """Test current metrics rendering."""
        # Mock columns
        mock_columns.return_value = [Mock(), Mock(), Mock(), Mock()]
        
        details_panel._render_current_metrics(sample_link_data)
        
        # Verify that metrics were called
        mock_metric.assert_called()
        
        # Verify structure
        mock_markdown.assert_called_with("### 🚗 Current Traffic Metrics")
        mock_columns.assert_called_with(4)


class TestInteractiveControls:
    """Test the interactive controls integration."""
    
    @pytest.fixture
    def interactive_controls(self):
        """Create InteractiveControls instance for testing."""
        return InteractiveControls()
    
    @pytest.fixture
    def sample_gdf(self):
        """Create sample GeoDataFrame for testing."""
        geometries = [LineString([(0, 0), (1, 1)])]
        return gpd.GeoDataFrame({
            'Id': ['LINK_001'],
            'From': ['NODE_A'],
            'To': ['NODE_B'],
            'geometry': geometries
        }, crs='EPSG:4326')
    
    @pytest.fixture
    def sample_bounds(self):
        """Create sample data bounds."""
        return {
            'min_date': date(2025, 1, 1),
            'max_date': date(2025, 1, 31),
            'min_hour': 0,
            'max_hour': 23
        }
    
    def test_controls_initialization(self, interactive_controls):
        """Test that interactive controls initialize correctly."""
        assert interactive_controls.filter_controls is not None
        assert interactive_controls.spatial_selection is not None
        assert interactive_controls.playback_controller is not None
        assert interactive_controls.kpi_display is not None
    
    @patch('streamlit.subheader')
    @patch('streamlit.button')
    def test_render_control_panel_hourly(self, mock_button, mock_subheader,
                                       interactive_controls, sample_gdf, sample_bounds):
        """Test control panel rendering for hourly map."""
        mock_button.return_value = False
        
        with patch.object(interactive_controls.filter_controls, 'render_filter_panel') as mock_filter, \
             patch.object(interactive_controls.spatial_selection, 'render_spatial_controls') as mock_spatial, \
             patch.object(interactive_controls.playback_controller, 'render_playback_controls') as mock_playback:
            
            mock_filter.return_value = {'test': 'filter'}
            mock_spatial.return_value = {'test': 'spatial'}
            mock_playback.return_value = {'test': 'playback'}
            
            result = interactive_controls.render_control_panel(
                sample_gdf, sample_bounds, "hourly", "test"
            )
            
            assert 'filters' in result
            assert 'spatial' in result
            assert 'playback' in result
    
    def test_kpi_calculation(self, interactive_controls, sample_gdf):
        """Test KPI calculation and display."""
        # Add some sample data to the GeoDataFrame
        sample_gdf['avg_speed_kmh'] = [35.0]
        sample_gdf['avg_duration_sec'] = [120.0]
        sample_gdf['n_valid'] = [15]
        sample_gdf['length_m'] = [1000.0]
        
        kpis = interactive_controls.kpi_display.calculate_kpis(
            sample_gdf, total_links=10, date_context={'n_days': 5}
        )
        
        assert 'coverage_percent' in kpis
        assert 'mean_speed' in kpis
        assert 'mean_duration' in kpis
        assert 'n_links' in kpis
        assert 'n_days' in kpis
        
        # Check calculated values
        assert kpis['coverage_percent'] == 10.0  # 1/10 * 100
        assert kpis['mean_speed'] == 35.0
        assert kpis['mean_duration'] == 2.0  # 120/60
        assert kpis['n_links'] == 1
        assert kpis['n_days'] == 5


class TestMapClickInteractions:
    """Test map click interactions and link selection."""
    
    @pytest.fixture
    def hourly_interface(self):
        """Create HourlyMapInterface instance for testing."""
        return HourlyMapInterface()
    
    @pytest.fixture
    def sample_map_data(self):
        """Create sample map click data."""
        return {
            'last_clicked': {
                'lat': 0.5,
                'lon': 0.5
            }
        }
    
    @pytest.fixture
    def sample_filtered_data(self):
        """Create sample filtered data."""
        geometries = [
            LineString([(0, 0), (1, 1)]),
            LineString([(1, 1), (2, 2)])
        ]
        
        return gpd.GeoDataFrame({
            'Id': ['LINK_001', 'LINK_002'],
            'From': ['NODE_A', 'NODE_B'],
            'To': ['NODE_B', 'NODE_C'],
            'avg_speed_kmh': [35.0, 40.0],
            'avg_duration_sec': [120.0, 100.0],
            'geometry': geometries
        }, crs='EPSG:4326')
    
    @patch('streamlit.session_state', {})
    def test_handle_map_clicks(self, hourly_interface, sample_map_data, 
                              sample_filtered_data):
        """Test map click handling."""
        results_data = pd.DataFrame()
        control_state = {}
        
        with patch.object(hourly_interface, '_find_closest_link') as mock_find, \
             patch.object(hourly_interface, '_display_link_details_panel') as mock_display:
            
            mock_find.return_value = sample_filtered_data.iloc[0]
            
            hourly_interface._handle_map_clicks(
                sample_map_data, sample_filtered_data, results_data, control_state
            )
            
            # Verify closest link was found
            mock_find.assert_called_once_with(0.5, 0.5, sample_filtered_data)
            
            # Verify details panel was displayed
            mock_display.assert_called_once()
    
    def test_find_closest_link_success(self, hourly_interface, sample_filtered_data):
        """Test successful closest link finding."""
        closest_link = hourly_interface._find_closest_link(0.5, 0.5, sample_filtered_data)
        
        assert closest_link is not None
        assert closest_link['Id'] in ['LINK_001', 'LINK_002']
    
    def test_find_closest_link_empty_data(self, hourly_interface):
        """Test closest link finding with empty data."""
        empty_gdf = gpd.GeoDataFrame()
        
        closest_link = hourly_interface._find_closest_link(0.5, 0.5, empty_gdf)
        
        assert closest_link is None


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])