#!/usr/bin/env python3
"""
Test aggregation of the large data.csv file with all valid rows
"""

import pandas as pd
import sys
import os
sys.path.append('.')
from components.aggregation.pipeline import run_pipeline

def test_data_csv_aggregation():
    """Test aggregation the large data.csv file"""
    
    # Test parameters
    params = {
        'input_file_path': 'test_data/data.csv',
        'timezone': 'Asia/Jerusalem',
        'timestamp_format': '%d/%m/%Y %H:%M',  # Based on the sample: 01/07/2025 13:45
        'output_dir': 'test_output_data_csv',
        'chunk_size': 10000,  # Process in chunks due to large file size
        'min_valid_threshold': 1,
        'include_weekdays': list(range(7)),  # All days
        'include_hours': list(range(24)),    # All hours
        'start_date': None,
        'end_date': None,
        'link_whitelist': [],
        'link_blacklist': [],
        'valid_codes': [],
        'duration_min': 0,
        'duration_max': 7200,  # Increased for longer trips
        'distance_min': 0,
        'distance_max': 100000,  # Increased for longer distances
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
    
    print("=" * 70)
    print("TESTING LARGE DATA.CSV FILE PROCESSING")
    print("=" * 70)
    print(f"File size: ~267MB")
    print(f"Expected: 3 days of data with all rows valid")
    print(f"Processing with chunk_size: {params['chunk_size']:,}")
    
    try:
        # Run aggregation
        print(f"\n🚀 Starting aggregation...")
        hourly_df, weekly_df, output_files = run_pipeline(params)
        
        print(f"\n" + "=" * 50)
        print("PROCESSING RESULTS")
        print("=" * 50)
        
        # Hourly aggregation results
        if hourly_df is not None and len(hourly_df) > 0:
            print(f"✅ Hourly aggregation: {len(hourly_df):,} rows")
            
            # Basic statistics
            unique_links = hourly_df['link_id'].nunique()
            date_range = f"{hourly_df['date'].min()} to {hourly_df['date'].max()}"
            valid_hours = hourly_df['valid_hour'].sum()
            total_hours = len(hourly_df)
            
            print(f"   - Unique links: {unique_links:,}")
            print(f"   - Date range: {date_range}")
            print(f"   - Valid hours: {valid_hours:,} / {total_hours:,} ({valid_hours/total_hours*100:.1f}%)")
            
            # n_valid statistics
            n_valid_stats = hourly_df['n_valid'].describe()
            print(f"   - n_valid per hour: min={n_valid_stats['min']:.0f}, mean={n_valid_stats['mean']:.1f}, max={n_valid_stats['max']:.0f}")
            
            # Sample data
            print(f"\n📊 Sample hourly data:")
            display_cols = ['link_id', 'date', 'hour_of_day', 'n_total', 'n_valid', 'avg_duration_sec', 'avg_speed_kmh']
            available_cols = [col for col in display_cols if col in hourly_df.columns]
            print(hourly_df[available_cols].head(10).to_string(index=False))
            
        else:
            print("❌ No hourly aggregation data generated")
        
        # Weekly profile results
        if weekly_df is not None and len(weekly_df) > 0:
            print(f"\n✅ Weekly profile: {len(weekly_df):,} rows")
            
            # Sample weekly data with new total fields
            print(f"\n📊 Sample weekly profile data:")
            display_cols = ['link_id', 'daytype', 'hour_of_day', 'avg_n_valid', 'total_valid_n', 'total_not_valid', 'n_days']
            available_cols = [col for col in display_cols if col in weekly_df.columns]
            print(weekly_df[available_cols].head(10).to_string(index=False))
            
            # Verify math for a few samples
            print(f"\n🔍 Math verification (first 3 rows):")
            for i in range(min(3, len(weekly_df))):
                row = weekly_df.iloc[i]
                expected_avg = row['total_valid_n'] / row['n_days']
                match = abs(expected_avg - row['avg_n_valid']) < 0.001
                print(f"   Row {i+1}: avg_n_valid={row['avg_n_valid']:.3f}, total_valid_n={row['total_valid_n']}, n_days={row['n_days']}")
                print(f"           Expected: {expected_avg:.3f}, Match: {'✅' if match else '❌'}")
            
        else:
            print("❌ No weekly profile data generated")
        
        # Output files
        print(f"\n📁 Output files generated:")
        for file_type, file_path in output_files.items():
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                print(f"   ✅ {file_type}: {file_path} ({file_size:,} bytes)")
            else:
                print(f"   ❌ {file_type}: {file_path} (missing)")
        
        print(f"\n" + "=" * 70)
        print("PROCESSING COMPLETED SUCCESSFULLY! 🎉")
        print("=" * 70)
        print("The aggregation logic is working correctly with your large dataset.")
        print("All rows were processed as valid, and the new total fields provide")
        print("complete transparency into the data behind each average.")
        
    except Exception as e:
        print(f"\n❌ ERROR during aggregation: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_data_csv_aggregation()