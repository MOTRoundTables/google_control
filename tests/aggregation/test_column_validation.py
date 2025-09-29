#!/usr/bin/env python3
"""
Test column validation with the actual CSV file
"""

import pandas as pd
import sys
sys.path.append('.')

from components.aggregation.pipeline import validate_csv_columns, normalize_column_names, REQUIRED_COLUMNS, COLUMN_MAPPING

def test_column_validation():
    """Test column validation with data_test_small.csv"""
    
    # Read the test file
    df = pd.read_csv('test_data/data_test_small.csv', encoding='utf-8')
    
    print("=== CSV File Analysis ===")
    print(f"Loaded {len(df)} rows")
    print(f"Columns in CSV: {list(df.columns)}")
    print()
    
    print("=== Required Columns ===")
    print(f"Required: {REQUIRED_COLUMNS}")
    print()
    
    print("=== Column Mapping ===")
    for original, normalized in COLUMN_MAPPING.items():
        if original in df.columns:
            print(f"✅ {original} -> {normalized}")
        else:
            print(f"❌ {original} (not found)")
    print()
    
    print("=== Validation Test ===")
    is_valid, missing_columns = validate_csv_columns(df)
    
    if is_valid:
        print("✅ All required columns found!")
    else:
        print(f"❌ Missing columns: {missing_columns}")
    print()
    
    print("=== Column Normalization Test ===")
    try:
        df_normalized = normalize_column_names(df)
        print("✅ Column normalization successful!")
        print(f"Normalized columns: {list(df_normalized.columns)}")
    except Exception as e:
        print(f"❌ Column normalization failed: {e}")

if __name__ == "__main__":
    test_column_validation()