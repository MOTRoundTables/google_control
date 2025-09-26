#!/usr/bin/env python3
"""
Test the actual app sorting by running the processing pipeline
"""

import pandas as pd
import sys
sys.path.append('.')

from components.processing.pipeline import run_pipeline

def test_app_sorting():
    """Test sorting with actual app data"""
    
    print("=== Testing App Sorting ===")
    
    # Run the actual processing pipeline
    config = {
        'input_file_path': 'test_data/data_test_small.csv',
        'output_dir': './test_output',
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
        
        # Apply the same sorting logic as in the app
        hourly_sorted = hourly_df.copy()
        
        # Ensure proper data types for sorting
        if 'date' in hourly_sorted.columns:
            if hourly_sorted['date'].dtype == 'object':
                try:
                    hourly_sorted['date'] = pd.to_datetime(hourly_sorted['date'])
                    print(f"✅ Converted date column to datetime")
                except:
                    print(f"❌ Failed to convert date column")
        
        if 'hour_of_day' in hourly_sorted.columns:
            hourly_sorted['hour_of_day'] = pd.to_numeric(hourly_sorted['hour_of_day'], errors='coerce')
            print(f"✅ Ensured hour_of_day is numeric")
        
        # Define sort columns
        sort_columns = []
        if 'link_id' in hourly_sorted.columns:
            sort_columns.append('link_id')
        if 'date' in hourly_sorted.columns:
            sort_columns.append('date')
        if 'hour_of_day' in hourly_sorted.columns:
            sort_columns.append('hour_of_day')
        
        print(f"Sorting by: {' → '.join(sort_columns)}")
        
        if sort_columns:
            hourly_sorted = hourly_sorted.sort_values(sort_columns, na_position='last')
            hourly_sorted = hourly_sorted.reset_index(drop=True)
        
        # Show the sorted results
        display_cols = ['link_id', 'date', 'hour_of_day', 'n_valid']
        available_cols = [col for col in display_cols if col in hourly_sorted.columns]
        
        print(f"\nSorted results (first 15 rows):")
        print(hourly_sorted[available_cols].head(15))
        
        # Verify sorting
        print(f"\n=== Sorting Verification ===")
        
        # Check if links are grouped
        unique_links = hourly_sorted['link_id'].unique()
        print(f"✅ Unique links: {list(unique_links)}")
        
        # Check if data is properly sorted within each link
        for link in unique_links[:2]:  # Check first 2 links
            link_data = hourly_sorted[hourly_sorted['link_id'] == link]
            dates = link_data['date'].tolist()
            
            # Check if dates are sorted
            dates_sorted = sorted(dates)
            if dates == dates_sorted:
                print(f"✅ Dates sorted correctly for {link}")
            else:
                print(f"❌ Dates NOT sorted for {link}")
                print(f"   Actual: {dates[:5]}")
                print(f"   Expected: {dates_sorted[:5]}")
        
        print(f"\n🎉 App sorting test completed!")
        
        return hourly_sorted
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = test_app_sorting()