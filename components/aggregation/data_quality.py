"""
Data quality and validation system for interactive map visualization.

This module implements comprehensive data quality checks including validation
for non-positive speeds, extreme durations, sparse observation flagging,
and join audit with counts for missing/duplicate/invalid data.
"""

import pandas as pd
import geopandas as gpd
from datetime import date, datetime
from typing import Dict, List, Tuple, Optional, Any, Union
import logging
import numpy as np

logger = logging.getLogger(__name__)


class DataQualityChecker:
    """
    Comprehensive data quality validation system.
    
    Handles validation for non-positive speeds, extreme durations,
    sparse observations, and join audit functionality.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize data quality checker with configuration.
        
        Args:
            config: Configuration dictionary with quality thresholds
        """
        self.config = config or self._get_default_config()
        
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for data quality checks."""
        return {
            'speed_thresholds': {
                'min_valid_speed': 0.1,  # km/h
                'max_valid_speed': 200.0,  # km/h
                'extreme_low_speed': 5.0,  # km/h
                'extreme_high_speed': 120.0  # km/h
            },
            'duration_thresholds': {
                'min_valid_duration': 1.0,  # seconds
                'max_valid_duration': 7200.0,  # seconds (2 hours)
                'extreme_short_duration': 30.0,  # seconds
                'extreme_long_duration': 3600.0  # seconds (1 hour)
            },
            'observation_thresholds': {
                'min_observations_reliable': 10,
                'min_observations_sparse': 3,
                'min_observations_critical': 1
            },
            'geometry_validation': {
                'min_length_meters': 1.0,
                'max_length_meters': 50000.0  # 50km
            }
        }
    
    def perform_comprehensive_quality_check(self, 
                                          gdf: gpd.GeoDataFrame,
                                          results_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Perform comprehensive data quality check on spatial and results data.
        
        Args:
            gdf: Shapefile GeoDataFrame
            results_df: Results DataFrame
            
        Returns:
            Dictionary with comprehensive quality check results
        """
        quality_report = {
            'timestamp': datetime.now().isoformat(),
            'data_summary': self._get_data_summary(gdf, results_df),
            'speed_validation': self._validate_speeds(results_df),
            'duration_validation': self._validate_durations(results_df),
            'observation_validation': self._validate_observations(results_df),
            'geometry_validation': self._validate_geometries(gdf),
            'join_audit': self._perform_join_audit(gdf, results_df),
            'overall_quality': {}
        }
        
        # Calculate overall quality score
        quality_report['overall_quality'] = self._calculate_overall_quality(quality_report)
        
        logger.info(f"Comprehensive quality check completed: {quality_report['overall_quality']}")
        return quality_report
    
    def _get_data_summary(self, gdf: gpd.GeoDataFrame, 
                         results_df: pd.DataFrame) -> Dict[str, Any]:
        """Get basic data summary statistics."""
        return {
            'shapefile_features': len(gdf),
            'results_records': len(results_df),
            'unique_link_ids': results_df['link_id'].nunique() if 'link_id' in results_df.columns else 0,
            'date_range': {
                'start': results_df['date'].min() if 'date' in results_df.columns else None,
                'end': results_df['date'].max() if 'date' in results_df.columns else None,
                'unique_dates': results_df['date'].nunique() if 'date' in results_df.columns else 0
            },
            'hour_coverage': {
                'min_hour': results_df['hour'].min() if 'hour' in results_df.columns else None,
                'max_hour': results_df['hour'].max() if 'hour' in results_df.columns else None,
                'unique_hours': results_df['hour'].nunique() if 'hour' in results_df.columns else 0
            }
        }
    
    def _validate_speeds(self, results_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate speed data for non-positive and extreme values.
        
        Args:
            results_df: Results DataFrame with speed data
            
        Returns:
            Dictionary with speed validation results
        """
        validation_result = {
            'total_records': len(results_df),
            'has_speed_data': 'avg_speed_kmh' in results_df.columns,
            'issues': [],
            'statistics': {},
            'flagged_records': []
        }
        
        if not validation_result['has_speed_data']:
            validation_result['issues'].append("No speed data column found (avg_speed_kmh)")
            return validation_result
        
        speed_col = results_df['avg_speed_kmh']
        speed_values = speed_col.dropna()
        
        if speed_values.empty:
            validation_result['issues'].append("All speed values are null/missing")
            return validation_result
        
        # Basic statistics
        validation_result['statistics'] = {
            'count': len(speed_values),
            'null_count': speed_col.isnull().sum(),
            'mean': float(speed_values.mean()),
            'median': float(speed_values.median()),
            'std': float(speed_values.std()),
            'min': float(speed_values.min()),
            'max': float(speed_values.max()),
            'q25': float(speed_values.quantile(0.25)),
            'q75': float(speed_values.quantile(0.75))
        }
        
        # Validation checks
        thresholds = self.config['speed_thresholds']
        
        # Non-positive speeds
        non_positive = speed_values <= 0
        if non_positive.any():
            count = non_positive.sum()
            validation_result['issues'].append(f"Found {count} non-positive speed values")
            validation_result['flagged_records'].extend(
                results_df[results_df['avg_speed_kmh'] <= 0].index.tolist()
            )
        
        # Extreme low speeds
        extreme_low = (speed_values > 0) & (speed_values < thresholds['extreme_low_speed'])
        if extreme_low.any():
            count = extreme_low.sum()
            validation_result['issues'].append(
                f"Found {count} extremely low speeds (< {thresholds['extreme_low_speed']} km/h)"
            )
        
        # Extreme high speeds
        extreme_high = speed_values > thresholds['extreme_high_speed']
        if extreme_high.any():
            count = extreme_high.sum()
            validation_result['issues'].append(
                f"Found {count} extremely high speeds (> {thresholds['extreme_high_speed']} km/h)"
            )
            validation_result['flagged_records'].extend(
                results_df[results_df['avg_speed_kmh'] > thresholds['extreme_high_speed']].index.tolist()
            )
        
        # Invalid range speeds
        invalid_range = (speed_values < thresholds['min_valid_speed']) | \
                       (speed_values > thresholds['max_valid_speed'])
        if invalid_range.any():
            count = invalid_range.sum()
            validation_result['issues'].append(
                f"Found {count} speeds outside valid range "
                f"({thresholds['min_valid_speed']}-{thresholds['max_valid_speed']} km/h)"
            )
        
        # Quality assessment
        total_issues = len([idx for idx in validation_result['flagged_records']])
        validation_result['quality_score'] = max(0, 100 - (total_issues / len(speed_values) * 100))
        
        if validation_result['quality_score'] >= 95:
            validation_result['quality_level'] = 'excellent'
        elif validation_result['quality_score'] >= 85:
            validation_result['quality_level'] = 'good'
        elif validation_result['quality_score'] >= 70:
            validation_result['quality_level'] = 'moderate'
        else:
            validation_result['quality_level'] = 'poor'
        
        return validation_result
    
    def _validate_durations(self, results_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate duration data for non-positive and extreme values.
        
        Args:
            results_df: Results DataFrame with duration data
            
        Returns:
            Dictionary with duration validation results
        """
        validation_result = {
            'total_records': len(results_df),
            'has_duration_data': 'avg_duration_sec' in results_df.columns,
            'issues': [],
            'statistics': {},
            'flagged_records': []
        }
        
        if not validation_result['has_duration_data']:
            validation_result['issues'].append("No duration data column found (avg_duration_sec)")
            return validation_result
        
        duration_col = results_df['avg_duration_sec']
        duration_values = duration_col.dropna()
        
        if duration_values.empty:
            validation_result['issues'].append("All duration values are null/missing")
            return validation_result
        
        # Basic statistics
        validation_result['statistics'] = {
            'count': len(duration_values),
            'null_count': duration_col.isnull().sum(),
            'mean': float(duration_values.mean()),
            'median': float(duration_values.median()),
            'std': float(duration_values.std()),
            'min': float(duration_values.min()),
            'max': float(duration_values.max()),
            'q25': float(duration_values.quantile(0.25)),
            'q75': float(duration_values.quantile(0.75)),
            'mean_minutes': float(duration_values.mean() / 60),
            'median_minutes': float(duration_values.median() / 60)
        }
        
        # Validation checks
        thresholds = self.config['duration_thresholds']
        
        # Non-positive durations
        non_positive = duration_values <= 0
        if non_positive.any():
            count = non_positive.sum()
            validation_result['issues'].append(f"Found {count} non-positive duration values")
            validation_result['flagged_records'].extend(
                results_df[results_df['avg_duration_sec'] <= 0].index.tolist()
            )
        
        # Extreme short durations
        extreme_short = (duration_values > 0) & (duration_values < thresholds['extreme_short_duration'])
        if extreme_short.any():
            count = extreme_short.sum()
            validation_result['issues'].append(
                f"Found {count} extremely short durations (< {thresholds['extreme_short_duration']} sec)"
            )
        
        # Extreme long durations
        extreme_long = duration_values > thresholds['extreme_long_duration']
        if extreme_long.any():
            count = extreme_long.sum()
            validation_result['issues'].append(
                f"Found {count} extremely long durations (> {thresholds['extreme_long_duration']} sec)"
            )
            validation_result['flagged_records'].extend(
                results_df[results_df['avg_duration_sec'] > thresholds['extreme_long_duration']].index.tolist()
            )
        
        # Invalid range durations
        invalid_range = (duration_values < thresholds['min_valid_duration']) | \
                       (duration_values > thresholds['max_valid_duration'])
        if invalid_range.any():
            count = invalid_range.sum()
            validation_result['issues'].append(
                f"Found {count} durations outside valid range "
                f"({thresholds['min_valid_duration']}-{thresholds['max_valid_duration']} sec)"
            )
        
        # Quality assessment
        total_issues = len([idx for idx in validation_result['flagged_records']])
        validation_result['quality_score'] = max(0, 100 - (total_issues / len(duration_values) * 100))
        
        if validation_result['quality_score'] >= 95:
            validation_result['quality_level'] = 'excellent'
        elif validation_result['quality_score'] >= 85:
            validation_result['quality_level'] = 'good'
        elif validation_result['quality_score'] >= 70:
            validation_result['quality_level'] = 'moderate'
        else:
            validation_result['quality_level'] = 'poor'
        
        return validation_result
    
    def _validate_observations(self, results_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate observation counts and flag sparse observations.
        
        Args:
            results_df: Results DataFrame with observation counts
            
        Returns:
            Dictionary with observation validation results
        """
        validation_result = {
            'total_records': len(results_df),
            'has_observation_data': 'n_valid' in results_df.columns,
            'issues': [],
            'statistics': {},
            'sparse_links': [],
            'critical_links': []
        }
        
        if not validation_result['has_observation_data']:
            validation_result['issues'].append("No observation count column found (n_valid)")
            return validation_result
        
        obs_col = results_df['n_valid']
        obs_values = obs_col.dropna()
        
        if obs_values.empty:
            validation_result['issues'].append("All observation count values are null/missing")
            return validation_result
        
        # Basic statistics
        validation_result['statistics'] = {
            'count': len(obs_values),
            'null_count': obs_col.isnull().sum(),
            'total_observations': int(obs_values.sum()),
            'mean': float(obs_values.mean()),
            'median': float(obs_values.median()),
            'std': float(obs_values.std()),
            'min': int(obs_values.min()),
            'max': int(obs_values.max()),
            'q25': float(obs_values.quantile(0.25)),
            'q75': float(obs_values.quantile(0.75))
        }
        
        # Validation checks
        thresholds = self.config['observation_thresholds']
        
        # Critical links (very few observations)
        critical_mask = obs_values < thresholds['min_observations_critical']
        if critical_mask.any():
            count = critical_mask.sum()
            validation_result['issues'].append(
                f"Found {count} links with critically low observations (< {thresholds['min_observations_critical']})"
            )
            validation_result['critical_links'] = results_df[
                results_df['n_valid'] < thresholds['min_observations_critical']
            ]['link_id'].tolist() if 'link_id' in results_df.columns else []
        
        # Sparse links
        sparse_mask = (obs_values >= thresholds['min_observations_critical']) & \
                     (obs_values < thresholds['min_observations_sparse'])
        if sparse_mask.any():
            count = sparse_mask.sum()
            validation_result['issues'].append(
                f"Found {count} links with sparse observations "
                f"({thresholds['min_observations_critical']}-{thresholds['min_observations_sparse']})"
            )
            validation_result['sparse_links'] = results_df[
                (results_df['n_valid'] >= thresholds['min_observations_critical']) &
                (results_df['n_valid'] < thresholds['min_observations_sparse'])
            ]['link_id'].tolist() if 'link_id' in results_df.columns else []
        
        # Unreliable links (below reliable threshold)
        unreliable_mask = obs_values < thresholds['min_observations_reliable']
        if unreliable_mask.any():
            count = unreliable_mask.sum()
            validation_result['issues'].append(
                f"Found {count} links with unreliable observation counts (< {thresholds['min_observations_reliable']})"
            )
        
        # Quality assessment based on observation distribution
        reliable_count = (obs_values >= thresholds['min_observations_reliable']).sum()
        validation_result['quality_score'] = (reliable_count / len(obs_values)) * 100
        
        if validation_result['quality_score'] >= 80:
            validation_result['quality_level'] = 'excellent'
        elif validation_result['quality_score'] >= 60:
            validation_result['quality_level'] = 'good'
        elif validation_result['quality_score'] >= 40:
            validation_result['quality_level'] = 'moderate'
        else:
            validation_result['quality_level'] = 'poor'
        
        return validation_result
    
    def _validate_geometries(self, gdf: gpd.GeoDataFrame) -> Dict[str, Any]:
        """
        Validate shapefile geometries for validity and reasonable properties.
        
        Args:
            gdf: Shapefile GeoDataFrame
            
        Returns:
            Dictionary with geometry validation results
        """
        validation_result = {
            'total_features': len(gdf),
            'issues': [],
            'statistics': {},
            'invalid_geometries': [],
            'extreme_geometries': []
        }
        
        if gdf.empty:
            validation_result['issues'].append("No geometries to validate")
            return validation_result
        
        # Check for invalid geometries
        invalid_mask = ~gdf.geometry.is_valid
        if invalid_mask.any():
            count = invalid_mask.sum()
            validation_result['issues'].append(f"Found {count} invalid geometries")
            validation_result['invalid_geometries'] = gdf[invalid_mask].index.tolist()
        
        # Check for null geometries
        null_mask = gdf.geometry.isnull()
        if null_mask.any():
            count = null_mask.sum()
            validation_result['issues'].append(f"Found {count} null geometries")
        
        # Calculate geometry lengths (if in projected CRS)
        try:
            lengths = gdf.geometry.length
            valid_lengths = lengths[lengths > 0]
            
            if not valid_lengths.empty:
                validation_result['statistics'] = {
                    'count': len(valid_lengths),
                    'mean_length': float(valid_lengths.mean()),
                    'median_length': float(valid_lengths.median()),
                    'std_length': float(valid_lengths.std()),
                    'min_length': float(valid_lengths.min()),
                    'max_length': float(valid_lengths.max()),
                    'q25_length': float(valid_lengths.quantile(0.25)),
                    'q75_length': float(valid_lengths.quantile(0.75))
                }
                
                # Check for extreme lengths
                thresholds = self.config['geometry_validation']
                
                # Very short links
                short_mask = (lengths > 0) & (lengths < thresholds['min_length_meters'])
                if short_mask.any():
                    count = short_mask.sum()
                    validation_result['issues'].append(
                        f"Found {count} very short links (< {thresholds['min_length_meters']} m)"
                    )
                
                # Very long links
                long_mask = lengths > thresholds['max_length_meters']
                if long_mask.any():
                    count = long_mask.sum()
                    validation_result['issues'].append(
                        f"Found {count} very long links (> {thresholds['max_length_meters']} m)"
                    )
                    validation_result['extreme_geometries'].extend(
                        gdf[lengths > thresholds['max_length_meters']].index.tolist()
                    )
        
        except Exception as e:
            validation_result['issues'].append(f"Could not calculate geometry lengths: {str(e)}")
        
        # Quality assessment
        total_issues = len(validation_result['invalid_geometries']) + len(validation_result['extreme_geometries'])
        validation_result['quality_score'] = max(0, 100 - (total_issues / len(gdf) * 100))
        
        if validation_result['quality_score'] >= 95:
            validation_result['quality_level'] = 'excellent'
        elif validation_result['quality_score'] >= 85:
            validation_result['quality_level'] = 'good'
        elif validation_result['quality_score'] >= 70:
            validation_result['quality_level'] = 'moderate'
        else:
            validation_result['quality_level'] = 'poor'
        
        return validation_result
    
    def _perform_join_audit(self, gdf: gpd.GeoDataFrame, 
                           results_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Perform comprehensive join audit with counts for missing/duplicate/invalid data.
        
        Args:
            gdf: Shapefile GeoDataFrame
            results_df: Results DataFrame
            
        Returns:
            Dictionary with join audit results
        """
        audit_result = {
            'shapefile_summary': {},
            'results_summary': {},
            'join_analysis': {},
            'missing_data': {},
            'duplicate_analysis': {},
            'recommendations': []
        }
        
        # Shapefile summary
        if not gdf.empty and all(col in gdf.columns for col in ['From', 'To']):
            shapefile_keys = 's_' + gdf['From'].astype(str) + '-' + gdf['To'].astype(str)
            audit_result['shapefile_summary'] = {
                'total_features': len(gdf),
                'unique_from_nodes': gdf['From'].nunique(),
                'unique_to_nodes': gdf['To'].nunique(),
                'unique_link_keys': shapefile_keys.nunique(),
                'duplicate_keys_in_shapefile': len(shapefile_keys) - shapefile_keys.nunique()
            }
        else:
            audit_result['shapefile_summary'] = {
                'total_features': len(gdf),
                'error': 'Missing required From/To columns'
            }
        
        # Results summary
        if not results_df.empty and 'link_id' in results_df.columns:
            audit_result['results_summary'] = {
                'total_records': len(results_df),
                'unique_link_ids': results_df['link_id'].nunique(),
                'duplicate_records': len(results_df) - len(results_df.drop_duplicates()),
                'null_link_ids': results_df['link_id'].isnull().sum()
            }
        else:
            audit_result['results_summary'] = {
                'total_records': len(results_df),
                'error': 'Missing required link_id column'
            }
        
        # Join analysis (only if both datasets are valid)
        if ('error' not in audit_result['shapefile_summary'] and 
            'error' not in audit_result['results_summary']):
            
            shapefile_keys = set('s_' + gdf['From'].astype(str) + '-' + gdf['To'].astype(str))
            results_keys = set(results_df['link_id'].unique())
            
            audit_result['join_analysis'] = {
                'shapefile_keys_count': len(shapefile_keys),
                'results_keys_count': len(results_keys),
                'successful_matches': len(shapefile_keys & results_keys),
                'missing_in_shapefile': len(results_keys - shapefile_keys),
                'missing_in_results': len(shapefile_keys - results_keys),
                'join_success_rate': (len(shapefile_keys & results_keys) / len(shapefile_keys)) * 100 if shapefile_keys else 0
            }
            
            # Missing data details
            audit_result['missing_data'] = {
                'results_links_not_in_shapefile': list(results_keys - shapefile_keys),
                'shapefile_links_not_in_results': list(shapefile_keys - results_keys)
            }
        
        # Duplicate analysis
        if 'link_id' in results_df.columns:
            # Find duplicates by link_id, date, hour combination
            if all(col in results_df.columns for col in ['link_id', 'date', 'hour']):
                duplicate_mask = results_df.duplicated(subset=['link_id', 'date', 'hour'], keep=False)
                duplicates = results_df[duplicate_mask]
                
                audit_result['duplicate_analysis'] = {
                    'total_duplicate_records': len(duplicates),
                    'unique_duplicate_combinations': duplicates[['link_id', 'date', 'hour']].drop_duplicates().shape[0],
                    'links_with_duplicates': duplicates['link_id'].nunique(),
                    'sample_duplicates': duplicates.head(10).to_dict('records') if not duplicates.empty else []
                }
            else:
                audit_result['duplicate_analysis'] = {
                    'error': 'Cannot analyze duplicates - missing date/hour columns'
                }
        
        # Generate recommendations
        audit_result['recommendations'] = self._generate_join_recommendations(audit_result)
        
        return audit_result
    
    def _generate_join_recommendations(self, audit_result: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on join audit results."""
        recommendations = []
        
        # Check join success rate
        if 'join_analysis' in audit_result:
            success_rate = audit_result['join_analysis'].get('join_success_rate', 0)
            if success_rate < 50:
                recommendations.append("Low join success rate - verify link_id format matches s_From-To pattern")
            elif success_rate < 80:
                recommendations.append("Moderate join success rate - review missing links for data completeness")
        
        # Check for missing data
        if 'missing_data' in audit_result:
            missing_in_shapefile = len(audit_result['missing_data'].get('results_links_not_in_shapefile', []))
            missing_in_results = len(audit_result['missing_data'].get('shapefile_links_not_in_results', []))
            
            if missing_in_shapefile > 0:
                recommendations.append(f"Consider updating shapefile - {missing_in_shapefile} result links have no geometry")
            
            if missing_in_results > 0:
                recommendations.append(f"Consider data collection - {missing_in_results} shapefile links have no results")
        
        # Check for duplicates
        if 'duplicate_analysis' in audit_result and 'total_duplicate_records' in audit_result['duplicate_analysis']:
            duplicate_count = audit_result['duplicate_analysis']['total_duplicate_records']
            if duplicate_count > 0:
                recommendations.append(f"Remove {duplicate_count} duplicate records before analysis")
        
        return recommendations
    
    def _calculate_overall_quality(self, quality_report: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall quality score and assessment."""
        quality_scores = []
        
        # Collect individual quality scores
        for validation_type in ['speed_validation', 'duration_validation', 'observation_validation', 'geometry_validation']:
            if validation_type in quality_report and 'quality_score' in quality_report[validation_type]:
                quality_scores.append(quality_report[validation_type]['quality_score'])
        
        if not quality_scores:
            return {
                'overall_score': 0,
                'overall_level': 'unknown',
                'summary': 'No quality metrics available'
            }
        
        # Calculate weighted average (can be customized)
        overall_score = np.mean(quality_scores)
        
        # Determine overall quality level
        if overall_score >= 90:
            overall_level = 'excellent'
            summary = 'Data quality is excellent with minimal issues'
        elif overall_score >= 75:
            overall_level = 'good'
            summary = 'Data quality is good with minor issues'
        elif overall_score >= 60:
            overall_level = 'moderate'
            summary = 'Data quality is moderate with some issues requiring attention'
        else:
            overall_level = 'poor'
            summary = 'Data quality is poor with significant issues requiring immediate attention'
        
        return {
            'overall_score': overall_score,
            'overall_level': overall_level,
            'summary': summary,
            'component_scores': {
                'speed': quality_report.get('speed_validation', {}).get('quality_score', 0),
                'duration': quality_report.get('duration_validation', {}).get('quality_score', 0),
                'observations': quality_report.get('observation_validation', {}).get('quality_score', 0),
                'geometry': quality_report.get('geometry_validation', {}).get('quality_score', 0)
            }
        }
    
    def get_sparse_observation_filter(self, results_df: pd.DataFrame,
                                    min_observations: Optional[int] = None) -> pd.DataFrame:
        """
        Create one-click filter for sparse observations.
        
        Args:
            results_df: Results DataFrame
            min_observations: Minimum observation threshold (uses config default if None)
            
        Returns:
            Filtered DataFrame excluding sparse observations
        """
        if min_observations is None:
            min_observations = self.config['observation_thresholds']['min_observations_reliable']
        
        if 'n_valid' not in results_df.columns:
            logger.warning("No observation count column found - returning original data")
            return results_df
        
        # Filter out sparse observations
        filtered_df = results_df[results_df['n_valid'] >= min_observations].copy()
        
        removed_count = len(results_df) - len(filtered_df)
        logger.info(f"Sparse observation filter removed {removed_count} records with < {min_observations} observations")
        
        return filtered_df
    
    def get_quality_flagged_records(self, results_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        Get records flagged for various quality issues.
        
        Args:
            results_df: Results DataFrame
            
        Returns:
            Dictionary with DataFrames for different quality issues
        """
        flagged_records = {}
        
        # Speed issues
        if 'avg_speed_kmh' in results_df.columns:
            speed_thresholds = self.config['speed_thresholds']
            
            # Non-positive speeds
            flagged_records['non_positive_speeds'] = results_df[
                results_df['avg_speed_kmh'] <= 0
            ].copy()
            
            # Extreme speeds
            flagged_records['extreme_speeds'] = results_df[
                (results_df['avg_speed_kmh'] > speed_thresholds['extreme_high_speed']) |
                ((results_df['avg_speed_kmh'] > 0) & (results_df['avg_speed_kmh'] < speed_thresholds['extreme_low_speed']))
            ].copy()
        
        # Duration issues
        if 'avg_duration_sec' in results_df.columns:
            duration_thresholds = self.config['duration_thresholds']
            
            # Non-positive durations
            flagged_records['non_positive_durations'] = results_df[
                results_df['avg_duration_sec'] <= 0
            ].copy()
            
            # Extreme durations
            flagged_records['extreme_durations'] = results_df[
                (results_df['avg_duration_sec'] > duration_thresholds['extreme_long_duration']) |
                ((results_df['avg_duration_sec'] > 0) & (results_df['avg_duration_sec'] < duration_thresholds['extreme_short_duration']))
            ].copy()
        
        # Sparse observations
        if 'n_valid' in results_df.columns:
            obs_threshold = self.config['observation_thresholds']['min_observations_sparse']
            flagged_records['sparse_observations'] = results_df[
                results_df['n_valid'] < obs_threshold
            ].copy()
        
        return flagged_records