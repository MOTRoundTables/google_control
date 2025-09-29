#!/usr/bin/env python3
"""
Integration test for quality reporting with existing aggregation functions
"""

import pandas as pd
import tempfile
import os
from datetime import datetime, date
from components.aggregation.pipeline import (
    validate_and_normalize_columns,
    apply_data_validation_and_cleaning,
    apply_temporal_enhancements,
    create_hourly_aggregation,
    write_quality_reports,
    write_aggregation_log_and_config
)

def create_test_data():
    """Create test data that mimics real CSV aggregation"""
    # Create raw CSV-like data
    raw_data = {
        'DataID': ['ID001', 'ID002', 'ID003', 'ID004', 'ID005', 'ID006'],
        'Name': ['Link_A', 'Link_A', 'Link_B', 'Link_B', 'Link_C', 'Link_C'],
        'SegmentID': ['SEG1', 'SEG1', 'SEG2', 'SEG2', 'SEG3', 'SEG3'],
        'RouteAlternative': ['Route1', 'Route1', 'Route2', 'Route2', 'Route3', 'Route3'],
        'RequestedTime': ['2024-01-01 08:00:00', '2024-01-01 09:00:00', '2024-01-01 08:00:00', 
                         '2024-01-01 09:00:00', '2024-01-01 08:00:00', '2024-01-01 09:00:00'],
        'Timestamp': ['2024-01-01 08:05:00', '2024-01-01 09:05:00', '2024-01-01 08:05:00',
                     '2024-01-01 09:05:00', '2024-01-01 08:05:00', '2024-01-01 09:05:00'],
        'DayInWeek': ['יום ב', 'יום ב', 'יום ב', 'יום ב', 'יום ב', 'יום ב'],
        'DayType': ['יום חול', 'יום חול', 'יום חול', 'יום חול', 'יום חול', 'יום חול'],
        'Duration': [300, 320, 999, 310, 305, 315],  # One invalid duration (999)
        'Distance': [2000, 2100, 2050, 2200, 2150, 2250],
        'Speed': [24, 23.5, 7.4, 25.4, 25.1, 25.7],  # One invalid speed (7.4)
        'Url': ['http://example.com/1', 'http://example.com/2', 'http://example.com/3',
               'http://example.com/4', 'http://example.com/5', 'http://example.com/6'],
        'Polyline': ['poly1', 'poly2', 'poly3', 'poly4', 'poly5', 'poly6']
    }
    
    return pd.DataFrame(raw_data)

def test_quality_reporting_integration():
    """Test quality reporting integration with aggregation pipeline"""
    print("Testing quality reporting integration with aggregation pipeline...")
    
    # Create test data
    raw_df = create_test_data()
    print(f"Created test data with {len(raw_df)} rows")
    
    # Processing parameters
    params = {
        'ts_format': '%Y-%m-%d %H:%M:%S',
        'tz': 'Asia/Jerusalem',
        'duration_range_sec': [0, 600],  # Will make 999 invalid
        'distance_range_m': [0, 5000],
        'speed_range_kmh': [10, 50],  # Will make 7.4 invalid
        'min_valid_per_hour': 1,
        'remove_data_id_duplicates': True,
        'remove_link_timestamp_duplicates': True
    }
    
    try:
        # Step 1: Validate and normalize columns
        print("Step 1: Validating and normalizing columns...")
        df_normalized = validate_and_normalize_columns(raw_df)
        print(f"Normalized columns: {list(df_normalized.columns)}")
        
        # Step 2: Apply data validation and cleaning
        print("Step 2: Applying data validation and cleaning...")
        df_cleaned, aggregation_stats = apply_data_validation_and_cleaning(df_normalized, params)
        print(f"Cleaned data: {len(df_cleaned)} rows")
        print(f"Validation stats: {aggregation_stats['validation_stats']}")
        
        # Step 3: Apply temporal enhancements
        print("Step 3: Applying temporal enhancements...")
        df_enhanced = apply_temporal_enhancements(df_cleaned, params)
        print(f"Enhanced data columns: {list(df_enhanced.columns)}")
        
        # Step 4: Create hourly aggregation
        print("Step 4: Creating hourly aggregation...")
        hourly_df = create_hourly_aggregation(df_enhanced, params)
        print(f"Hourly aggregation: {len(hourly_df)} rows")
        print("Hourly columns:", list(hourly_df.columns))
        
        # Step 5: Test quality reporting
        print("Step 5: Testing quality reporting...")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Write quality reports
            quality_files = write_quality_reports(
                df_enhanced, hourly_df, aggregation_stats['validation_stats'], temp_dir
            )
            print(f"Generated quality files: {list(quality_files.keys())}")
            
            # Write aggregation log and config
            start_time = datetime(2024, 1, 1, 10, 0, 0)
            end_time = datetime(2024, 1, 1, 10, 1, 30)
            
            log_files = write_aggregation_log_and_config(
                df_enhanced, hourly_df, pd.DataFrame(),  # Empty weekly for now
                aggregation_stats['validation_stats'], params, 
                start_time, end_time, temp_dir
            )
            print(f"Generated log files: {list(log_files.keys())}")
            
            # Verify files exist and have content
            all_files = {**quality_files, **log_files}
            for file_type, file_path in all_files.items():
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    print(f"  {file_type}: {file_path} ({file_size} bytes)")
                    
                    # Quick content check
                    if file_type == 'quality_by_link':
                        quality_df = pd.read_csv(file_path)
                        print(f"    Quality report has {len(quality_df)} links")
                        
                    elif file_type == 'invalid_reason_counts':
                        reasons_df = pd.read_csv(file_path)
                        print(f"    Invalid reasons report has {len(reasons_df)} reasons")
                        
                    elif file_type == 'aggregation_log':
                        with open(file_path, 'r') as f:
                            log_content = f.read()
                        print(f"    Processing log has {len(log_content)} characters")
                        
                    elif file_type == 'run_config':
                        import json
                        with open(file_path, 'r') as f:
                            config = json.load(f)
                        print(f"    Run config has {len(config)} parameters")
                else:
                    print(f"  {file_type}: FILE NOT FOUND - {file_path}")
        
        print("✓ Quality reporting integration test passed")
        
    except Exception as e:
        print(f"❌ Quality reporting integration test failed: {e}")
        import traceback
        traceback.print_exc()
        raise

def test_quality_metrics_accuracy():
    """Test that quality metrics are calculated accurately"""
    print("Testing quality metrics accuracy...")
    
    # Create specific test data with known quality issues
    test_data = pd.DataFrame({
        'name': ['Link_X'] * 10,  # Single link for easy verification
        'is_valid': [True, True, False, False, True, True, False, True, True, False],  # 6 valid, 4 invalid
        'date': [date(2024, 1, 1)] * 5 + [date(2024, 1, 2)] * 5,  # 2 days
        'hour_of_day': [8, 9, 10, 11, 12] * 2,  # 5 hours per day
        'duration': [300, 320, 999, 888, 310, 305, 777, 315, 325, 666]
    })
    
    # Create corresponding hourly data
    hourly_data = pd.DataFrame({
        'link_id': ['Link_X'] * 10,
        'date': [date(2024, 1, 1)] * 5 + [date(2024, 1, 2)] * 5,
        'hour_of_day': [8, 9, 10, 11, 12] * 2,
        'daytype': ['weekday'] * 10,
        'n_total': [1] * 10,
        'n_valid': [1, 1, 0, 0, 1, 1, 0, 1, 1, 0],  # Matches is_valid
        'valid_hour': [True, True, False, False, True, True, False, True, True, False],
        'avg_duration_sec': [300, 320, None, None, 310, 305, None, 315, 325, None]
    })
    
    # Import the quality function
    from components.aggregation.pipeline import generate_quality_by_link_report
    
    quality_df = generate_quality_by_link_report(test_data, hourly_data)
    
    # Verify calculations
    link_x_metrics = quality_df[quality_df['link_id'] == 'Link_X'].iloc[0]
    
    expected_percent_valid = 60.0  # 6 valid out of 10 total
    expected_hours_with_data = 10
    expected_hours_valid = 6
    expected_hours_dropped = 4
    expected_percent_valid_hours = 60.0  # 6 valid hours out of 10 total
    expected_days_covered = 2
    
    assert abs(link_x_metrics['percent_valid'] - expected_percent_valid) < 0.1, \
        f"Expected {expected_percent_valid}%, got {link_x_metrics['percent_valid']}%"
    
    assert link_x_metrics['hours_with_data'] == expected_hours_with_data, \
        f"Expected {expected_hours_with_data} hours, got {link_x_metrics['hours_with_data']}"
    
    assert link_x_metrics['hours_valid'] == expected_hours_valid, \
        f"Expected {expected_hours_valid} valid hours, got {link_x_metrics['hours_valid']}"
    
    assert link_x_metrics['hours_dropped'] == expected_hours_dropped, \
        f"Expected {expected_hours_dropped} dropped hours, got {link_x_metrics['hours_dropped']}"
    
    assert abs(link_x_metrics['percent_valid_hours'] - expected_percent_valid_hours) < 0.1, \
        f"Expected {expected_percent_valid_hours}% valid hours, got {link_x_metrics['percent_valid_hours']}%"
    
    assert link_x_metrics['days_covered'] == expected_days_covered, \
        f"Expected {expected_days_covered} days, got {link_x_metrics['days_covered']}"
    
    print("✓ Quality metrics accuracy test passed")

def main():
    """Run integration tests"""
    print("Running quality reporting integration tests...\n")
    
    try:
        test_quality_reporting_integration()
        print()
        
        test_quality_metrics_accuracy()
        print()
        
        print("🎉 All quality reporting integration tests passed!")
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()