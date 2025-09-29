#!/usr/bin/env python3
"""
Test the enhanced timestamp parsing with your data format
"""

import pandas as pd
import sys
sys.path.append('.')

def test_enhanced_parsing():
    """Test the enhanced timestamp parsing logic"""
    
    # Sample timestamps from your data
    test_data = {
        'Timestamp': ['01/07/2025 13:45', '01/07/2025 14:15', '29/06/2025 06:01', '29/06/2025 01:31']
    }
    df = pd.DataFrame(test_data)
    
    print("=== Testing Enhanced Timestamp Parsing ===")
    print(f"Sample timestamps: {df['Timestamp'].tolist()}")
    
    # Test the enhanced format detection logic
    cleaned_timestamps = df['Timestamp'].astype(str).str.strip()
    
    timestamp_formats = [
        '%Y-%m-%d %H:%M:%S',  # Default format (should fail)
        '%d/%m/%Y %H:%M',  # European format DD/MM/YYYY HH:MM (should work)
        '%d/%m/%Y %H:%M:%S',  # European format DD/MM/YYYY HH:MM:SS
        '%m/%d/%Y %H:%M',  # US format MM/DD/YYYY HH:MM
    ]
    
    for fmt in timestamp_formats:
        try:
            test_parsed = pd.to_datetime(cleaned_timestamps, format=fmt, errors='coerce')
            test_failed_count = test_parsed.isna().sum()
            success_rate = (len(cleaned_timestamps) - test_failed_count) / len(cleaned_timestamps)
            
            print(f"\nFormat: {fmt}")
            print(f"Success rate: {success_rate:.1%}")
            if success_rate > 0:
                print(f"Parsed results: {test_parsed.tolist()}")
            
            if success_rate > 0.5:
                print(f"✅ This format would be selected!")
                break
        except Exception as e:
            print(f"Format {fmt} failed: {e}")

if __name__ == "__main__":
    test_enhanced_parsing()