#!/usr/bin/env python3
"""
Comprehensive test of the sorting functionality
"""

import pandas as pd
import datetime

def test_comprehensive_sorting():
    """Test comprehensive sorting with realistic data"""
    
    print("=== Comprehensive Sorting Test ===")
    
    # Create realistic test data that matches the actual data structure
    test_data = {
        'link_id': [
            's_653,655', 's_653-655', 's_9054-99', 's_653-655', 's_653,655',
            's_9054-99', 's_653-655', 's_653,655', 's_9054-99', 's_653-655'
        ],
        'date': [
            datetime.date(2015, 6, 30),  # Note: using 2015 like in the screenshot
            datetime.date(2015, 6, 29),
            datetime.date(2015, 6, 29),
            datetime.date(2015, 6, 29),
            datetime.date(2015, 6, 29),
            datetime.date(2015, 6, 30),
            datetime.date(2015, 6, 30),
            datetime.date(2015, 6, 30),
            datetime.date(2015, 6, 30),
            datetime.date(2015, 7, 1)
        ],
        'hour_of_day': [7, 0, 8, 1, 6, 14, 8, 8, 15, 9],
        'daytype': ['weekday'] * 10,
        'n_total': [1, 4, 3, 4, 2, 1, 3, 2, 1, 4],
        'n_valid': [0, 3, 2, 2, 1, 0, 1, 1, 0, 3]
    }
    
    df = pd.DataFrame(test_data)
    
    print("Original data (unsorted):")
    print(df[['link_id', 'date', 'hour_of_day']])
    
    # Apply the exact same sorting logic as in the app
    hourly_sorted = df.copy()
    
    # Ensure proper data types for sorting
    if 'date' in hourly_sorted.columns:
        if hourly_sorted['date'].dtype == 'object':
            try:
                hourly_sorted['date'] = pd.to_datetime(hourly_sorted['date'])
                print(f"\n✅ Converted date column to datetime")
            except:
                print(f"\n❌ Failed to convert date column")
    
    if 'hour_of_day' in hourly_sorted.columns:
        hourly_sorted['hour_of_day'] = pd.to_numeric(hourly_sorted['hour_of_day'], errors='coerce')
        print(f"✅ Ensured hour_of_day is numeric")
    
    # Define sort columns
    sort_columns = []
    if 'link_id' in hourly_sorted.columns:
        sort_columns.append('link_id')
    if 'date' in hourly_sorted.columns:
        sort_columns.append('date')
    if 'hour_of_day' in hourly_sorted.columns:
        sort_columns.append('hour_of_day')
    
    print(f"\nSorting by: {' → '.join(sort_columns)}")
    
    if sort_columns:
        hourly_sorted = hourly_sorted.sort_values(sort_columns, na_position='last')
        # Reset index to ensure proper display order
        hourly_sorted = hourly_sorted.reset_index(drop=True)
    
    print(f"\nAfter sorting:")
    print(hourly_sorted[['link_id', 'date', 'hour_of_day']])
    
    # Verify the sorting is correct
    print(f"\n=== Sorting Verification ===")
    
    # Check if the first few rows are correctly sorted
    expected_order = [
        ('s_653,655', '2015-06-29', 6),
        ('s_653,655', '2015-06-30', 7),
        ('s_653,655', '2015-06-30', 8),
        ('s_653-655', '2015-06-29', 0),
        ('s_653-655', '2015-06-29', 1)
    ]
    
    print("Expected vs Actual (first 5 rows):")
    for i, (exp_link, exp_date, exp_hour) in enumerate(expected_order):
        if i < len(hourly_sorted):
            actual_link = hourly_sorted.iloc[i]['link_id']
            actual_date = hourly_sorted.iloc[i]['date'].strftime('%Y-%m-%d')
            actual_hour = hourly_sorted.iloc[i]['hour_of_day']
            
            match = (actual_link == exp_link and actual_date == exp_date and actual_hour == exp_hour)
            status = "✅" if match else "❌"
            
            print(f"  {status} Row {i}: Expected ({exp_link}, {exp_date}, {exp_hour}) → Got ({actual_link}, {actual_date}, {actual_hour})")
        else:
            print(f"  ❌ Row {i}: Expected ({exp_link}, {exp_date}, {exp_hour}) → Missing")
    
    # Check if data is properly grouped by link_id
    link_groups = hourly_sorted.groupby('link_id')
    print(f"\n✅ Links are grouped: {list(link_groups.groups.keys())}")
    
    print(f"\n🎉 Comprehensive sorting test completed!")
    
    return hourly_sorted

if __name__ == "__main__":
    result = test_comprehensive_sorting()