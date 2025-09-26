#!/usr/bin/env python3
"""
Debug script to test file validation issues
"""

import pandas as pd
import sys
sys.path.append('.')
from processing import validate_csv_columns, REQUIRED_COLUMNS, detect_file_encoding

def test_file_validation():
    """Test file validation with the actual data.csv file"""
    
    file_path = 'test_data/data.csv'
    
    print("=== File Validation Debug ===")
    print(f"File path: {file_path}")
    
    # Test encoding detection
    try:
        detected_encoding = detect_file_encoding(file_path)
        print(f"Detected encoding: {detected_encoding}")
    except Exception as e:
        print(f"Encoding detection failed: {e}")
        detected_encoding = 'utf-8'
    
    # Test reading with detected encoding
    try:
        print(f"\nReading with encoding: {detected_encoding}")
        sample_df = pd.read_csv(file_path, nrows=1000, encoding=detected_encoding)
        print(f"Successfully read {len(sample_df)} rows")
        print(f"Columns: {list(sample_df.columns)}")
        
        # Test validation
        is_valid, missing_columns = validate_csv_columns(sample_df)
        print(f"\nValidation result: {is_valid}")
        if not is_valid:
            print(f"Missing columns: {missing_columns}")
        else:
            print("✅ All required columns found!")
            
        # Check for any data issues
        print(f"\nData sample:")
        print(sample_df.head(2))
        
        # Check timestamp column
        if 'Timestamp' in sample_df.columns:
            print(f"\nTimestamp samples:")
            print(sample_df['Timestamp'].head(5).tolist())
            
    except Exception as e:
        print(f"Error reading file: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_file_validation()