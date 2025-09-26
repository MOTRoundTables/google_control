#!/usr/bin/env python3
"""
Integration test for the complete chunked CSV reading pipeline
"""

import pandas as pd
import tempfile
import os
from datetime import datetime, date
from components.processing.pipeline import read_csv_chunked, run_pipeline

def create_larger_test_csv(num_rows=100):
    """Create a larger test CSV file for chunked reading"""
    import random
    from datetime import datetime, timedelta
    
    # Generate sample data
    data = []
    base_date = datetime(2024, 1, 1, 8, 0, 0)
    links = ['Link_A', 'Link_B', 'Link_C', 'Link_D', 'Link_E']
    hebrew_days = ['יום ב', 'יום ג', 'יום ד', 'יום ה', 'יום ו', 'יום ש', 'יום א']
    day_types = ['יום חול', 'יום חול', 'יום חול', 'יום חול', 'יום חול', 'סוף שבוע', 'סוף שבוע']
    
    for i in range(num_rows):
        timestamp = base_date + timedelta(hours=i % 24, days=i // 24)
        weekday = timestamp.weekday()
        
        row = {
            'DataID': f'ID{i:06d}',
            'Name': random.choice(links),
            'SegmentID': f'SEG{i % 10}',
            'RouteAlternative': f'Route{i % 5}',
            'RequestedTime': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'Timestamp': (timestamp + timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S'),
            'DayInWeek': hebrew_days[weekday],
            'DayType': day_types[weekday],
            'Duration': round(random.uniform(200, 600), 1),
            'Distance': round(random.uniform(1000, 3000), 0),
            'Speed': round(random.uniform(15, 25), 1),
            'Url': f'http://example.com/{i}',
            'Polyline': f'poly{i}'
        }
        data.append(row)
    
    df = pd.DataFrame(data)
    
    # Create temporary CSV file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
    df.to_csv(temp_file.name, index=False)
    
    # Debug: check what's actually in the CSV
    print(f"CSV columns: {df.columns.tolist()}")
    temp_file.close()
    
    return temp_file.name, df

def test_chunked_csv_reading():
    """Test the complete chunked CSV reading pipeline"""
    print("Testing chunked CSV reading pipeline...")
    
    # Create test CSV with 100 rows
    csv_file, original_df = create_larger_test_csv(100)
    
    try:
        # Test parameters
        params = {
            'chunk_size': 25,  # Small chunks to test chunking
            'ts_format': '%Y-%m-%d %H:%M:%S',
            'tz': 'Asia/Jerusalem',
            'duration_range_sec': [0, 1000],
            'distance_range_m': [0, 5000],
            'speed_range_kmh': [0, 50],
            'remove_data_id_duplicates': True,
            'remove_link_timestamp_duplicates': True
        }
        
        # Read CSV using chunked processing
        df_processed = read_csv_chunked(csv_file, params)
        
        print(f"Original rows: {len(original_df)}")
        print(f"Processed rows: {len(df_processed)}")
        print(f"Columns: {list(df_processed.columns)}")
        
        # Verify expected columns are present
        expected_columns = [
            'data_id', 'name', 'segment_id', 'route_alternative', 'requested_time',
            'timestamp', 'day_in_week', 'day_type', 'duration', 'distance', 'speed',
            'url', 'polyline', 'is_valid', 'date', 'hour_of_day', 'iso_week', 
            'weekday_index', 'daytype'
        ]
        
        for col in expected_columns:
            assert col in df_processed.columns, f"Missing column: {col}"
        
        # Verify timestamp parsing
        assert pd.api.types.is_datetime64_any_dtype(df_processed['timestamp'])
        assert df_processed['timestamp'].dt.tz is not None  # Should be timezone-aware
        
        # Verify derived columns
        assert df_processed['date'].notna().all()
        assert df_processed['hour_of_day'].between(0, 23).all()
        assert df_processed['weekday_index'].between(0, 6).all()
        
        # Verify Hebrew day mapping worked
        assert df_processed['weekday_index'].notna().sum() > 0
        
        # Verify daytype mapping
        assert df_processed['daytype'].isin(['weekday', 'weekend']).all()
        
        print("✓ Chunked CSV reading pipeline passed")
        
    finally:
        os.unlink(csv_file)

def test_pipeline_with_filtering():
    """Test the pipeline with filtering applied"""
    print("Testing pipeline with filtering...")
    
    csv_file, original_df = create_larger_test_csv(50)
    
    try:
        # Test parameters with filtering
        params = {
            'input_file_path': csv_file,
            'chunk_size': 20,
            'ts_format': '%Y-%m-%d %H:%M:%S',
            'tz': 'Asia/Jerusalem',
            'duration_range_sec': [0, 1000],
            'distance_range_m': [0, 5000],
            'speed_range_kmh': [0, 50],
            'weekday_include': [0, 1, 2, 3, 4],  # Weekdays only
            'hours_include': [8, 9, 10, 11, 12, 13, 14, 15, 16, 17],  # Business hours
            'whitelist_links': ['Link_A', 'Link_B', 'Link_C']
        }
        
        # Run the pipeline (will return empty DataFrames for now since aggregation not implemented)
        hourly_df, weekly_df, output_files = run_pipeline(params)
        
        print("✓ Pipeline with filtering completed successfully")
        
    except Exception as e:
        print(f"Pipeline test failed: {e}")
        raise
    finally:
        os.unlink(csv_file)

def main():
    """Run integration tests"""
    print("Running integration tests for chunked CSV reading...\n")
    
    try:
        test_chunked_csv_reading()
        print()
        
        test_pipeline_with_filtering()
        print()
        
        print("🎉 All integration tests passed!")
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()