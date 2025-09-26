#!/usr/bin/env python3
"""
Debug script to test timestamp parsing with actual data
"""

import pandas as pd
import numpy as np
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_timestamp_parsing():
    """Test timestamp parsing with actual data from data_test_small.csv"""
    
    # Read the CSV file - try different encodings
    print("Reading CSV file...")
    
    # Try different encodings
    encodings_to_try = ['utf-8', 'cp1255', 'latin-1', 'utf-8-sig']
    df = None
    
    for encoding in encodings_to_try:
        try:
            print(f"Trying encoding: {encoding}")
            df = pd.read_csv('test_data/data_test_small.csv', encoding=encoding)
            print(f"Success with encoding: {encoding}")
            break
        except Exception as e:
            print(f"Failed with {encoding}: {e}")
            continue
    
    if df is None:
        print("Could not read file with any encoding!")
        return
    
    print(f"Loaded {len(df)} rows")
    print(f"Columns: {list(df.columns)}")
    
    # Check the Timestamp column
    if 'Timestamp' in df.columns:
        print(f"\nTimestamp column found with {len(df['Timestamp'])} values")
        
        # Show first few timestamp values
        print("\nFirst 5 timestamp values:")
        for i, ts in enumerate(df['Timestamp'].head()):
            print(f"  {i}: '{ts}' (type: {type(ts)})")
        
        # Check for any null values
        null_count = df['Timestamp'].isnull().sum()
        print(f"\nNull timestamp values: {null_count}")
        
        # Try different parsing approaches
        print("\n=== Testing different parsing approaches ===")
        
        # Approach 1: Direct pandas to_datetime
        print("\n1. Testing pd.to_datetime with format '%Y-%m-%d %H:%M:%S':")
        try:
            parsed1 = pd.to_datetime(df['Timestamp'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
            success_count1 = len(parsed1) - parsed1.isna().sum()
            print(f"   Success: {success_count1}/{len(parsed1)} timestamps parsed")
            if success_count1 > 0:
                print(f"   Sample parsed: {parsed1.dropna().iloc[0]}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Approach 2: Without format specification
        print("\n2. Testing pd.to_datetime without format:")
        try:
            parsed2 = pd.to_datetime(df['Timestamp'], errors='coerce')
            success_count2 = len(parsed2) - parsed2.isna().sum()
            print(f"   Success: {success_count2}/{len(parsed2)} timestamps parsed")
            if success_count2 > 0:
                print(f"   Sample parsed: {parsed2.dropna().iloc[0]}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Approach 3: Clean strings first
        print("\n3. Testing with string cleaning:")
        try:
            # Clean the timestamp strings
            cleaned_timestamps = df['Timestamp'].astype(str).str.strip()
            parsed3 = pd.to_datetime(cleaned_timestamps, format='%Y-%m-%d %H:%M:%S', errors='coerce')
            success_count3 = len(parsed3) - parsed3.isna().sum()
            print(f"   Success: {success_count3}/{len(parsed3)} timestamps parsed")
            if success_count3 > 0:
                print(f"   Sample parsed: {parsed3.dropna().iloc[0]}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # Approach 4: Manual parsing of first few
        print("\n4. Testing manual parsing of first few values:")
        for i in range(min(5, len(df))):
            ts_str = str(df['Timestamp'].iloc[i])
            print(f"   Trying to parse: '{ts_str}'")
            try:
                dt = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
                print(f"     Success: {dt}")
            except Exception as e:
                print(f"     Failed: {e}")
                # Try to identify the issue
                print(f"     Length: {len(ts_str)}")
                print(f"     Repr: {repr(ts_str)}")
    
    else:
        print("No 'Timestamp' column found!")
        print(f"Available columns: {list(df.columns)}")

if __name__ == "__main__":
    test_timestamp_parsing()