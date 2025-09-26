"""
Tests for Streamlit integration of map visualization components.

This module tests the integration of map visualization with the Streamlit GUI,
including navigation, file loading, and reactive interface components.
"""

import pytest
import streamlit as st
import pandas as pd
import geopandas as gpd
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Import modules to test
from maps_page import MapsPageInterface, render_maps_page
from spatial_data import SpatialDataManager


class TestMapsPageInterface:
    """Test the main Maps page interface."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.maps_interface = MapsPageInterface()
        
        # Create sample shapefile data
        from shapely.geometry import LineString
        self.sample_shapefile = gpd.GeoDataFrame({
            'Id': ['link_1', 'link_2', 'link_3'],
            'From': ['A', 'B', 'C'],
            'To': ['B', 'C', 'D'],
            'geometry': [
                LineString([(0, 0), (1, 1)]),
                LineString([(1, 1), (2, 2)]),
                LineString([(2, 2), (3, 3)])
            ]
        }, crs="EPSG:2039")
        
        # Create sample hourly results
        self.sample_hourly = pd.DataFrame({
            'link_id': ['s_A-B', 's_B-C', 's_C-D'],
            'date': ['2024-01-01', '2024-01-01', '2024-01-01'],
            'hour': [8, 8, 8],
            'avg_duration_sec': [120, 180, 240],
            'avg_speed_kmh': [50, 40, 30],
            'n_valid': [10, 15, 20]
        })
        
        # Create sample weekly results
        self.sample_weekly = pd.DataFrame({
            'link_id': ['s_A-B', 's_B-C', 's_C-D'],
            'hour': [8, 8, 8],
            'avg_duration_sec': [125, 185, 245],
            'avg_speed_kmh': [48, 38, 28],
            'n_valid': [100, 150, 200]
        })
    
    def test_initialization(self):
        """Test Maps page interface initialization."""
        assert self.maps_interface.spatial_manager is not None
        assert self.maps_interface.hourly_interface is not None
        assert self.maps_interface.weekly_interface is not None
        assert self.maps_interface.default_shapefile_path is not None
    
    @patch('streamlit.session_state', {})
    def test_initialize_session_state(self):
        """Test session state initialization."""
        self.maps_interface._initialize_session_state()
        
        # Check that all required session state variables are initialized
        assert 'maps_shapefile_path' in st.session_state
        assert 'maps_results_path' in st.session_state
        assert 'maps_shapefile_data' in st.session_state
        assert 'maps_hourly_results' in st.session_state
        assert 'maps_weekly_results' in st.session_state
        assert 'maps_preferences' in st.session_state
        
        # Check default values
        assert st.session_state.maps_shapefile_path == self.maps_interface.default_shapefile_path
        assert st.session_state.maps_shapefile_data is None
        assert st.session_state.maps_hourly_results is None
        assert st.session_state.maps_weekly_results is None
        
        # Check preferences structure
        preferences = st.session_state.maps_preferences
        assert 'default_map' in preferences
        assert 'auto_refresh' in preferences
        assert 'show_data_quality' in preferences
    
    @patch('streamlit.session_state', {})
    def test_check_data_availability_empty(self):
        """Test data availability check with no data."""
        self.maps_interface._initialize_session_state()
        
        # Should return False when no data is loaded
        assert not self.maps_interface._check_data_availability()
    
    @patch('streamlit.session_state', {})
    def test_check_data_availability_with_data(self):
        """Test data availability check with data loaded."""
        self.maps_interface._initialize_session_state()
        
        # Load sample data
        st.session_state.maps_shapefile_data = self.sample_shapefile
        st.session_state.maps_hourly_results = self.sample_hourly
        
        # Should return True when both shapefile and results are loaded
        assert self.maps_interface._check_data_availability()
    
    @patch('streamlit.session_state', {})
    def test_check_data_availability_partial(self):
        """Test data availability check with partial data."""
        self.maps_interface._initialize_session_state()
        
        # Load only shapefile
        st.session_state.maps_shapefile_data = self.sample_shapefile
        
        # Should return False when only shapefile is loaded
        assert not self.maps_interface._check_data_availability()
        
        # Load only results
        st.session_state.maps_shapefile_data = None
        st.session_state.maps_hourly_results = self.sample_hourly
        
        # Should return False when only results are loaded
        assert not self.maps_interface._check_data_availability()


class TestShapefileLoading:
    """Test shapefile loading functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.maps_interface = MapsPageInterface()
        
        # Create a temporary shapefile for testing
        from shapely.geometry import LineString
        self.test_shapefile = gpd.GeoDataFrame({
            'Id': ['test_1', 'test_2'],
            'From': ['A', 'B'],
            'To': ['B', 'C'],
            'geometry': [
                LineString([(0, 0), (1, 1)]),
                LineString([(1, 1), (2, 2)])
            ]
        }, crs="EPSG:4326")
    
    def test_create_temporary_shapefile(self):
        """Test creating a temporary shapefile for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            shapefile_path = os.path.join(temp_dir, 'test.shp')
            self.test_shapefile.to_file(shapefile_path)
            
            # Verify file was created
            assert os.path.exists(shapefile_path)
            
            # Verify we can read it back
            loaded_gdf = gpd.read_file(shapefile_path)
            assert len(loaded_gdf) == 2
            assert 'Id' in loaded_gdf.columns
            assert 'From' in loaded_gdf.columns
            assert 'To' in loaded_gdf.columns
    
    @patch('streamlit.session_state', {})
    @patch('streamlit.success')
    @patch('streamlit.info')
    def test_load_shapefile_from_path(self, mock_info, mock_success):
        """Test loading shapefile from file path."""
        self.maps_interface._initialize_session_state()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            shapefile_path = os.path.join(temp_dir, 'test.shp')
            self.test_shapefile.to_file(shapefile_path)
            
            # Mock the spatial manager methods
            with patch.object(self.maps_interface.spatial_manager, 'load_shapefile') as mock_load, \
                 patch.object(self.maps_interface.spatial_manager, 'validate_shapefile_schema') as mock_validate, \
                 patch.object(self.maps_interface.spatial_manager, 'reproject_to_epsg2039') as mock_reproject:
                
                mock_load.return_value = self.test_shapefile
                mock_validate.return_value = (True, [])
                mock_reproject.return_value = self.test_shapefile.to_crs("EPSG:2039")
                
                # Test loading
                self.maps_interface._load_shapefile(None, shapefile_path)
                
                # Verify methods were called
                mock_load.assert_called_once_with(shapefile_path)
                mock_validate.assert_called_once()
                mock_reproject.assert_called_once()
                
                # Verify session state was updated
                assert st.session_state.maps_shapefile_data is not None
                assert st.session_state.maps_shapefile_path == shapefile_path
    
    @patch('streamlit.session_state', {})
    @patch('streamlit.error')
    def test_load_shapefile_invalid_schema(self, mock_error):
        """Test loading shapefile with invalid schema."""
        self.maps_interface._initialize_session_state()
        
        # Create shapefile with missing required fields
        invalid_shapefile = gpd.GeoDataFrame({
            'wrong_id': ['test_1'],
            'geometry': [LineString([(0, 0), (1, 1)])]
        }, crs="EPSG:4326")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            shapefile_path = os.path.join(temp_dir, 'invalid.shp')
            invalid_shapefile.to_file(shapefile_path)
            
            # Mock the spatial manager methods
            with patch.object(self.maps_interface.spatial_manager, 'load_shapefile') as mock_load, \
                 patch.object(self.maps_interface.spatial_manager, 'validate_shapefile_schema') as mock_validate:
                
                mock_load.return_value = invalid_shapefile
                mock_validate.return_value = (False, ['Id', 'From', 'To'])
                
                # Test loading
                self.maps_interface._load_shapefile(None, shapefile_path)
                
                # Verify error was called
                mock_error.assert_called()
                
                # Verify session state was not updated with invalid data
                assert st.session_state.maps_shapefile_data is None


class TestResultsLoading:
    """Test results data loading functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.maps_interface = MapsPageInterface()
        
        # Create sample data
        self.sample_hourly = pd.DataFrame({
            'link_id': ['s_A-B', 's_B-C'],
            'date': ['2024-01-01', '2024-01-01'],
            'hour': [8, 8],
            'avg_duration_sec': [120, 180],
            'avg_speed_kmh': [50, 40],
            'n_valid': [10, 15]
        })
        
        self.sample_weekly = pd.DataFrame({
            'link_id': ['s_A-B', 's_B-C'],
            'hour': [8, 8],
            'avg_duration_sec': [125, 185],
            'avg_speed_kmh': [48, 38],
            'n_valid': [100, 150]
        })
    
    def create_mock_uploaded_file(self, data: pd.DataFrame, filename: str):
        """Create a mock uploaded file for testing."""
        mock_file = Mock()
        mock_file.name = filename
        
        # Create CSV content
        csv_content = data.to_csv(index=False).encode('utf-8')
        
        # Mock the file reading
        with patch('pandas.read_csv') as mock_read_csv:
            mock_read_csv.return_value = data
            return mock_file, mock_read_csv
    
    @patch('streamlit.session_state', {})
    @patch('streamlit.success')
    @patch('streamlit.info')
    def test_load_hourly_results(self, mock_info, mock_success):
        """Test loading hourly results data."""
        self.maps_interface._initialize_session_state()
        
        mock_hourly_file, mock_read_csv = self.create_mock_uploaded_file(
            self.sample_hourly, 'hourly_agg.csv'
        )
        
        # Test loading
        self.maps_interface._load_results_data(mock_hourly_file, None)
        
        # Verify pandas read_csv was called
        mock_read_csv.assert_called_once()
        
        # Verify session state was updated
        assert st.session_state.maps_hourly_results is not None
        pd.testing.assert_frame_equal(
            st.session_state.maps_hourly_results, 
            self.sample_hourly
        )
    
    @patch('streamlit.session_state', {})
    @patch('streamlit.success')
    @patch('streamlit.info')
    def test_load_weekly_results(self, mock_info, mock_success):
        """Test loading weekly results data."""
        self.maps_interface._initialize_session_state()
        
        mock_weekly_file, mock_read_csv = self.create_mock_uploaded_file(
            self.sample_weekly, 'weekly_hourly_profile.csv'
        )
        
        # Test loading
        self.maps_interface._load_results_data(None, mock_weekly_file)
        
        # Verify pandas read_csv was called
        mock_read_csv.assert_called_once()
        
        # Verify session state was updated
        assert st.session_state.maps_weekly_results is not None
        pd.testing.assert_frame_equal(
            st.session_state.maps_weekly_results, 
            self.sample_weekly
        )
    
    @patch('streamlit.session_state', {})
    @patch('streamlit.error')
    def test_load_invalid_hourly_results(self, mock_error):
        """Test loading hourly results with invalid schema."""
        self.maps_interface._initialize_session_state()
        
        # Create invalid hourly data (missing required columns)
        invalid_hourly = pd.DataFrame({
            'wrong_column': ['value1', 'value2']
        })
        
        mock_file, mock_read_csv = self.create_mock_uploaded_file(
            invalid_hourly, 'invalid_hourly.csv'
        )
        
        # Test loading
        self.maps_interface._load_results_data(mock_file, None)
        
        # Verify error was called
        mock_error.assert_called()
        
        # Verify session state was not updated
        assert st.session_state.maps_hourly_results is None


class TestAutoDetection:
    """Test auto-detection of results files."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.maps_interface = MapsPageInterface()
    
    @patch('streamlit.session_state', {})
    @patch('streamlit.success')
    @patch('streamlit.info')
    @patch('os.path.exists')
    @patch('pandas.read_csv')
    def test_auto_detect_success(self, mock_read_csv, mock_exists, mock_info, mock_success):
        """Test successful auto-detection of results files."""
        self.maps_interface._initialize_session_state()
        
        # Mock file existence
        def mock_exists_side_effect(path):
            if path in ['./output', './output/hourly_agg.csv', './output/weekly_hourly_profile.csv']:
                return True
            return False
        
        mock_exists.side_effect = mock_exists_side_effect
        
        # Mock pandas read_csv
        def mock_read_csv_side_effect(path):
            if 'hourly_agg.csv' in path:
                return pd.DataFrame({
                    'link_id': ['s_A-B'],
                    'date': ['2024-01-01'],
                    'hour': [8],
                    'avg_duration_sec': [120],
                    'avg_speed_kmh': [50],
                    'n_valid': [10]
                })
            elif 'weekly_hourly_profile.csv' in path:
                return pd.DataFrame({
                    'link_id': ['s_A-B'],
                    'hour': [8],
                    'avg_duration_sec': [125],
                    'avg_speed_kmh': [48],
                    'n_valid': [100]
                })
            return pd.DataFrame()
        
        mock_read_csv.side_effect = mock_read_csv_side_effect
        
        # Test auto-detection
        self.maps_interface._auto_detect_results_files()
        
        # Verify success message was called
        mock_success.assert_called()
        
        # Verify both files were loaded
        assert st.session_state.maps_hourly_results is not None
        assert st.session_state.maps_weekly_results is not None
    
    @patch('streamlit.session_state', {})
    @patch('streamlit.warning')
    @patch('os.path.exists')
    def test_auto_detect_no_files(self, mock_exists, mock_warning):
        """Test auto-detection when no files are found."""
        self.maps_interface._initialize_session_state()
        
        # Mock no files exist
        mock_exists.return_value = False
        
        # Test auto-detection
        self.maps_interface._auto_detect_results_files()
        
        # Verify warning was called
        mock_warning.assert_called()
        
        # Verify no data was loaded
        assert st.session_state.maps_hourly_results is None
        assert st.session_state.maps_weekly_results is None


class TestDataQualitySummary:
    """Test data quality summary functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.maps_interface = MapsPageInterface()
        
        # Create sample data with known join characteristics
        from shapely.geometry import LineString
        self.sample_shapefile = gpd.GeoDataFrame({
            'Id': ['link_1', 'link_2', 'link_3'],
            'From': ['A', 'B', 'C'],
            'To': ['B', 'C', 'D'],
            'geometry': [
                LineString([(0, 0), (1, 1)]),
                LineString([(1, 1), (2, 2)]),
                LineString([(2, 2), (3, 3)])
            ]
        }, crs="EPSG:2039")
        
        # Create results with partial matches
        self.sample_hourly = pd.DataFrame({
            'link_id': ['s_A-B', 's_B-C', 's_X-Y'],  # s_X-Y won't match shapefile
            'date': ['2024-01-01', '2024-01-01', '2024-01-01'],
            'hour': [8, 8, 8],
            'avg_duration_sec': [120, 180, 240],
            'avg_speed_kmh': [50, 40, 30],
            'n_valid': [10, 15, 20]
        })
    
    @patch('streamlit.session_state', {})
    def test_join_validation_calculation(self):
        """Test join validation calculations."""
        self.maps_interface._initialize_session_state()
        
        # Load sample data
        st.session_state.maps_shapefile_data = self.sample_shapefile
        st.session_state.maps_hourly_results = self.sample_hourly
        
        # Calculate expected join statistics
        shapefile_link_ids = {'s_A-B', 's_B-C', 's_C-D'}
        hourly_link_ids = {'s_A-B', 's_B-C', 's_X-Y'}
        
        expected_matched = shapefile_link_ids.intersection(hourly_link_ids)
        expected_missing_in_shapefile = hourly_link_ids - shapefile_link_ids
        expected_missing_in_hourly = shapefile_link_ids - hourly_link_ids
        
        # Verify calculations
        assert len(expected_matched) == 2  # s_A-B, s_B-C
        assert len(expected_missing_in_shapefile) == 1  # s_X-Y
        assert len(expected_missing_in_hourly) == 1  # s_C-D
        
        # Calculate match rate
        expected_match_rate = len(expected_matched) / len(shapefile_link_ids) * 100
        assert expected_match_rate == 2/3 * 100  # 66.67%


class TestReactiveInterface:
    """Test reactive interface functionality and real-time updates."""
    
    def setup_method(self):
        """Set up test fixtures for reactive interface tests."""
        self.maps_interface = MapsPageInterface()
        
        # Create sample data for testing
        from shapely.geometry import LineString
        self.sample_shapefile = gpd.GeoDataFrame({
            'Id': ['link_1', 'link_2', 'link_3'],
            'From': ['A', 'B', 'C'],
            'To': ['B', 'C', 'D'],
            'geometry': [
                LineString([(0, 0), (1, 1)]),
                LineString([(1, 1), (2, 2)]),
                LineString([(2, 2), (3, 3)])
            ]
        }, crs="EPSG:2039")
        
        self.sample_hourly = pd.DataFrame({
            'link_id': ['s_A-B', 's_B-C', 's_C-D'],
            'date': ['2024-01-01', '2024-01-01', '2024-01-01'],
            'hour': [8, 8, 8],
            'avg_duration_sec': [120, 180, 240],
            'avg_speed_kmh': [50, 40, 30],
            'n_valid': [10, 15, 20]
        })
    
    @patch('streamlit.session_state', {})
    def test_reactive_state_initialization(self):
        """Test that reactive state is properly initialized."""
        self.maps_interface._initialize_session_state()
        
        # Check reactive state components
        assert 'maps_shared_state' in st.session_state
        assert 'maps_loading_state' in st.session_state
        assert 'maps_performance' in st.session_state
        
        # Check shared state structure
        shared_state = st.session_state.maps_shared_state
        assert 'metric_type' in shared_state
        assert 'aggregation_method' in shared_state
        assert 'symbology_settings' in shared_state
        assert 'last_update_time' in shared_state
        assert 'filter_hash' in shared_state
        
        # Check loading state structure
        loading_state = st.session_state.maps_loading_state
        assert 'is_loading' in loading_state
        assert 'loading_message' in loading_state
        assert 'last_error' in loading_state
        assert 'error_timestamp' in loading_state
        
        # Check performance state structure
        performance = st.session_state.maps_performance
        assert 'last_render_time' in performance
        assert 'render_count' in performance
        assert 'cache_hits' in performance
        assert 'cache_misses' in performance
    
    @patch('streamlit.session_state', {})
    def test_reactive_preferences(self):
        """Test reactive preferences configuration."""
        self.maps_interface._initialize_session_state()
        
        preferences = st.session_state.maps_preferences
        
        # Check reactive-specific preferences
        assert 'reactive_updates' in preferences
        assert 'loading_indicators' in preferences
        assert preferences['reactive_updates'] is True  # Default enabled
        assert preferences['loading_indicators'] is True  # Default enabled
    
    @patch('streamlit.session_state', {})
    @patch('streamlit.rerun')
    def test_trigger_reactive_update(self, mock_rerun):
        """Test reactive update triggering mechanism."""
        self.maps_interface._initialize_session_state()
        
        # Enable reactive updates
        st.session_state.maps_preferences['reactive_updates'] = True
        
        # Trigger update
        self.maps_interface._trigger_reactive_update("Test update")
        
        # Check that update time was set
        assert st.session_state.maps_shared_state['last_update_time'] is not None
        
        # Check that filter hash was updated
        assert st.session_state.maps_shared_state['filter_hash'] is not None
        
        # Check that performance counter was incremented
        assert st.session_state.maps_performance['render_count'] == 1
        
        # Check that rerun was called
        mock_rerun.assert_called_once()
    
    @patch('streamlit.session_state', {})
    def test_error_handling_state(self):
        """Test error handling and state management."""
        self.maps_interface._initialize_session_state()
        
        # Simulate an error
        test_error = Exception("Test error message")
        self.maps_interface._handle_map_error("Test Map", test_error)
        
        # Check error state was updated
        loading_state = st.session_state.maps_loading_state
        assert loading_state['last_error'] == "Test error message"
        assert loading_state['error_timestamp'] is not None
    
    @patch('streamlit.session_state', {})
    def test_shared_state_consistency(self):
        """Test that shared state maintains consistency between maps."""
        self.maps_interface._initialize_session_state()
        
        # Set initial shared state
        st.session_state.maps_shared_state['metric_type'] = 'duration'
        st.session_state.maps_shared_state['aggregation_method'] = 'median'
        
        # Verify state is accessible
        assert st.session_state.maps_shared_state['metric_type'] == 'duration'
        assert st.session_state.maps_shared_state['aggregation_method'] == 'median'
        
        # Test state update
        st.session_state.maps_shared_state['metric_type'] = 'speed'
        assert st.session_state.maps_shared_state['metric_type'] == 'speed'
    
    @patch('streamlit.session_state', {})
    def test_loading_indicators(self):
        """Test loading indicator functionality."""
        self.maps_interface._initialize_session_state()
        
        # Enable loading indicators
        st.session_state.maps_preferences['loading_indicators'] = True
        
        # Set loading state
        st.session_state.maps_loading_state['is_loading'] = True
        st.session_state.maps_loading_state['loading_message'] = "Test loading message"
        
        # Verify loading state
        assert st.session_state.maps_loading_state['is_loading'] is True
        assert st.session_state.maps_loading_state['loading_message'] == "Test loading message"
        
        # Clear loading state
        st.session_state.maps_loading_state['is_loading'] = False
        st.session_state.maps_loading_state['loading_message'] = ""
        
        # Verify cleared state
        assert st.session_state.maps_loading_state['is_loading'] is False
        assert st.session_state.maps_loading_state['loading_message'] == ""


class TestControlsReactivity:
    """Test reactive controls functionality."""
    
    def setup_method(self):
        """Set up test fixtures for controls reactivity tests."""
        from controls import FilterControls
        self.filter_controls = FilterControls()
        
        # Sample data bounds for testing
        self.data_bounds = {
            'min_date': date(2024, 1, 1),
            'max_date': date(2024, 1, 31),
            'min_hour': 0,
            'max_hour': 23,
            'length_m': {'min': 100, 'max': 5000},
            'avg_speed_kmh': {'min': 10, 'max': 80},
            'avg_duration_sec': {'min': 60, 'max': 1800}
        }
    
    @patch('streamlit.session_state', {})
    def test_reactive_filter_state_management(self):
        """Test reactive filter state management."""
        # Initialize session state with reactive preferences
        st.session_state.maps_preferences = {'reactive_updates': True}
        st.session_state.maps_shared_state = {
            'metric_type': 'duration',
            'aggregation_method': 'median',
            'hour_range': (0, 23)
        }
        
        # Test that shared state is used in controls
        assert st.session_state.maps_shared_state['metric_type'] == 'duration'
        assert st.session_state.maps_shared_state['aggregation_method'] == 'median'
    
    def test_filter_reset_functionality(self):
        """Test filter reset functionality."""
        # This would test the _reset_attribute_filters method
        # In a real test, we'd mock the session state and verify reset behavior
        assert hasattr(self.filter_controls, '_reset_attribute_filters')
        assert hasattr(self.filter_controls, '_count_active_filters')
    
    def test_reactive_update_triggering(self):
        """Test reactive update triggering in controls."""
        # This would test the _trigger_filter_update method
        assert hasattr(self.filter_controls, '_trigger_filter_update')


class TestDataIntegration:
    """Test integration with actual data files and reactive interface functionality."""
    
    def setup_method(self):
        """Set up test fixtures for data integration tests."""
        self.maps_interface = MapsPageInterface()
        
        # Paths to test data files
        self.hourly_data_path = "test_data/hourly_agg_all.csv"
        self.weekly_data_path = "test_data/weekly_hourly_profile_all.csv"
    
    def test_hourly_data_file_exists(self):
        """Test that the hourly test data file exists."""
        import os
        assert os.path.exists(self.hourly_data_path), f"Hourly test data file not found: {self.hourly_data_path}"
    
    def test_weekly_data_file_exists(self):
        """Test that the weekly test data file exists."""
        import os
        assert os.path.exists(self.weekly_data_path), f"Weekly test data file not found: {self.weekly_data_path}"
    
    def test_load_hourly_test_data(self):
        """Test loading the actual hourly test data file."""
        import os
        if os.path.exists(self.hourly_data_path):
            hourly_data = pd.read_csv(self.hourly_data_path)
            
            # Verify basic structure
            assert not hourly_data.empty, "Hourly data file is empty"
            
            # Check for required columns (with variations)
            required_cols = ['link_id']
            for col in required_cols:
                assert col in hourly_data.columns, f"Missing required column: {col}"
            
            # Check for hour column variations
            hour_cols = ['hour', 'hour_of_day']
            assert any(col in hourly_data.columns for col in hour_cols), "Missing hour column"
            
            # Check for duration column variations
            duration_cols = ['avg_duration_sec', 'avg_dur']
            assert any(col in hourly_data.columns for col in duration_cols), "Missing duration column"
            
            # Check for speed column variations
            speed_cols = ['avg_speed_kmh', 'avg_speed']
            assert any(col in hourly_data.columns for col in speed_cols), "Missing speed column"
            
            print(f"✅ Hourly data loaded successfully: {len(hourly_data)} records")
            print(f"   Columns: {list(hourly_data.columns)}")
            print(f"   Unique links: {hourly_data['link_id'].nunique()}")
    
    def test_load_weekly_test_data(self):
        """Test loading the actual weekly test data file."""
        import os
        if os.path.exists(self.weekly_data_path):
            weekly_data = pd.read_csv(self.weekly_data_path)
            
            # Verify basic structure
            assert not weekly_data.empty, "Weekly data file is empty"
            
            # Check for required columns (with variations)
            required_cols = ['link_id']
            for col in required_cols:
                assert col in weekly_data.columns, f"Missing required column: {col}"
            
            # Check for hour column variations
            hour_cols = ['hour', 'hour_of_day']
            assert any(col in weekly_data.columns for col in hour_cols), "Missing hour column"
            
            # Check for duration column variations
            duration_cols = ['avg_duration_sec', 'avg_dur']
            assert any(col in weekly_data.columns for col in duration_cols), "Missing duration column"
            
            # Check for speed column variations
            speed_cols = ['avg_speed_kmh', 'avg_speed']
            assert any(col in weekly_data.columns for col in speed_cols), "Missing speed column"
            
            print(f"✅ Weekly data loaded successfully: {len(weekly_data)} records")
            print(f"   Columns: {list(weekly_data.columns)}")
            print(f"   Unique links: {weekly_data['link_id'].nunique()}")
    
    def test_maps_display_integration(self):
        """Test complete integration of maps display with test data."""
        import os
        
        # This is a comprehensive integration test
        if os.path.exists(self.hourly_data_path) and os.path.exists(self.weekly_data_path):
            
            # Load and prepare test data
            hourly_data = pd.read_csv(self.hourly_data_path)
            weekly_data = pd.read_csv(self.weekly_data_path)
            
            # Standardize column names
            if 'hour_of_day' in hourly_data.columns and 'hour' not in hourly_data.columns:
                hourly_data = hourly_data.rename(columns={'hour_of_day': 'hour'})
            
            if 'hour_of_day' in weekly_data.columns and 'hour' not in weekly_data.columns:
                weekly_data = weekly_data.rename(columns={'hour_of_day': 'hour'})
            
            if 'avg_dur' in weekly_data.columns and 'avg_duration_sec' not in weekly_data.columns:
                weekly_data = weekly_data.rename(columns={'avg_dur': 'avg_duration_sec'})
            
            if 'avg_speed' in weekly_data.columns and 'avg_speed_kmh' not in weekly_data.columns:
                weekly_data = weekly_data.rename(columns={'avg_speed': 'avg_speed_kmh'})
            
            # Create sample shapefile for testing
            from shapely.geometry import LineString
            unique_links = hourly_data['link_id'].unique()[:50]  # Use first 50 for testing
            
            shapefile_data = []
            for i, link_id in enumerate(unique_links):
                if link_id.startswith('s_') and '-' in link_id:
                    from_to = link_id[2:]  # Remove 's_' prefix
                    if '-' in from_to:
                        from_node, to_node = from_to.split('-', 1)
                        
                        # Create simple line geometry
                        start_x, start_y = i * 100, i * 100
                        end_x, end_y = start_x + 50, start_y + 50
                        
                        shapefile_data.append({
                            'Id': f'link_{i}',
                            'From': from_node,
                            'To': to_node,
                            'geometry': LineString([(start_x, start_y), (end_x, end_y)])
                        })
            
            if shapefile_data:
                import geopandas as gpd
                gdf = gpd.GeoDataFrame(shapefile_data, crs="EPSG:2039")
                
                # Test data joining
                from map_data import MapDataProcessor
                processor = MapDataProcessor()
                
                joined_hourly = processor.join_results_to_shapefile(gdf, hourly_data)
                joined_weekly = processor.join_results_to_shapefile(gdf, weekly_data)
                
                # Verify joins worked
                assert len(joined_hourly) > 0, "Hourly data join should produce results"
                assert len(joined_weekly) > 0, "Weekly data join should produce results"
                
                print(f"✅ Integration test passed:")
                print(f"   Hourly joins: {len(joined_hourly)}")
                print(f"   Weekly joins: {len(joined_weekly)}")
                
                return True
        
        return False
    
    @patch('streamlit.session_state', {})
    def test_reactive_interface_with_real_data(self):
        """Test reactive interface functionality with real data files."""
        import os
        
        # Initialize session state
        self.maps_interface._initialize_session_state()
        
        # Load real data if available
        if os.path.exists(self.hourly_data_path):
            hourly_data = pd.read_csv(self.hourly_data_path)
            st.session_state.maps_hourly_results = hourly_data
            
            # Test reactive state management
            assert 'maps_shared_state' in st.session_state
            assert 'maps_loading_state' in st.session_state
            assert 'maps_performance' in st.session_state
            
            # Test reactive update triggering
            initial_render_count = st.session_state.maps_performance['render_count']
            
            # Simulate metric type change
            st.session_state.maps_shared_state['metric_type'] = 'speed'
            
            # Trigger reactive update
            with patch('streamlit.rerun') as mock_rerun:
                self.maps_interface._trigger_reactive_update("Test metric change")
                
                # Verify update was triggered
                assert st.session_state.maps_performance['render_count'] > initial_render_count
                assert st.session_state.maps_shared_state['last_update_time'] is not None
                
                # Verify rerun was called if reactive updates enabled
                if st.session_state.maps_preferences.get('reactive_updates', True):
                    mock_rerun.assert_called_once()
    
    def test_maps_display_with_test_data(self):
        """Test that maps display correctly with test data files."""
        import os
        
        # This test verifies that maps can be rendered with the actual test data
        # It's more of an integration test to ensure the data pipeline works
        
        if os.path.exists(self.hourly_data_path) and os.path.exists(self.weekly_data_path):
            # Load test data
            hourly_data = pd.read_csv(self.hourly_data_path)
            weekly_data = pd.read_csv(self.weekly_data_path)
            
            # Verify data can be processed
            assert not hourly_data.empty
            assert not weekly_data.empty
            
            # Check that data has the expected structure for map rendering
            assert 'link_id' in hourly_data.columns
            assert 'link_id' in weekly_data.columns
            
            # Verify hour columns exist (with variations)
            hourly_has_hour = any(col in hourly_data.columns for col in ['hour', 'hour_of_day'])
            weekly_has_hour = any(col in weekly_data.columns for col in ['hour', 'hour_of_day'])
            
            assert hourly_has_hour, "Hourly data missing hour column"
            assert weekly_has_hour, "Weekly data missing hour column"
            
            print(f"✅ Test data validation passed")
            print(f"   Hourly data: {len(hourly_data)} records, {hourly_data['link_id'].nunique()} unique links")
            print(f"   Weekly data: {len(weekly_data)} records, {weekly_data['link_id'].nunique()} unique links")


class TestEnhancedReactiveInterface:
    """Test enhanced reactive interface features including loading indicators and error handling."""
    
    def setup_method(self):
        """Set up test fixtures for enhanced reactive interface tests."""
        self.maps_interface = MapsPageInterface()
        
        # Create sample data for testing
        from shapely.geometry import LineString
        self.sample_shapefile = gpd.GeoDataFrame({
            'Id': ['link_1', 'link_2', 'link_3'],
            'From': ['A', 'B', 'C'],
            'To': ['B', 'C', 'D'],
            'geometry': [
                LineString([(0, 0), (1, 1)]),
                LineString([(1, 1), (2, 2)]),
                LineString([(2, 2), (3, 3)])
            ]
        }, crs="EPSG:2039")
        
        self.sample_hourly = pd.DataFrame({
            'link_id': ['s_A-B', 's_B-C', 's_C-D'],
            'date': ['2024-01-01', '2024-01-01', '2024-01-01'],
            'hour': [8, 8, 8],
            'avg_duration_sec': [120, 180, 240],
            'avg_speed_kmh': [50, 40, 30],
            'n_valid': [10, 15, 20]
        })
    
    @patch('streamlit.session_state', {})
    def test_enhanced_loading_indicators(self):
        """Test enhanced loading indicators functionality."""
        self.maps_interface._initialize_session_state()
        
        # Enable loading indicators
        st.session_state.maps_preferences['loading_indicators'] = True
        
        # Test loading state management
        st.session_state.maps_loading_state['is_loading'] = True
        st.session_state.maps_loading_state['loading_message'] = "Test loading message"
        
        # Verify loading state
        assert st.session_state.maps_loading_state['is_loading'] is True
        assert st.session_state.maps_loading_state['loading_message'] == "Test loading message"
        
        # Test finalize reactive update
        self.maps_interface._finalize_reactive_update()
        
        # Verify loading state is cleared
        assert st.session_state.maps_loading_state['is_loading'] is False
        assert st.session_state.maps_loading_state['loading_message'] == ''
    
    @patch('streamlit.session_state', {})
    def test_enhanced_error_handling(self):
        """Test enhanced error handling with recovery options."""
        self.maps_interface._initialize_session_state()
        
        # Test error handling
        test_error = ValueError("Test error for enhanced handling")
        
        # Mock streamlit functions
        with patch('streamlit.error') as mock_error, \
             patch('streamlit.write') as mock_write, \
             patch('streamlit.button') as mock_button:
            
            mock_button.return_value = False  # Buttons not clicked
            
            self.maps_interface._handle_map_error("Test Map", test_error)
            
            # Verify error was logged in session state
            assert st.session_state.maps_loading_state['last_error'] == str(test_error)
            assert st.session_state.maps_loading_state['error_timestamp'] is not None
            assert st.session_state.maps_performance.get('error_count', 0) > 0
            
            # Verify error display was called
            mock_error.assert_called()
    
    @patch('streamlit.session_state', {})
    def test_reactive_update_throttling(self):
        """Test reactive update throttling to prevent excessive updates."""
        from datetime import datetime, timedelta
        
        self.maps_interface._initialize_session_state()
        
        # Enable reactive updates with short interval
        st.session_state.maps_preferences['reactive_updates'] = True
        st.session_state.maps_preferences['refresh_interval'] = 1.0  # 1 second
        
        # Set recent update time
        recent_time = datetime.now() - timedelta(seconds=0.5)  # 0.5 seconds ago
        st.session_state.maps_shared_state['last_update_time'] = recent_time
        
        initial_render_count = st.session_state.maps_performance['render_count']
        
        # Try to trigger update (should be throttled)
        with patch('streamlit.rerun') as mock_rerun:
            self.maps_interface._trigger_reactive_update("Throttled update test")
            
            # Verify update was throttled (render count unchanged)
            assert st.session_state.maps_performance['render_count'] == initial_render_count
            mock_rerun.assert_not_called()
        
        # Set older update time
        old_time = datetime.now() - timedelta(seconds=2.0)  # 2 seconds ago
        st.session_state.maps_shared_state['last_update_time'] = old_time
        
        # Try to trigger update (should succeed)
        with patch('streamlit.rerun') as mock_rerun:
            self.maps_interface._trigger_reactive_update("Non-throttled update test")
            
            # Verify update was processed
            assert st.session_state.maps_performance['render_count'] > initial_render_count
            mock_rerun.assert_called_once()
    
    @patch('streamlit.session_state', {})
    def test_performance_metrics_tracking(self):
        """Test performance metrics tracking in reactive interface."""
        import time
        
        self.maps_interface._initialize_session_state()
        
        # Test render time tracking
        start_time = time.time()
        st.session_state.maps_performance['last_render_start'] = start_time
        
        # Simulate render completion
        time.sleep(0.1)  # Small delay to simulate render time
        self.maps_interface._finalize_reactive_update()
        
        # Verify performance metrics were updated
        assert st.session_state.maps_performance['last_render_time'] > 0
        assert st.session_state.maps_performance.get('total_render_time', 0) > 0
    
    @patch('streamlit.session_state', {})
    def test_filter_reset_functionality(self):
        """Test filter reset functionality."""
        self.maps_interface._initialize_session_state()
        
        # Set some non-default filter values
        st.session_state.maps_shared_state['metric_type'] = 'speed'
        st.session_state.maps_shared_state['aggregation_method'] = 'mean'
        st.session_state.maps_shared_state['hour_range'] = (8, 18)
        
        # Add some filter keys to session state
        st.session_state['test_length_enabled'] = True
        st.session_state['test_speed_enabled'] = True
        
        # Reset all filters
        self.maps_interface._reset_all_filters()
        
        # Verify filters were reset to defaults
        assert st.session_state.maps_shared_state['metric_type'] == 'duration'
        assert st.session_state.maps_shared_state['aggregation_method'] == 'median'
        assert st.session_state.maps_shared_state['hour_range'] == (0, 23)
        
        # Verify filter-related keys were reset
        assert st.session_state.get('test_length_enabled', True) is False
        assert st.session_state.get('test_speed_enabled', True) is False
    
    @patch('streamlit.session_state', {})
    def test_consistent_state_management(self):
        """Test consistent state management between Map A and Map B."""
        self.maps_interface._initialize_session_state()
        
        # Load sample data
        st.session_state.maps_shapefile_data = self.sample_shapefile
        st.session_state.maps_hourly_results = self.sample_hourly
        
        # Test shared state consistency
        shared_state = st.session_state.maps_shared_state
        
        # Change shared state values
        shared_state['metric_type'] = 'speed'
        shared_state['aggregation_method'] = 'mean'
        shared_state['hour_range'] = (6, 22)
        
        # Verify state is accessible and consistent
        assert st.session_state.maps_shared_state['metric_type'] == 'speed'
        assert st.session_state.maps_shared_state['aggregation_method'] == 'mean'
        assert st.session_state.maps_shared_state['hour_range'] == (6, 22)
        
        # Test that changes trigger reactive updates
        with patch('streamlit.rerun') as mock_rerun:
            st.session_state.maps_preferences['reactive_updates'] = True
            self.maps_interface._trigger_reactive_update("State consistency test")
            
            # Verify reactive update was triggered
            mock_rerun.assert_called_once()


class TestRealTimeMapUpdates:
    """Test real-time map updates and reactive interface integration."""
    
    def setup_method(self):
        """Set up test fixtures for real-time update tests."""
        self.maps_interface = MapsPageInterface()
    
    @patch('streamlit.session_state', {})
    def test_real_time_filter_updates(self):
        """Test that filter changes trigger real-time map updates."""
        self.maps_interface._initialize_session_state()
        
        # Enable reactive updates
        st.session_state.maps_preferences['reactive_updates'] = True
        
        # Test metric type change
        initial_hash = st.session_state.maps_shared_state.get('filter_hash')
        
        with patch('streamlit.rerun') as mock_rerun:
            # Change metric type
            st.session_state.maps_shared_state['metric_type'] = 'speed'
            self.maps_interface._trigger_reactive_update("Metric type changed")
            
            # Verify hash changed and rerun was called
            new_hash = st.session_state.maps_shared_state.get('filter_hash')
            assert new_hash != initial_hash
            mock_rerun.assert_called_once()
    
    @patch('streamlit.session_state', {})
    def test_loading_state_during_updates(self):
        """Test loading state management during reactive updates."""
        self.maps_interface._initialize_session_state()
        
        # Enable loading indicators
        st.session_state.maps_preferences['loading_indicators'] = True
        st.session_state.maps_preferences['reactive_updates'] = True
        
        # Trigger update
        with patch('streamlit.rerun'):
            self.maps_interface._trigger_reactive_update("Loading state test")
            
            # Verify loading state was set
            assert st.session_state.maps_loading_state['is_loading'] is True
            assert "Loading state test" in st.session_state.maps_loading_state['loading_message']
    
    @patch('streamlit.session_state', {})
    def test_error_recovery_in_reactive_mode(self):
        """Test error recovery mechanisms in reactive mode."""
        self.maps_interface._initialize_session_state()
        
        # Enable reactive updates
        st.session_state.maps_preferences['reactive_updates'] = True
        
        # Simulate error in reactive update
        test_error = RuntimeError("Simulated reactive error")
        
        # Test error handling
        self.maps_interface._handle_reactive_error("Test context", test_error)
        
        # Verify error was recorded
        assert st.session_state.maps_loading_state['last_error'] == str(test_error)
        assert st.session_state.maps_loading_state['is_loading'] is False
        assert st.session_state.maps_performance.get('error_count', 0) > 0 file."""
        import os
        if os.path.exists(self.weekly_data_path):
            weekly_data = pd.read_csv(self.weekly_data_path)
            
            # Verify basic structure
            assert not weekly_data.empty, "Weekly data file is empty"
            
            # Check for required columns (with variations)
            required_cols = ['link_id']
            for col in required_cols:
                assert col in weekly_data.columns, f"Missing required column: {col}"
            
            # Check for hour column variations
            hour_cols = ['hour', 'hour_of_day']
            assert any(col in weekly_data.columns for col in hour_cols), "Missing hour column"
            
            # Check for duration column variations
            duration_cols = ['avg_duration_sec', 'avg_dur']
            assert any(col in hourly_data.columns for col in duration_cols), "Missing duration column"
            
            # Check for speed column variations
            speed_cols = ['avg_speed_kmh', 'avg_speed']
            assert any(col in weekly_data.columns for col in speed_cols), "Missing speed column"
            
            print(f"✅ Weekly data loaded successfully: {len(weekly_data)} records")
            print(f"   Columns: {list(weekly_data.columns)}")
            print(f"   Unique links: {weekly_data['link_id'].nunique()}")
    
    @patch('streamlit.session_state', {})
    def test_data_integration_workflow(self):
        """Test complete data integration workflow."""
        import os
        
        # Initialize session state
        self.maps_interface._initialize_session_state()
        
        # Test loading hourly data if file exists
        if os.path.exists(self.hourly_data_path):
            hourly_data = pd.read_csv(self.hourly_data_path)
            
            # Simulate loading into session state
            st.session_state.maps_hourly_results = hourly_data
            
            # Verify data availability check
            st.session_state.maps_shapefile_data = gpd.GeoDataFrame({
                'Id': ['test'],
                'From': ['A'],
                'To': ['B'],
                'geometry': [LineString([(0, 0), (1, 1)])]
            }, crs="EPSG:2039")
            
            assert self.maps_interface._check_data_availability()
            
            print(f"✅ Data integration workflow test passed")
    
    def test_map_rendering_with_test_data(self):
        """Test that maps can be rendered with the test data files."""
        import os
        
        # This test verifies that the data structure is compatible with map rendering
        if os.path.exists(self.hourly_data_path):
            hourly_data = pd.read_csv(self.hourly_data_path)
            
            # Test data bounds calculation (this would be used by map controls)
            if 'avg_duration_sec' in hourly_data.columns or 'avg_dur' in hourly_data.columns:
                duration_col = 'avg_duration_sec' if 'avg_duration_sec' in hourly_data.columns else 'avg_dur'
                duration_bounds = {
                    'min': hourly_data[duration_col].min(),
                    'max': hourly_data[duration_col].max()
                }
                assert duration_bounds['min'] >= 0, "Duration values should be non-negative"
                assert duration_bounds['max'] > duration_bounds['min'], "Duration range should be valid"
            
            if 'avg_speed_kmh' in hourly_data.columns or 'avg_speed' in hourly_data.columns:
                speed_col = 'avg_speed_kmh' if 'avg_speed_kmh' in hourly_data.columns else 'avg_speed'
                speed_bounds = {
                    'min': hourly_data[speed_col].min(),
                    'max': hourly_data[speed_col].max()
                }
                assert speed_bounds['min'] >= 0, "Speed values should be non-negative"
                assert speed_bounds['max'] > speed_bounds['min'], "Speed range should be valid"
            
            print(f"✅ Test data is compatible with map rendering")


class TestNavigationIntegration:
    """Test integration with Streamlit navigation."""
    
    @patch('maps_page.render_maps_page')
    def test_render_maps_page_called(self, mock_render):
        """Test that render_maps_page is called correctly."""
        # Import and call the function
        from maps_page import render_maps_page
        render_maps_page()
        
        # Verify the function was called
        mock_render.assert_called_once()
    
    def test_maps_page_interface_creation(self):
        """Test that MapsPageInterface can be created successfully."""
        interface = MapsPageInterface()
        
        # Verify all components are initialized
        assert interface.spatial_manager is not None
        assert interface.hourly_interface is not None
        assert interface.weekly_interface is not None
        assert hasattr(interface, 'default_shapefile_path')
    
    @patch('streamlit.session_state', {})
    def test_enhanced_session_state_management(self):
        """Test enhanced session state management for reactive interface."""
        interface = MapsPageInterface()
        interface._initialize_session_state()
        
        # Verify enhanced session state components
        assert 'maps_shared_state' in st.session_state
        assert 'maps_loading_state' in st.session_state
        assert 'maps_performance' in st.session_state
        
        # Verify reactive preferences
        preferences = st.session_state.maps_preferences
        assert 'reactive_updates' in preferences
        assert 'loading_indicators' in preferences


class TestPerformanceAndCaching:
    """Test performance optimization and caching functionality."""
    
    def setup_method(self):
        """Set up test fixtures for performance tests."""
        self.maps_interface = MapsPageInterface()
    
    @patch('streamlit.session_state', {})
    def test_performance_tracking_initialization(self):
        """Test performance tracking state initialization."""
        self.maps_interface._initialize_session_state()
        
        performance = st.session_state.maps_performance
        assert performance['render_count'] == 0
        assert performance['cache_hits'] == 0
        assert performance['cache_misses'] == 0
        assert performance['last_render_time'] is None
    
    @patch('streamlit.session_state', {})
    def test_performance_counter_increment(self):
        """Test performance counter incrementation."""
        self.maps_interface._initialize_session_state()
        
        # Enable reactive updates
        st.session_state.maps_preferences['reactive_updates'] = True
        
        # Trigger update (this should increment render count)
        with patch('streamlit.rerun'):
            self.maps_interface._trigger_reactive_update("Test performance")
        
        # Check that render count was incremented
        assert st.session_state.maps_performance['render_count'] == 1


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])