"""
Simple test for weekly profile functionality
"""

import pandas as pd
from datetime import date, datetime
from components.aggregation.pipeline import create_weekly_profile, write_weekly_hourly_profile_csv
import tempfile
import os

def test_weekly_profile_basic():
    """Test basic weekly profile creation"""
    
    # Create sample hourly data
    hourly_data = {
        'link_id': ['link1', 'link1', 'link1', 'link2', 'link2', 'link2'],
        'date': [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3), 
                 date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)],
        'hour_of_day': [8, 8, 8, 9, 9, 9],
        'daytype': ['weekday', 'weekday', 'weekday', 'weekday', 'weekday', 'weekday'],
        'valid_hour': [True, True, True, True, True, True],
        'n_valid': [10, 12, 8, 15, 18, 12],
        'avg_duration_sec': [300.0, 320.0, 280.0, 400.0, 420.0, 380.0],
        'std_duration_sec': [50.0, 60.0, 40.0, 80.0, 90.0, 70.0],
        'avg_distance_m': [1000.0, 1100.0, 900.0, 1500.0, 1600.0, 1400.0],
        'avg_speed_kmh': [12.0, 12.4, 11.6, 13.5, 13.7, 13.3]
    }
    
    hourly_df = pd.DataFrame(hourly_data)
    
    # Test parameters
    params = {
        'weekly_grouping': 'daytype',
        'recompute_std_from_raw': False
    }
    
    # Create weekly profile
    weekly_df = create_weekly_profile(hourly_df, params)
    
    # Verify results
    assert not weekly_df.empty, "Weekly profile should not be empty"
    assert len(weekly_df) == 2, f"Expected 2 weekly profiles, got {len(weekly_df)}"
    
    # Check columns
    expected_cols = ['link_id', 'daytype', 'hour_of_day', 'avg_n_valid', 'avg_dur', 'std_dur', 'avg_dist', 'avg_speed', 'n_days']
    for col in expected_cols:
        assert col in weekly_df.columns, f"Missing column: {col}"
    
    # Check values for link1, hour 8
    link1_row = weekly_df[(weekly_df['link_id'] == 'link1') & (weekly_df['hour_of_day'] == 8)]
    assert len(link1_row) == 1, "Should have exactly one row for link1, hour 8"
    
    row = link1_row.iloc[0]
    assert row['avg_n_valid'] == 10.0, f"Expected avg_n_valid=10.0, got {row['avg_n_valid']}"
    assert row['avg_dur'] == 300.0, f"Expected avg_dur=300.0, got {row['avg_dur']}"
    assert row['n_days'] == 3, f"Expected n_days=3, got {row['n_days']}"
    
    print("✓ Basic weekly profile test passed")


def test_weekly_profile_csv_writing():
    """Test CSV writing functionality"""
    
    # Create sample weekly profile data
    weekly_data = {
        'link_id': ['link1', 'link2'],
        'daytype': ['weekday', 'weekday'],
        'hour_of_day': [8, 9],
        'avg_n_valid': [10.0, 15.0],
        'avg_dur': [300.0, 400.0],
        'std_dur': [50.0, 80.0],
        'avg_dist': [1000.0, 1500.0],
        'avg_speed': [12.0, 13.5],
        'n_days': [3, 3]
    }
    
    weekly_df = pd.DataFrame(weekly_data)
    
    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
        tmp_path = tmp_file.name
    
    try:
        # Test CSV writing
        success = write_weekly_hourly_profile_csv(weekly_df, tmp_path)
        assert success, "CSV writing should succeed"
        
        # Verify file was created and has content
        assert os.path.exists(tmp_path), "CSV file should exist"
        
        # Read back and verify
        read_df = pd.read_csv(tmp_path)
        assert len(read_df) == 2, f"Expected 2 rows in CSV, got {len(read_df)}"
        assert 'link_id' in read_df.columns, "link_id column should exist"
        assert 'avg_dur' in read_df.columns, "avg_dur column should exist"
        
        print("✓ CSV writing test passed")
        
    finally:
        # Clean up
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


if __name__ == "__main__":
    test_weekly_profile_basic()
    test_weekly_profile_csv_writing()
    print("All tests passed!")