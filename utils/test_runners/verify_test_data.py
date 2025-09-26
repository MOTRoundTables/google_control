#!/usr/bin/env python3
"""
Script to verify and fix the test data formatting
"""

import pandas as pd
import sys

def verify_and_fix_data(csv_file):
    print(f"Verifying {csv_file}...")
    
    # Read the data
    df = pd.read_csv(csv_file, encoding='utf-8')
    
    print(f"Total records: {len(df)}")
    print(f"is_valid column type: {df['is_valid'].dtype}")
    print(f"Unique values: {df['is_valid'].unique()}")
    
    # Fix boolean values to strings
    if df['is_valid'].dtype == 'bool':
        print("Converting boolean values to strings...")
        df['is_valid'] = df['is_valid'].map({True: 'TRUE', False: 'FALSE'})
        
        # Save back
        df.to_csv(csv_file, index=False, encoding='utf-8')
        print(f"Fixed and saved {csv_file}")
    
    # Final verification
    df_check = pd.read_csv(csv_file, encoding='utf-8', dtype={'is_valid': str})
    true_count = (df_check['is_valid'] == 'TRUE').sum()
    false_count = (df_check['is_valid'] == 'FALSE').sum()
    
    print(f"Final counts - TRUE: {true_count}, FALSE: {false_count}")
    print(f"Hebrew characters preserved: {'יום' in str(df_check['DayInWeek'].iloc[0])}")
    
    return df_check

if __name__ == "__main__":
    files = ['test_data/data_test_small.csv', 'test_data/data.csv', 'test_data/data_test.csv']
    
    for file in files:
        try:
            verify_and_fix_data(file)
            print("-" * 50)
        except Exception as e:
            print(f"Error processing {file}: {e}")