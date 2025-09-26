#!/usr/bin/env python3
"""
Simple test script for chunked CSV reading functionality
"""

import pandas as pd
import tempfile
import os
from components.processing.pipeline import (
    detect_csv_format,
    configure_chunk_size,
    optimize_dtypes,
    apply_date_range_filter,
    apply_weekday_filter,
    apply_hour_filter,
    apply_link_filter,
    apply_preset_filters
)

def create_test_csv():
    """Create a test CSV file with sample data"""
    # Create sample data matching the expected schema
    data = {
        'DataID': ['ID001', 'ID002', 'ID003', 'ID004', 'ID005'],
        'Name': ['Link_A', 'Link_B', 'Link_A', 'Link_C', 'Link_B'],
        'SegmentID': ['SEG1', 'SEG2', 'SEG1', 'SEG3', 'SEG2'],
        'RouteAlternative': ['Route1', 'Route2', 'Route1', 'Route3', 'Route2'],
        'RequestedTime': ['2024-01-01 08:00:00', '2024-01-01 09:00:00', '2024-01-01 10:00:00', '2024-01-01 11:00:00', '2024-01-01 12:00:00'],
        'Timestamp': ['2024-01-01 08:05:00', '2024-01-01 09:05:00', '2024-01-01 10:05:00', '2024-01-01 11:05:00', '2024-01-01 12:05:00'],
        'DayInWeek': ['יום ב', 'יום ב', 'יום ב', 'יום ב', 'יום ב'],
        'DayType': ['יום חול', 'יום חול', 'יום חול', 'יום חול', 'יום חול'],
        'Duration': [300.5, 450.2, 320.1, 280.9, 410.3],
        'Distance': [1500.0, 2200.0, 1600.0, 1400.0, 2000.0],
        'Speed': [18.0, 17.6, 18.0, 18.1, 17.5],
        'Url': ['http://example.com/1', 'http://example.com/2', 'http://example.com/3', 'http://example.com/4', 'http://example.com/5'],
        'Polyline': ['poly1', 'poly2', 'poly3', 'poly4', 'poly5']
    }
    
    df = pd.DataFrame(data)
    
    # Create temporary CSV file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
    df.to_csv(temp_file.name, index=False)
    temp_file.close()
    
    return temp_file.name, df

def test_csv_format_detection():
    """Test CSV format detection"""
    print("Testing CSV format detection...")
    
    csv_file, original_df = create_test_csv()
    
    try:
        format_params = detect_csv_format(csv_file)
        print(f"Detected format: {format_params}")
        
        assert format_params['delimiter'] == ','
        assert format_params['decimal'] == '.'
        print("✓ CSV format detection passed")
        
    finally:
        os.unlink(csv_file)

def test_chunk_size_calculation():
    """Test chunk size calculation"""
    print("Testing chunk size calculation...")
    
    csv_file, original_df = create_test_csv()
    
    try:
        chunk_size = configure_chunk_size(csv_file, available_memory_gb=1.0)
        print(f"Calculated chunk size: {chunk_size}")
        
        assert isinstance(chunk_size, int)
        assert chunk_size > 0
        print("✓ Chunk size calculation passed")
        
    finally:
        os.unlink(csv_file)

def test_dtype_optimization():
    """Test dtype optimization"""
    print("Testing dtype optimization...")
    
    # Create test DataFrame with various data types
    df = pd.DataFrame({
        'small_int': [1, 2, 3, 4, 5],
        'large_int': [1000000, 2000000, 3000000, 4000000, 5000000],
        'float_col': [1.1, 2.2, 3.3, 4.4, 5.5],
        'category_col': ['A', 'B', 'A', 'B', 'A'],
        'unique_col': ['X1', 'X2', 'X3', 'X4', 'X5']
    })
    
    print(f"Original dtypes:\n{df.dtypes}")
    print(f"Original memory usage: {df.memory_usage(deep=True).sum()} bytes")
    
    df_optimized = optimize_dtypes(df)
    
    print(f"Optimized dtypes:\n{df_optimized.dtypes}")
    print(f"Optimized memory usage: {df_optimized.memory_usage(deep=True).sum()} bytes")
    
    # Verify data integrity
    pd.testing.assert_frame_equal(df.astype(str), df_optimized.astype(str))
    print("✓ Dtype optimization passed")

def test_filtering_functions():
    """Test filtering and selection functions"""
    print("Testing filtering functions...")
    
    # Create test DataFrame with temporal data
    df = pd.DataFrame({
        'name': ['Link_A', 'Link_B', 'Link_A', 'Link_C', 'Link_B'],
        'date': [pd.to_datetime('2024-01-01').date(), pd.to_datetime('2024-01-02').date(), 
                 pd.to_datetime('2024-01-03').date(), pd.to_datetime('2024-01-04').date(),
                 pd.to_datetime('2024-01-05').date()],
        'weekday_index': [0, 1, 2, 3, 4],  # Monday to Friday
        'hour_of_day': [8, 9, 10, 11, 12],
        'daytype': ['weekday', 'weekday', 'weekday', 'weekday', 'weekday']
    })
    
    print(f"Original DataFrame shape: {df.shape}")
    
    # Test date range filtering
    params = {
        'start_date': pd.to_datetime('2024-01-02').date(),
        'end_date': pd.to_datetime('2024-01-04').date()
    }
    df_filtered = apply_date_range_filter(df, params)
    print(f"After date filtering: {df_filtered.shape}")
    assert len(df_filtered) == 3
    
    # Test weekday filtering
    params = {'weekday_include': [0, 1, 2]}  # Monday, Tuesday, Wednesday
    df_filtered = apply_weekday_filter(df, params)
    print(f"After weekday filtering: {df_filtered.shape}")
    assert len(df_filtered) == 3
    
    # Test hour filtering
    params = {'hours_include': [8, 9, 10]}
    df_filtered = apply_hour_filter(df, params)
    print(f"After hour filtering: {df_filtered.shape}")
    assert len(df_filtered) == 3
    
    # Test link filtering
    params = {'whitelist_links': ['Link_A', 'Link_B']}
    df_filtered = apply_link_filter(df, params)
    print(f"After link whitelist filtering: {df_filtered.shape}")
    assert len(df_filtered) == 4
    
    params = {'blacklist_links': ['Link_C']}
    df_filtered = apply_link_filter(df, params)
    print(f"After link blacklist filtering: {df_filtered.shape}")
    assert len(df_filtered) == 4
    
    # Test preset filters
    params = {'weekday_only': True}
    df_filtered = apply_preset_filters(df, params)
    print(f"After weekday-only preset: {df_filtered.shape}")
    assert len(df_filtered) == 5  # All are weekdays
    
    print("✓ Filtering functions passed")

def main():
    """Run all tests"""
    print("Running chunked CSV reading tests...\n")
    
    try:
        test_csv_format_detection()
        print()
        
        test_chunk_size_calculation()
        print()
        
        test_dtype_optimization()
        print()
        
        test_filtering_functions()
        print()
        
        print("🎉 All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()