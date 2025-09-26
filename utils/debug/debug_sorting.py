#!/usr/bin/env python3
"""
Debug the sorting issue in results tables
"""

import pandas as pd
import sys
sys.path.append('.')

from processing import run_pipeline

def debug_sorting():
    """Debug sorting with actual data"""
    
    print("=== Debugging Sorting Issue ===")
    
    # Test with actual processing results
    config = {
        'input_file_path': 'test_data/data_test_small.csv',
        'output_dir': './output/debug_outputs/debug_output',
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
        print("Running processing pipeline...")
        hourly_df, weekly_df, output_files = run_pipeline(config)
        
        print(f"✅ Processing completed!")
        print(f"Hourly data: {len(hourly_df)} rows")
        print(f"Weekly data: {len(weekly_df)} rows")
        
        # Debug hourly data sorting
        print(f"\n=== Hourly Data Sorting Debug ===")
        print(f"Columns: {list(hourly_df.columns)}")
        
        # Check data types
        print(f"\nData types:")
        for col in ['link_id', 'date', 'hour_of_day']:
            if col in hourly_df.columns:
                print(f"  {col}: {hourly_df[col].dtype}")
                print(f"    Sample values: {hourly_df[col].head(3).tolist()}")
        
        # Test sorting
        print(f"\nBefore sorting (first 10 rows):")
        display_cols = ['link_id', 'date', 'hour_of_day']
        available_cols = [col for col in display_cols if col in hourly_df.columns]
        print(hourly_df[available_cols].head(10))
        
        # Apply sorting
        sort_columns = []
        if 'link_id' in hourly_df.columns:
            sort_columns.append('link_id')
        if 'date' in hourly_df.columns:
            sort_columns.append('date')
        if 'hour_of_day' in hourly_df.columns:
            sort_columns.append('hour_of_day')
        
        print(f"\nSorting by: {sort_columns}")
        
        if sort_columns:
            hourly_sorted = hourly_df.sort_values(sort_columns)
            print(f"\nAfter sorting (first 10 rows):")
            print(hourly_sorted[available_cols].head(10))
            
            print(f"\nAfter sorting (last 10 rows):")
            print(hourly_sorted[available_cols].tail(10))
        
        # Check if date column needs conversion
        if 'date' in hourly_df.columns:
            print(f"\nDate column analysis:")
            print(f"  Type: {hourly_df['date'].dtype}")
            print(f"  Sample: {hourly_df['date'].iloc[0]} (type: {type(hourly_df['date'].iloc[0])})")
            
            # Try converting to datetime for proper sorting
            if hourly_df['date'].dtype == 'object':
                print(f"  Converting date column to datetime...")
                hourly_df_fixed = hourly_df.copy()
                hourly_df_fixed['date'] = pd.to_datetime(hourly_df_fixed['date'])
                hourly_sorted_fixed = hourly_df_fixed.sort_values(sort_columns)
                print(f"  After date conversion and sorting:")
                print(hourly_sorted_fixed[available_cols].head(10))
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_sorting()