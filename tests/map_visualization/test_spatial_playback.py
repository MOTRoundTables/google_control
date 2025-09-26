"""
Tests for spatial selection tools and playback animation functionality.

This module tests the enhanced spatial selection and playback animation features
for the interactive map visualization system.
"""

import pytest
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString, box, Polygon
from unittest.mock import Mock, patch, MagicMock
import streamlit as st

# Import the classes to test
from controls import SpatialSelection, PlaybackController, InteractiveControls


class TestSpatialSelection:
    """Test cases for spatial selection tools."""
    
    @pytest.fixture
    def sample_geodataframe(self):
        """Create sample GeoDataFrame for testing."""
        # Create sample network data
        data = {
            'link_id': ['s_1-2', 's_2-3', 's_3-4', 's_4-5', 's_5-6'],
            'From': ['1', '2', '3', '4', '5'],
            'To': ['2', '3', '4', '5', '6'],
            'Id': ['link1', 'link2', 'link3', 'link4', 'link5'],
            'avg_speed_kmh': [45.5, 32.1, 67.8, 23.4, 55.2],
            'avg_duration_sec': [120, 180, 90, 240, 110],
            'length_m': [1000, 1500, 800, 2000, 900],
            'geometry': [
                LineString([(0, 0), (1, 0)]),
                LineString([(1, 0), (2, 0)]),
                LineString([(2, 0), (3, 0)]),
                LineString([(3, 0), (4, 0)]),
                LineString([(4, 0), (5, 0)])
            ]
        }
        
        gdf = gpd.GeoDataFrame(data, crs='EPSG:2039')
        return gdf
    
    @pytest.fixture
    def spatial_selection(self):
        """Create SpatialSelection instance."""
        return SpatialSelection()
    
    def test_spatial_selection_initialization(self, spatial_selection):
        """Test SpatialSelection initialization."""
        assert spatial_selection.selection_types == ['box', 'lasso', 'text_search']
        assert spatial_selection.active_selection is None
        assert spatial_selection.selection_geometry is None
    
    def test_apply_enhanced_text_search_basic(self, spatial_selection, sample_geodataframe):
        """Test basic enhanced text search functionality."""
        # Test search by link_id
        result = spatial_selection.apply_enhanced_text_search(
            sample_geodataframe, 'link_id', 's_1-2'
        )
        assert len(result) == 1
        assert result.iloc[0]['link_id'] == 's_1-2'
        
        # Test search by From field
        result = spatial_selection.apply_enhanced_text_search(
            sample_geodataframe, 'From', '2'
        )
        assert len(result) == 1
        assert result.iloc[0]['From'] == '2'
        
        # Test search by To field
        result = spatial_selection.apply_enhanced_text_search(
            sample_geodataframe, 'To', '3'
        )
        assert len(result) == 1
        assert result.iloc[0]['To'] == '3'
    
    def test_apply_enhanced_text_search_case_sensitive(self, spatial_selection, sample_geodataframe):
        """Test case-sensitive text search."""
        # Add mixed case data
        sample_geodataframe.loc[0, 'Id'] = 'Link1'
        sample_geodataframe.loc[1, 'Id'] = 'LINK2'
        
        # Case insensitive (default)
        result = spatial_selection.apply_enhanced_text_search(
            sample_geodataframe, 'Id', 'link', case_sensitive=False
        )
        assert len(result) >= 2
        
        # Case sensitive
        result = spatial_selection.apply_enhanced_text_search(
            sample_geodataframe, 'Id', 'link', case_sensitive=True
        )
        assert len(result) == 1  # Only 'link3', 'link4', 'link5' match
    
    def test_apply_enhanced_text_search_exact_match(self, spatial_selection, sample_geodataframe):
        """Test exact match text search."""
        # Exact match
        result = spatial_selection.apply_enhanced_text_search(
            sample_geodataframe, 'From', '2', exact_match=True
        )
        assert len(result) == 1
        assert result.iloc[0]['From'] == '2'
        
        # Partial match (default)
        result = spatial_selection.apply_enhanced_text_search(
            sample_geodataframe, 'link_id', 's_', exact_match=False
        )
        assert len(result) == 5  # All links contain 's_'
    
    def test_apply_enhanced_text_search_multi_search(self, spatial_selection, sample_geodataframe):
        """Test multi-term text search."""
        multi_search_terms = "s_1-2\ns_3-4\ns_5-6"
        
        result = spatial_selection.apply_enhanced_text_search(
            sample_geodataframe, 'link_id', '', multi_search=multi_search_terms
        )
        assert len(result) == 3
        expected_ids = ['s_1-2', 's_3-4', 's_5-6']
        assert all(link_id in result['link_id'].values for link_id in expected_ids)
    
    def test_apply_spatial_filter_box(self, spatial_selection, sample_geodataframe):
        """Test spatial filtering with box selection."""
        # Create a box that intersects with first 3 links
        selection_box = box(0, -0.5, 2.5, 0.5)
        
        result = spatial_selection.apply_spatial_filter(sample_geodataframe, selection_box)
        assert len(result) == 3  # First 3 links should intersect
        
        # Verify correct links are selected
        expected_ids = ['s_1-2', 's_2-3', 's_3-4']
        assert all(link_id in result['link_id'].values for link_id in expected_ids)
    
    def test_apply_spatial_filter_polygon(self, spatial_selection, sample_geodataframe):
        """Test spatial filtering with polygon selection."""
        # Create a polygon that intersects with middle links
        selection_polygon = Polygon([(1.5, -0.5), (3.5, -0.5), (3.5, 0.5), (1.5, 0.5)])
        
        result = spatial_selection.apply_spatial_filter(sample_geodataframe, selection_polygon)
        assert len(result) == 2  # Links 2-3 and 3-4 should intersect
        
        expected_ids = ['s_2-3', 's_3-4']
        assert all(link_id in result['link_id'].values for link_id in expected_ids)
    
    def test_handle_spatial_selection_text_search(self, spatial_selection, sample_geodataframe):
        """Test handle_spatial_selection with text search."""
        result = spatial_selection.handle_spatial_selection(
            'text_search', 
            sample_geodataframe,
            search_field='link_id',
            search_value='s_2-3'
        )
        assert len(result) == 1
        assert result.iloc[0]['link_id'] == 's_2-3'
    
    def test_handle_spatial_selection_box(self, spatial_selection, sample_geodataframe):
        """Test handle_spatial_selection with box selection."""
        selection_box = box(0, -0.5, 1.5, 0.5)
        
        result = spatial_selection.handle_spatial_selection(
            'box',
            sample_geodataframe,
            selection_geometry=selection_box
        )
        assert len(result) == 2  # First 2 links should intersect
    
    def test_apply_text_search_backward_compatibility(self, spatial_selection, sample_geodataframe):
        """Test backward compatibility of apply_text_search method."""
        result = spatial_selection.apply_text_search(
            sample_geodataframe, 'link_id', 's_4-5'
        )
        assert len(result) == 1
        assert result.iloc[0]['link_id'] == 's_4-5'
    
    def test_text_search_invalid_field(self, spatial_selection, sample_geodataframe):
        """Test text search with invalid field name."""
        result = spatial_selection.apply_enhanced_text_search(
            sample_geodataframe, 'invalid_field', 'test'
        )
        # Should return original data when field doesn't exist
        assert len(result) == len(sample_geodataframe)
    
    def test_text_search_empty_value(self, spatial_selection, sample_geodataframe):
        """Test text search with empty search value."""
        result = spatial_selection.apply_enhanced_text_search(
            sample_geodataframe, 'link_id', ''
        )
        # Should return original data when no search terms
        assert len(result) == len(sample_geodataframe)


class TestPlaybackController:
    """Test cases for playback animation system."""
    
    @pytest.fixture
    def playback_controller(self):
        """Create PlaybackController instance."""
        return PlaybackController()
    
    def test_playback_controller_initialization(self, playback_controller):
        """Test PlaybackController initialization."""
        assert playback_controller.playback_speeds == [0.25, 0.5, 1.0, 2.0, 4.0, 8.0]
        assert playback_controller.throttle_interval == 1.0
        assert playback_controller.playback_state['is_playing'] is False
        assert playback_controller.playback_state['current_hour'] == 0
    
    def test_create_playback_controls(self, playback_controller):
        """Test creation of playback controls configuration."""
        time_range = (6, 22)
        config = playback_controller.create_playback_controls(time_range)
        
        assert config['enabled'] is True
        assert config['time_range'] == time_range
        assert config['current_hour'] == 6
        assert config['is_playing'] is False
        assert config['playback_speed'] == 1.0
        assert config['loop_playback'] is True
        assert config['auto_advance'] is False
        assert config['throttle_fps'] == 2
        assert config['step_size'] == 1
    
    def test_should_update_frame_not_playing(self, playback_controller):
        """Test frame update check when not playing."""
        config = {'is_playing': False}
        assert playback_controller.should_update_frame(config) is False
    
    def test_should_update_frame_throttling(self, playback_controller):
        """Test frame update throttling."""
        config = {
            'is_playing': True,
            'throttle_fps': 2
        }
        
        # First call should return True
        assert playback_controller.should_update_frame(config) is True
        
        # Immediate second call should return False (throttled)
        assert playback_controller.should_update_frame(config) is False
    
    def test_advance_playback_normal(self, playback_controller):
        """Test normal playback advancement."""
        config = {
            'is_playing': True,
            'current_hour': 10,
            'time_range': (6, 22),
            'step_size': 1,
            'loop_playback': True,
            'throttle_fps': 10  # High FPS to avoid throttling
        }
        
        # Mock session state
        with patch('streamlit.session_state', {}):
            updated_config = playback_controller.advance_playback(config, "test")
            assert updated_config['current_hour'] == 11
    
    def test_advance_playback_loop(self, playback_controller):
        """Test playback looping at end of range."""
        config = {
            'is_playing': True,
            'current_hour': 22,  # At end of range
            'time_range': (6, 22),
            'step_size': 1,
            'loop_playback': True,
            'throttle_fps': 10
        }
        
        with patch('streamlit.session_state', {}):
            updated_config = playback_controller.advance_playback(config, "test")
            assert updated_config['current_hour'] == 6  # Should loop back to start
    
    def test_advance_playback_no_loop(self, playback_controller):
        """Test playback stopping at end when loop is disabled."""
        config = {
            'is_playing': True,
            'current_hour': 22,
            'time_range': (6, 22),
            'step_size': 1,
            'loop_playback': False,
            'throttle_fps': 10
        }
        
        with patch('streamlit.session_state', {}) as mock_session:
            updated_config = playback_controller.advance_playback(config, "test")
            assert updated_config['current_hour'] == 22  # Should stay at end
            assert updated_config['is_playing'] is False  # Should stop playing
            assert mock_session['test_is_playing'] is False
    
    def test_advance_playback_step_size(self, playback_controller):
        """Test playback with different step sizes."""
        config = {
            'is_playing': True,
            'current_hour': 10,
            'time_range': (6, 22),
            'step_size': 3,  # Advance by 3 hours
            'loop_playback': True,
            'throttle_fps': 10
        }
        
        with patch('streamlit.session_state', {}):
            updated_config = playback_controller.advance_playback(config, "test")
            assert updated_config['current_hour'] == 13
    
    def test_get_playback_status(self, playback_controller):
        """Test getting playback status."""
        status = playback_controller.get_playback_status()
        
        assert 'state' in status
        assert 'throttle_interval' in status
        assert 'frame_count' in status
        assert status['throttle_interval'] == 1.0
        assert isinstance(status['state'], dict)
    
    def test_reset_playback_state(self, playback_controller):
        """Test resetting playback state."""
        # Modify state first
        playback_controller.playback_state['is_playing'] = True
        playback_controller.playback_state['current_hour'] = 15
        playback_controller.playback_state['frame_count'] = 100
        
        # Reset state
        playback_controller.reset_playback_state()
        
        # Verify reset
        assert playback_controller.playback_state['is_playing'] is False
        assert playback_controller.playback_state['current_hour'] == 0
        assert playback_controller.playback_state['frame_count'] == 0
        assert playback_controller.playback_state['last_update'] is None


class TestInteractiveControlsIntegration:
    """Integration tests for spatial selection and playback features."""
    
    @pytest.fixture
    def interactive_controls(self):
        """Create InteractiveControls instance."""
        return InteractiveControls()
    
    @pytest.fixture
    def sample_data_bounds(self):
        """Create sample data bounds for testing."""
        return {
            'min_date': pd.Timestamp('2025-01-01').date(),
            'max_date': pd.Timestamp('2025-01-31').date(),
            'min_hour': 6,
            'max_hour': 22,
            'length_m': {'min': 100, 'max': 5000},
            'avg_speed_kmh': {'min': 10, 'max': 80},
            'avg_duration_sec': {'min': 60, 'max': 600}
        }
    
    def test_interactive_controls_initialization(self, interactive_controls):
        """Test InteractiveControls initialization."""
        assert hasattr(interactive_controls, 'filter_controls')
        assert hasattr(interactive_controls, 'spatial_selection')
        assert hasattr(interactive_controls, 'playback_controller')
        assert hasattr(interactive_controls, 'kpi_display')
    
    @patch('streamlit.subheader')
    @patch('streamlit.selectbox')
    @patch('streamlit.text_input')
    @patch('streamlit.checkbox')
    @patch('streamlit.info')
    def test_spatial_selection_integration(self, mock_info, mock_checkbox, mock_text_input, 
                                         mock_selectbox, mock_subheader, interactive_controls):
        """Test spatial selection integration with InteractiveControls."""
        # Mock Streamlit components
        mock_selectbox.side_effect = ['text_search', 'link_id']
        mock_text_input.return_value = 's_1-2'
        mock_checkbox.side_effect = [False, False]  # case_sensitive, exact_match
        
        # Create sample data
        sample_gdf = gpd.GeoDataFrame({
            'link_id': ['s_1-2', 's_2-3'],
            'geometry': [LineString([(0, 0), (1, 0)]), LineString([(1, 0), (2, 0)])]
        })
        
        # Test spatial selection rendering
        result = interactive_controls.spatial_selection.render_spatial_controls(
            sample_gdf, "test"
        )
        
        assert 'type' in result
        assert 'search_field' in result
        assert 'search_value' in result
    
    @patch('streamlit.subheader')
    @patch('streamlit.button')
    @patch('streamlit.slider')
    @patch('streamlit.selectbox')
    @patch('streamlit.session_state', {})
    def test_playback_integration(self, mock_selectbox, mock_slider, mock_button, 
                                mock_subheader, interactive_controls):
        """Test playback controls integration."""
        # Mock Streamlit components
        mock_button.return_value = False
        mock_slider.return_value = 10
        mock_selectbox.return_value = 1.0
        
        time_range = (6, 22)
        
        # Test playback controls rendering
        result = interactive_controls.playback_controller.render_playback_controls(
            time_range, "test"
        )
        
        assert 'is_playing' in result
        assert 'current_hour' in result
        assert 'playback_speed' in result
        assert 'time_range' in result
        assert result['time_range'] == time_range


class TestSpatialPlaybackPerformance:
    """Performance tests for spatial selection and playback features."""
    
    def test_large_dataset_text_search_performance(self):
        """Test text search performance with large dataset."""
        # Create large dataset
        n_links = 10000
        data = {
            'link_id': [f's_{i}-{i+1}' for i in range(n_links)],
            'From': [str(i) for i in range(n_links)],
            'To': [str(i+1) for i in range(n_links)],
            'geometry': [LineString([(i, 0), (i+1, 0)]) for i in range(n_links)]
        }
        
        large_gdf = gpd.GeoDataFrame(data, crs='EPSG:2039')
        spatial_selection = SpatialSelection()
        
        import time
        start_time = time.time()
        
        # Perform text search
        result = spatial_selection.apply_enhanced_text_search(
            large_gdf, 'link_id', 's_5000'
        )
        
        end_time = time.time()
        search_time = end_time - start_time
        
        # Should complete within reasonable time (< 1 second for 10k records)
        assert search_time < 1.0
        assert len(result) == 1
        assert result.iloc[0]['link_id'] == 's_5000-5001'
    
    def test_spatial_filter_performance(self):
        """Test spatial filtering performance."""
        # Create grid of links
        n_side = 100  # 100x100 grid = 10k links
        data = []
        
        for i in range(n_side):
            for j in range(n_side):
                link_id = f's_{i}_{j}-{i}_{j+1}'
                geometry = LineString([(i, j), (i, j+1)])
                data.append({'link_id': link_id, 'geometry': geometry})
        
        large_gdf = gpd.GeoDataFrame(data, crs='EPSG:2039')
        spatial_selection = SpatialSelection()
        
        # Create selection box covering small area
        selection_box = box(10, 10, 20, 20)
        
        import time
        start_time = time.time()
        
        result = spatial_selection.apply_spatial_filter(large_gdf, selection_box)
        
        end_time = time.time()
        filter_time = end_time - start_time
        
        # Should complete within reasonable time
        assert filter_time < 2.0
        assert len(result) > 0  # Should find some intersecting links
    
    def test_playback_throttling_effectiveness(self):
        """Test that playback throttling works effectively."""
        playback_controller = PlaybackController()
        
        config = {
            'is_playing': True,
            'throttle_fps': 2  # 2 FPS = 0.5 second intervals
        }
        
        # First call should pass
        assert playback_controller.should_update_frame(config) is True
        
        # Immediate subsequent calls should be throttled
        for _ in range(5):
            assert playback_controller.should_update_frame(config) is False
        
        # After waiting, should pass again
        import time
        time.sleep(0.6)  # Wait longer than throttle interval
        assert playback_controller.should_update_frame(config) is True


if __name__ == '__main__':
    pytest.main([__file__])