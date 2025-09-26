#!/usr/bin/env python3
"""
Debug the aggregation issue with s_10005-91_all_true.csv
"""

import pandas as pd
import sys
sys.path.append('.')

from processing import run_pipeline

def debug_aggregation_issue():
    """Debug why the all-true file returns no results"""
    
    print("=== Debugging Aggregation Issue ===")
    
    # First, let's examine the file structure
    print("1. Examining file structure...")
    try:
        # Try different encodings
        encodings_to_try = ['utf-8', 'cp1255', 'latin1', 'utf-8-sig', 'cp1252']
        df = None
        
        for encoding in encodings_to_try:
            try:
                df = pd.read_csv('test_data/s_10005-91_all_true_FIXED.csv', encoding=encoding)
                print(f"✅ File loaded with encoding: {encoding}")
                break
            except Exception as e:
                print(f"❌ Failed with {encoding}: {e}")
                continue
        
        if df is None:
            print("❌ Could not read file with any encoding")
            return
        print(f"✅ File loaded: {len(df)} rows")
        print(f"Columns: {list(df.columns)}")
        
        # Check the data types and sample values
        print(f"\nSample data:")
        for col in ['Timestamp', 'RequestedTime', 'DayInWeek', 'is_valid']:
            if col in df.columns:
                print(f"  {col}: {df[col].dtype}")
                print(f"    Sample: {df[col].head(3).tolist()}")
        
        # Check if all records are valid
        if 'is_valid' in df.columns:
            valid_count = df['is_valid'].sum() if df['is_valid'].dtype == bool else (df['is_valid'] == 'TRUE').sum()
            print(f"\nValid records: {valid_count}/{len(df)} ({valid_count/len(df)*100:.1f}%)")
        
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return
    
    # Try to run the processing pipeline
    print(f"\n2. Running processing pipeline...")
    
    config = {
        'input_file_path': 'test_data/s_10005-91_all_true_FIXED.csv',
        'output_dir': './output/debug_outputs/debug_agg_output',
        'ts_format': '%Y-%m-%d %H:%M:%S',  # This might be the issue
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
        
        if len(hourly_df) == 0:
            print(f"\n❌ NO HOURLY DATA GENERATED!")
            print(f"This indicates a problem in the processing pipeline.")
        else:
            print(f"\n✅ Hourly data generated successfully")
            print(f"Sample hourly data:")
            display_cols = ['link_id', 'date', 'hour_of_day', 'n_total', 'n_valid']
            available_cols = [col for col in display_cols if col in hourly_df.columns]
            print(hourly_df[available_cols].head())
        
        if len(weekly_df) == 0:
            print(f"\n❌ NO WEEKLY DATA GENERATED!")
        else:
            print(f"\n✅ Weekly data generated successfully")
        
        # Check the processing log for clues
        if 'processing_log' in output_files:
            log_path = output_files['processing_log']
            try:
                with open(log_path, 'r') as f:
                    log_content = f.read()
                print(f"\n=== Processing Log ===")
                print(log_content[-1000:])  # Last 1000 characters
            except:
                print(f"Could not read processing log")
        
    except Exception as e:
        print(f"❌ Processing failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Let's try to identify the specific issue
        print(f"\n=== Diagnosing the Issue ===")
        
        # Check timestamp parsing
        print(f"3. Testing timestamp parsing...")
        sample_timestamps = df['Timestamp'].head(5)
        print(f"Sample timestamps: {sample_timestamps.tolist()}")
        
        # Try to parse with different formats
        formats_to_try = [
            '%Y-%m-%d %H:%M:%S',
            '%m/%d/%Y %H:%M:%S',
            '%d/%m/%Y %H:%M:%S'
        ]
        
        for fmt in formats_to_try:
            try:
                parsed = pd.to_datetime(sample_timestamps, format=fmt, errors='coerce')
                success_count = len(parsed) - parsed.isna().sum()
                print(f"  Format '{fmt}': {success_count}/5 successful")
            except Exception as e:
                print(f"  Format '{fmt}': Failed - {e}")
        
        # Try automatic parsing
        try:
            parsed_auto = pd.to_datetime(sample_timestamps, errors='coerce')
            success_count = len(parsed_auto) - parsed_auto.isna().sum()
            print(f"  Automatic parsing: {success_count}/5 successful")
            if success_count > 0:
                print(f"    Sample parsed: {parsed_auto.dropna().iloc[0]}")
        except Exception as e:
            print(f"  Automatic parsing failed: {e}")

if __name__ == "__main__":
    debug_aggregation_issue()