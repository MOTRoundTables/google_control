#!/usr/bin/env python3
"""
Fix Excel serial date timestamps in the CSV file
"""

import pandas as pd
from datetime import datetime, timedelta

def convert_excel_serial_to_datetime(serial_date):
    """Convert Excel serial date to datetime"""
    try:
        # Excel serial date starts from 1900-01-01 (but Excel incorrectly treats 1900 as a leap year)
        # So we need to subtract 2 days to get the correct date
        base_date = datetime(1899, 12, 30)  # Excel's epoch adjusted for the leap year bug
        return base_date + timedelta(days=serial_date)
    except:
        return None

def fix_excel_timestamps():
    """Fix the Excel timestamps in the CSV file"""
    
    print("=== Fixing Excel Timestamps ===")
    
    # Read the file with correct encoding
    df = pd.read_csv('test_data/s_10005-91_all_true.csv', encoding='cp1255')
    print(f"Loaded {len(df)} rows")
    
    # Check current timestamp format
    print(f"Current timestamp samples: {df['Timestamp'].head(3).tolist()}")
    print(f"Current timestamp type: {df['Timestamp'].dtype}")
    
    # Convert Excel serial dates to proper datetime format
    print(f"\nConverting Excel serial dates...")
    
    df['Timestamp_Fixed'] = df['Timestamp'].apply(convert_excel_serial_to_datetime)
    
    # Format as string in the expected format
    df['Timestamp_String'] = df['Timestamp_Fixed'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    print(f"Converted timestamp samples: {df['Timestamp_String'].head(3).tolist()}")
    
    # Replace the original Timestamp column
    df['Timestamp'] = df['Timestamp_String']
    df = df.drop(['Timestamp_Fixed', 'Timestamp_String'], axis=1)
    
    # Also fix RequestedTime if needed (convert decimal hours to HH:MM:SS)
    print(f"\nFixing RequestedTime...")
    print(f"Current RequestedTime samples: {df['RequestedTime'].head(3).tolist()}")
    
    def decimal_to_time(decimal_time):
        """Convert decimal time (like 0.666666667) to HH:MM:SS"""
        try:
            hours = int(decimal_time * 24)
            minutes = int((decimal_time * 24 * 60) % 60)
            seconds = int((decimal_time * 24 * 3600) % 60)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        except:
            return "00:00:00"
    
    df['RequestedTime'] = df['RequestedTime'].apply(decimal_to_time)
    print(f"Fixed RequestedTime samples: {df['RequestedTime'].head(3).tolist()}")
    
    # Save the fixed file
    output_file = 'test_data/s_10005-91_all_true_FIXED.csv'
    df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"\n✅ Fixed file saved as: {output_file}")
    
    return output_file

if __name__ == "__main__":
    fixed_file = fix_excel_timestamps()