"""
Tests for data quality and validation system.

This module tests the comprehensive data quality checks including validation
for non-positive speeds, extreme durations, sparse observation flagging,
and join audit functionality.
"""

import pytest
import pandas as pd
import geopandas as gpd
import numpy as np
from datetime import date, datetime
from shapely.geometry import LineString, Point
import tempfile
import os
import sys

# Add parent directories to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from data_quality import DataQualityChecker
from quality_reporting import QualityReportingInterface


class TestDataQualityChecker:
    """Test suite for DataQualityChecker class."""
    
    @pytest.fixture
    def sample_shapefile_data(self):
        """Create sample shapefile data for testing."""
        # Create sample geometries
        geometries = [
            LineString([(0, 0), (1, 1)]),
            LineString([(1, 1), (2, 2)]),
            LineString([(2, 2), (3, 3)]),
            LineString([(3, 3), (4, 4)]),
            LineString([(4, 4), (5, 5)])
        ]
        
        data = {
            'Id': [1, 2, 3, 4, 5],
            'From': [100, 101, 102, 103, 104],
            'To': [101, 102, 103, 104, 105],
            'geometry': geometries
        }
        
        return gpd.GeoDataFrame(data, crs='EPSG:4326')
    
    @pytest.fixture
    def sample_results_data(self):
        """Create sample results data for testing."""
        data = {
            'link_id': ['s_100-101', 's_101-102', 's_102-103', 's_103-104', 's_104-105'],
            'date': ['2025-01-01', '2025-01-01', '2025-01-01', '2025-01-01', '2025-01-01'],
            'hour': [8, 8, 8, 8, 8],
            'avg_speed_kmh': [45.5, 52.3, 38.7, 61.2, 49.8],
            'avg_duration_sec': [120, 95, 180, 85, 110],
            'n_valid': [25, 18, 32, 15, 28]
        }
        
        return pd.DataFrame(data)
    
    @pytest.fixture
    def quality_checker(self):
        """Create DataQualityChecker instance with default config."""
        return DataQualityChecker()
    
    @pytest.fixture
    def problematic_results_data(self):
        """Create results data with various quality issues."""
        data = {
            'link_id': ['s_100-101', 's_101-102', 's_102-103', 's_103-104', 's_104-105', 's_105-106'],
            'date': ['2025-01-01', '2025-01-01', '2025-01-01', '2025-01-01', '2025-01-01', '2025-01-01'],
            'hour': [8, 8, 8, 8, 8, 8],
            'avg_speed_kmh': [-5.0, 250.0, 2.5, 0.0, 45.5, np.nan],  # Issues: negative, extreme high, extreme low, zero, normal, null
            'avg_duration_sec': [5400, -30, 15, 0, 120, np.nan],  # Issues: extreme long, negative, extreme short, zero, normal, null
            'n_valid': [1, 2, 50, 0, 25, 5]  # Issues: critical, sparse, good, zero, good, sparse
        }
        
        return pd.DataFrame(data)
    
    def test_initialization_default_config(self):
        """Test DataQualityChecker initialization with default config."""
        checker = DataQualityChecker()
        
        assert checker.config is not None
        assert 'speed_thresholds' in checker.config
        assert 'duration_thresholds' in checker.config
        assert 'observation_thresholds' in checker.config
        assert 'geometry_validation' in checker.config
    
    def test_initialization_custom_config(self):
        """Test DataQualityChecker initialization with custom config."""
        custom_config = {
            'speed_thresholds': {
                'min_valid_speed': 1.0,
                'max_valid_speed': 150.0
            }
        }
        
        checker = DataQualityChecker(custom_config)
        assert checker.config['speed_thresholds']['max_valid_speed'] == 150.0
    
    def test_comprehensive_quality_check_valid_data(self, quality_checker, sample_shapefile_data, sample_results_data):
        """Test comprehensive quality check with valid data."""
        quality_report = quality_checker.perform_comprehensive_quality_check(
            sample_shapefile_data, sample_results_data
        )
        
        # Check report structure
        assert 'timestamp' in quality_report
        assert 'data_summary' in quality_report
        assert 'speed_validation' in quality_report
        assert 'duration_validation' in quality_report
        assert 'observation_validation' in quality_report
        assert 'geometry_validation' in quality_report
        assert 'join_audit' in quality_report
        assert 'overall_quality' in quality_report
        
        # Check that valid data has good quality scores
        assert quality_report['speed_validation']['quality_score'] > 90
        assert quality_report['duration_validation']['quality_score'] > 90
        assert quality_report['observation_validation']['quality_score'] > 80
        assert quality_report['overall_quality']['overall_score'] > 80
    
    def test_comprehensive_quality_check_problematic_data(self, quality_checker, sample_shapefile_data, problematic_results_data):
        """Test comprehensive quality check with problematic data."""
        quality_report = quality_checker.perform_comprehensive_quality_check(
            sample_shapefile_data, problematic_results_data
        )
        
        # Check that problematic data has lower quality scores
        assert quality_report['speed_validation']['quality_score'] < 70
        assert quality_report['duration_validation']['quality_score'] < 70
        assert quality_report['observation_validation']['quality_score'] < 70
        assert quality_report['overall_quality']['overall_score'] < 70
        
        # Check that issues are detected
        assert len(quality_report['speed_validation']['issues']) > 0
        assert len(quality_report['duration_validation']['issues']) > 0
        assert len(quality_report['observation_validation']['issues']) > 0
    
    def test_speed_validation_valid_data(self, quality_checker, sample_results_data):
        """Test speed validation with valid data."""
        validation_result = quality_checker._validate_speeds(sample_results_data)
        
        assert validation_result['has_speed_data'] is True
        assert validation_result['quality_score'] > 90
        assert validation_result['quality_level'] == 'excellent'
        assert len(validation_result['issues']) == 0
        assert len(validation_result['flagged_records']) == 0
        
        # Check statistics
        stats = validation_result['statistics']
        assert stats['count'] == 5
        assert stats['null_count'] == 0
        assert stats['mean'] > 0
        assert stats['min'] > 0
        assert stats['max'] < 200
    
    def test_speed_validation_problematic_data(self, quality_checker, problematic_results_data):
        """Test speed validation with problematic data."""
        validation_result = quality_checker._validate_speeds(problematic_results_data)
        
        assert validation_result['has_speed_data'] is True
        assert validation_result['quality_score'] < 70
        assert validation_result['quality_level'] in ['poor', 'moderate']
        assert len(validation_result['issues']) > 0
        assert len(validation_result['flagged_records']) > 0
        
        # Check that specific issues are detected
        issues_text = ' '.join(validation_result['issues'])
        assert 'non-positive' in issues_text
        assert 'extreme' in issues_text
    
    def test_speed_validation_no_data(self, quality_checker):
        """Test speed validation with no speed data."""
        data = pd.DataFrame({'link_id': ['test'], 'other_col': [1]})
        validation_result = quality_checker._validate_speeds(data)
        
        assert validation_result['has_speed_data'] is False
        assert len(validation_result['issues']) == 1
        assert 'No speed data column found' in validation_result['issues'][0]
    
    def test_duration_validation_valid_data(self, quality_checker, sample_results_data):
        """Test duration validation with valid data."""
        validation_result = quality_checker._validate_durations(sample_results_data)
        
        assert validation_result['has_duration_data'] is True
        assert validation_result['quality_score'] > 90
        assert validation_result['quality_level'] == 'excellent'
        assert len(validation_result['issues']) == 0
        assert len(validation_result['flagged_records']) == 0
        
        # Check statistics
        stats = validation_result['statistics']
        assert stats['count'] == 5
        assert stats['null_count'] == 0
        assert stats['mean'] > 0
        assert stats['mean_minutes'] > 0
    
    def test_duration_validation_problematic_data(self, quality_checker, problematic_results_data):
        """Test duration validation with problematic data."""
        validation_result = quality_checker._validate_durations(problematic_results_data)
        
        assert validation_result['has_duration_data'] is True
        assert validation_result['quality_score'] < 70
        assert validation_result['quality_level'] in ['poor', 'moderate']
        assert len(validation_result['issues']) > 0
        assert len(validation_result['flagged_records']) > 0
        
        # Check that specific issues are detected
        issues_text = ' '.join(validation_result['issues'])
        assert 'non-positive' in issues_text
        assert 'extreme' in issues_text
    
    def test_observation_validation_valid_data(self, quality_checker, sample_results_data):
        """Test observation validation with valid data."""
        validation_result = quality_checker._validate_observations(sample_results_data)
        
        assert validation_result['has_observation_data'] is True
        assert validation_result['quality_score'] > 80
        assert validation_result['quality_level'] in ['excellent', 'good']
        
        # Check statistics
        stats = validation_result['statistics']
        assert stats['count'] == 5
        assert stats['total_observations'] > 0
        assert stats['mean'] > 0
    
    def test_observation_validation_problematic_data(self, quality_checker, problematic_results_data):
        """Test observation validation with problematic data."""
        validation_result = quality_checker._validate_observations(problematic_results_data)
        
        assert validation_result['has_observation_data'] is True
        assert validation_result['quality_score'] < 70
        assert len(validation_result['issues']) > 0
        assert len(validation_result['sparse_links']) > 0
        assert len(validation_result['critical_links']) > 0
    
    def test_geometry_validation_valid_data(self, quality_checker, sample_shapefile_data):
        """Test geometry validation with valid data."""
        validation_result = quality_checker._validate_geometries(sample_shapefile_data)
        
        assert validation_result['total_features'] == 5
        assert validation_result['quality_score'] > 90
        assert validation_result['quality_level'] == 'excellent'
        assert len(validation_result['issues']) == 0
        assert len(validation_result['invalid_geometries']) == 0
    
    def test_geometry_validation_invalid_data(self, quality_checker):
        """Test geometry validation with invalid geometries."""
        # Create invalid geometries
        invalid_geom = LineString([(0, 0), (0, 0)])  # Zero-length line
        null_geom = None
        
        data = {
            'Id': [1, 2, 3],
            'From': [100, 101, 102],
            'To': [101, 102, 103],
            'geometry': [invalid_geom, null_geom, LineString([(0, 0), (1, 1)])]
        }
        
        gdf = gpd.GeoDataFrame(data, crs='EPSG:4326')
        validation_result = quality_checker._validate_geometries(gdf)
        
        assert validation_result['quality_score'] < 90
        assert len(validation_result['issues']) > 0
    
    def test_join_audit_perfect_match(self, quality_checker, sample_shapefile_data, sample_results_data):
        """Test join audit with perfect data match."""
        audit_result = quality_checker._perform_join_audit(sample_shapefile_data, sample_results_data)
        
        assert 'shapefile_summary' in audit_result
        assert 'results_summary' in audit_result
        assert 'join_analysis' in audit_result
        
        join_analysis = audit_result['join_analysis']
        assert join_analysis['join_success_rate'] == 100.0
        assert join_analysis['missing_in_shapefile'] == 0
        assert join_analysis['missing_in_results'] == 0
    
    def test_join_audit_missing_data(self, quality_checker, sample_shapefile_data):
        """Test join audit with missing data."""
        # Create results with some missing and some extra links
        results_data = pd.DataFrame({
            'link_id': ['s_100-101', 's_101-102', 's_999-888'],  # Missing s_102-103, s_103-104, s_104-105, extra s_999-888
            'date': ['2025-01-01', '2025-01-01', '2025-01-01'],
            'hour': [8, 8, 8],
            'avg_speed_kmh': [45.5, 52.3, 30.0],
            'avg_duration_sec': [120, 95, 200],
            'n_valid': [25, 18, 10]
        })
        
        audit_result = quality_checker._perform_join_audit(sample_shapefile_data, results_data)
        
        join_analysis = audit_result['join_analysis']
        assert join_analysis['join_success_rate'] < 100.0
        assert join_analysis['missing_in_shapefile'] > 0  # s_999-888 not in shapefile
        assert join_analysis['missing_in_results'] > 0  # Some shapefile links not in results
        
        missing_data = audit_result['missing_data']
        assert 's_999-888' in missing_data['results_links_not_in_shapefile']
        assert len(missing_data['shapefile_links_not_in_results']) > 0
    
    def test_sparse_observation_filter(self, quality_checker, problematic_results_data):
        """Test sparse observation filtering functionality."""
        # Filter with default threshold
        filtered_data = quality_checker.get_sparse_observation_filter(problematic_results_data)
        
        # Should remove records with n_valid < 10 (default threshold)
        assert len(filtered_data) < len(problematic_results_data)
        assert all(filtered_data['n_valid'] >= 10)
        
        # Filter with custom threshold
        filtered_data_custom = quality_checker.get_sparse_observation_filter(problematic_results_data, min_observations=5)
        
        # Should remove records with n_valid < 5
        assert len(filtered_data_custom) < len(problematic_results_data)
        assert all(filtered_data_custom['n_valid'] >= 5)
        assert len(filtered_data_custom) > len(filtered_data)  # Less restrictive
    
    def test_sparse_observation_filter_no_data(self, quality_checker):
        """Test sparse observation filter with no observation data."""
        data = pd.DataFrame({'link_id': ['test'], 'other_col': [1]})
        filtered_data = quality_checker.get_sparse_observation_filter(data)
        
        # Should return original data unchanged
        assert len(filtered_data) == len(data)
        assert filtered_data.equals(data)
    
    def test_quality_flagged_records(self, quality_checker, problematic_results_data):
        """Test getting quality flagged records."""
        flagged_records = quality_checker.get_quality_flagged_records(problematic_results_data)
        
        # Check that different types of flagged records are identified
        assert 'non_positive_speeds' in flagged_records
        assert 'extreme_speeds' in flagged_records
        assert 'non_positive_durations' in flagged_records
        assert 'extreme_durations' in flagged_records
        assert 'sparse_observations' in flagged_records
        
        # Check that flagged records contain actual issues
        assert len(flagged_records['non_positive_speeds']) > 0
        assert len(flagged_records['extreme_speeds']) > 0
        assert len(flagged_records['non_positive_durations']) > 0
        assert len(flagged_records['extreme_durations']) > 0
        assert len(flagged_records['sparse_observations']) > 0
    
    def test_overall_quality_calculation(self, quality_checker, sample_shapefile_data, sample_results_data):
        """Test overall quality score calculation."""
        quality_report = quality_checker.perform_comprehensive_quality_check(
            sample_shapefile_data, sample_results_data
        )
        
        overall_quality = quality_report['overall_quality']
        
        assert 'overall_score' in overall_quality
        assert 'overall_level' in overall_quality
        assert 'summary' in overall_quality
        assert 'component_scores' in overall_quality
        
        # Check that overall score is reasonable
        assert 0 <= overall_quality['overall_score'] <= 100
        assert overall_quality['overall_level'] in ['excellent', 'good', 'moderate', 'poor', 'unknown']
        
        # Check component scores
        component_scores = overall_quality['component_scores']
        assert 'speed' in component_scores
        assert 'duration' in component_scores
        assert 'observations' in component_scores
        assert 'geometry' in component_scores


class TestQualityReportingInterface:
    """Test suite for QualityReportingInterface class."""
    
    @pytest.fixture
    def reporting_interface(self):
        """Create QualityReportingInterface instance."""
        return QualityReportingInterface()
    
    @pytest.fixture
    def sample_quality_report(self):
        """Create sample quality report for testing."""
        return {
            'timestamp': '2025-01-01T12:00:00',
            'data_summary': {
                'shapefile_features': 100,
                'results_records': 500,
                'unique_link_ids': 100
            },
            'speed_validation': {
                'has_speed_data': True,
                'quality_score': 85.0,
                'quality_level': 'good',
                'issues': ['Found 5 extremely high speeds (> 120 km/h)'],
                'statistics': {
                    'mean': 45.5,
                    'median': 42.0,
                    'std': 15.2,
                    'min': 5.0,
                    'max': 180.0,
                    'q25': 35.0,
                    'q75': 55.0
                }
            },
            'duration_validation': {
                'has_duration_data': True,
                'quality_score': 90.0,
                'quality_level': 'excellent',
                'issues': [],
                'statistics': {
                    'mean': 120.0,
                    'median': 110.0,
                    'mean_minutes': 2.0,
                    'median_minutes': 1.83
                }
            },
            'observation_validation': {
                'has_observation_data': True,
                'quality_score': 75.0,
                'quality_level': 'good',
                'issues': ['Found 20 links with sparse observations'],
                'sparse_links': ['s_100-101', 's_102-103'],
                'critical_links': ['s_999-888']
            },
            'geometry_validation': {
                'quality_score': 95.0,
                'quality_level': 'excellent',
                'issues': []
            },
            'join_audit': {
                'join_analysis': {
                    'shapefile_keys_count': 100,
                    'results_keys_count': 95,
                    'successful_matches': 90,
                    'join_success_rate': 90.0
                },
                'missing_data': {
                    'results_links_not_in_shapefile': ['s_999-888'],
                    'shapefile_links_not_in_results': ['s_105-106', 's_106-107']
                },
                'recommendations': ['Review missing links for data completeness']
            },
            'overall_quality': {
                'overall_score': 86.25,
                'overall_level': 'good',
                'summary': 'Data quality is good with minor issues',
                'component_scores': {
                    'speed': 85.0,
                    'duration': 90.0,
                    'observations': 75.0,
                    'geometry': 95.0
                }
            }
        }
    
    def test_quality_level_determination(self, reporting_interface):
        """Test quality level determination from scores."""
        assert reporting_interface._get_quality_level(95) == 'excellent'
        assert reporting_interface._get_quality_level(85) == 'good'
        assert reporting_interface._get_quality_level(65) == 'moderate'
        assert reporting_interface._get_quality_level(45) == 'poor'
    
    def test_issue_severity_determination(self, reporting_interface):
        """Test issue severity determination."""
        assert reporting_interface._get_issue_severity('Found 5 non-positive speed values') == 'Critical'
        assert reporting_interface._get_issue_severity('Found 10 extremely high speeds') == 'Warning'
        assert reporting_interface._get_issue_severity('Found 3 links with good coverage') == 'Info'
    
    def test_count_extraction_from_issue(self, reporting_interface):
        """Test count extraction from issue text."""
        assert reporting_interface._extract_count_from_issue('Found 15 non-positive speed values') == 15
        assert reporting_interface._extract_count_from_issue('Found 0 issues') == 0
        assert reporting_interface._extract_count_from_issue('No issues found') == 0
    
    def test_suggested_action_generation(self, reporting_interface):
        """Test suggested action generation."""
        action = reporting_interface._get_suggested_action('Found 5 non-positive speed values', 'Speed Quality')
        assert 'Review data collection' in action
        
        action = reporting_interface._get_suggested_action('Found 10 extremely high speeds', 'Speed Quality')
        assert 'Investigate outliers' in action
        
        action = reporting_interface._get_suggested_action('Found 20 sparse observations', 'Observation Quality')
        assert 'Increase observation frequency' in action
    
    def test_quality_warning_table_creation(self, reporting_interface, sample_quality_report):
        """Test quality warning table creation."""
        warning_table = reporting_interface.create_quality_warning_table(sample_quality_report)
        
        assert isinstance(warning_table, pd.DataFrame)
        assert len(warning_table) > 0
        
        # Check required columns
        required_columns = ['Category', 'Issue', 'Severity', 'Count', 'Action']
        for col in required_columns:
            assert col in warning_table.columns
        
        # Check that different categories are represented
        categories = warning_table['Category'].unique()
        assert len(categories) > 1
        
        # Check severity levels
        severities = warning_table['Severity'].unique()
        assert all(severity in ['Critical', 'Warning', 'Info'] for severity in severities)
    
    def test_quality_warning_table_empty_report(self, reporting_interface):
        """Test quality warning table with empty report."""
        empty_report = {
            'overall_quality': {'overall_score': 100, 'overall_level': 'excellent'},
            'speed_validation': {'issues': []},
            'duration_validation': {'issues': []},
            'observation_validation': {'issues': []},
            'geometry_validation': {'issues': []},
            'join_audit': {'missing_data': {}}
        }
        
        warning_table = reporting_interface.create_quality_warning_table(empty_report)
        
        assert isinstance(warning_table, pd.DataFrame)
        # Should have columns but no rows
        assert len(warning_table) == 0
        assert 'Category' in warning_table.columns
    
    def test_quality_filter_controls_structure(self, reporting_interface, sample_quality_report):
        """Test quality filter controls structure (without Streamlit rendering)."""
        # This test focuses on the logic rather than Streamlit rendering
        # We can test the data processing parts
        
        # Test filter settings logic
        obs_validation = sample_quality_report.get('observation_validation', {})
        has_obs_data = obs_validation.get('has_observation_data', False)
        
        assert has_obs_data is True
        
        sparse_links = obs_validation.get('sparse_links', [])
        critical_links = obs_validation.get('critical_links', [])
        
        assert len(sparse_links) > 0
        assert len(critical_links) > 0
    
    def test_quality_indicators_configuration(self, reporting_interface):
        """Test quality indicators configuration."""
        indicators = reporting_interface.quality_indicators
        
        # Check that all required quality levels are defined
        required_levels = ['excellent', 'good', 'moderate', 'poor']
        for level in required_levels:
            assert level in indicators
            assert 'color' in indicators[level]
            assert 'icon' in indicators[level]
            assert 'threshold' in indicators[level]
        
        # Check threshold ordering
        assert indicators['excellent']['threshold'] > indicators['good']['threshold']
        assert indicators['good']['threshold'] > indicators['moderate']['threshold']
        assert indicators['moderate']['threshold'] > indicators['poor']['threshold']


class TestDataQualityIntegration:
    """Integration tests for data quality system."""
    
    @pytest.fixture
    def quality_checker(self):
        """Create DataQualityChecker instance."""
        return DataQualityChecker()
    
    @pytest.fixture
    def reporting_interface(self):
        """Create QualityReportingInterface instance."""
        return QualityReportingInterface()
    
    def test_end_to_end_quality_workflow(self, quality_checker, reporting_interface):
        """Test complete end-to-end quality workflow."""
        # Create test data
        geometries = [LineString([(i, i), (i+1, i+1)]) for i in range(5)]
        shapefile_data = gpd.GeoDataFrame({
            'Id': range(1, 6),
            'From': range(100, 105),
            'To': range(101, 106),
            'geometry': geometries
        }, crs='EPSG:4326')
        
        results_data = pd.DataFrame({
            'link_id': [f's_{i}-{i+1}' for i in range(100, 105)],
            'date': ['2025-01-01'] * 5,
            'hour': [8] * 5,
            'avg_speed_kmh': [45.5, 52.3, 38.7, 61.2, 49.8],
            'avg_duration_sec': [120, 95, 180, 85, 110],
            'n_valid': [25, 18, 32, 15, 28]
        })
        
        # Perform quality check
        quality_report = quality_checker.perform_comprehensive_quality_check(
            shapefile_data, results_data
        )
        
        # Create warning table
        warning_table = reporting_interface.create_quality_warning_table(quality_report)
        
        # Verify integration
        assert quality_report is not None
        assert 'overall_quality' in quality_report
        assert isinstance(warning_table, pd.DataFrame)
        
        # Test sparse observation filtering
        filtered_data = quality_checker.get_sparse_observation_filter(results_data, min_observations=20)
        assert len(filtered_data) <= len(results_data)
        
        # Test flagged records
        flagged_records = quality_checker.get_quality_flagged_records(results_data)
        assert isinstance(flagged_records, dict)
    
    def test_quality_system_with_real_world_issues(self, quality_checker, reporting_interface):
        """Test quality system with realistic data quality issues."""
        # Create realistic problematic data
        geometries = [LineString([(i, i), (i+1, i+1)]) for i in range(10)]
        shapefile_data = gpd.GeoDataFrame({
            'Id': range(1, 11),
            'From': range(100, 110),
            'To': range(101, 111),
            'geometry': geometries
        }, crs='EPSG:4326')
        
        # Results with various realistic issues
        results_data = pd.DataFrame({
            'link_id': [f's_{i}-{i+1}' for i in range(100, 115)],  # 5 extra links not in shapefile
            'date': ['2025-01-01'] * 15,
            'hour': [8] * 15,
            'avg_speed_kmh': [
                -2.0, 0.0, 3.5, 15.0, 45.5,  # Issues: negative, zero, very low
                52.3, 38.7, 61.2, 49.8, 85.0,  # Normal speeds
                150.0, 220.0, np.nan, 45.0, 50.0  # Issues: high, extreme, null
            ],
            'avg_duration_sec': [
                -30, 0, 10, 45, 120,  # Issues: negative, zero, very short
                95, 180, 85, 110, 200,  # Normal durations
                3800, 7200, np.nan, 150, 180  # Issues: long, extreme, null
            ],
            'n_valid': [
                0, 1, 2, 3, 25,  # Issues: zero, critical, sparse
                18, 32, 15, 28, 45,  # Mixed quality
                8, 12, 5, 35, 50  # Mixed quality
            ]
        })
        
        # Perform comprehensive quality check
        quality_report = quality_checker.perform_comprehensive_quality_check(
            shapefile_data, results_data
        )
        
        # Verify that issues are detected
        assert quality_report['overall_quality']['overall_score'] < 80  # Should detect issues
        assert len(quality_report['speed_validation']['issues']) > 0
        assert len(quality_report['duration_validation']['issues']) > 0
        assert len(quality_report['observation_validation']['issues']) > 0
        assert quality_report['join_audit']['join_analysis']['missing_in_shapefile'] > 0
        
        # Create and verify warning table
        warning_table = reporting_interface.create_quality_warning_table(quality_report)
        assert len(warning_table) > 0
        assert 'Critical' in warning_table['Severity'].values
        assert 'Warning' in warning_table['Severity'].values
        
        # Test filtering capabilities
        filtered_data = quality_checker.get_sparse_observation_filter(results_data, min_observations=10)
        assert len(filtered_data) < len(results_data)
        
        flagged_records = quality_checker.get_quality_flagged_records(results_data)
        assert len(flagged_records['non_positive_speeds']) > 0
        assert len(flagged_records['extreme_speeds']) > 0
        assert len(flagged_records['sparse_observations']) > 0


if __name__ == '__main__':
    pytest.main([__file__])