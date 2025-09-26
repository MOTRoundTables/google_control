#!/usr/bin/env python3
"""
Quick test to verify timestamp parsing with your data format
"""

import pandas as pd

def test_timestamp_formats():
    """Test different timestamp formats with your data"""
    
    # Sample timestamps from your data
    timestamps = ['01/07/2025 13:45', '01/07/2025 14:15', '29/06/2025 06:01']
    
    formats_to_try = [
        '%d/%m/%Y %H:%M',      # DD/MM/YYYY HH:MM (your format)
        '%Y-%m-%d %H:%M:%S',   # YYYY-MM-DD HH:MM:SS (default)
        '%m/%d/%Y %H:%M',      # MM/DD/YYYY HH:MM (US format)
    ]
    
    print("Testing timestamp formats:")
    for fmt in formats_to_try:
        print(f"\nFormat: {fmt}")
        try:
            parsed = pd.to_datetime(timestamps, format=fmt)
            print(f"✅ Success: {parsed.tolist()}")
        except Exception as e:
            print(f"❌ Failed: {e}")

if __name__ == "__main__":
    test_timestamp_formats()