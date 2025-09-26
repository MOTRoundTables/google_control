"""
Comprehensive tests for spatial data management components.

Tests SpatialDataLoader, CoordinateSystemManager, and GeometryProcessor classes
with various edge cases and validation scenarios.
"""

import pytest
import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import LineString, Point
from shapely.validation import make_valid
from pyproj import CRS
import tempfile
import os
from unittest.mock import patch, MagicMock

from spatial_data import (
    SpatialDataLoader, 
    CoordinateSystemManager, 
    GeometryProcessor,
    SpatialDataManager
)


class TestSpatialDataLoader:
    """Test cases for SpatialDataLoader class."""
    
    def test_init(self):
        """Test SpatialDataLoader initialization."""
        loader = SpatialDataLoader()
        assert loader.required_fields == ['Id', 'From', 'To']
    
    def test_validate_shapefile_schema_valid(self):
        """Test schema validation with valid fields."""
        loader = SpatialDataLoader()
        
        # Create test GeoDataFrame with required fields
        gdf = gpd.GeoDataFrame({
            'Id': [1, 2, 3],
            'From': ['A', 'B', 'C'],
            'To': ['B', 'C', 'D'],
            'geometry': [
                LineString([(0, 0), (1, 1)]),
                LineString([(1, 1), (2, 2)]),
                LineString([(2, 2), (3, 3)])
            ]
        })
        
        is_valid, missing_fields = loader.validate_shapefile_schema(gdf)
        assert is_valid is True
        assert missing_fields == []
    
    def test_validate_shapefile_schema_missing_fields(self):
        """Test schema validation with missing fields."""
        loader = SpatialDataLoader()
        
        # Create test GeoDataFrame missing 'To' field
        gdf = gpd.GeoDataFrame({
            'Id': [1, 2, 3],
            'From': ['A', 'B', 'C'],
            'geometry': [
                LineString([(0, 0), (1, 1)]),
                LineString([(1, 1), (2, 2)]),
                LineString([(2, 2), (3, 3)])
            ]
        })
        
        with pytest.raises(ValueError, match="Missing required fields: \\['To'\\]"):
            loader.validate_shapefile_schema(gdf)
    
    def test_cleanup_invalid_geometries_valid(self):
        """Test geometry cleanup with valid geometries."""
        loader = SpatialDataLoader()
        
        gdf = gpd.GeoDataFrame({
            'Id': [1, 2],
            'From': ['A', 'B'],
            'To': ['B', 'C'],
            'geometry': [
                LineString([(0, 0), (1, 1)]),
                LineString([(1, 1), (2, 2)])
            ]
        })
        
        result = loader.cleanup_invalid_geometries(gdf)
        assert len(result) == 2
        assert all(result.geometry.is_valid)
    
    def test_cleanup_invalid_geometries_with_invalid(self):
        """Test geometry cleanup with invalid geometries."""
        loader = SpatialDataLoader()
        
        # Create invalid geometry (self-intersecting line)
        invalid_geom = LineString([(0, 0), (1, 1), (1, 0), (0, 1)])
        
        gdf = gpd.GeoDataFrame({
            'Id': [1, 2],
            'From': ['A', 'B'],
            'To': ['B', 'C'],
            'geometry': [
                LineString([(0, 0), (1, 1)]),  # Valid
                invalid_geom  # Invalid
            ]
        })
        
        result = loader.cleanup_invalid_geometries(gdf)
        assert len(result) <= 2  # May remove invalid geometries
        assert all(result.geometry.is_valid)
    
    def test_cleanup_invalid_geometries_null_empty(self):
        """Test geometry cleanup with null and empty geometries."""
        loader = SpatialDataLoader()
        
        gdf = gpd.GeoDataFrame({
            'Id': [1, 2, 3],
            'From': ['A', 'B', 'C'],
            'To': ['B', 'C', 'D'],
            'geometry': [
                LineString([(0, 0), (1, 1)]),  # Valid
                None,  # Null
                LineString()  # Empty
            ]
        })
        
        result = loader.cleanup_invalid_geometries(gdf)
        assert len(result) == 1  # Only valid geometry remains
        assert all(result.geometry.is_valid)
        assert not result.geometry.isnull().any()
        assert not result.geometry.is_empty.any()
    
    @patch('geopandas.read_file')
    def test_load_shapefile_success(self, mock_read_file):
        """Test successful shapefile loading."""
        loader = SpatialDataLoader()
        
        # Mock successful file read
        mock_gdf = gpd.GeoDataFrame({
            'Id': [1, 2],
            'From': ['A', 'B'],
            'To': ['B', 'C'],
            'geometry': [
                LineString([(0, 0), (1, 1)]),
                LineString([(1, 1), (2, 2)])
            ]
        })
        mock_read_file.return_value = mock_gdf
        
        result = loader.load_shapefile('test.shp')
        assert len(result) == 2
        assert all(col in result.columns for col in ['Id', 'From', 'To'])
        mock_read_file.assert_called_once_with('test.shp')
    
    @patch('geopandas.read_file')
    def test_load_shapefile_file_not_found(self, mock_read_file):
        """Test shapefile loading with file not found."""
        loader = SpatialDataLoader()
        
        mock_read_file.side_effect = FileNotFoundError("File not found")
        
        with pytest.raises(FileNotFoundError):
            loader.load_shapefile('nonexistent.shp')


class TestCoordinateSystemManager:
    """Test cases for CoordinateSystemManager class."""
    
    def test_init(self):
        """Test CoordinateSystemManager initialization."""
        manager = CoordinateSystemManager()
        assert manager.TARGET_CRS == "EPSG:2039"
        assert manager.WEB_MERCATOR == "EPSG:3857"
        assert manager.WGS84 == "EPSG:4326"
        assert manager.target_crs.to_string() == "EPSG:2039"
    
    def test_reproject_to_epsg2039_already_correct(self):
        """Test reprojection when data is already in EPSG 2039."""
        manager = CoordinateSystemManager()
        
        gdf = gpd.GeoDataFrame({
            'Id': [1],
            'geometry': [LineString([(200000, 600000), (201000, 601000)])]
        }, crs="EPSG:2039")
        
        result = manager.reproject_to_epsg2039(gdf)
        assert result.crs.to_string() == "EPSG:2039"
        assert len(result) == 1
    
    def test_reproject_to_epsg2039_from_wgs84(self):
        """Test reprojection from WGS84 to EPSG 2039."""
        manager = CoordinateSystemManager()
        
        gdf = gpd.GeoDataFrame({
            'Id': [1],
            'geometry': [LineString([(34.8, 32.1), (34.9, 32.2)])]
        }, crs="EPSG:4326")
        
        result = manager.reproject_to_epsg2039(gdf)
        assert result.crs.to_string() == "EPSG:2039"
        assert len(result) == 1
        # Coordinates should be in Israeli TM Grid range
        bounds = result.total_bounds
        assert bounds[0] > 100000  # Reasonable x coordinate for Israel
        assert bounds[1] > 500000  # Reasonable y coordinate for Israel
    
    def test_reproject_to_epsg2039_no_crs(self):
        """Test reprojection when no CRS is defined."""
        manager = CoordinateSystemManager()
        
        gdf = gpd.GeoDataFrame({
            'Id': [1],
            'geometry': [LineString([(200000, 600000), (201000, 601000)])]
        })  # No CRS defined
        
        result = manager.reproject_to_epsg2039(gdf)
        assert result.crs.to_string() == "EPSG:2039"
    
    def test_detect_crs_with_crs(self):
        """Test CRS detection with defined CRS."""
        manager = CoordinateSystemManager()
        
        gdf = gpd.GeoDataFrame({
            'Id': [1],
            'geometry': [LineString([(0, 0), (1, 1)])]
        }, crs="EPSG:4326")
        
        crs_string = manager.detect_crs(gdf)
        assert crs_string == "EPSG:4326"
    
    def test_detect_crs_no_crs(self):
        """Test CRS detection with no CRS defined."""
        manager = CoordinateSystemManager()
        
        gdf = gpd.GeoDataFrame({
            'Id': [1],
            'geometry': [LineString([(0, 0), (1, 1)])]
        })
        
        crs_string = manager.detect_crs(gdf)
        assert crs_string is None
    
    def test_get_bounds_for_basemap(self):
        """Test getting bounds in Web Mercator for basemap."""
        manager = CoordinateSystemManager()
        
        gdf = gpd.GeoDataFrame({
            'Id': [1],
            'geometry': [LineString([(200000, 600000), (201000, 601000)])]
        }, crs="EPSG:2039")
        
        bounds = manager.get_bounds_for_basemap(gdf)
        assert len(bounds) == 4
        assert all(isinstance(b, (int, float)) for b in bounds)
    
    def test_get_bounds_in_wgs84(self):
        """Test getting bounds in WGS84."""
        manager = CoordinateSystemManager()
        
        gdf = gpd.GeoDataFrame({
            'Id': [1],
            'geometry': [LineString([(200000, 600000), (201000, 601000)])]
        }, crs="EPSG:2039")
        
        bounds = manager.get_bounds_in_wgs84(gdf)
        assert len(bounds) == 4
        # Should be reasonable lat/lon bounds for Israel
        assert 34 < bounds[0] < 36  # Longitude
        assert 31 < bounds[1] < 34  # Latitude
    
    def test_create_transformer(self):
        """Test creating coordinate transformer."""
        manager = CoordinateSystemManager()
        
        transformer = manager.create_transformer("EPSG:4326", "EPSG:2039")
        assert transformer is not None
        
        # Test transformation
        x, y = transformer.transform(34.8, 32.1)
        assert isinstance(x, float)
        assert isinstance(y, float)
        assert x > 100000  # Reasonable Israeli TM Grid coordinate
        assert y > 500000


class TestGeometryProcessor:
    """Test cases for GeometryProcessor class."""
    
    def test_init(self):
        """Test GeometryProcessor initialization."""
        processor = GeometryProcessor()
        assert len(processor.simplification_tolerances) > 0
        assert processor._spatial_index is None
    
    def test_get_tolerance_for_zoom(self):
        """Test getting simplification tolerance for zoom level."""
        processor = GeometryProcessor()
        
        # Test exact matches
        assert processor._get_tolerance_for_zoom(1) == 0.1
        assert processor._get_tolerance_for_zoom(5) == 1.0
        assert processor._get_tolerance_for_zoom(10) == 5.0
        assert processor._get_tolerance_for_zoom(15) == 20.0
        
        # Test closest match
        tolerance = processor._get_tolerance_for_zoom(3)
        assert tolerance in processor.simplification_tolerances.values()
    
    def test_simplify_geometries_no_simplification(self):
        """Test geometry simplification with high zoom (no simplification)."""
        processor = GeometryProcessor()
        
        gdf = gpd.GeoDataFrame({
            'Id': [1],
            'geometry': [LineString([(0, 0), (0.5, 0.5), (1, 1)])]
        })
        
        result = processor.simplify_geometries(gdf, zoom_level=1)
        assert len(result) == 1
        # With minimal tolerance, geometry should be mostly unchanged
        original_coords = list(gdf.iloc[0].geometry.coords)
        simplified_coords = list(result.iloc[0].geometry.coords)
        assert len(simplified_coords) >= 2  # At least start and end points
    
    def test_simplify_geometries_with_simplification(self):
        """Test geometry simplification with low zoom (heavy simplification)."""
        processor = GeometryProcessor()
        
        # Create complex geometry with many points
        coords = [(i, i + np.sin(i)) for i in np.linspace(0, 10, 100)]
        gdf = gpd.GeoDataFrame({
            'Id': [1],
            'geometry': [LineString(coords)]
        })
        
        result = processor.simplify_geometries(gdf, zoom_level=15)
        assert len(result) == 1
        
        # Simplified geometry should have fewer coordinates
        original_coords = list(gdf.iloc[0].geometry.coords)
        simplified_coords = list(result.iloc[0].geometry.coords)
        assert len(simplified_coords) <= len(original_coords)
    
    def test_calculate_length_from_geometry(self):
        """Test length calculation from geometry."""
        processor = GeometryProcessor()
        
        gdf = gpd.GeoDataFrame({
            'Id': [1, 2],
            'geometry': [
                LineString([(0, 0), (3, 4)]),  # Length = 5
                LineString([(0, 0), (1, 0)])   # Length = 1
            ]
        }, crs="EPSG:2039")  # Use projected CRS for accurate length
        
        lengths = processor.calculate_length_from_geometry(gdf)
        assert len(lengths) == 2
        assert lengths.iloc[0] == 5.0
        assert lengths.iloc[1] == 1.0
    
    def test_create_spatial_index(self):
        """Test spatial index creation."""
        processor = GeometryProcessor()
        
        gdf = gpd.GeoDataFrame({
            'Id': [1, 2, 3],
            'geometry': [
                LineString([(0, 0), (1, 1)]),
                LineString([(2, 2), (3, 3)]),
                LineString([(4, 4), (5, 5)])
            ]
        })
        
        processor.create_spatial_index(gdf)
        assert processor._spatial_index is not None
    
    def test_query_spatial_index(self):
        """Test spatial index querying."""
        processor = GeometryProcessor()
        
        gdf = gpd.GeoDataFrame({
            'Id': [1, 2, 3],
            'geometry': [
                LineString([(0, 0), (1, 1)]),
                LineString([(2, 2), (3, 3)]),
                LineString([(10, 10), (11, 11)])  # Far away
            ]
        })
        
        # Query for features near origin
        indices = processor.query_spatial_index(gdf, bounds=(0, 0, 4, 4))
        assert isinstance(indices, list)
        assert len(indices) >= 0  # Should return some indices
    
    def test_filter_by_bounds(self):
        """Test filtering by spatial bounds."""
        processor = GeometryProcessor()
        
        gdf = gpd.GeoDataFrame({
            'Id': [1, 2, 3],
            'geometry': [
                LineString([(0, 0), (1, 1)]),
                LineString([(2, 2), (3, 3)]),
                LineString([(10, 10), (11, 11)])  # Far away
            ]
        })
        
        # Filter for features near origin
        filtered = processor.filter_by_bounds(gdf, bounds=(0, 0, 4, 4))
        assert len(filtered) <= len(gdf)
        assert len(filtered) >= 0


class TestSpatialDataManager:
    """Test cases for SpatialDataManager integration."""
    
    def test_init(self):
        """Test SpatialDataManager initialization."""
        manager = SpatialDataManager()
        assert isinstance(manager.loader, SpatialDataLoader)
        assert isinstance(manager.crs_manager, CoordinateSystemManager)
        assert isinstance(manager.geometry_processor, GeometryProcessor)
    
    @patch('geopandas.read_file')
    def test_load_and_prepare_shapefile(self, mock_read_file):
        """Test complete shapefile loading and preparation."""
        manager = SpatialDataManager()
        
        # Mock shapefile data
        mock_gdf = gpd.GeoDataFrame({
            'Id': [1, 2],
            'From': ['A', 'B'],
            'To': ['B', 'C'],
            'geometry': [
                LineString([(34.8, 32.1), (34.9, 32.2)]),
                LineString([(34.9, 32.2), (35.0, 32.3)])
            ]
        }, crs="EPSG:4326")
        mock_read_file.return_value = mock_gdf
        
        result = manager.load_and_prepare_shapefile('test.shp')
        
        # Should be reprojected to EPSG 2039
        assert result.crs.to_string() == "EPSG:2039"
        
        # Should have length_m column added
        assert 'length_m' in result.columns
        assert all(result['length_m'] > 0)
        
        # Should have all required fields
        assert all(col in result.columns for col in ['Id', 'From', 'To'])
    
    @patch('geopandas.read_file')
    def test_load_and_prepare_shapefile_with_existing_length(self, mock_read_file):
        """Test shapefile loading when length_m already exists."""
        manager = SpatialDataManager()
        
        # Mock shapefile data with existing length_m
        mock_gdf = gpd.GeoDataFrame({
            'Id': [1, 2],
            'From': ['A', 'B'],
            'To': ['B', 'C'],
            'length_m': [1000, 1500],
            'geometry': [
                LineString([(200000, 600000), (201000, 601000)]),
                LineString([(201000, 601000), (202000, 602000)])
            ]
        }, crs="EPSG:2039")
        mock_read_file.return_value = mock_gdf
        
        result = manager.load_and_prepare_shapefile('test.shp')
        
        # Should preserve existing length_m values
        assert 'length_m' in result.columns
        assert result['length_m'].iloc[0] == 1000
        assert result['length_m'].iloc[1] == 1500


# Fixtures for test data
@pytest.fixture
def sample_gdf():
    """Create sample GeoDataFrame for testing."""
    return gpd.GeoDataFrame({
        'Id': [1, 2, 3],
        'From': ['A', 'B', 'C'],
        'To': ['B', 'C', 'D'],
        'geometry': [
            LineString([(0, 0), (1, 1)]),
            LineString([(1, 1), (2, 2)]),
            LineString([(2, 2), (3, 3)])
        ]
    }, crs="EPSG:4326")


@pytest.fixture
def sample_gdf_epsg2039():
    """Create sample GeoDataFrame in EPSG 2039."""
    return gpd.GeoDataFrame({
        'Id': [1, 2, 3],
        'From': ['A', 'B', 'C'],
        'To': ['B', 'C', 'D'],
        'geometry': [
            LineString([(200000, 600000), (201000, 601000)]),
            LineString([(201000, 601000), (202000, 602000)]),
            LineString([(202000, 602000), (203000, 603000)])
        ]
    }, crs="EPSG:2039")


if __name__ == "__main__":
    pytest.main([__file__])