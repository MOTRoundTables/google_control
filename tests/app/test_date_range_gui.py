#!/usr/bin/env python3
"""
Test script to verify date range auto-detection functionality
"""

import pandas as pd
import sys
sys.path.append('.')

def test_date_extraction():
    """Test date extraction from data_test_small.csv"""
    
    # Read the test file
    df = pd.read_csv('test_data/data_test_small.csv', encoding='utf-8')
    
    print(f"Loaded {len(df)} rows from test file")
    print(f"Columns: {list(df.columns)}")
    
    if 'Timestamp' in df.columns:
        # Clean timestamp strings
        cleaned_timestamps = df['Timestamp'].astype(str).str.strip()
        
        print(f"\nFirst 5 timestamps:")
        for i, ts in enumerate(cleaned_timestamps.head()):
            print(f"  {i}: '{ts}'")
        
        # Parse timestamps
        timestamps = pd.to_datetime(cleaned_timestamps, format='%Y-%m-%d %H:%M:%S', errors='coerce')
        
        valid_timestamps = timestamps.dropna()
        print(f"\nParsed {len(valid_timestamps)}/{len(timestamps)} timestamps successfully")
        
        if not valid_timestamps.empty:
            # Filter out unrealistic dates (like the app does)
            current_year = pd.Timestamp.now().year
            realistic_timestamps = valid_timestamps[
                (valid_timestamps.dt.year >= current_year - 10) & 
                (valid_timestamps.dt.year <= current_year + 10)
            ]
            
            # Use realistic timestamps if available, otherwise use all valid timestamps
            timestamps_to_use = realistic_timestamps if not realistic_timestamps.empty else valid_timestamps
            
            print(f"\nFiltering results:")
            print(f"  Total valid timestamps: {len(valid_timestamps)}")
            print(f"  Realistic timestamps (±10 years): {len(realistic_timestamps)}")
            print(f"  Using: {'realistic' if not realistic_timestamps.empty else 'all valid'}")
            
            file_start_date = timestamps_to_use.min().date()
            file_end_date = timestamps_to_use.max().date()
            
            print(f"\nDate range detected:")
            print(f"  Start date: {file_start_date}")
            print(f"  End date: {file_end_date}")
            
            # This is what should be set in the GUI
            print(f"\nGUI should show:")
            print(f"  📅 Auto-detected date range: {file_start_date} to {file_end_date}")
            print(f"  Start date input should default to: {file_start_date}")
            print(f"  End date input should default to: {file_end_date}")
            
            return file_start_date, file_end_date
        else:
            print("No valid timestamps found!")
            return None, None
    else:
        print("No Timestamp column found!")
        return None, None

if __name__ == "__main__":
    test_date_extraction()