#!/usr/bin/env python3
"""
Test the sorting functionality for results display
"""

import pandas as pd
import sys
sys.path.append('.')

def test_sorting():
    """Test the sorting logic for hourly and weekly data"""
    
    print("=== Testing Results Sorting ===")
    
    # Create sample hourly data
    hourly_data = {
        'link_id': ['s_653-655', 's_653-655', 's_9054-99', 's_653-655', 's_9054-99'],
        'date': ['2025-06-29', '2025-06-30', '2025-06-29', '2025-06-29', '2025-06-30'],
        'hour_of_day': [14, 8, 14, 8, 14],
        'n_valid': [5, 3, 2, 4, 1],
        'avg_duration_sec': [2400, 2500, 1800, 2300, 1900]
    }
    
    hourly_df = pd.DataFrame(hourly_data)
    
    print("Original hourly data:")
    print(hourly_df)
    
    # Test sorting
    sort_columns = ['link_id', 'date', 'hour_of_day']
    hourly_sorted = hourly_df.sort_values(sort_columns)
    
    print(f"\nSorted by {' → '.join(sort_columns)}:")
    print(hourly_sorted)
    
    # Create sample weekly data
    weekly_data = {
        'link_id': ['s_653-655', 's_9054-99', 's_653-655', 's_653-655', 's_9054-99'],
        'daytype': ['weekday', 'weekday', 'weekend', 'weekday', 'weekend'],
        'hour_of_day': [14, 8, 14, 8, 14],
        'avg_n_valid': [5.2, 3.1, 2.8, 4.5, 1.9],
        'avg_dur': [2400, 2500, 1800, 2300, 1900]
    }
    
    weekly_df = pd.DataFrame(weekly_data)
    
    print("\n" + "="*50)
    print("Original weekly data:")
    print(weekly_df)
    
    # Test sorting
    sort_columns = ['link_id', 'daytype', 'hour_of_day']
    weekly_sorted = weekly_df.sort_values(sort_columns)
    
    print(f"\nSorted by {' → '.join(sort_columns)}:")
    print(weekly_sorted)
    
    print("\n✅ Sorting test completed!")
    print("\nExpected behavior:")
    print("- Hourly data: grouped by link_id, then chronological by date, then by hour")
    print("- Weekly data: grouped by link_id, then by daytype, then by hour")
    print("- Results page shows 20 rows instead of 10 for better overview")

if __name__ == "__main__":
    test_sorting()