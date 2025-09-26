"""
Test suite for quality reporting and logging functions
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, date
import tempfile
import json
from pathlib import Path

from components.processing.pipeline import (
    generate_quality_by_link_report,
    generate_invalid_reason_counts_report,
    write_quality_reports,
    generate_processing_log,
    save_run_configuration,
    write_processing_log_and_config
)


@pytest.fixture
def sample_raw_data():
    """Create sample raw data for testing"""
    return pd.DataFrame({
        'name': ['link_1', 'link_1', 'link_1', 'link_2', 'link_2', 'link_3'],
        'is_valid': [True, True, False, True, False, True],
        'date': [date(2024, 1, 1), date(2024, 1, 1), date(2024, 1, 1), 
                date(2024, 1, 2), date(2024, 1, 2), date(2024, 1, 3)],
        'hour_of_day': [8, 9, 10, 8, 9, 8],
        'duration': [120, 130, 999, 125, 888, 115]
    })


@pytest.fixture
def sample_hourly_data():
    """Create sample hourly aggregation data for testing"""
    return pd.DataFrame({
        'link_id': ['link_1', 'link_1', 'link_1', 'link_2', 'link_2', 'link_3'],
        'date': [date(2024, 1, 1), date(2024, 1, 1), date(2024, 1, 1),
                date(2024, 1, 2), date(2024, 1, 2), date(2024, 1, 3)],
        'hour_of_day': [8, 9, 10, 8, 9, 8],
        'daytype': ['weekday', 'weekday', 'weekday', 'weekday', 'weekday', 'weekday'],
        'n_total': [1, 1, 1, 1, 1, 1],
        'n_valid': [1, 1, 0, 1, 0, 1],
        'valid_hour': [True, True, False, True, False, True],
        'avg_duration_sec': [120, 130, None, 125, None, 115]
    })


@pytest.fixture
def sample_weekly_data():
    """Create sample weekly profile data for testing"""
    return pd.DataFrame({
        'link_id': ['link_1', 'link_2', 'link_3'],
        'daytype': ['weekday', 'weekday', 'weekday'],
        'hour_of_day': [8, 8, 8],
        'avg_n_valid': [1.0, 0.5, 1.0],
        'avg_dur': [125.0, 125.0, 115.0],
        'n_days': [2, 1, 1]
    })


@pytest.fixture
def sample_validation_stats():
    """Create sample validation statistics for testing"""
    return {
        'method_used': 'numeric_range_rules',
        'total_rows': 6,
        'valid_rows': 4,
        'invalid_reasons': {
            'duration_out_of_range': 2,
            'speed_out_of_range': 1
        }
    }


def test_generate_quality_by_link_report(sample_raw_data, sample_hourly_data):
    """Test quality by link report generation"""
    quality_df = generate_quality_by_link_report(sample_raw_data, sample_hourly_data)
    
    assert not quality_df.empty
    assert len(quality_df) == 3  # 3 unique links
    assert list(quality_df.columns) == [
        'link_id', 'percent_valid', 'hours_with_data', 'hours_valid', 
        'hours_dropped', 'percent_valid_hours', 'days_covered'
    ]
    
    # Check specific values for link_1
    link_1_row = quality_df[quality_df['link_id'] == 'link_1'].iloc[0]
    assert link_1_row['percent_valid'] == 66.67  # 2 valid out of 3 total
    assert link_1_row['hours_with_data'] == 3
    assert link_1_row['hours_valid'] == 2
    assert link_1_row['hours_dropped'] == 1


def test_generate_invalid_reason_counts_report(sample_validation_stats):
    """Test invalid reason counts report generation"""
    reason_counts_df = generate_invalid_reason_counts_report(sample_validation_stats)
    
    assert not reason_counts_df.empty
    assert len(reason_counts_df) == 2  # 2 invalid reasons
    assert list(reason_counts_df.columns) == ['invalid_reason', 'count']
    
    # Check that results are sorted by count descending
    assert reason_counts_df.iloc[0]['count'] >= reason_counts_df.iloc[1]['count']
    
    # Check specific values
    duration_row = reason_counts_df[reason_counts_df['invalid_reason'] == 'duration_out_of_range'].iloc[0]
    assert duration_row['count'] == 2


def test_generate_invalid_reason_counts_report_empty():
    """Test invalid reason counts with no invalid reasons (boolean validity)"""
    validation_stats = {
        'method_used': 'boolean_valid_column',
        'total_rows': 100,
        'valid_rows': 95,
        'invalid_reasons': {}
    }
    
    reason_counts_df = generate_invalid_reason_counts_report(validation_stats)
    
    assert reason_counts_df.empty or len(reason_counts_df) == 0
    assert list(reason_counts_df.columns) == ['invalid_reason', 'count']


def test_generate_processing_log(sample_raw_data, sample_hourly_data, sample_weekly_data, sample_validation_stats):
    """Test processing log generation"""
    start_time = datetime(2024, 1, 1, 10, 0, 0)
    end_time = datetime(2024, 1, 1, 10, 5, 30)
    
    log_content = generate_processing_log(
        sample_raw_data, sample_hourly_data, sample_weekly_data,
        sample_validation_stats, start_time, end_time
    )
    
    assert isinstance(log_content, str)
    assert len(log_content) > 0
    
    # Check that key information is included
    assert "PROCESSING LOG" in log_content
    assert "Processing duration: 330.0 seconds" in log_content
    assert "Raw data rows processed: 6" in log_content
    assert "Hourly aggregation rows: 6" in log_content
    assert "Weekly profile rows: 3" in log_content
    assert "Valid rows: 4 / 6 (66.7%)" in log_content
    assert "Distinct links processed: 3" in log_content
    assert "duration_out_of_range: 2 rows" in log_content


def test_save_run_configuration():
    """Test run configuration saving"""
    params = {
        'chunk_size': 10000,
        'ts_format': '%Y-%m-%d %H:%M:%S',
        'tz': 'Asia/Jerusalem',
        'duration_range_sec': [0, 3600],
        'min_valid_per_hour': 5,
        'enable_holiday_classification': True,
        'output_dir': '/tmp/test'
    }
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = save_run_configuration(params, temp_dir)
        
        assert config_path != ""
        assert Path(config_path).exists()
        
        # Load and verify the saved configuration
        with open(config_path, 'r') as f:
            saved_config = json.load(f)
        
        assert saved_config['chunk_size'] == 10000
        assert saved_config['ts_format'] == '%Y-%m-%d %H:%M:%S'
        assert saved_config['tz'] == 'Asia/Jerusalem'
        assert saved_config['duration_range_sec'] == [0, 3600]
        assert '_metadata' in saved_config
        assert 'generated_at' in saved_config['_metadata']


def test_write_quality_reports(sample_raw_data, sample_hourly_data, sample_validation_stats):
    """Test writing quality reports to files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        output_files = write_quality_reports(
            sample_raw_data, sample_hourly_data, sample_validation_stats, temp_dir
        )
        
        assert 'quality_by_link' in output_files
        assert 'invalid_reason_counts' in output_files
        
        # Check that files exist and have content
        quality_path = Path(output_files['quality_by_link'])
        assert quality_path.exists()
        
        quality_df = pd.read_csv(quality_path)
        assert len(quality_df) == 3  # 3 links
        
        reason_counts_path = Path(output_files['invalid_reason_counts'])
        assert reason_counts_path.exists()
        
        reason_counts_df = pd.read_csv(reason_counts_path)
        assert len(reason_counts_df) == 2  # 2 invalid reasons


def test_write_processing_log_and_config(sample_raw_data, sample_hourly_data, sample_weekly_data, sample_validation_stats):
    """Test writing processing log and configuration files"""
    params = {
        'chunk_size': 10000,
        'ts_format': '%Y-%m-%d %H:%M:%S',
        'tz': 'Asia/Jerusalem'
    }
    
    start_time = datetime(2024, 1, 1, 10, 0, 0)
    end_time = datetime(2024, 1, 1, 10, 5, 30)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_files = write_processing_log_and_config(
            sample_raw_data, sample_hourly_data, sample_weekly_data,
            sample_validation_stats, params, start_time, end_time, temp_dir
        )
        
        assert 'processing_log' in output_files
        assert 'run_config' in output_files
        
        # Check processing log file
        log_path = Path(output_files['processing_log'])
        assert log_path.exists()
        
        with open(log_path, 'r') as f:
            log_content = f.read()
        
        assert "PROCESSING LOG" in log_content
        assert "Processing duration: 330.0 seconds" in log_content
        
        # Check config file
        config_path = Path(output_files['run_config'])
        assert config_path.exists()
        
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        assert config_data['chunk_size'] == 10000
        assert config_data['ts_format'] == '%Y-%m-%d %H:%M:%S'


def test_empty_dataframes():
    """Test functions with empty DataFrames"""
    empty_df = pd.DataFrame()
    validation_stats = {'method_used': 'test', 'total_rows': 0, 'valid_rows': 0, 'invalid_reasons': {}}
    
    # Test quality report with empty data
    quality_df = generate_quality_by_link_report(empty_df, empty_df)
    assert quality_df.empty
    
    # Test processing log with empty data
    start_time = datetime.now()
    end_time = datetime.now()
    log_content = generate_processing_log(empty_df, empty_df, empty_df, validation_stats, start_time, end_time)
    
    assert isinstance(log_content, str)
    assert "Raw data rows processed: 0" in log_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])