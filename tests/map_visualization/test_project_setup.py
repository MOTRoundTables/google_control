"""
Test project setup and library imports for map visualization.

This module tests that all required libraries can be imported and
the module structure is correctly set up.
"""

import pytest
import sys
import importlib
from pathlib import Path


class TestLibraryImports:
    """Test that all required geospatial libraries can be imported."""
    
    def test_geopandas_import(self):
        """Test that geopandas can be imported."""
        try:
            import geopandas as gpd
            assert hasattr(gpd, 'GeoDataFrame')
            assert hasattr(gpd, 'read_file')
        except ImportError as e:
            pytest.fail(f"Failed to import geopandas: {e}")
    
    def test_folium_import(self):
        """Test that folium can be imported."""
        try:
            import folium
            assert hasattr(folium, 'Map')
            assert hasattr(folium, 'GeoJson')
        except ImportError as e:
            pytest.fail(f"Failed to import folium: {e}")
    
    def test_pyproj_import(self):
        """Test that pyproj can be imported."""
        try:
            import pyproj
            assert hasattr(pyproj, 'CRS')
            assert hasattr(pyproj, 'Transformer')
        except ImportError as e:
            pytest.fail(f"Failed to import pyproj: {e}")
    
    def test_shapely_import(self):
        """Test that shapely can be imported."""
        try:
            from shapely.geometry import LineString, Point, Polygon
            from shapely import ops
            assert LineString is not None
            assert Point is not None
            assert Polygon is not None
        except ImportError as e:
            pytest.fail(f"Failed to import shapely: {e}")
    
    def test_streamlit_import(self):
        """Test that streamlit can be imported (existing dependency)."""
        try:
            import streamlit as st
            assert hasattr(st, 'selectbox')
            assert hasattr(st, 'slider')
        except ImportError as e:
            pytest.fail(f"Failed to import streamlit: {e}")
    
    def test_pandas_import(self):
        """Test that pandas can be imported (existing dependency)."""
        try:
            import pandas as pd
            assert hasattr(pd, 'DataFrame')
            assert hasattr(pd, 'read_csv')
        except ImportError as e:
            pytest.fail(f"Failed to import pandas: {e}")
    
    def test_numpy_import(self):
        """Test that numpy can be imported (existing dependency)."""
        try:
            import numpy as np
            assert hasattr(np, 'array')
            assert hasattr(np, 'linspace')
        except ImportError as e:
            pytest.fail(f"Failed to import numpy: {e}")


class TestModuleStructure:
    """Test that all map visualization modules can be imported."""
    
    def test_spatial_data_module(self):
        """Test that spatial_data module can be imported."""
        try:
            import spatial_data
            assert hasattr(spatial_data, 'SpatialDataLoader')
            assert hasattr(spatial_data, 'CoordinateSystemManager')
            assert hasattr(spatial_data, 'GeometryProcessor')
            assert hasattr(spatial_data, 'SpatialDataManager')
        except ImportError as e:
            pytest.fail(f"Failed to import spatial_data module: {e}")
    
    def test_map_data_module(self):
        """Test that map_data module can be imported."""
        try:
            import map_data
            assert hasattr(map_data, 'DataJoiner')
            assert hasattr(map_data, 'FilterManager')
            assert hasattr(map_data, 'AggregationEngine')
            assert hasattr(map_data, 'MapDataProcessor')
        except ImportError as e:
            pytest.fail(f"Failed to import map_data module: {e}")
    
    def test_map_renderer_module(self):
        """Test that map_renderer module can be imported."""
        try:
            import map_renderer
            assert hasattr(map_renderer, 'MapRenderer')
            assert hasattr(map_renderer, 'LegendGenerator')
            assert hasattr(map_renderer, 'BasemapManager')
            assert hasattr(map_renderer, 'MapVisualizationRenderer')
        except ImportError as e:
            pytest.fail(f"Failed to import map_renderer module: {e}")
    
    def test_symbology_module(self):
        """Test that symbology module can be imported."""
        try:
            import symbology
            assert hasattr(symbology, 'ColorSchemeManager')
            assert hasattr(symbology, 'ClassificationEngine')
            assert hasattr(symbology, 'StyleCalculator')
            assert hasattr(symbology, 'SymbologyEngine')
        except ImportError as e:
            pytest.fail(f"Failed to import symbology module: {e}")
    
    def test_controls_module(self):
        """Test that controls module can be imported."""
        try:
            import controls
            assert hasattr(controls, 'FilterControls')
            assert hasattr(controls, 'SpatialSelection')
            assert hasattr(controls, 'PlaybackController')
            assert hasattr(controls, 'InteractiveControls')
        except ImportError as e:
            pytest.fail(f"Failed to import controls module: {e}")
    
    def test_map_config_module(self):
        """Test that map_config module can be imported."""
        try:
            import map_config
            assert hasattr(map_config, 'MapSymbologyConfig')
            assert hasattr(map_config, 'MapPresetManager')
            assert hasattr(map_config, 'get_map_config')
        except ImportError as e:
            pytest.fail(f"Failed to import map_config module: {e}")


class TestModuleInstantiation:
    """Test that main classes can be instantiated without errors."""
    
    def test_spatial_data_manager_instantiation(self):
        """Test that SpatialDataManager can be instantiated."""
        try:
            from spatial_data import SpatialDataManager
            manager = SpatialDataManager()
            assert manager is not None
            assert hasattr(manager, 'loader')
            assert hasattr(manager, 'crs_manager')
            assert hasattr(manager, 'geometry_processor')
        except Exception as e:
            pytest.fail(f"Failed to instantiate SpatialDataManager: {e}")
    
    def test_map_data_processor_instantiation(self):
        """Test that MapDataProcessor can be instantiated."""
        try:
            from map_data import MapDataProcessor
            processor = MapDataProcessor()
            assert processor is not None
            assert hasattr(processor, 'joiner')
            assert hasattr(processor, 'filter_manager')
            assert hasattr(processor, 'aggregation_engine')
        except Exception as e:
            pytest.fail(f"Failed to instantiate MapDataProcessor: {e}")
    
    def test_map_renderer_instantiation(self):
        """Test that MapRenderer can be instantiated."""
        try:
            from map_renderer import MapRenderer
            renderer = MapRenderer()
            assert renderer is not None
            assert hasattr(renderer, 'target_crs')
            assert hasattr(renderer, 'default_zoom')
        except Exception as e:
            pytest.fail(f"Failed to instantiate MapRenderer: {e}")
    
    def test_symbology_engine_instantiation(self):
        """Test that SymbologyEngine can be instantiated."""
        try:
            from symbology import SymbologyEngine
            engine = SymbologyEngine()
            assert engine is not None
            assert hasattr(engine, 'color_manager')
            assert hasattr(engine, 'classifier')
            assert hasattr(engine, 'style_calculator')
        except Exception as e:
            pytest.fail(f"Failed to instantiate SymbologyEngine: {e}")
    
    def test_interactive_controls_instantiation(self):
        """Test that InteractiveControls can be instantiated."""
        try:
            from controls import InteractiveControls
            controls = InteractiveControls()
            assert controls is not None
            assert hasattr(controls, 'filter_controls')
            assert hasattr(controls, 'spatial_selection')
            assert hasattr(controls, 'playback_controller')
        except Exception as e:
            pytest.fail(f"Failed to instantiate InteractiveControls: {e}")
    
    def test_map_config_instantiation(self):
        """Test that MapSymbologyConfig can be instantiated."""
        try:
            from map_config import MapSymbologyConfig
            config = MapSymbologyConfig()
            assert config is not None
            assert hasattr(config, 'config')
            assert hasattr(config, 'default_config')
        except Exception as e:
            pytest.fail(f"Failed to instantiate MapSymbologyConfig: {e}")


class TestFileStructure:
    """Test that required files and directories exist."""
    
    def test_module_files_exist(self):
        """Test that all module files exist."""
        required_files = [
            'spatial_data.py',
            'map_data.py', 
            'map_renderer.py',
            'symbology.py',
            'controls.py',
            'map_config.py'
        ]
        
        for file_name in required_files:
            file_path = Path(file_name)
            assert file_path.exists(), f"Required module file {file_name} does not exist"
    
    def test_test_directory_structure(self):
        """Test that test directory structure is correct."""
        test_dirs = [
            Path('tests'),
            Path('tests/map_visualization')
        ]
        
        for test_dir in test_dirs:
            assert test_dir.exists(), f"Test directory {test_dir} does not exist"
            assert test_dir.is_dir(), f"{test_dir} is not a directory"
    
    def test_init_files_exist(self):
        """Test that __init__.py files exist in test directories."""
        init_files = [
            Path('tests/__init__.py'),
            Path('tests/map_visualization/__init__.py')
        ]
        
        for init_file in init_files:
            assert init_file.exists(), f"Init file {init_file} does not exist"
    
    def test_pytest_config_exists(self):
        """Test that pytest configuration exists."""
        config_files = [
            Path('pytest.ini'),
            Path('tests/conftest.py')
        ]
        
        for config_file in config_files:
            assert config_file.exists(), f"Pytest config file {config_file} does not exist"
    
    def test_requirements_updated(self):
        """Test that requirements.txt contains geospatial libraries."""
        requirements_file = Path('requirements.txt')
        assert requirements_file.exists(), "requirements.txt does not exist"
        
        with open(requirements_file, 'r') as f:
            content = f.read()
        
        required_libs = ['geopandas', 'folium', 'pyproj', 'shapely']
        for lib in required_libs:
            assert lib in content, f"Required library {lib} not found in requirements.txt"


class TestBasicFunctionality:
    """Test basic functionality of key components."""
    
    def test_coordinate_system_manager_basic(self):
        """Test basic functionality of CoordinateSystemManager."""
        try:
            from spatial_data import CoordinateSystemManager
            manager = CoordinateSystemManager()
            
            # Test target CRS
            assert manager.TARGET_CRS == "EPSG:2039"
            assert manager.target_crs is not None
        except Exception as e:
            pytest.fail(f"CoordinateSystemManager basic test failed: {e}")
    
    def test_color_scheme_manager_basic(self):
        """Test basic functionality of ColorSchemeManager."""
        try:
            from symbology import ColorSchemeManager
            manager = ColorSchemeManager()
            
            # Test palette retrieval
            duration_colors = manager.get_color_palette('duration', 5)
            speed_colors = manager.get_color_palette('speed', 5)
            
            assert len(duration_colors) == 5
            assert len(speed_colors) == 5
            assert all(color.startswith('#') for color in duration_colors)
            assert all(color.startswith('#') for color in speed_colors)
        except Exception as e:
            pytest.fail(f"ColorSchemeManager basic test failed: {e}")
    
    def test_map_config_basic(self):
        """Test basic functionality of MapSymbologyConfig."""
        try:
            from map_config import MapSymbologyConfig
            config = MapSymbologyConfig()
            
            # Test configuration access
            duration_config = config.get_symbology_config('duration')
            speed_config = config.get_symbology_config('speed')
            thresholds = config.get_thresholds()
            
            assert 'palette' in duration_config
            assert 'palette' in speed_config
            assert 'free_flow_speed_kmh' in thresholds
        except Exception as e:
            pytest.fail(f"MapSymbologyConfig basic test failed: {e}")


# Run with: python -m pytest tests/map_visualization/test_project_setup.py -v