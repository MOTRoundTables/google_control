"""
KPI calculation engine for interactive map visualization.

This module implements comprehensive KPI calculations including coverage percent,
mean speed, mean duration, number of links rendered, and N days computation
with reactive updates based on filter changes. Now includes data quality metrics.
"""

import pandas as pd
import geopandas as gpd
from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Union
import logging
import numpy as np

logger = logging.getLogger(__name__)


class KPICalculationEngine:
    """
    Comprehensive KPI calculation engine for map visualization.
    
    Handles calculation of coverage percent, mean speed, mean duration,
    number of links rendered, and N days computation with reactive updates.
    """
    
    def __init__(self):
        self.kpi_metrics = [
            'coverage_percent', 'mean_speed', 'mean_duration', 
            'n_links_rendered', 'n_days', 'total_observations',
            'network_length_km', 'data_quality_score', 'quality_issues_count',
            'sparse_links_count', 'join_success_rate'
        ]
        
    def calculate_comprehensive_kpis(self, 
                                   filtered_data: gpd.GeoDataFrame,
                                   total_network_links: int,
                                   date_context: Optional[Dict[str, Any]] = None,
                                   original_results: Optional[pd.DataFrame] = None,
                                   quality_report: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Calculate comprehensive KPI metrics for current filtered data.
        
        Args:
            filtered_data: Current filtered/displayed GeoDataFrame
            total_network_links: Total number of links in the complete network
            date_context: Date context information (n_days, date_range, etc.)
            original_results: Original results DataFrame for comparison
            quality_report: Data quality report from DataQualityChecker
            
        Returns:
            Dictionary with calculated KPI metrics
        """
        if filtered_data.empty:
            return self._get_empty_kpis()
        
        kpis = {}
        
        # Basic coverage metrics
        kpis.update(self._calculate_coverage_metrics(filtered_data, total_network_links))
        
        # Speed and duration metrics
        kpis.update(self._calculate_performance_metrics(filtered_data))
        
        # Network and observation metrics
        kpis.update(self._calculate_network_metrics(filtered_data))
        
        # Date and temporal metrics
        kpis.update(self._calculate_temporal_metrics(date_context))
        
        # Data quality metrics
        kpis.update(self._calculate_quality_metrics(filtered_data, original_results))
        
        # Filter effectiveness metrics
        kpis.update(self._calculate_filter_effectiveness(filtered_data, original_results))
        
        # Quality metrics from quality report
        kpis.update(self._calculate_quality_kpis(quality_report))
        
        logger.debug(f"Calculated comprehensive KPIs: {kpis}")
        return kpis
    
    def _calculate_coverage_metrics(self, data: gpd.GeoDataFrame, 
                                   total_links: int) -> Dict[str, Any]:
        """Calculate coverage-related KPI metrics."""
        metrics = {}
        
        # Coverage percentage
        metrics['coverage_percent'] = (len(data) / total_links * 100) if total_links > 0 else 0
        
        # Links rendered count
        metrics['n_links_rendered'] = len(data)
        
        # Coverage quality assessment
        if metrics['coverage_percent'] >= 90:
            metrics['coverage_quality'] = 'excellent'
        elif metrics['coverage_percent'] >= 75:
            metrics['coverage_quality'] = 'good'
        elif metrics['coverage_percent'] >= 50:
            metrics['coverage_quality'] = 'moderate'
        else:
            metrics['coverage_quality'] = 'limited'
        
        return metrics
    
    def _calculate_performance_metrics(self, data: gpd.GeoDataFrame) -> Dict[str, Any]:
        """Calculate speed and duration performance metrics."""
        metrics = {}
        
        # Mean speed (km/h)
        if 'avg_speed_kmh' in data.columns:
            speed_values = data['avg_speed_kmh'].dropna()
            if not speed_values.empty:
                metrics['mean_speed'] = float(speed_values.mean())
                metrics['median_speed'] = float(speed_values.median())
                metrics['speed_std'] = float(speed_values.std())
                metrics['min_speed'] = float(speed_values.min())
                metrics['max_speed'] = float(speed_values.max())
            else:
                metrics.update({
                    'mean_speed': 0, 'median_speed': 0, 'speed_std': 0,
                    'min_speed': 0, 'max_speed': 0
                })
        else:
            metrics.update({
                'mean_speed': 0, 'median_speed': 0, 'speed_std': 0,
                'min_speed': 0, 'max_speed': 0
            })
        
        # Mean duration (minutes)
        if 'avg_duration_sec' in data.columns:
            duration_values = data['avg_duration_sec'].dropna() / 60  # Convert to minutes
            if not duration_values.empty:
                metrics['mean_duration'] = float(duration_values.mean())
                metrics['median_duration'] = float(duration_values.median())
                metrics['duration_std'] = float(duration_values.std())
                metrics['min_duration'] = float(duration_values.min())
                metrics['max_duration'] = float(duration_values.max())
            else:
                metrics.update({
                    'mean_duration': 0, 'median_duration': 0, 'duration_std': 0,
                    'min_duration': 0, 'max_duration': 0
                })
        elif 'avg_duration_min' in data.columns:
            duration_values = data['avg_duration_min'].dropna()
            if not duration_values.empty:
                metrics['mean_duration'] = float(duration_values.mean())
                metrics['median_duration'] = float(duration_values.median())
                metrics['duration_std'] = float(duration_values.std())
                metrics['min_duration'] = float(duration_values.min())
                metrics['max_duration'] = float(duration_values.max())
            else:
                metrics.update({
                    'mean_duration': 0, 'median_duration': 0, 'duration_std': 0,
                    'min_duration': 0, 'max_duration': 0
                })
        else:
            metrics.update({
                'mean_duration': 0, 'median_duration': 0, 'duration_std': 0,
                'min_duration': 0, 'max_duration': 0
            })
        
        return metrics
    
    def _calculate_network_metrics(self, data: gpd.GeoDataFrame) -> Dict[str, Any]:
        """Calculate network-related metrics."""
        metrics = {}
        
        # Total observations
        if 'n_valid' in data.columns:
            metrics['total_observations'] = int(data['n_valid'].sum())
            metrics['mean_observations_per_link'] = float(data['n_valid'].mean())
            metrics['median_observations_per_link'] = float(data['n_valid'].median())
        else:
            metrics.update({
                'total_observations': len(data),
                'mean_observations_per_link': 1.0,
                'median_observations_per_link': 1.0
            })
        
        # Network length
        if 'length_m' in data.columns:
            total_length_m = data['length_m'].sum()
            metrics['network_length_km'] = float(total_length_m / 1000)
            metrics['mean_link_length_m'] = float(data['length_m'].mean())
            metrics['median_link_length_m'] = float(data['length_m'].median())
        else:
            # Try to calculate from geometry if available
            if hasattr(data, 'geometry') and not data.geometry.empty:
                try:
                    # Calculate length from geometry (assuming projected CRS)
                    lengths = data.geometry.length
                    total_length_m = lengths.sum()
                    metrics['network_length_km'] = float(total_length_m / 1000)
                    metrics['mean_link_length_m'] = float(lengths.mean())
                    metrics['median_link_length_m'] = float(lengths.median())
                except Exception as e:
                    logger.warning(f"Could not calculate geometry lengths: {e}")
                    metrics.update({
                        'network_length_km': 0,
                        'mean_link_length_m': 0,
                        'median_link_length_m': 0
                    })
            else:
                metrics.update({
                    'network_length_km': 0,
                    'mean_link_length_m': 0,
                    'median_link_length_m': 0
                })
        
        return metrics
    
    def _calculate_temporal_metrics(self, date_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate temporal-related metrics."""
        metrics = {}
        
        if date_context:
            metrics['n_days'] = date_context.get('n_days', 1)
            metrics['date_range_str'] = date_context.get('date_range_str', 'Unknown')
            
            # Calculate temporal coverage quality
            n_days = metrics['n_days']
            if n_days >= 30:
                metrics['temporal_coverage'] = 'excellent'
            elif n_days >= 14:
                metrics['temporal_coverage'] = 'good'
            elif n_days >= 7:
                metrics['temporal_coverage'] = 'moderate'
            else:
                metrics['temporal_coverage'] = 'limited'
        else:
            metrics.update({
                'n_days': 1,
                'date_range_str': 'Single period',
                'temporal_coverage': 'limited'
            })
        
        return metrics
    
    def _calculate_quality_metrics(self, data: gpd.GeoDataFrame, 
                                  original_results: Optional[pd.DataFrame]) -> Dict[str, Any]:
        """Calculate data quality metrics."""
        metrics = {}
        
        if data.empty:
            metrics['data_quality_score'] = 0
            return metrics
        
        quality_factors = []
        
        # Observation count quality
        if 'n_valid' in data.columns:
            obs_counts = data['n_valid']
            low_obs_threshold = 5
            sparse_links_ratio = (obs_counts < low_obs_threshold).sum() / len(obs_counts)
            obs_quality = 1 - sparse_links_ratio  # Higher is better
            quality_factors.append(obs_quality)
            
            metrics['sparse_links_percent'] = sparse_links_ratio * 100
        else:
            quality_factors.append(0.5)  # Neutral score when no observation data
            metrics['sparse_links_percent'] = 0
        
        # Speed validity quality
        if 'avg_speed_kmh' in data.columns:
            speed_values = data['avg_speed_kmh'].dropna()
            if not speed_values.empty:
                # Check for reasonable speed values (0-200 km/h)
                valid_speeds = ((speed_values > 0) & (speed_values <= 200)).sum()
                speed_quality = valid_speeds / len(speed_values)
                quality_factors.append(speed_quality)
                
                metrics['invalid_speeds_percent'] = (1 - speed_quality) * 100
            else:
                quality_factors.append(0)
                metrics['invalid_speeds_percent'] = 100
        else:
            metrics['invalid_speeds_percent'] = 0
        
        # Duration validity quality
        if 'avg_duration_sec' in data.columns:
            duration_values = data['avg_duration_sec'].dropna()
            if not duration_values.empty:
                # Check for reasonable duration values (0-3600 seconds = 1 hour)
                valid_durations = ((duration_values > 0) & (duration_values <= 3600)).sum()
                duration_quality = valid_durations / len(duration_values)
                quality_factors.append(duration_quality)
                
                metrics['invalid_durations_percent'] = (1 - duration_quality) * 100
            else:
                quality_factors.append(0)
                metrics['invalid_durations_percent'] = 100
        else:
            metrics['invalid_durations_percent'] = 0
        
        # Calculate overall quality score (0-100)
        if quality_factors:
            metrics['data_quality_score'] = np.mean(quality_factors) * 100
        else:
            metrics['data_quality_score'] = 50  # Neutral score
        
        # Quality assessment
        if metrics['data_quality_score'] >= 90:
            metrics['quality_assessment'] = 'excellent'
        elif metrics['data_quality_score'] >= 75:
            metrics['quality_assessment'] = 'good'
        elif metrics['data_quality_score'] >= 50:
            metrics['quality_assessment'] = 'moderate'
        else:
            metrics['quality_assessment'] = 'poor'
        
        return metrics
    
    def _calculate_filter_effectiveness(self, filtered_data: gpd.GeoDataFrame,
                                      original_results: Optional[pd.DataFrame]) -> Dict[str, Any]:
        """Calculate filter effectiveness metrics."""
        metrics = {}
        
        if original_results is None:
            metrics.update({
                'filter_reduction_percent': 0,
                'filter_effectiveness': 'unknown'
            })
            return metrics
        
        original_count = len(original_results)
        filtered_count = len(filtered_data)
        
        if original_count > 0:
            reduction_percent = ((original_count - filtered_count) / original_count) * 100
            metrics['filter_reduction_percent'] = reduction_percent
            
            # Assess filter effectiveness
            if reduction_percent > 80:
                metrics['filter_effectiveness'] = 'very_high'
            elif reduction_percent > 60:
                metrics['filter_effectiveness'] = 'high'
            elif reduction_percent > 40:
                metrics['filter_effectiveness'] = 'moderate'
            elif reduction_percent > 20:
                metrics['filter_effectiveness'] = 'low'
            else:
                metrics['filter_effectiveness'] = 'minimal'
        else:
            metrics.update({
                'filter_reduction_percent': 0,
                'filter_effectiveness': 'unknown'
            })
        
        return metrics
    
    def _calculate_quality_kpis(self, quality_report: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate quality-related KPI metrics from quality report."""
        metrics = {}
        
        if quality_report is None:
            metrics.update({
                'quality_issues_count': 0,
                'sparse_links_count': 0,
                'join_success_rate': 100.0,
                'quality_level': 'unknown',
                'speed_quality_score': 0,
                'duration_quality_score': 0,
                'observation_quality_score': 0
            })
            return metrics
        
        # Overall quality metrics
        overall_quality = quality_report.get('overall_quality', {})
        metrics['quality_level'] = overall_quality.get('overall_level', 'unknown')
        
        # Count total quality issues
        total_issues = 0
        for validation_type in ['speed_validation', 'duration_validation', 'observation_validation', 'geometry_validation']:
            validation_data = quality_report.get(validation_type, {})
            issues = validation_data.get('issues', [])
            total_issues += len(issues)
        
        metrics['quality_issues_count'] = total_issues
        
        # Component quality scores
        component_scores = overall_quality.get('component_scores', {})
        metrics['speed_quality_score'] = component_scores.get('speed', 0)
        metrics['duration_quality_score'] = component_scores.get('duration', 0)
        metrics['observation_quality_score'] = component_scores.get('observations', 0)
        
        # Sparse links count
        obs_validation = quality_report.get('observation_validation', {})
        sparse_links = obs_validation.get('sparse_links', [])
        critical_links = obs_validation.get('critical_links', [])
        metrics['sparse_links_count'] = len(sparse_links) + len(critical_links)
        
        # Join success rate
        join_audit = quality_report.get('join_audit', {})
        join_analysis = join_audit.get('join_analysis', {})
        metrics['join_success_rate'] = join_analysis.get('join_success_rate', 100.0)
        
        # Quality indicators for display
        if metrics['quality_issues_count'] == 0:
            metrics['quality_indicator'] = '✅'
        elif metrics['quality_issues_count'] <= 3:
            metrics['quality_indicator'] = '⚠️'
        else:
            metrics['quality_indicator'] = '❌'
        
        return metrics
    
    def _get_empty_kpis(self) -> Dict[str, Any]:
        """Return KPI dictionary with zero/empty values."""
        return {
            'coverage_percent': 0,
            'coverage_quality': 'none',
            'mean_speed': 0,
            'median_speed': 0,
            'speed_std': 0,
            'min_speed': 0,
            'max_speed': 0,
            'mean_duration': 0,
            'median_duration': 0,
            'duration_std': 0,
            'min_duration': 0,
            'max_duration': 0,
            'n_links_rendered': 0,
            'total_observations': 0,
            'mean_observations_per_link': 0,
            'median_observations_per_link': 0,
            'network_length_km': 0,
            'mean_link_length_m': 0,
            'median_link_length_m': 0,
            'n_days': 0,
            'date_range_str': 'No data',
            'temporal_coverage': 'none',
            'data_quality_score': 0,
            'quality_assessment': 'none',
            'sparse_links_percent': 0,
            'invalid_speeds_percent': 0,
            'invalid_durations_percent': 0,
            'filter_reduction_percent': 0,
            'filter_effectiveness': 'none',
            'quality_issues_count': 0,
            'sparse_links_count': 0,
            'join_success_rate': 100.0,
            'quality_level': 'none',
            'speed_quality_score': 0,
            'duration_quality_score': 0,
            'observation_quality_score': 0,
            'quality_indicator': '❓'
        }
    
    def calculate_reactive_kpis(self, 
                               current_data: gpd.GeoDataFrame,
                               previous_kpis: Optional[Dict[str, Any]],
                               total_network_links: int,
                               date_context: Optional[Dict[str, Any]] = None,
                               original_results: Optional[pd.DataFrame] = None,
                               quality_report: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Calculate KPIs with reactive updates, showing changes from previous state.
        
        Args:
            current_data: Current filtered data
            previous_kpis: Previous KPI values for comparison
            total_network_links: Total network links
            date_context: Date context information
            original_results: Original results for comparison
            quality_report: Data quality report
            
        Returns:
            Dictionary with current KPIs and change indicators
        """
        # Calculate current KPIs
        current_kpis = self.calculate_comprehensive_kpis(
            current_data, total_network_links, date_context, original_results, quality_report
        )
        
        # Add change indicators if previous KPIs available
        if previous_kpis:
            current_kpis['changes'] = self._calculate_kpi_changes(previous_kpis, current_kpis)
        else:
            current_kpis['changes'] = {}
        
        return current_kpis
    
    def _calculate_kpi_changes(self, previous: Dict[str, Any], 
                              current: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate changes between previous and current KPIs."""
        changes = {}
        
        # Numeric metrics to track changes for
        numeric_metrics = [
            'coverage_percent', 'mean_speed', 'mean_duration', 
            'n_links_rendered', 'total_observations', 'network_length_km',
            'data_quality_score', 'quality_issues_count', 'sparse_links_count',
            'join_success_rate'
        ]
        
        for metric in numeric_metrics:
            if metric in previous and metric in current:
                prev_val = previous[metric]
                curr_val = current[metric]
                
                if prev_val != 0:
                    change_percent = ((curr_val - prev_val) / prev_val) * 100
                    changes[f"{metric}_change"] = change_percent
                    changes[f"{metric}_direction"] = 'up' if change_percent > 0 else 'down' if change_percent < 0 else 'same'
                else:
                    changes[f"{metric}_change"] = 0
                    changes[f"{metric}_direction"] = 'same'
        
        return changes
    
    def format_kpi_for_display(self, kpis: Dict[str, Any], 
                              metric_name: str) -> Tuple[str, str, Optional[str]]:
        """
        Format KPI metric for display in Streamlit.
        
        Args:
            kpis: KPI dictionary
            metric_name: Name of the metric to format
            
        Returns:
            Tuple of (formatted_value, unit, change_indicator)
        """
        if metric_name not in kpis:
            return "N/A", "", None
        
        value = kpis[metric_name]
        change_key = f"{metric_name}_change"
        
        # Format based on metric type
        if metric_name == 'coverage_percent':
            formatted_value = f"{value:.1f}"
            unit = "%"
        elif metric_name in ['mean_speed', 'median_speed']:
            formatted_value = f"{value:.1f}"
            unit = "km/h"
        elif metric_name in ['mean_duration', 'median_duration']:
            formatted_value = f"{value:.1f}"
            unit = "min"
        elif metric_name == 'n_links_rendered':
            formatted_value = f"{int(value):,}"
            unit = ""
        elif metric_name == 'total_observations':
            formatted_value = f"{int(value):,}"
            unit = ""
        elif metric_name == 'network_length_km':
            formatted_value = f"{value:.1f}"
            unit = "km"
        elif metric_name == 'n_days':
            formatted_value = f"{int(value)}"
            unit = ""
        elif metric_name == 'data_quality_score':
            formatted_value = f"{value:.0f}"
            unit = "/100"
        elif metric_name == 'quality_issues_count':
            formatted_value = f"{int(value)}"
            unit = ""
        elif metric_name == 'sparse_links_count':
            formatted_value = f"{int(value)}"
            unit = ""
        elif metric_name == 'join_success_rate':
            formatted_value = f"{value:.1f}"
            unit = "%"
        else:
            formatted_value = f"{value:.2f}"
            unit = ""
        
        # Add change indicator if available
        change_indicator = None
        if 'changes' in kpis and change_key in kpis['changes']:
            change_percent = kpis['changes'][change_key]
            if abs(change_percent) > 0.1:  # Only show significant changes
                direction = "↑" if change_percent > 0 else "↓"
                change_indicator = f"{direction} {abs(change_percent):.1f}%"
        
        return formatted_value, unit, change_indicator
    
    def get_kpi_summary_text(self, kpis: Dict[str, Any]) -> str:
        """
        Generate a summary text description of current KPIs.
        
        Args:
            kpis: KPI dictionary
            
        Returns:
            Summary text string
        """
        if kpis.get('n_links_rendered', 0) == 0:
            return "No data available for analysis."
        
        coverage = kpis.get('coverage_percent', 0)
        n_links = kpis.get('n_links_rendered', 0)
        quality = kpis.get('quality_assessment', 'unknown')
        
        summary_parts = [
            f"Displaying {n_links:,} links ({coverage:.1f}% coverage)",
            f"Data quality: {quality.title()}"
        ]
        
        # Add performance summary
        if kpis.get('mean_speed', 0) > 0:
            mean_speed = kpis['mean_speed']
            summary_parts.append(f"Average speed: {mean_speed:.1f} km/h")
        
        if kpis.get('mean_duration', 0) > 0:
            mean_duration = kpis['mean_duration']
            summary_parts.append(f"Average duration: {mean_duration:.1f} min")
        
        # Add temporal context
        n_days = kpis.get('n_days', 1)
        if n_days > 1:
            summary_parts.append(f"Across {n_days} days")
        
        return " • ".join(summary_parts)