#!/usr/bin/env python3
"""
Test the fixed file with the aggregation pipeline
"""

import pandas as pd
import sys
sys.path.append('.')

from components.aggregation.pipeline import run_pipeline

def test_fixed_file():
    """Test the fixed file"""
    
    print("=== Testing Fixed File ===")
    
    config = {
        'input_file_path': 'test_data/s_10005-91_all_true_FIXED.csv',
        'output_dir': './test_fixed_output',
        'ts_format': '%Y-%m-%d %H:%M:%S',
        'tz': 'Asia/Jerusalem',
        'chunk_size': 50000,
        'weekdays': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
        'hours': list(range(24)),
        'min_valid_per_hour': 1,
        'start_date': None,
        'end_date': None,
        'link_whitelist': [],
        'link_blacklist': []
    }
    
    try:
        hourly_df, weekly_df, output_files = run_pipeline(config)
        
        print(f"✅ Processing completed!")
        print(f"Hourly data: {len(hourly_df)} rows")
        print(f"Weekly data: {len(weekly_df)} rows")
        
        if len(hourly_df) > 0:
            print(f"\n✅ SUCCESS! Hourly data generated")
            display_cols = ['link_id', 'date', 'hour_of_day', 'n_total', 'n_valid', 'avg_duration_sec']
            available_cols = [col for col in display_cols if col in hourly_df.columns]
            print(f"Sample hourly data:")
            print(hourly_df[available_cols].head(10))
        else:
            print(f"\n❌ Still no hourly data generated")
        
        if len(weekly_df) > 0:
            print(f"\n✅ SUCCESS! Weekly data generated")
            display_cols = ['link_id', 'daytype', 'hour_of_day', 'avg_n_valid', 'avg_dur']
            available_cols = [col for col in display_cols if col in weekly_df.columns]
            print(f"Sample weekly data:")
            print(weekly_df[available_cols].head(10))
        else:
            print(f"\n❌ Still no weekly data generated")
        
    except Exception as e:
        print(f"❌ Processing failed: {e}")

if __name__ == "__main__":
    test_fixed_file()