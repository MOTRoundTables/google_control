"""
Map data processing module for interactive map visualization.

This module handles joining spatial and tabular data, applying filters,
and preparing data for visualization.
"""

import pandas as pd
import geopandas as gpd
from datetime import date, datetime
from typing import Dict, List, Tuple, Optional, Any
import logging

logger = logging.getLogger(__name__)


class DataJoiner:
    """Handles joining results data to shapefile using link_id mapping rule."""
    
    def __init__(self):
        self.join_rule = "s_{From}-{To}"  # link_id equals s_From-To
    
    def join_results_to_shapefile(self, gdf: gpd.GeoDataFrame, results_df: pd.DataFrame) -> gpd.GeoDataFrame:
        """
        Join results data to shapefile using s_From-To rule.
        
        Args:
            gdf: Shapefile GeoDataFrame with Id, From, To fields
            results_df: Results DataFrame with link_id field
            
        Returns:
            Joined GeoDataFrame with results data
        """
        # Create join key in shapefile using s_From-To rule
        gdf = gdf.copy()
        gdf['join_key'] = 's_' + gdf['From'].astype(str) + '-' + gdf['To'].astype(str)
        
        # Perform left join to keep all shapefile features
        joined = gdf.merge(results_df, left_on='join_key', right_on='link_id', how='left')
        
        logger.info(f"Joined {len(results_df)} results records to {len(gdf)} shapefile features")
        
        return joined
    
    def validate_joins(self, gdf: gpd.GeoDataFrame, results_df: pd.DataFrame) -> Dict[str, int]:
        """
        Validate join results and return statistics.
        
        Args:
            gdf: Shapefile GeoDataFrame
            results_df: Results DataFrame
            
        Returns:
            Dictionary with join validation statistics
        """
        # Create join keys
        shapefile_keys = set('s_' + gdf['From'].astype(str) + '-' + gdf['To'].astype(str))
        results_keys = set(results_df['link_id'].unique())
        
        stats = {
            'shapefile_features': len(gdf),
            'results_records': len(results_df),
            'unique_results_links': len(results_keys),
            'missing_in_shapefile': len(results_keys - shapefile_keys),
            'missing_in_results': len(shapefile_keys - results_keys),
            'successful_joins': len(shapefile_keys & results_keys)
        }
        
        logger.info(f"Join validation: {stats}")
        return stats
    
    def get_missing_links(self, gdf: gpd.GeoDataFrame, results_df: pd.DataFrame) -> List[str]:
        """
        Get list of link_ids in results that don't match shapefile.
        
        Args:
            gdf: Shapefile GeoDataFrame
            results_df: Results DataFrame
            
        Returns:
            List of missing link_ids
        """
        shapefile_keys = set('s_' + gdf['From'].astype(str) + '-' + gdf['To'].astype(str))
        results_keys = set(results_df['link_id'].unique())
        
        return list(results_keys - shapefile_keys)


class FilterManager:
    """Manages temporal, spatial, and attribute filters."""
    
    def __init__(self):
        self.active_filters = {}
    
    def apply_temporal_filters(self, data: pd.DataFrame, date_range: Optional[Tuple[date, date]] = None,
                             hour_range: Optional[Tuple[int, int]] = None) -> pd.DataFrame:
        """
        Apply temporal filters to data.
        
        Args:
            data: Input DataFrame with date and hour columns
            date_range: Optional tuple of (start_date, end_date)
            hour_range: Optional tuple of (start_hour, end_hour)
            
        Returns:
            Filtered DataFrame
        """
        filtered_data = data.copy()
        
        if date_range is not None:
            start_date, end_date = date_range
            filtered_data = filtered_data[
                (pd.to_datetime(filtered_data['date']) >= pd.to_datetime(start_date)) &
                (pd.to_datetime(filtered_data['date']) <= pd.to_datetime(end_date))
            ]
            logger.debug(f"Applied date filter: {start_date} to {end_date}")
        
        if hour_range is not None:
            start_hour, end_hour = hour_range
            filtered_data = filtered_data[
                (filtered_data['hour'] >= start_hour) &
                (filtered_data['hour'] <= end_hour)
            ]
            logger.debug(f"Applied hour filter: {start_hour} to {end_hour}")
        
        return filtered_data
    
    def apply_attribute_filters(self, data: pd.DataFrame, filters: Dict[str, Dict]) -> pd.DataFrame:
        """
        Apply attribute filters (length, speed, time).
        
        Args:
            data: Input DataFrame
            filters: Dictionary of filter configurations
                    e.g., {'length': {'operator': 'above', 'value': 1000}}
            
        Returns:
            Filtered DataFrame
        """
        filtered_data = data.copy()
        
        for field, filter_config in filters.items():
            if field not in data.columns:
                continue
                
            operator = filter_config.get('operator')
            value = filter_config.get('value')
            
            if operator == 'above':
                filtered_data = filtered_data[filtered_data[field] > value]
            elif operator == 'below':
                filtered_data = filtered_data[filtered_data[field] < value]
            elif operator == 'between':
                min_val, max_val = value if isinstance(value, (list, tuple)) else (value, value)
                filtered_data = filtered_data[
                    (filtered_data[field] >= min_val) & (filtered_data[field] <= max_val)
                ]
            
            logger.debug(f"Applied {field} filter: {operator} {value}")
        
        return filtered_data
    
    def apply_spatial_filters(self, gdf: gpd.GeoDataFrame, spatial_selection: Optional[gpd.GeoDataFrame] = None) -> gpd.GeoDataFrame:
        """
        Apply spatial selection filters.
        
        Args:
            gdf: Input GeoDataFrame
            spatial_selection: GeoDataFrame defining spatial selection area
            
        Returns:
            Spatially filtered GeoDataFrame
        """
        if spatial_selection is None:
            return gdf
        
        # Perform spatial intersection
        filtered_gdf = gpd.overlay(gdf, spatial_selection, how='intersection')
        logger.debug(f"Applied spatial filter: {len(filtered_gdf)} features selected")
        
        return filtered_gdf


class AggregationEngine:
    """Handles weekly aggregation and statistics computation."""
    
    def __init__(self):
        self.aggregation_methods = ['mean', 'median']
    
    def compute_weekly_aggregation(self, hourly_data: pd.DataFrame, method: str = 'median') -> pd.DataFrame:
        """
        Compute weekly hourly aggregation across all available dates.
        
        Args:
            hourly_data: DataFrame with hourly data
            method: Aggregation method ('mean' or 'median')
            
        Returns:
            DataFrame with weekly aggregated data
        """
        if method not in self.aggregation_methods:
            raise ValueError(f"Method must be one of {self.aggregation_methods}")
        
        # Group by link_id and hour, then aggregate across dates
        agg_funcs = {
            'avg_duration_sec': method,
            'avg_speed_kmh': method,
            'n_valid': 'sum'  # Sum observations across dates
        }
        
        # Add any additional numeric columns
        numeric_cols = hourly_data.select_dtypes(include=['number']).columns
        for col in numeric_cols:
            if col not in agg_funcs and col not in ['hour']:
                agg_funcs[col] = method
        
        weekly_agg = hourly_data.groupby(['link_id', 'hour']).agg(agg_funcs).reset_index()
        
        logger.info(f"Computed weekly aggregation using {method} for {len(weekly_agg)} link-hour combinations")
        
        return weekly_agg
    
    def calculate_date_span_context(self, hourly_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate date span and day count for context display.
        
        Args:
            hourly_data: DataFrame with date column
            
        Returns:
            Dictionary with date span information
        """
        dates = pd.to_datetime(hourly_data['date']).dt.date
        unique_dates = sorted(dates.unique())
        
        context = {
            'start_date': unique_dates[0],
            'end_date': unique_dates[-1],
            'n_days': len(unique_dates),
            'date_range_str': f"{unique_dates[0]} to {unique_dates[-1]}"
        }
        
        return context
    
    def compute_aggregation_statistics(self, hourly_data: pd.DataFrame, 
                                     link_id: str, method: str = 'median') -> Dict[str, Any]:
        """
        Compute aggregation statistics for a specific link for details panel.
        
        Args:
            hourly_data: DataFrame with hourly data for all links
            link_id: Specific link ID to compute statistics for
            method: Aggregation method ('mean' or 'median')
            
        Returns:
            Dictionary with aggregation statistics for the link
        """
        # Filter data for specific link
        link_data = hourly_data[hourly_data['link_id'] == link_id].copy()
        
        if link_data.empty:
            return {
                'total_observations': 0,
                'unique_dates': 0,
                'unique_hours': 0,
                'date_coverage': [],
                'hour_coverage': [],
                'aggregation_method': method,
                'data_quality': 'no_data'
            }
        
        # Calculate basic statistics
        total_observations = link_data['n_valid'].sum() if 'n_valid' in link_data.columns else len(link_data)
        unique_dates = link_data['date'].nunique() if 'date' in link_data.columns else 0
        unique_hours = link_data['hour'].nunique() if 'hour' in link_data.columns else 0
        
        # Get date and hour coverage
        date_coverage = sorted(link_data['date'].unique()) if 'date' in link_data.columns else []
        hour_coverage = sorted(link_data['hour'].unique()) if 'hour' in link_data.columns else []
        
        # Assess data quality
        data_quality = self._assess_aggregation_data_quality(link_data, total_observations)
        
        # Calculate weekly patterns for each metric
        weekly_patterns = {}
        if 'avg_duration_sec' in link_data.columns:
            weekly_patterns['duration'] = self._calculate_weekly_pattern(
                link_data, 'avg_duration_sec', method
            )
        
        if 'avg_speed_kmh' in link_data.columns:
            weekly_patterns['speed'] = self._calculate_weekly_pattern(
                link_data, 'avg_speed_kmh', method
            )
        
        statistics = {
            'total_observations': total_observations,
            'unique_dates': unique_dates,
            'unique_hours': unique_hours,
            'date_coverage': date_coverage,
            'hour_coverage': hour_coverage,
            'aggregation_method': method,
            'data_quality': data_quality,
            'weekly_patterns': weekly_patterns
        }
        
        logger.debug(f"Computed aggregation statistics for link {link_id}: {statistics}")
        return statistics
    
    def _assess_aggregation_data_quality(self, link_data: pd.DataFrame, 
                                       total_observations: int) -> str:
        """
        Assess data quality for aggregation based on coverage and observations.
        
        Args:
            link_data: DataFrame with link-specific data
            total_observations: Total number of observations
            
        Returns:
            String indicating data quality level
        """
        if total_observations == 0:
            return 'no_data'
        elif total_observations < 10:
            return 'sparse'
        elif len(link_data) < 5:  # Less than 5 time periods
            return 'limited'
        elif total_observations < 50:
            return 'moderate'
        else:
            return 'good'
    
    def _calculate_weekly_pattern(self, link_data: pd.DataFrame, 
                                metric_column: str, method: str) -> Dict[str, Any]:
        """
        Calculate weekly pattern statistics for a specific metric.
        
        Args:
            link_data: DataFrame with link-specific data
            metric_column: Column name for the metric
            method: Aggregation method
            
        Returns:
            Dictionary with weekly pattern statistics
        """
        if metric_column not in link_data.columns or 'hour' not in link_data.columns:
            return {}
        
        # Group by hour and aggregate
        if method == 'median':
            hourly_agg = link_data.groupby('hour')[metric_column].median()
        else:  # mean
            hourly_agg = link_data.groupby('hour')[metric_column].mean()
        
        # Calculate pattern statistics
        pattern_stats = {
            'hourly_values': hourly_agg.to_dict(),
            'min_value': hourly_agg.min(),
            'max_value': hourly_agg.max(),
            'mean_value': hourly_agg.mean(),
            'std_value': hourly_agg.std(),
            'peak_hour': hourly_agg.idxmax(),
            'off_peak_hour': hourly_agg.idxmin(),
            'variation_coefficient': hourly_agg.std() / hourly_agg.mean() if hourly_agg.mean() > 0 else 0
        }
        
        return pattern_stats
    
    def validate_aggregation_results(self, original_data: pd.DataFrame, 
                                   aggregated_data: pd.DataFrame, 
                                   method: str) -> Dict[str, Any]:
        """
        Validate aggregation results and provide quality metrics.
        
        Args:
            original_data: Original hourly data
            aggregated_data: Aggregated weekly data
            method: Aggregation method used
            
        Returns:
            Dictionary with validation results
        """
        validation_results = {
            'method': method,
            'original_records': len(original_data),
            'aggregated_records': len(aggregated_data),
            'compression_ratio': len(aggregated_data) / len(original_data) if len(original_data) > 0 else 0,
            'links_processed': original_data['link_id'].nunique() if 'link_id' in original_data.columns else 0,
            'links_in_result': aggregated_data['link_id'].nunique() if 'link_id' in aggregated_data.columns else 0,
            'data_loss': False,
            'warnings': []
        }
        
        # Check for data loss
        original_links = set(original_data['link_id'].unique()) if 'link_id' in original_data.columns else set()
        aggregated_links = set(aggregated_data['link_id'].unique()) if 'link_id' in aggregated_data.columns else set()
        
        if len(aggregated_links) < len(original_links):
            validation_results['data_loss'] = True
            missing_links = original_links - aggregated_links
            validation_results['warnings'].append(f"Lost {len(missing_links)} links during aggregation")
        
        # Check for reasonable compression ratio
        if validation_results['compression_ratio'] > 0.8:
            validation_results['warnings'].append("Low compression ratio - aggregation may not be effective")
        
        # Check for extreme values
        if 'avg_duration_sec' in aggregated_data.columns:
            extreme_durations = aggregated_data[aggregated_data['avg_duration_sec'] > 3600]  # > 1 hour
            if len(extreme_durations) > 0:
                validation_results['warnings'].append(f"Found {len(extreme_durations)} links with extreme durations")
        
        if 'avg_speed_kmh' in aggregated_data.columns:
            extreme_speeds = aggregated_data[aggregated_data['avg_speed_kmh'] > 200]  # > 200 km/h
            if len(extreme_speeds) > 0:
                validation_results['warnings'].append(f"Found {len(extreme_speeds)} links with extreme speeds")
        
        logger.info(f"Aggregation validation completed: {validation_results}")
        return validation_results


class MapDataProcessor:
    """Main interface for map data processing operations."""
    
    def __init__(self):
        self.joiner = DataJoiner()
        self.filter_manager = FilterManager()
        self.aggregation_engine = AggregationEngine()
    
    def prepare_map_data(self, gdf: gpd.GeoDataFrame, results_df: pd.DataFrame,
                        filters: Optional[Dict] = None) -> gpd.GeoDataFrame:
        """
        Prepare data for map visualization by joining and filtering.
        
        Args:
            gdf: Shapefile GeoDataFrame
            results_df: Results DataFrame
            filters: Optional filter configuration
            
        Returns:
            Prepared GeoDataFrame ready for visualization
        """
        # Join results to shapefile
        joined_data = self.joiner.join_results_to_shapefile(gdf, results_df)
        
        # Apply filters if provided
        if filters:
            # Apply temporal filters to results data first
            if 'temporal' in filters:
                results_df = self.filter_manager.apply_temporal_filters(
                    results_df, 
                    filters['temporal'].get('date_range'),
                    filters['temporal'].get('hour_range')
                )
                # Re-join with filtered results
                joined_data = self.joiner.join_results_to_shapefile(gdf, results_df)
            
            # Apply attribute filters
            if 'attributes' in filters:
                # Convert to DataFrame for filtering, then back to GeoDataFrame
                df_filtered = self.filter_manager.apply_attribute_filters(
                    pd.DataFrame(joined_data), filters['attributes']
                )
                joined_data = gpd.GeoDataFrame(df_filtered, geometry=df_filtered['geometry'])
            
            # Apply spatial filters
            if 'spatial' in filters:
                joined_data = self.filter_manager.apply_spatial_filters(
                    joined_data, filters['spatial'].get('selection')
                )
        
        return joined_data
    
    def join_results_to_shapefile(self, gdf: gpd.GeoDataFrame, results_df: pd.DataFrame) -> gpd.GeoDataFrame:
        """
        Convenience method to join results to shapefile.
        
        Args:
            gdf: Shapefile GeoDataFrame
            results_df: Results DataFrame
            
        Returns:
            Joined GeoDataFrame
        """
        return self.joiner.join_results_to_shapefile(gdf, results_df)