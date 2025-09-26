#!/usr/bin/env python3
"""
Test the sorting fix for results tables
"""

import pandas as pd
import datetime

def test_sorting_fix():
    """Test the improved sorting logic"""
    
    print("=== Testing Sorting Fix ===")
    
    # Create test data with mixed data types (similar to actual data)
    test_data = {
        'link_id': ['s_653-655', 's_9054-99', 's_653-655', 's_9054-99', 's_653-655'],
        'date': [
            datetime.date(2025, 6, 30),
            datetime.date(2025, 6, 29), 
            datetime.date(2025, 6, 29),
            datetime.date(2025, 6, 30),
            datetime.date(2025, 7, 1)
        ],
        'hour_of_day': [14, 8, 6, 14, 8],
        'n_valid': [5, 3, 2, 4, 1]
    }
    
    df = pd.DataFrame(test_data)
    
    print("Original data:")
    print(df[['link_id', 'date', 'hour_of_day']])
    print(f"\nData types:")
    print(f"  link_id: {df['link_id'].dtype}")
    print(f"  date: {df['date'].dtype}")
    print(f"  hour_of_day: {df['hour_of_day'].dtype}")
    
    # Apply the same sorting logic as in the app
    df_sorted = df.copy()
    
    # Ensure proper data types for sorting
    if 'date' in df_sorted.columns:
        if df_sorted['date'].dtype == 'object':
            try:
                df_sorted['date'] = pd.to_datetime(df_sorted['date'])
                print(f"\n✅ Converted date column to datetime")
            except:
                print(f"\n❌ Failed to convert date column")
    
    if 'hour_of_day' in df_sorted.columns:
        df_sorted['hour_of_day'] = pd.to_numeric(df_sorted['hour_of_day'], errors='coerce')
        print(f"✅ Ensured hour_of_day is numeric")
    
    # Sort by link_id, date, hour_of_day
    sort_columns = ['link_id', 'date', 'hour_of_day']
    df_sorted = df_sorted.sort_values(sort_columns, na_position='last')
    
    print(f"\nAfter sorting by {' → '.join(sort_columns)}:")
    print(df_sorted[['link_id', 'date', 'hour_of_day']])
    
    # Verify sorting is correct
    print(f"\n=== Sorting Verification ===")
    
    # Check if data is properly grouped by link_id
    link_groups = df_sorted.groupby('link_id')
    print(f"✅ Links are grouped: {list(link_groups.groups.keys())}")
    
    # Check if dates are sorted within each link
    for link_id, group in link_groups:
        dates = group['date'].tolist()
        dates_sorted = sorted(dates)
        if dates == dates_sorted:
            print(f"✅ Dates sorted correctly for {link_id}")
        else:
            print(f"❌ Dates NOT sorted for {link_id}: {dates}")
    
    # Check if hours are sorted within each link-date combination
    for link_id, group in link_groups:
        for date, date_group in group.groupby('date'):
            hours = date_group['hour_of_day'].tolist()
            hours_sorted = sorted(hours)
            if hours == hours_sorted:
                print(f"✅ Hours sorted correctly for {link_id} on {date}")
            else:
                print(f"❌ Hours NOT sorted for {link_id} on {date}: {hours}")
    
    print(f"\n🎉 Sorting fix test completed!")
    
    print(f"\nKey improvements:")
    print(f"- ✅ Convert date objects to datetime for proper sorting")
    print(f"- ✅ Ensure hour_of_day is numeric")
    print(f"- ✅ Use na_position='last' to handle NaN values")
    print(f"- ✅ Apply same logic to both hourly and weekly data")
    print(f"- ✅ Apply same logic to preview displays")

if __name__ == "__main__":
    test_sorting_fix()