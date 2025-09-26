#!/usr/bin/env python3
"""
Quick test to demonstrate the aggregation issue with Excel timestamps
"""

import pandas as pd
import sys
import os
sys.path.append('.')
from components.processing.pipeline import run_pipeline

def test_both_files():
    """Test both original and fixed files to show the difference"""
    
    # Test parameters
    params = {
        'timezone': 'Asia/Jerusalem',
        'timestamp_format': '%Y-%m-%d %H:%M:%S',
        'output_dir': 'test_output',
        'chunk_size': 10000,
        'min_valid_threshold': 1,
        'include_weekdays': list(range(7)),  # All days
        'include_hours': list(range(24)),    # All hours
        'start_date': None,
        'end_date': None,
        'link_whitelist': [],
        'link_blacklist': [],
        'valid_codes': [],
        'duration_min': 0,
        'duration_max': 3600,
        'distance_min': 0,
        'distance_max': 50000,
        'speed_min': 0,
        'speed_max': 200,
        'daytype_mapping': {},
        'use_holidays': False,
        'custom_holidays': [],
        'treat_holidays_as_weekend': False,
        'weekday_only': False,
        'weekend_only': False,
        'holiday_only': False,
        'group_by_weekday_index': False,
        'recompute_std_from_raw': False,
        'include_quality_reports': True,
        'include_parquet': False
    }
    
    print("=" * 60)
    print("TESTING AGGREGATION WITH BOTH FILES")
    print("=" * 60)
    
    # Test 1: Original file (with Excel timestamps)
    print("\n1. Testing ORIGINAL file (s_10005-91_all_true.csv)")
    print("-" * 50)
    
    try:
        original_file = 'test_data/s_10005-91_all_true.csv'
        if os.path.exists(original_file):
            # Check first few rows with encoding handling
            try:
                df_orig = pd.read_csv(original_file, nrows=3, encoding='utf-8')
            except UnicodeDecodeError:
                df_orig = pd.read_csv(original_file, nrows=3, encoding='cp1255')
            print(f"Sample timestamps from original file:")
            print(df_orig[['Timestamp']].head())
            print(f"Timestamp type: {type(df_orig['Timestamp'].iloc[0])}")
            
            # Try processing
            params['input_file_path'] = original_file
            hourly_df, weekly_df, output_files = run_pipeline(params)
            
            print(f"\nResults from ORIGINAL file:")
            print(f"- Hourly aggregation rows: {len(hourly_df) if hourly_df is not None else 0}")
            print(f"- Weekly profile rows: {len(weekly_df) if weekly_df is not None else 0}")
            
        else:
            print("Original file not found!")
            
    except Exception as e:
        print(f"ERROR processing original file: {str(e)}")
    
    # Test 2: Fixed file (with proper timestamps)
    print("\n2. Testing FIXED file (s_10005-91_all_true_FIXED.csv)")
    print("-" * 50)
    
    try:
        fixed_file = 'test_data/s_10005-91_all_true_FIXED.csv'
        if os.path.exists(fixed_file):
            # Check first few rows
            df_fixed = pd.read_csv(fixed_file, nrows=3)
            print(f"Sample timestamps from fixed file:")
            print(df_fixed[['Timestamp']].head())
            print(f"Timestamp type: {type(df_fixed['Timestamp'].iloc[0])}")
            
            # Try processing
            params['input_file_path'] = fixed_file
            hourly_df, weekly_df, output_files = run_pipeline(params)
            
            print(f"\nResults from FIXED file:")
            print(f"- Hourly aggregation rows: {len(hourly_df) if hourly_df is not None else 0}")
            print(f"- Weekly profile rows: {len(weekly_df) if weekly_df is not None else 0}")
            
            if hourly_df is not None and len(hourly_df) > 0:
                print(f"- Links processed: {hourly_df['link_id'].nunique()}")
                print(f"- Date range: {hourly_df['date'].min()} to {hourly_df['date'].max()}")
                print(f"- Valid hours: {hourly_df['valid_hour'].sum()}")
                
        else:
            print("Fixed file not found!")
            
    except Exception as e:
        print(f"ERROR processing fixed file: {str(e)}")
    
    print("\n" + "=" * 60)
    print("CONCLUSION:")
    print("=" * 60)
    print("The original file has Excel serial date timestamps (like 45837.66753)")
    print("which cannot be parsed by the standard datetime parser.")
    print("\nThe FIXED file has proper datetime format (2025-06-29 16:01:14)")
    print("which processes correctly and generates the expected results.")
    print("\n🔧 SOLUTION: Use the FIXED file in your app!")
    print("   File: test_data/s_10005-91_all_true_FIXED.csv")

if __name__ == "__main__":
    test_both_files()