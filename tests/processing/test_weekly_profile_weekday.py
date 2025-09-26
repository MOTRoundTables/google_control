"""
Test weekly profile with weekday_index grouping
"""

import pandas as pd
from datetime import date
from components.processing.pipeline import create_weekly_profile

def test_weekly_profile_weekday_grouping():
    """Test weekly profile creation with weekday_index grouping"""
    
    # Create sample hourly data with weekday_index
    hourly_data = {
        'link_id': ['link1', 'link1', 'link1', 'link2', 'link2', 'link2'],
        'date': [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3), 
                 date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)],
        'hour_of_day': [8, 8, 8, 9, 9, 9],
        'daytype': ['weekday', 'weekday', 'weekday', 'weekday', 'weekday', 'weekday'],
        'weekday_index': [0, 1, 2, 0, 1, 2],  # Monday, Tuesday, Wednesday
        'valid_hour': [True, True, True, True, True, True],
        'n_valid': [10, 12, 8, 15, 18, 12],
        'avg_duration_sec': [300.0, 320.0, 280.0, 400.0, 420.0, 380.0],
        'std_duration_sec': [50.0, 60.0, 40.0, 80.0, 90.0, 70.0],
        'avg_distance_m': [1000.0, 1100.0, 900.0, 1500.0, 1600.0, 1400.0],
        'avg_speed_kmh': [12.0, 12.4, 11.6, 13.5, 13.7, 13.3]
    }
    
    hourly_df = pd.DataFrame(hourly_data)
    
    # Test parameters with weekday_index grouping
    params = {
        'weekly_grouping': 'weekday_index',
        'recompute_std_from_raw': False
    }
    
    # Create weekly profile
    weekly_df = create_weekly_profile(hourly_df, params)
    
    # Verify results
    assert not weekly_df.empty, "Weekly profile should not be empty"
    assert len(weekly_df) == 6, f"Expected 6 weekly profiles (2 links × 3 weekdays), got {len(weekly_df)}"
    
    # Check columns
    expected_cols = ['link_id', 'weekday_index', 'hour_of_day', 'avg_n_valid', 'avg_dur', 'std_dur', 'avg_dist', 'avg_speed', 'n_days']
    for col in expected_cols:
        assert col in weekly_df.columns, f"Missing column: {col}"
    
    # Check that weekday_index values are preserved
    weekday_values = set(weekly_df['weekday_index'].unique())
    expected_weekdays = {0, 1, 2}
    assert weekday_values == expected_weekdays, f"Expected weekdays {expected_weekdays}, got {weekday_values}"
    
    print("✓ Weekday grouping test passed")


if __name__ == "__main__":
    test_weekly_profile_weekday_grouping()
    print("Weekday grouping test completed!")