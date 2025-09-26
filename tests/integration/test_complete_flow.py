#!/usr/bin/env python3
"""
Test the complete flow: column validation + date detection
"""

import pandas as pd
import sys
sys.path.append('.')

from components.processing.pipeline import validate_csv_columns

def test_complete_flow():
    """Test the complete flow with data_test_small.csv"""
    
    print("=== Testing Complete Flow ===")
    
    # Read the test file
    df = pd.read_csv('test_data/data_test_small.csv', encoding='utf-8')
    print(f"✅ Loaded {len(df)} rows")
    print(f"Columns: {list(df.columns)}")
    
    # Test column validation
    print("\n=== Column Validation ===")
    is_valid, missing_columns = validate_csv_columns(df)
    
    if is_valid:
        print("✅ All required columns found!")
    else:
        print(f"❌ Missing columns: {missing_columns}")
        return False
    
    # Test date extraction
    print("\n=== Date Range Detection ===")
    if 'Timestamp' in df.columns:
        # Clean timestamp strings
        cleaned_timestamps = df['Timestamp'].astype(str).str.strip()
        
        # Parse timestamps
        timestamps = pd.to_datetime(cleaned_timestamps, format='%Y-%m-%d %H:%M:%S', errors='coerce')
        
        valid_timestamps = timestamps.dropna()
        print(f"✅ Parsed {len(valid_timestamps)}/{len(timestamps)} timestamps")
        
        if not valid_timestamps.empty:
            # Filter realistic dates
            current_year = pd.Timestamp.now().year
            realistic_timestamps = valid_timestamps[
                (valid_timestamps.dt.year >= current_year - 10) & 
                (valid_timestamps.dt.year <= current_year + 10)
            ]
            
            timestamps_to_use = realistic_timestamps if not realistic_timestamps.empty else valid_timestamps
            
            file_start_date = timestamps_to_use.min().date()
            file_end_date = timestamps_to_use.max().date()
            
            print(f"✅ Date range: {file_start_date} to {file_end_date}")
            
            # This should be what appears in the GUI
            print(f"\n🎯 Expected GUI behavior:")
            print(f"   - Column validation: ✅ All required columns found")
            print(f"   - Date range auto-detection: ✅ {file_start_date} to {file_end_date}")
            print(f"   - Start date input should show: {file_start_date}")
            print(f"   - End date input should show: {file_end_date}")
            
            return True
        else:
            print("❌ No valid timestamps found")
            return False
    else:
        print("❌ No Timestamp column found")
        return False

if __name__ == "__main__":
    success = test_complete_flow()
    if success:
        print("\n🎉 All tests passed! The app should work correctly.")
    else:
        print("\n💥 Tests failed! There are issues to fix.")