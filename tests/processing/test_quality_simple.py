"""
Simple test script for quality reporting functions
"""

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


def create_sample_data():
    """Create sample data for testing"""
    raw_df = pd.DataFrame({
        'name': ['link_1', 'link_1', 'link_1', 'link_2', 'link_2', 'link_3'],
        'is_valid': [True, True, False, True, False, True],
        'date': [date(2024, 1, 1), date(2024, 1, 1), date(2024, 1, 1), 
                date(2024, 1, 2), date(2024, 1, 2), date(2024, 1, 3)],
        'hour_of_day': [8, 9, 10, 8, 9, 8],
        'duration': [120, 130, 999, 125, 888, 115]
    })
    
    hourly_df = pd.DataFrame({
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
    
    weekly_df = pd.DataFrame({
        'link_id': ['link_1', 'link_2', 'link_3'],
        'daytype': ['weekday', 'weekday', 'weekday'],
        'hour_of_day': [8, 8, 8],
        'avg_n_valid': [1.0, 0.5, 1.0],
        'avg_dur': [125.0, 125.0, 115.0],
        'n_days': [2, 1, 1]
    })
    
    validation_stats = {
        'method_used': 'numeric_range_rules',
        'total_rows': 6,
        'valid_rows': 4,
        'invalid_reasons': {
            'duration_out_of_range': 2,
            'speed_out_of_range': 1
        }
    }
    
    return raw_df, hourly_df, weekly_df, validation_stats


def test_quality_by_link_report():
    """Test quality by link report generation"""
    print("Testing quality by link report...")
    
    raw_df, hourly_df, _, _ = create_sample_data()
    quality_df = generate_quality_by_link_report(raw_df, hourly_df)
    
    print(f"Generated quality report with {len(quality_df)} links")
    print("Quality report columns:", list(quality_df.columns))
    print("Sample data:")
    print(quality_df.head())
    
    # Basic validation
    assert not quality_df.empty, "Quality report should not be empty"
    assert len(quality_df) == 3, "Should have 3 unique links"
    
    expected_columns = [
        'link_id', 'percent_valid', 'hours_with_data', 'hours_valid', 
        'hours_dropped', 'percent_valid_hours', 'days_covered'
    ]
    assert list(quality_df.columns) == expected_columns, f"Columns mismatch: {list(quality_df.columns)}"
    
    print("✓ Quality by link report test passed\n")


def test_invalid_reason_counts_report():
    """Test invalid reason counts report generation"""
    print("Testing invalid reason counts report...")
    
    _, _, _, validation_stats = create_sample_data()
    reason_counts_df = generate_invalid_reason_counts_report(validation_stats)
    
    print(f"Generated reason counts report with {len(reason_counts_df)} reasons")
    print("Reason counts columns:", list(reason_counts_df.columns))
    print("Sample data:")
    print(reason_counts_df.head())
    
    # Basic validation
    assert not reason_counts_df.empty, "Reason counts report should not be empty"
    assert len(reason_counts_df) == 2, "Should have 2 invalid reasons"
    assert list(reason_counts_df.columns) == ['invalid_reason', 'count'], "Columns mismatch"
    
    print("✓ Invalid reason counts report test passed\n")


def test_processing_log():
    """Test processing log generation"""
    print("Testing processing log generation...")
    
    raw_df, hourly_df, weekly_df, validation_stats = create_sample_data()
    start_time = datetime(2024, 1, 1, 10, 0, 0)
    end_time = datetime(2024, 1, 1, 10, 5, 30)
    
    log_content = generate_processing_log(
        raw_df, hourly_df, weekly_df, validation_stats, start_time, end_time
    )
    
    print("Generated processing log:")
    print("=" * 50)
    print(log_content[:500] + "..." if len(log_content) > 500 else log_content)
    print("=" * 50)
    
    # Basic validation
    assert isinstance(log_content, str), "Log content should be a string"
    assert len(log_content) > 0, "Log content should not be empty"
    assert "PROCESSING LOG" in log_content, "Should contain log header"
    assert "Processing duration: 330.0 seconds" in log_content, "Should contain duration"
    
    print("✓ Processing log test passed\n")


def test_run_configuration():
    """Test run configuration saving"""
    print("Testing run configuration saving...")
    
    params = {
        'chunk_size': 10000,
        'ts_format': '%Y-%m-%d %H:%M:%S',
        'tz': 'Asia/Jerusalem',
        'duration_range_sec': [0, 3600],
        'min_valid_per_hour': 5,
        'enable_holiday_classification': True
    }
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = save_run_configuration(params, temp_dir)
        
        print(f"Saved configuration to: {config_path}")
        
        # Basic validation
        assert config_path != "", "Config path should not be empty"
        assert Path(config_path).exists(), "Config file should exist"
        
        # Load and verify
        with open(config_path, 'r') as f:
            saved_config = json.load(f)
        
        print("Sample config content:")
        for key, value in list(saved_config.items())[:5]:
            print(f"  {key}: {value}")
        
        assert saved_config['chunk_size'] == 10000, "Chunk size should be preserved"
        assert '_metadata' in saved_config, "Should contain metadata"
    
    print("✓ Run configuration test passed\n")


def test_write_quality_reports():
    """Test writing quality reports to files"""
    print("Testing quality reports file writing...")
    
    raw_df, hourly_df, _, validation_stats = create_sample_data()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_files = write_quality_reports(
            raw_df, hourly_df, validation_stats, temp_dir
        )
        
        print(f"Generated output files: {list(output_files.keys())}")
        
        # Basic validation
        assert 'quality_by_link' in output_files, "Should generate quality_by_link file"
        assert 'invalid_reason_counts' in output_files, "Should generate invalid_reason_counts file"
        
        # Check files exist and have content
        for file_type, file_path in output_files.items():
            assert Path(file_path).exists(), f"File {file_path} should exist"
            df = pd.read_csv(file_path)
            assert not df.empty, f"File {file_path} should have content"
            print(f"  {file_type}: {len(df)} rows")
    
    print("✓ Quality reports file writing test passed\n")


def test_complete_logging_and_config():
    """Test complete logging and configuration writing"""
    print("Testing complete logging and configuration writing...")
    
    raw_df, hourly_df, weekly_df, validation_stats = create_sample_data()
    params = {
        'chunk_size': 10000,
        'ts_format': '%Y-%m-%d %H:%M:%S',
        'tz': 'Asia/Jerusalem'
    }
    
    start_time = datetime(2024, 1, 1, 10, 0, 0)
    end_time = datetime(2024, 1, 1, 10, 5, 30)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_files = write_processing_log_and_config(
            raw_df, hourly_df, weekly_df, validation_stats, 
            params, start_time, end_time, temp_dir
        )
        
        print(f"Generated output files: {list(output_files.keys())}")
        
        # Basic validation
        assert 'processing_log' in output_files, "Should generate processing log"
        assert 'run_config' in output_files, "Should generate run config"
        
        # Check files exist
        for file_type, file_path in output_files.items():
            assert Path(file_path).exists(), f"File {file_path} should exist"
            print(f"  {file_type}: {file_path}")
    
    print("✓ Complete logging and configuration test passed\n")


def main():
    """Run all tests"""
    print("Running quality reporting and logging tests...\n")
    
    try:
        test_quality_by_link_report()
        test_invalid_reason_counts_report()
        test_processing_log()
        test_run_configuration()
        test_write_quality_reports()
        test_complete_logging_and_config()
        
        print("🎉 All tests passed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()