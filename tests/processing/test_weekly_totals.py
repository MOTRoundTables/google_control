#!/usr/bin/env python3
"""
Test the new total_valid_n and total_not_valid fields in weekly profile
"""

import pandas as pd
import sys
import os
sys.path.append('.')
from components.processing.pipeline import run_pipeline

def test_weekly_totals():
    """Test the new total fields in weekly profile"""
    
    # Test parameters
    params = {
        'input_file_path': 'test_data/s_10005-91_all_true_FIXED.csv',
        'timezone': 'Asia/Jerusalem',
        'timestamp_format': '%d/%m/%Y %H:%M',
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
    print("TESTING NEW WEEKLY PROFILE TOTAL FIELDS")
    print("=" * 60)
    
    try:
        # Run processing
        hourly_df, weekly_df, output_files = run_pipeline(params)
        
        if weekly_df is not None and len(weekly_df) > 0:
            print(f"\n✅ Weekly profile generated: {len(weekly_df)} rows")
            
            # Show the new columns
            display_cols = ['link_id', 'daytype', 'hour_of_day', 'avg_n_valid', 'total_valid_n', 'total_not_valid', 'n_days']
            available_cols = [col for col in display_cols if col in weekly_df.columns]
            
            print(f"\nWeekly profile with new total fields:")
            print(weekly_df[available_cols].head(10))
            
            # Verify the math for a specific hour
            sample_hour = weekly_df.iloc[0]
            print(f"\n🔍 Math verification for hour {sample_hour['hour_of_day']}:")
            print(f"- avg_n_valid: {sample_hour['avg_n_valid']:.4f}")
            print(f"- total_valid_n: {sample_hour['total_valid_n']}")
            print(f"- total_not_valid: {sample_hour['total_not_valid']}")
            print(f"- n_days: {sample_hour['n_days']}")
            
            # Calculate expected average
            expected_avg = sample_hour['total_valid_n'] / sample_hour['n_days']
            print(f"- Expected avg (total_valid_n / n_days): {expected_avg:.4f}")
            print(f"- Match: {'✅' if abs(expected_avg - sample_hour['avg_n_valid']) < 0.001 else '❌'}")
            
            # Show total observations per day
            total_obs_per_day = (sample_hour['total_valid_n'] + sample_hour['total_not_valid']) / sample_hour['n_days']
            print(f"- Total observations per day: {total_obs_per_day:.1f}")
            
        else:
            print("❌ No weekly profile data generated")
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_weekly_totals()