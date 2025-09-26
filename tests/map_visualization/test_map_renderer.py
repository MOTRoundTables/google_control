"""
Tests for map rendering functionality.

This module tests MapRenderer, LegendGenerator, and BasemapManager classes
for interactive map visualization.
"""

import pytest
import folium
import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point
from unittest.mock import Mock, patch
import tempfile
import os

from map_renderer import (
    MapRenderer, LegendGenerator, BasemapManager, 
    MapVisualizationRenderer
)


class TestMapRenderer:
    """Test MapRenderer class functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.renderer = MapRenderer()
        
        # Create test data
        self.test_data = gpd.GeoDataFrame({
            'Id': ['1', '2', '3'],
            'From': ['A', 'B', 'C'],
            'To': ['B', 'C', 'D'],
            'avg_speed_kmh': [45.5, 32.1, 67.8],
            'avg_duration_sec': [120, 180, 90],
            'n_valid': [10, 15, 8],
            'geometry': [
                LineString([(34.0, 31.0), (34.1, 31.1)]),
                LineString([(34.1, 31.1), (34.2, 31.2)]),
                LineString([(34.2, 31.2), (34.3, 31.3)])
            ]
        }, crs="EPSG:2039")
    
    def test_create_base_map_default(self):
        """Test creating base map with default parameters."""
        map_obj = self.renderer.create_base_map()
        
        assert isinstance(map_obj, folium.Map)
        assert map_obj.location == [31.5, 34.8]  # Default center
        assert map_obj.zoom_start == 10  # Default zoom
    
    def test_create_base_map_with_bounds(self):
        """Test creating base map with specified bounds."""
        bounds = (34.0, 31.0, 34.3, 31.3)
        map_obj = self.renderer.create_base_map(bounds)
        
        assert isinstance(map_obj, folium.Map)
        # Check that center is calculated from bounds
        expected_center = [31.15, 34.15]  # (miny+maxy)/2, (minx+maxx)/2
        assert map_obj.location == expected_center
    
    def test_add_network_layer_empty_data(self):
        """Test adding network layer with empty data."""
        map_obj = folium.Map()
        empty_data = gpd.GeoDataFrame(columns=['geometry'], crs="EPSG:2039")
        
        result_map = self.renderer.add_network_layer(map_obj, empty_data, {})
        
        assert result_map is map_obj
        # Should not add any features
        assert len([child for child in map_obj._children.values() 
                   if hasattr(child, 'data')]) == 0
    
    def test_add_network_layer_with_data(self):
        """Test adding network layer with valid data."""
        map_obj = folium.Map()
        style_config = {
            'color': '#ff0000',
            'weight': 5,
            'opacity': 0.9
        }
        
        result_map = self.renderer.add_network_layer(map_obj, self.test_data, style_config)
        
        assert result_map is map_obj
        # Should add GeoJson features
        geojson_children = [child for child in map_obj._children.values() 
                           if 'GeoJson' in str(type(child))]
        assert len(geojson_children) == len(self.test_data)
    
    def test_add_controls_default(self):
        """Test adding default controls to map."""
        map_obj = folium.Map()
        control_config = {'fullscreen': True}
        
        result_map = self.renderer.add_controls(map_obj, control_config)
        
        assert result_map is map_obj
        # Check that fullscreen control was added
        fullscreen_controls = [child for child in map_obj._children.values() 
                              if 'Fullscreen' in str(type(child))]
        assert len(fullscreen_controls) > 0
    
    def test_add_controls_layer_control(self):
        """Test adding layer control to map."""
        map_obj = folium.Map()
        control_config = {'layer_control': True}
        
        result_map = self.renderer.add_controls(map_obj, control_config)
        
        assert result_map is map_obj
        # Check that layer control was added
        layer_controls = [child for child in map_obj._children.values() 
                         if 'LayerControl' in str(type(child))]
        assert len(layer_controls) > 0
    
    @patch('map_renderer.st_folium')
    def test_render_to_streamlit(self, mock_st_folium):
        """Test rendering map to Streamlit."""
        map_obj = folium.Map()
        
        self.renderer.render_to_streamlit(map_obj, height=500)
        
        mock_st_folium.assert_called_once_with(
            map_obj, width=None, height=500, returned_objects=["last_clicked"]
        )
    
    def test_create_popup_content(self):
        """Test creating popup content for features."""
        feature = pd.Series({
            'Id': 'test_link',
            'From': 'NodeA',
            'To': 'NodeB',
            'avg_speed_kmh': 45.5,
            'avg_duration_sec': 120,
            'n_valid': 10
        })
        
        popup_content = self.renderer._create_popup_content(feature)
        
        assert 'test_link' in popup_content
        assert 'NodeA' in popup_content
        assert 'NodeB' in popup_content
        assert '45.5 km/h' in popup_content
        assert '2.0 minutes' in popup_content
        assert '10' in popup_content
    
    def test_create_tooltip_content(self):
        """Test creating tooltip content for features."""
        feature = pd.Series({
            'Id': 'test_link',
            'avg_speed_kmh': 45.5
        })
        
        tooltip_content = self.renderer._create_tooltip_content(feature)
        
        assert 'test_link' in tooltip_content
        assert '45.5 km/h' in tooltip_content


class TestLegendGenerator:
    """Test LegendGenerator class functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.legend_generator = LegendGenerator()
    
    def test_create_legend_basic(self):
        """Test creating basic legend."""
        title = "Speed (km/h)"
        class_breaks = [0, 20, 40, 60, 80]
        colors = ['#green', '#yellow', '#orange', '#red']
        
        legend_html = self.legend_generator.create_legend(title, class_breaks, colors)
        
        assert title in legend_html
        assert '0.0 - 20.0' in legend_html
        assert '20.0 - 40.0' in legend_html
        assert '#green' in legend_html
        assert '#red' in legend_html
    
    def test_create_legend_with_filters(self):
        """Test creating legend with active filters."""
        title = "Duration (minutes)"
        class_breaks = [0, 5, 10, 15]
        colors = ['#green', '#yellow', '#red']
        active_filters = ['Date: 2025-01-01', 'Hour: 8:00-9:00']
        
        legend_html = self.legend_generator.create_legend(
            title, class_breaks, colors, active_filters
        )
        
        assert title in legend_html
        assert 'Active Filters' in legend_html
        assert 'Date: 2025-01-01' in legend_html
        assert 'Hour: 8:00-9:00' in legend_html
    
    def test_create_legend_with_outlier_caps(self):
        """Test creating legend with outlier caps."""
        title = "Speed (km/h)"
        class_breaks = [10, 30, 50, 70, 90]
        colors = ['#green', '#yellow', '#orange', '#red']
        outlier_caps = (5, 95)
        
        legend_html = self.legend_generator.create_legend(
            title, class_breaks, colors, outlier_caps=outlier_caps
        )
        
        assert title in legend_html
        assert 'Capped: 5th - 95th percentile' in legend_html
    
    def test_create_legend_with_units_duration(self):
        """Test creating legend with duration units."""
        class_breaks = [0, 2, 4, 6, 8]
        colors = ['#green', '#yellow', '#orange', '#red']
        
        legend_html = self.legend_generator.create_legend_with_units(
            'duration', class_breaks, colors
        )
        
        assert 'Duration (minutes)' in legend_html
    
    def test_create_legend_with_units_speed(self):
        """Test creating legend with speed units."""
        class_breaks = [0, 25, 50, 75, 100]
        colors = ['#red', '#orange', '#yellow', '#green']
        
        legend_html = self.legend_generator.create_legend_with_units(
            'speed', class_breaks, colors
        )
        
        assert 'Speed (km/h)' in legend_html
    
    def test_format_active_filters(self):
        """Test formatting filter state into descriptions."""
        filter_state = {
            'date_range': ('2025-01-01', '2025-01-07'),
            'hour_range': (8, 17),
            'length_filter': (100, 1000),
            'speed_filter': (20.0, 80.0),
            'text_search': 'main_street',
            'spatial_selection_active': True
        }
        
        filters = self.legend_generator.format_active_filters(filter_state)
        
        assert 'Dates: 2025-01-01 to 2025-01-07' in filters
        assert 'Hours: 8:00-17:00' in filters
        assert 'Length: 100-1000m' in filters
        assert 'Speed: 20.0-80.0 km/h' in filters
        assert "Search: 'main_street'" in filters
        assert 'Spatial selection active' in filters
    
    def test_add_legend_to_map(self):
        """Test adding legend to Folium map."""
        map_obj = folium.Map()
        legend_html = "<div>Test Legend</div>"
        
        result_map = self.legend_generator.add_legend_to_map(map_obj, legend_html)
        
        assert result_map is map_obj
        # Check that HTML element was added
        html_elements = [child for child in map_obj.get_root().html._children 
                        if hasattr(child, 'data') and 'Test Legend' in str(child.data)]
        assert len(html_elements) > 0


class TestBasemapManager:
    """Test BasemapManager class functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.basemap_manager = BasemapManager()
        
        # Create test data for labeling
        self.test_data = gpd.GeoDataFrame({
            'Id': ['slow_link', 'fast_link', 'medium_link'],
            'From': ['A', 'B', 'C'],
            'To': ['B', 'C', 'D'],
            'avg_speed_kmh': [15.0, 65.0, 45.0],
            'avg_duration_sec': [300, 60, 120],
            'length_m': [500, 800, 600],
            'geometry': [
                LineString([(34.0, 31.0), (34.1, 31.1)]),
                LineString([(34.1, 31.1), (34.2, 31.2)]),
                LineString([(34.2, 31.2), (34.3, 31.3)])
            ]
        }, crs="EPSG:2039")
    
    def test_available_basemaps(self):
        """Test that available basemaps are properly configured."""
        assert 'OpenStreetMap' in self.basemap_manager.available_basemaps
        assert 'CartoDB Positron' in self.basemap_manager.available_basemaps
        assert 'None' in self.basemap_manager.available_basemaps
        
        # Check EPSG 2039 compatibility flags
        assert not self.basemap_manager.available_basemaps['OpenStreetMap']['epsg2039_compatible']
        assert self.basemap_manager.available_basemaps['None']['epsg2039_compatible']
    
    def test_add_basemap_options_openstreetmap(self):
        """Test adding OpenStreetMap basemap."""
        map_obj = folium.Map()
        
        result_map = self.basemap_manager.add_basemap_options(map_obj, 'OpenStreetMap')
        
        assert result_map is map_obj
        # Check that tile layer was added
        tile_layers = [child for child in map_obj._children.values() 
                      if 'TileLayer' in str(type(child))]
        assert len(tile_layers) > 0
    
    def test_add_basemap_options_none(self):
        """Test adding no basemap option."""
        map_obj = folium.Map()
        
        result_map = self.basemap_manager.add_basemap_options(map_obj, 'None')
        
        assert result_map is map_obj
        # Should remove default OpenStreetMap tiles
        openstreetmap_children = [key for key in map_obj._children.keys() 
                                 if 'openstreetmap' in key.lower()]
        assert len(openstreetmap_children) == 0
    
    def test_add_multiple_basemaps(self):
        """Test adding multiple basemap options."""
        map_obj = folium.Map()
        basemap_types = ['OpenStreetMap', 'CartoDB Positron']
        
        result_map = self.basemap_manager.add_multiple_basemaps(map_obj, basemap_types)
        
        assert result_map is map_obj
        # Check that layer control was added
        layer_controls = [child for child in map_obj._children.values() 
                         if 'LayerControl' in str(type(child))]
        assert len(layer_controls) > 0
    
    def test_add_link_labels_slowest_speed(self):
        """Test adding labels for slowest links by speed."""
        map_obj = folium.Map()
        label_config = {
            'top_k': 2,
            'metric': 'avg_speed_kmh',
            'label_type': 'slowest',
            'show_values': True
        }
        
        result_map = self.basemap_manager.add_link_labels(map_obj, self.test_data, label_config)
        
        assert result_map is map_obj
        # Check that feature group was added
        feature_groups = [child for child in map_obj._children.values() 
                         if 'FeatureGroup' in str(type(child))]
        assert len(feature_groups) > 0
    
    def test_add_link_labels_longest_duration(self):
        """Test adding labels for longest duration links."""
        map_obj = folium.Map()
        label_config = {
            'top_k': 1,
            'metric': 'avg_duration_sec',
            'label_type': 'longest',
            'show_values': True
        }
        
        result_map = self.basemap_manager.add_link_labels(map_obj, self.test_data, label_config)
        
        assert result_map is map_obj
        # Should add labels for top duration links
        feature_groups = [child for child in map_obj._children.values() 
                         if 'FeatureGroup' in str(type(child))]
        assert len(feature_groups) > 0
    
    def test_add_link_labels_empty_data(self):
        """Test adding labels with empty data."""
        map_obj = folium.Map()
        empty_data = gpd.GeoDataFrame(columns=['geometry'], crs="EPSG:2039")
        label_config = {'top_k': 5, 'metric': 'avg_speed_kmh'}
        
        result_map = self.basemap_manager.add_link_labels(map_obj, empty_data, label_config)
        
        assert result_map is map_obj
        # Should not add any labels
        feature_groups = [child for child in map_obj._children.values() 
                         if 'FeatureGroup' in str(type(child))]
        assert len(feature_groups) == 0
    
    def test_add_link_labels_missing_metric(self):
        """Test adding labels with missing metric column."""
        map_obj = folium.Map()
        label_config = {
            'top_k': 2,
            'metric': 'nonexistent_metric',
            'label_type': 'slowest'
        }
        
        result_map = self.basemap_manager.add_link_labels(map_obj, self.test_data, label_config)
        
        assert result_map is map_obj
        # Should not add any labels due to missing metric
        feature_groups = [child for child in map_obj._children.values() 
                         if 'FeatureGroup' in str(type(child))]
        assert len(feature_groups) == 0
    
    def test_handle_epsg2039_basemap(self):
        """Test handling EPSG 2039 basemap compatibility."""
        map_obj = folium.Map()
        data_bounds = (34.0, 31.0, 34.3, 31.3)
        
        result_map = self.basemap_manager.handle_epsg2039_basemap(map_obj, data_bounds)
        
        assert result_map is map_obj
        # Check that note was added
        html_elements = [child for child in map_obj.get_root().html._children 
                        if hasattr(child, 'data') and 'EPSG:2039' in str(child.data)]
        assert len(html_elements) > 0
    
    def test_clear_labels(self):
        """Test clearing existing labels from map."""
        map_obj = folium.Map()
        
        # Add some labels first
        label_config = {'top_k': 1, 'metric': 'avg_speed_kmh'}
        self.basemap_manager.add_link_labels(map_obj, self.test_data, label_config)
        
        # Verify labels were added
        feature_groups_before = [child for child in map_obj._children.values() 
                               if 'FeatureGroup' in str(type(child))]
        assert len(feature_groups_before) > 0
        
        # Clear labels
        result_map = self.basemap_manager.clear_labels(map_obj)
        
        assert result_map is map_obj


class TestMapVisualizationRenderer:
    """Test MapVisualizationRenderer integration class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.renderer = MapVisualizationRenderer()
        
        # Create test data
        self.test_data = gpd.GeoDataFrame({
            'Id': ['1', '2'],
            'From': ['A', 'B'],
            'To': ['B', 'C'],
            'avg_speed_kmh': [45.5, 32.1],
            'avg_duration_sec': [120, 180],
            'geometry': [
                LineString([(34.0, 31.0), (34.1, 31.1)]),
                LineString([(34.1, 31.1), (34.2, 31.2)])
            ]
        }, crs="EPSG:2039")
    
    def test_create_interactive_map_complete(self):
        """Test creating complete interactive map with all components."""
        style_config = {
            'color': '#ff0000',
            'weight': 3,
            'opacity': 0.8
        }
        legend_config = {
            'title': 'Speed (km/h)',
            'class_breaks': [0, 25, 50, 75, 100],
            'colors': ['#green', '#yellow', '#orange', '#red']
        }
        control_config = {
            'fullscreen': True,
            'layer_control': False
        }
        
        map_obj = self.renderer.create_interactive_map(
            self.test_data, style_config, legend_config, control_config
        )
        
        assert isinstance(map_obj, folium.Map)
        
        # Check that network layer was added
        geojson_children = [child for child in map_obj._children.values() 
                           if 'GeoJson' in str(type(child))]
        assert len(geojson_children) == len(self.test_data)
        
        # Check that legend was added
        html_elements = [child for child in map_obj.get_root().html._children 
                        if hasattr(child, 'data') and 'Speed (km/h)' in str(child.data)]
        assert len(html_elements) > 0
        
        # Check that controls were added
        fullscreen_controls = [child for child in map_obj._children.values() 
                              if 'Fullscreen' in str(type(child))]
        assert len(fullscreen_controls) > 0
    
    def test_create_interactive_map_empty_data(self):
        """Test creating interactive map with empty data."""
        empty_data = gpd.GeoDataFrame(columns=['geometry'], crs="EPSG:2039")
        style_config = {}
        legend_config = None
        
        map_obj = self.renderer.create_interactive_map(
            empty_data, style_config, legend_config
        )
        
        assert isinstance(map_obj, folium.Map)
        # Should still create map but with no features
        geojson_children = [child for child in map_obj._children.values() 
                           if 'GeoJson' in str(type(child))]
        assert len(geojson_children) == 0
    
    def test_renderer_components_initialization(self):
        """Test that all renderer components are properly initialized."""
        assert isinstance(self.renderer.renderer, MapRenderer)
        assert isinstance(self.renderer.legend_generator, LegendGenerator)
        assert isinstance(self.renderer.basemap_manager, BasemapManager)


if __name__ == '__main__':
    pytest.main([__file__])