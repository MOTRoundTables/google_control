"""
Performance optimization module for interactive map visualization.

This module implements viewport-first rendering, geometry simplification,
and caching systems to ensure responsive performance with large networks.
"""

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon
from shapely.ops import transform
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Union
import logging
import hashlib
import pickle
import os
from datetime import datetime, timedelta
import time
from functools import wraps

logger = logging.getLogger(__name__)


class GeometrySimplifier:
    """
    Handles zoom-dependent geometry simplification for performance optimization.
    """
    
    def __init__(self):
        # Simplification tolerances by zoom level (in map units)
        self.zoom_tolerances = {
            1: 1000,   # Very zoomed out - high simplification
            2: 500,
            3: 250,
            4: 100,
            5: 50,
            6: 25,
            7: 10,
            8: 5,
            9: 2,
            10: 1,
            11: 0.5,
            12: 0.25,
            13: 0.1,   # Very zoomed in - minimal simplification
            14: 0.05,
            15: 0.01
        }
        
        # Minimum feature size thresholds by zoom level
        self.min_feature_sizes = {
            1: 5000,   # Only show features > 5km at zoom 1
            2: 2000,
            3: 1000,
            4: 500,
            5: 200,
            6: 100,
            7: 50,
            8: 20,
            9: 10,
            10: 5,
            11: 2,
            12: 1,
            13: 0.5,
            14: 0.1,
            15: 0     # Show all features at highest zoom
        }
    
    def simplify_for_zoom_level(self, gdf: gpd.GeoDataFrame, 
                               zoom_level: int) -> gpd.GeoDataFrame:
        """
        Simplify geometries based on zoom level for performance.
        
        Args:
            gdf: Input GeoDataFrame with geometries
            zoom_level: Current map zoom level (1-15)
            
        Returns:
            GeoDataFrame with simplified geometries
        """
        if gdf.empty:
            return gdf
        
        # Clamp zoom level to valid range
        zoom_level = max(1, min(15, zoom_level))
        
        # Get simplification parameters
        tolerance = self.zoom_tolerances.get(zoom_level, 1.0)
        min_size = self.min_feature_sizes.get(zoom_level, 0)
        
        logger.debug(f"Simplifying geometries for zoom {zoom_level}: tolerance={tolerance}, min_size={min_size}")
        
        simplified_gdf = gdf.copy()
        
        try:
            # Filter out features smaller than minimum size
            if min_size > 0 and 'length_m' in simplified_gdf.columns:
                size_mask = simplified_gdf['length_m'] >= min_size
                simplified_gdf = simplified_gdf[size_mask]
                logger.debug(f"Filtered to {len(simplified_gdf)} features above {min_size}m")
            
            # Simplify geometries
            if tolerance > 0:
                simplified_gdf['geometry'] = simplified_gdf['geometry'].simplify(
                    tolerance, preserve_topology=True
                )
                logger.debug(f"Applied simplification with tolerance {tolerance}")
            
            # Remove any invalid geometries created by simplification
            valid_mask = simplified_gdf['geometry'].is_valid
            if not valid_mask.all():
                invalid_count = (~valid_mask).sum()
                logger.warning(f"Removing {invalid_count} invalid geometries after simplification")
                simplified_gdf = simplified_gdf[valid_mask]
            
        except Exception as e:
            logger.error(f"Error during geometry simplification: {e}")
            # Return original data if simplification fails
            return gdf
        
        return simplified_gdf
    
    def calculate_optimal_zoom_level(self, bounds: Tuple[float, float, float, float],
                                   viewport_size: Tuple[int, int]) -> int:
        """
        Calculate optimal zoom level based on data bounds and viewport size.
        
        Args:
            bounds: Tuple of (minx, miny, maxx, maxy) in map units
            viewport_size: Tuple of (width, height) in pixels
            
        Returns:
            Optimal zoom level (1-15)
        """
        if not bounds or not viewport_size:
            return 10  # Default zoom level
        
        minx, miny, maxx, maxy = bounds
        width_pixels, height_pixels = viewport_size
        
        # Calculate map extent in map units
        map_width = maxx - minx
        map_height = maxy - miny
        
        if map_width <= 0 or map_height <= 0:
            return 10
        
        # Calculate resolution (map units per pixel)
        x_resolution = map_width / width_pixels
        y_resolution = map_height / height_pixels
        resolution = max(x_resolution, y_resolution)
        
        # Map resolution to zoom level (rough approximation)
        if resolution > 1000:
            zoom_level = 1
        elif resolution > 500:
            zoom_level = 2
        elif resolution > 250:
            zoom_level = 3
        elif resolution > 100:
            zoom_level = 4
        elif resolution > 50:
            zoom_level = 5
        elif resolution > 25:
            zoom_level = 6
        elif resolution > 10:
            zoom_level = 7
        elif resolution > 5:
            zoom_level = 8
        elif resolution > 2:
            zoom_level = 9
        elif resolution > 1:
            zoom_level = 10
        elif resolution > 0.5:
            zoom_level = 11
        elif resolution > 0.25:
            zoom_level = 12
        elif resolution > 0.1:
            zoom_level = 13
        elif resolution > 0.05:
            zoom_level = 14
        else:
            zoom_level = 15
        
        logger.debug(f"Calculated zoom level {zoom_level} for resolution {resolution}")
        return zoom_level


class ViewportRenderer:
    """
    Handles viewport-first rendering with progressive fill for large datasets.
    """
    
    def __init__(self):
        self.viewport_buffer = 0.1  # 10% buffer around viewport
        self.progressive_batch_size = 1000  # Features per batch
        
    def filter_to_viewport(self, gdf: gpd.GeoDataFrame, 
                          viewport_bounds: Tuple[float, float, float, float]) -> gpd.GeoDataFrame:
        """
        Filter data to viewport with buffer for performance.
        
        Args:
            gdf: Input GeoDataFrame
            viewport_bounds: Tuple of (minx, miny, maxx, maxy) for viewport
            
        Returns:
            GeoDataFrame filtered to viewport area
        """
        if gdf.empty or not viewport_bounds:
            return gdf
        
        minx, miny, maxx, maxy = viewport_bounds
        
        # Add buffer to viewport
        width = maxx - minx
        height = maxy - miny
        buffer_x = width * self.viewport_buffer
        buffer_y = height * self.viewport_buffer
        
        buffered_bounds = (
            minx - buffer_x,
            miny - buffer_y, 
            maxx + buffer_x,
            maxy + buffer_y
        )
        
        try:
            # Create viewport polygon
            viewport_poly = Polygon([
                (buffered_bounds[0], buffered_bounds[1]),
                (buffered_bounds[2], buffered_bounds[1]),
                (buffered_bounds[2], buffered_bounds[3]),
                (buffered_bounds[0], buffered_bounds[3])
            ])
            
            # Filter geometries that intersect viewport
            intersects_mask = gdf.geometry.intersects(viewport_poly)
            viewport_data = gdf[intersects_mask]
            
            logger.debug(f"Filtered to {len(viewport_data)} features in viewport from {len(gdf)} total")
            return viewport_data
            
        except Exception as e:
            logger.error(f"Error filtering to viewport: {e}")
            return gdf
    
    def create_progressive_batches(self, gdf: gpd.GeoDataFrame, 
                                  priority_column: Optional[str] = None) -> List[gpd.GeoDataFrame]:
        """
        Create progressive rendering batches prioritized by importance.
        
        Args:
            gdf: Input GeoDataFrame
            priority_column: Column to use for prioritization (higher values first)
            
        Returns:
            List of GeoDataFrame batches for progressive rendering
        """
        if gdf.empty:
            return []
        
        # Sort by priority if specified
        if priority_column and priority_column in gdf.columns:
            sorted_gdf = gdf.sort_values(priority_column, ascending=False)
        else:
            # Default priority: longer links first (assuming they're more important)
            if 'length_m' in gdf.columns:
                sorted_gdf = gdf.sort_values('length_m', ascending=False)
            else:
                sorted_gdf = gdf.copy()
        
        # Create batches
        batches = []
        total_features = len(sorted_gdf)
        
        for start_idx in range(0, total_features, self.progressive_batch_size):
            end_idx = min(start_idx + self.progressive_batch_size, total_features)
            batch = sorted_gdf.iloc[start_idx:end_idx].copy()
            batches.append(batch)
        
        logger.debug(f"Created {len(batches)} progressive batches from {total_features} features")
        return batches
    
    def estimate_rendering_time(self, feature_count: int) -> float:
        """
        Estimate rendering time based on feature count.
        
        Args:
            feature_count: Number of features to render
            
        Returns:
            Estimated rendering time in seconds
        """
        # Rough estimates based on typical performance
        base_time = 0.1  # Base rendering overhead
        time_per_feature = 0.001  # Time per feature in seconds
        
        estimated_time = base_time + (feature_count * time_per_feature)
        return estimated_time


class CachingSystem:
    """
    Implements caching system keyed by metric, hour set, date range, and filters.
    """
    
    def __init__(self, cache_dir: str = ".cache/map_visualization"):
        self.cache_dir = cache_dir
        self.max_cache_age_hours = 24  # Cache expires after 24 hours
        self.max_cache_size_mb = 500   # Maximum cache size in MB
        
        # Create cache directory if it doesn't exist
        os.makedirs(cache_dir, exist_ok=True)
    
    def generate_cache_key(self, metric_type: str, hour_set: Tuple[int, ...],
                          date_range: Optional[Tuple[str, str]], 
                          filters: Dict[str, Any]) -> str:
        """
        Generate unique cache key based on parameters.
        
        Args:
            metric_type: Type of metric ('duration' or 'speed')
            hour_set: Tuple of hours included
            date_range: Optional tuple of (start_date, end_date)
            filters: Dictionary of active filters
            
        Returns:
            Unique cache key string
        """
        # Create a deterministic string representation
        key_components = [
            f"metric:{metric_type}",
            f"hours:{','.join(map(str, sorted(hour_set)))}",
            f"dates:{date_range[0] if date_range else 'all'}-{date_range[1] if date_range else 'all'}",
            f"filters:{self._serialize_filters(filters)}"
        ]
        
        key_string = "|".join(key_components)
        
        # Generate hash for consistent key length
        cache_key = hashlib.md5(key_string.encode()).hexdigest()
        
        logger.debug(f"Generated cache key: {cache_key} for {key_string}")
        return cache_key
    
    def _serialize_filters(self, filters: Dict[str, Any]) -> str:
        """Serialize filters dictionary to consistent string."""
        if not filters:
            return "none"
        
        # Sort keys for consistency
        sorted_items = []
        for key in sorted(filters.keys()):
            value = filters[key]
            if isinstance(value, dict):
                # Handle nested dictionaries
                nested_items = []
                for nested_key in sorted(value.keys()):
                    nested_items.append(f"{nested_key}:{value[nested_key]}")
                sorted_items.append(f"{key}:({','.join(nested_items)})")
            else:
                sorted_items.append(f"{key}:{value}")
        
        return ",".join(sorted_items)
    
    def get_cached_data(self, cache_key: str) -> Optional[Any]:
        """
        Retrieve cached data if available and not expired.
        
        Args:
            cache_key: Cache key to retrieve
            
        Returns:
            Cached data or None if not available/expired
        """
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        
        if not os.path.exists(cache_file):
            return None
        
        try:
            # Check if cache is expired
            file_age = time.time() - os.path.getmtime(cache_file)
            if file_age > (self.max_cache_age_hours * 3600):
                logger.debug(f"Cache expired for key {cache_key}")
                os.remove(cache_file)
                return None
            
            # Load cached data
            with open(cache_file, 'rb') as f:
                cached_data = pickle.load(f)
            
            logger.debug(f"Retrieved cached data for key {cache_key}")
            return cached_data
            
        except Exception as e:
            logger.error(f"Error loading cached data for key {cache_key}: {e}")
            # Remove corrupted cache file
            try:
                os.remove(cache_file)
            except:
                pass
            return None
    
    def cache_data(self, cache_key: str, data: Any) -> bool:
        """
        Cache data with the given key.
        
        Args:
            cache_key: Cache key to store under
            data: Data to cache
            
        Returns:
            True if successfully cached, False otherwise
        """
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        
        try:
            # Check cache size limits
            if self._get_cache_size_mb() > self.max_cache_size_mb:
                self._cleanup_old_cache_files()
            
            # Save data to cache
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
            
            logger.debug(f"Cached data for key {cache_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error caching data for key {cache_key}: {e}")
            return False
    
    def _get_cache_size_mb(self) -> float:
        """Get total cache size in MB."""
        total_size = 0
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.pkl'):
                    file_path = os.path.join(self.cache_dir, filename)
                    total_size += os.path.getsize(file_path)
        except:
            pass
        
        return total_size / (1024 * 1024)  # Convert to MB
    
    def _cleanup_old_cache_files(self) -> None:
        """Remove oldest cache files to free space."""
        try:
            cache_files = []
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.pkl'):
                    file_path = os.path.join(self.cache_dir, filename)
                    mtime = os.path.getmtime(file_path)
                    cache_files.append((file_path, mtime))
            
            # Sort by modification time (oldest first)
            cache_files.sort(key=lambda x: x[1])
            
            # Remove oldest 25% of files
            files_to_remove = len(cache_files) // 4
            for file_path, _ in cache_files[:files_to_remove]:
                os.remove(file_path)
                logger.debug(f"Removed old cache file: {file_path}")
                
        except Exception as e:
            logger.error(f"Error during cache cleanup: {e}")
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.pkl'):
                    file_path = os.path.join(self.cache_dir, filename)
                    os.remove(file_path)
            logger.info("Cleared all cached data")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")


class PerformanceMonitor:
    """
    Monitors and logs performance metrics for optimization.
    """
    
    def __init__(self):
        self.performance_log = []
        
    def time_operation(self, operation_name: str):
        """Decorator to time operations."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    success = True
                    error = None
                except Exception as e:
                    result = None
                    success = False
                    error = str(e)
                    raise
                finally:
                    end_time = time.time()
                    duration = end_time - start_time
                    
                    self.log_performance(
                        operation=operation_name,
                        duration=duration,
                        success=success,
                        error=error,
                        args_info=self._get_args_info(args, kwargs)
                    )
                
                return result
            return wrapper
        return decorator
    
    def log_performance(self, operation: str, duration: float, 
                       success: bool = True, error: Optional[str] = None,
                       args_info: Optional[Dict] = None) -> None:
        """Log performance metrics."""
        log_entry = {
            'timestamp': datetime.now(),
            'operation': operation,
            'duration': duration,
            'success': success,
            'error': error,
            'args_info': args_info or {}
        }
        
        self.performance_log.append(log_entry)
        
        # Log to standard logger
        if success:
            logger.debug(f"Performance: {operation} completed in {duration:.3f}s")
        else:
            logger.warning(f"Performance: {operation} failed after {duration:.3f}s - {error}")
    
    def _get_args_info(self, args: tuple, kwargs: dict) -> Dict[str, Any]:
        """Extract useful information from function arguments."""
        info = {}
        
        # Look for common data structures
        for i, arg in enumerate(args):
            if hasattr(arg, '__len__'):
                info[f'arg_{i}_length'] = len(arg)
            if isinstance(arg, (gpd.GeoDataFrame, pd.DataFrame)):
                info[f'arg_{i}_type'] = type(arg).__name__
                info[f'arg_{i}_shape'] = arg.shape
        
        for key, value in kwargs.items():
            if hasattr(value, '__len__'):
                info[f'{key}_length'] = len(value)
            if isinstance(value, (gpd.GeoDataFrame, pd.DataFrame)):
                info[f'{key}_type'] = type(value).__name__
                info[f'{key}_shape'] = value.shape
        
        return info
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get summary of performance metrics."""
        if not self.performance_log:
            return {}
        
        # Group by operation
        operations = {}
        for entry in self.performance_log:
            op_name = entry['operation']
            if op_name not in operations:
                operations[op_name] = []
            operations[op_name].append(entry)
        
        summary = {}
        for op_name, entries in operations.items():
            durations = [e['duration'] for e in entries if e['success']]
            failures = [e for e in entries if not e['success']]
            
            if durations:
                summary[op_name] = {
                    'count': len(entries),
                    'success_count': len(durations),
                    'failure_count': len(failures),
                    'mean_duration': np.mean(durations),
                    'median_duration': np.median(durations),
                    'min_duration': np.min(durations),
                    'max_duration': np.max(durations),
                    'total_duration': np.sum(durations)
                }
        
        return summary


class PerformanceOptimizer:
    """
    Main performance optimization coordinator.
    """
    
    def __init__(self, cache_dir: str = ".cache/map_visualization"):
        self.geometry_simplifier = GeometrySimplifier()
        self.viewport_renderer = ViewportRenderer()
        self.caching_system = CachingSystem(cache_dir)
        self.performance_monitor = PerformanceMonitor()
    
    @property
    def monitor(self):
        """Access to performance monitor for decorating functions."""
        return self.performance_monitor
    
    def optimize_data_for_rendering(self, gdf: gpd.GeoDataFrame,
                                   zoom_level: int,
                                   viewport_bounds: Optional[Tuple[float, float, float, float]] = None,
                                   cache_key: Optional[str] = None) -> gpd.GeoDataFrame:
        """
        Apply all performance optimizations to data for rendering.
        
        Args:
            gdf: Input GeoDataFrame
            zoom_level: Current zoom level
            viewport_bounds: Optional viewport bounds for filtering
            cache_key: Optional cache key for caching results
            
        Returns:
            Optimized GeoDataFrame ready for rendering
        """
        # Check cache first
        if cache_key:
            cached_result = self.caching_system.get_cached_data(cache_key)
            if cached_result is not None:
                logger.debug(f"Using cached optimized data for key {cache_key}")
                return cached_result
        
        # Apply optimizations
        optimized_data = gdf.copy()
        
        # 1. Filter to viewport if specified
        if viewport_bounds:
            optimized_data = self.viewport_renderer.filter_to_viewport(
                optimized_data, viewport_bounds
            )
        
        # 2. Simplify geometries based on zoom level
        optimized_data = self.geometry_simplifier.simplify_for_zoom_level(
            optimized_data, zoom_level
        )
        
        # Cache the result if cache key provided
        if cache_key and not optimized_data.empty:
            self.caching_system.cache_data(cache_key, optimized_data)
        
        logger.debug(f"Optimized data: {len(gdf)} -> {len(optimized_data)} features")
        return optimized_data
    
    def create_rendering_strategy(self, total_features: int,
                                viewport_size: Tuple[int, int]) -> Dict[str, Any]:
        """
        Create optimal rendering strategy based on data size and viewport.
        
        Args:
            total_features: Total number of features to render
            viewport_size: Viewport size in pixels
            
        Returns:
            Dictionary with rendering strategy configuration
        """
        strategy = {
            'use_progressive_rendering': False,
            'use_viewport_filtering': False,
            'use_geometry_simplification': False,
            'batch_size': 1000,
            'estimated_render_time': 0
        }
        
        # Estimate rendering time
        estimated_time = self.viewport_renderer.estimate_rendering_time(total_features)
        strategy['estimated_render_time'] = estimated_time
        
        # Determine optimizations needed
        if total_features > 10000:
            strategy['use_progressive_rendering'] = True
            strategy['use_viewport_filtering'] = True
            strategy['use_geometry_simplification'] = True
            strategy['batch_size'] = 500
        elif total_features > 5000:
            strategy['use_viewport_filtering'] = True
            strategy['use_geometry_simplification'] = True
            strategy['batch_size'] = 1000
        elif total_features > 1000:
            strategy['use_geometry_simplification'] = True
        
        logger.debug(f"Created rendering strategy for {total_features} features: {strategy}")
        return strategy
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get caching system statistics."""
        return {
            'cache_size_mb': self.caching_system._get_cache_size_mb(),
            'max_cache_size_mb': self.caching_system.max_cache_size_mb,
            'cache_dir': self.caching_system.cache_dir,
            'max_age_hours': self.caching_system.max_cache_age_hours
        }
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        return {
            'performance_summary': self.performance_monitor.get_performance_summary(),
            'cache_statistics': self.get_cache_statistics(),
            'optimization_settings': {
                'viewport_buffer': self.viewport_renderer.viewport_buffer,
                'progressive_batch_size': self.viewport_renderer.progressive_batch_size,
                'zoom_tolerances': self.geometry_simplifier.zoom_tolerances
            }
        }