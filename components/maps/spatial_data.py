"""
Spatial data management module for interactive map visualization.

This module handles shapefile loading, coordinate system management, and spatial operations
for the traffic monitoring GUI's map visualization feature.
"""

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString
from shapely.validation import make_valid
from pyproj import CRS, Transformer
from typing import Tuple, List, Optional, Dict, Any
import logging
import numpy as np

logger = logging.getLogger(__name__)


class SpatialDataLoader:
    """Handles loading and validation of shapefile data."""
    
    def __init__(self):
        self.required_fields = ['Id', 'From', 'To']
    
    def load_shapefile(self, path: str) -> gpd.GeoDataFrame:
        """
        Load shapefile and validate required fields.
        
        Args:
            path: Path to shapefile
            
        Returns:
            GeoDataFrame with validated shapefile data
            
        Raises:
            ValueError: If required fields are missing
            FileNotFoundError: If shapefile doesn't exist
        """
        try:
            gdf = gpd.read_file(path)
            self.validate_shapefile_schema(gdf)
            
            # Clean up invalid geometries
            gdf = self.cleanup_invalid_geometries(gdf)
            
            logger.info(f"Successfully loaded shapefile with {len(gdf)} features")
            return gdf
        except Exception as e:
            logger.error(f"Failed to load shapefile {path}: {e}")
            raise
    
    def validate_shapefile_schema(self, gdf: gpd.GeoDataFrame) -> Tuple[bool, List[str]]:
        """
        Validate that shapefile contains required fields.
        Handles column name variations (e.g., 'id' vs 'Id').
        
        Args:
            gdf: GeoDataFrame to validate
            
        Returns:
            Tuple of (is_valid, missing_fields)
        """
        # Handle column name variations
        column_variations = {
            'Id': ['Id', 'id', 'ID'],
            'From': ['From', 'from', 'FROM'],
            'To': ['To', 'to', 'TO']
        }
        
        missing_fields = []
        
        for required_field in self.required_fields:
            # Check if any variation of the field exists
            variations = column_variations.get(required_field, [required_field])
            field_found = any(var in gdf.columns for var in variations)
            
            if not field_found:
                missing_fields.append(required_field)
        
        is_valid = len(missing_fields) == 0
        
        if not is_valid:
            logger.warning(f"Missing required fields: {missing_fields}")
        
        return is_valid, missing_fields
    
    def cleanup_invalid_geometries(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Clean up invalid geometries and remove features that cannot be fixed.
        
        Args:
            gdf: Input GeoDataFrame
            
        Returns:
            GeoDataFrame with valid geometries
        """
        initial_count = len(gdf)
        
        # Check for invalid geometries
        invalid_mask = ~gdf.geometry.is_valid
        invalid_count = invalid_mask.sum()
        
        if invalid_count > 0:
            logger.warning(f"Found {invalid_count} invalid geometries, attempting to fix")
            
            # Try to fix invalid geometries (but skip null geometries)
            invalid_non_null = invalid_mask & ~gdf.geometry.isnull()
            if invalid_non_null.any():
                gdf.loc[invalid_non_null, 'geometry'] = gdf.loc[invalid_non_null, 'geometry'].apply(make_valid)
            
            # Check if any are still invalid after fixing
            still_invalid = ~gdf.geometry.is_valid
            still_invalid_count = still_invalid.sum()
            
            if still_invalid_count > 0:
                logger.warning(f"Removing {still_invalid_count} geometries that could not be fixed")
                gdf = gdf[~still_invalid].copy()
        
        # Remove null geometries
        null_geom_mask = gdf.geometry.isnull()
        null_count = null_geom_mask.sum()
        
        if null_count > 0:
            logger.warning(f"Removing {null_count} features with null geometries")
            gdf = gdf[~null_geom_mask].copy()
        
        # Remove empty geometries
        empty_geom_mask = gdf.geometry.is_empty
        empty_count = empty_geom_mask.sum()
        
        if empty_count > 0:
            logger.warning(f"Removing {empty_count} features with empty geometries")
            gdf = gdf[~empty_geom_mask].copy()
        
        final_count = len(gdf)
        removed_count = initial_count - final_count
        
        if removed_count > 0:
            logger.info(f"Removed {removed_count} invalid features, {final_count} features remaining")
        
        return gdf


class CoordinateSystemManager:
    """Handles coordinate system detection and transformation."""
    
    TARGET_CRS = "EPSG:2039"  # Israeli TM Grid
    WEB_MERCATOR = "EPSG:3857"  # Web Mercator for basemap tiles
    WGS84 = "EPSG:4326"  # WGS84 for lat/lon
    
    def __init__(self):
        self.target_crs = CRS.from_string(self.TARGET_CRS)
        self.web_mercator_crs = CRS.from_string(self.WEB_MERCATOR)
        self.wgs84_crs = CRS.from_string(self.WGS84)
    
    def reproject_to_epsg2039(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Reproject GeoDataFrame to EPSG 2039 if not already in that CRS.
        
        Args:
            gdf: Input GeoDataFrame
            
        Returns:
            GeoDataFrame in EPSG 2039
        """
        if gdf.crs is None:
            logger.warning("No CRS defined, assuming EPSG:2039")
            gdf = gdf.set_crs(self.TARGET_CRS)
        elif gdf.crs.to_string() != self.TARGET_CRS:
            logger.info(f"Reprojecting from {gdf.crs} to {self.TARGET_CRS}")
            gdf = gdf.to_crs(self.TARGET_CRS)
        else:
            logger.info(f"Data already in {self.TARGET_CRS}")
        
        return gdf
    
    def detect_crs(self, gdf: gpd.GeoDataFrame) -> Optional[str]:
        """
        Detect coordinate reference system of GeoDataFrame.
        
        Args:
            gdf: GeoDataFrame to analyze
            
        Returns:
            CRS string or None if not detected
        """
        if gdf.crs is not None:
            return gdf.crs.to_string()
        return None
    
    def get_bounds_for_basemap(self, gdf: gpd.GeoDataFrame) -> Tuple[float, float, float, float]:
        """
        Get bounds in Web Mercator for basemap tile requests.
        
        Args:
            gdf: GeoDataFrame in EPSG 2039
            
        Returns:
            Tuple of (minx, miny, maxx, maxy) in Web Mercator
        """
        # Convert to Web Mercator for basemap compatibility
        gdf_mercator = gdf.to_crs(self.WEB_MERCATOR)
        bounds = gdf_mercator.total_bounds
        return tuple(bounds)
    
    def get_bounds_in_wgs84(self, gdf: gpd.GeoDataFrame) -> Tuple[float, float, float, float]:
        """
        Get bounds in WGS84 (lat/lon) for map initialization.
        
        Args:
            gdf: GeoDataFrame in EPSG 2039
            
        Returns:
            Tuple of (minx, miny, maxx, maxy) in WGS84
        """
        # Convert to WGS84 for lat/lon bounds
        gdf_wgs84 = gdf.to_crs(self.WGS84)
        bounds = gdf_wgs84.total_bounds
        return tuple(bounds)
    
    def create_transformer(self, source_crs: str, target_crs: str) -> Transformer:
        """
        Create a coordinate transformer between two CRS.
        
        Args:
            source_crs: Source coordinate reference system
            target_crs: Target coordinate reference system
            
        Returns:
            PyProj Transformer object
        """
        return Transformer.from_crs(source_crs, target_crs, always_xy=True)


class GeometryProcessor:
    """Handles geometry processing and simplification."""
    
    def __init__(self):
        self.simplification_tolerances = {
            1: 0.1,    # High zoom - minimal simplification
            5: 1.0,    # Medium zoom
            10: 5.0,   # Low zoom - more simplification
            15: 20.0   # Very low zoom - heavy simplification
        }
        self._spatial_index = None
    
    def simplify_geometries(self, gdf: gpd.GeoDataFrame, zoom_level: int) -> gpd.GeoDataFrame:
        """
        Simplify geometries based on zoom level for performance.
        
        Args:
            gdf: Input GeoDataFrame
            zoom_level: Current map zoom level
            
        Returns:
            GeoDataFrame with simplified geometries
        """
        # Find appropriate tolerance based on zoom level
        tolerance = self._get_tolerance_for_zoom(zoom_level)
        
        if tolerance > 0:
            logger.debug(f"Simplifying geometries with tolerance {tolerance} for zoom {zoom_level}")
            gdf = gdf.copy()
            gdf['geometry'] = gdf['geometry'].simplify(tolerance, preserve_topology=True)
        
        return gdf
    
    def _get_tolerance_for_zoom(self, zoom_level: int) -> float:
        """Get simplification tolerance for given zoom level."""
        # Find the closest zoom level in our tolerance mapping
        closest_zoom = min(self.simplification_tolerances.keys(), 
                          key=lambda x: abs(x - zoom_level))
        return self.simplification_tolerances[closest_zoom]
    
    def calculate_length_from_geometry(self, gdf: gpd.GeoDataFrame) -> pd.Series:
        """
        Calculate link length from geometry when missing in results.
        
        Args:
            gdf: GeoDataFrame with LineString geometries
            
        Returns:
            Series with calculated lengths in meters
        """
        return gdf.geometry.length
    
    def create_spatial_index(self, gdf: gpd.GeoDataFrame) -> None:
        """
        Create spatial index for performance optimization.
        
        Args:
            gdf: GeoDataFrame to index
        """
        try:
            self._spatial_index = gdf.sindex
            logger.debug(f"Created spatial index for {len(gdf)} features")
        except Exception as e:
            logger.warning(f"Failed to create spatial index: {e}")
            self._spatial_index = None
    
    def query_spatial_index(self, gdf: gpd.GeoDataFrame, bounds: Tuple[float, float, float, float]) -> List[int]:
        """
        Query spatial index for features within bounds.
        
        Args:
            gdf: GeoDataFrame with spatial index
            bounds: Bounding box (minx, miny, maxx, maxy)
            
        Returns:
            List of indices for features within bounds
        """
        if self._spatial_index is None:
            self.create_spatial_index(gdf)
        
        if self._spatial_index is not None:
            try:
                # Query the spatial index
                possible_matches_index = list(self._spatial_index.intersection(bounds))
                return possible_matches_index
            except Exception as e:
                logger.warning(f"Spatial index query failed: {e}")
                return list(range(len(gdf)))
        else:
            # Fallback to all indices if no spatial index
            return list(range(len(gdf)))
    
    def filter_by_bounds(self, gdf: gpd.GeoDataFrame, bounds: Tuple[float, float, float, float]) -> gpd.GeoDataFrame:
        """
        Filter GeoDataFrame by spatial bounds using spatial index for performance.
        
        Args:
            gdf: Input GeoDataFrame
            bounds: Bounding box (minx, miny, maxx, maxy)
            
        Returns:
            Filtered GeoDataFrame
        """
        indices = self.query_spatial_index(gdf, bounds)
        return gdf.iloc[indices].copy()


class SpatialDataManager:
    """Main interface for spatial data operations."""
    
    def __init__(self):
        self.loader = SpatialDataLoader()
        self.crs_manager = CoordinateSystemManager()
        self.geometry_processor = GeometryProcessor()
    
    def load_and_prepare_shapefile(self, path: str) -> gpd.GeoDataFrame:
        """
        Load shapefile and prepare it for map visualization.
        
        Args:
            path: Path to shapefile
            
        Returns:
            Prepared GeoDataFrame in EPSG 2039
        """
        # Load shapefile
        gdf = self.loader.load_shapefile(path)
        
        # Reproject to EPSG 2039
        gdf = self.crs_manager.reproject_to_epsg2039(gdf)
        
        # Add length calculation if needed
        if 'length_m' not in gdf.columns:
            gdf['length_m'] = self.geometry_processor.calculate_length_from_geometry(gdf)
        
        return gdf
    
    def load_shapefile(self, path: str) -> gpd.GeoDataFrame:
        """Load shapefile using the internal loader."""
        return self.loader.load_shapefile(path)
    
    def validate_shapefile_schema(self, gdf: gpd.GeoDataFrame) -> Tuple[bool, List[str]]:
        """Validate shapefile schema using the internal loader."""
        return self.loader.validate_shapefile_schema(gdf)
    
    def reproject_to_epsg2039(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Reproject GeoDataFrame to EPSG 2039."""
        return self.crs_manager.reproject_to_epsg2039(gdf)