#!/usr/bin/env python3
"""
Advanced Test Data Generator for Maps Link Monitoring Application

This script creates comprehensive test datasets with application-specific edge cases
based on the actual validation logic, data processing patterns, and error scenarios
found in the maps link monitoring application.

Features:
- Realistic failure patterns based on time, day type, and operational scenarios
- Application-specific edge cases for validation, parsing, and aggregation
- Hebrew formatting preservation for DayInWeek and DayType fields
- Multiple test dataset sizes for different testing phases
- Comprehensive edge case coverage for all processing components

Supports:
- test_data/data.csv (714k records) - Full production simulation
- test_data/data_test_small.csv (300 records) - Quick development testing
- test_data/data_test.csv (714k records) - Comprehensive edge case testing
"""

import pandas as pd
import random
import numpy as np
from datetime import datetime, time, timedelta
import sys
from pathlib import Path

def populate_is_valid_field(csv_file_path):
    """
    Populate the is_valid field with comprehensive edge cases based on the 
    actual application validation logic and processing patterns.
    
    Edge Case Categories:
    1. Time-based patterns (peak hours, DST transitions, timezone issues)
    2. Numeric validation failures (duration, distance, speed out of bounds)
    3. Data quality issues (duplicates, missing values, format errors)
    4. Hebrew text handling (day names, day types, encoding issues)
    5. Aggregation edge cases (zero valid hours, extreme values)
    6. Filtering scenarios (date boundaries, link selections)
    7. CSV format detection issues (delimiters, decimal separators)
    8. Memory and performance stress testing patterns
    
    Distribution Strategy:
    - 70-80% TRUE (valid data) for realistic operational conditions
    - 20-30% FALSE (invalid data) covering all major failure modes
    - Clustered failures to simulate real-world outage scenarios
    - Scattered failures to test general resilience
    """
    
    print(f"Loading data from {csv_file_path}...")
    # Read with explicit encoding to preserve Hebrew characters
    df = pd.read_csv(csv_file_path, encoding='utf-8')
    
    print(f"Found {len(df)} records to process")
    
    # Parse time information for intelligent distribution
    df['hour'] = pd.to_datetime(df['RequestedTime'], format='%H:%M:%S').dt.hour
    df['is_weekend'] = df['DayInWeek'].isin(['יום ו', 'יום ש'])  # Friday, Saturday
    
    # Add is_valid column if it doesn't exist
    if 'is_valid' not in df.columns:
        df['is_valid'] = 'TRUE'
    
    # Initialize all as TRUE, then selectively set to FALSE
    df['is_valid'] = 'TRUE'
    
    # Define failure rate based on conditions
    def get_failure_rate(row):
        hour = row['hour']
        is_weekend = row['is_weekend']
        
        # Peak hours (7-9 AM, 5-7 PM) - higher failure rate
        if (7 <= hour <= 9) or (17 <= hour <= 19):
            base_rate = 0.40
        # Late night/early morning (11 PM - 5 AM) - moderate failure rate
        elif hour >= 23 or hour <= 5:
            base_rate = 0.25
        # Regular hours - lower failure rate
        else:
            base_rate = 0.20
            
        # Weekend adjustment - slightly higher failure rate
        if is_weekend:
            base_rate += 0.05
            
        return min(base_rate, 0.45)  # Cap at 45%
    
    # Apply failure rates
    random.seed(42)  # For reproducible results
    
    for idx, row in df.iterrows():
        failure_rate = get_failure_rate(row)
        if random.random() < failure_rate:
            df.at[idx, 'is_valid'] = 'FALSE'
        else:
            df.at[idx, 'is_valid'] = 'TRUE'
    
    # Ensure we have some specific edge cases for testing
    total_records = len(df)
    
    # Force some specific patterns for edge case testing:
    
    # 1. Consecutive failures (simulate server downtime)
    consecutive_start = random.randint(100, 200)
    for i in range(consecutive_start, min(consecutive_start + 5, total_records)):
        df.at[i, 'is_valid'] = 'FALSE'
    
    # 2. All failures in a specific hour (simulate API rate limiting)
    if total_records > 50:
        target_hour = 14  # 2 PM
        hour_mask = df['hour'] == target_hour
        hour_indices = df[hour_mask].index[:10]  # First 10 records of that hour
        for idx in hour_indices:
            df.at[idx, 'is_valid'] = 'FALSE'
    
    # 3. Alternating pattern (simulate intermittent issues)
    alternating_start = random.randint(300, 400) if total_records > 400 else total_records // 2
    for i in range(alternating_start, min(alternating_start + 10, total_records), 2):
        df.at[i, 'is_valid'] = 'FALSE'
    
    # 4. Random scattered failures throughout
    additional_failures = random.sample(range(total_records), min(50, total_records // 10))
    for idx in additional_failures:
        df.at[idx, 'is_valid'] = 'FALSE'
    
    # 5. Application-specific edge cases
    df = add_application_edge_cases(df, total_records)
    
    # Ensure all values are strings
    df['is_valid'] = df['is_valid'].astype(str)
    
    # Clean up temporary columns
    df = df.drop(['hour', 'is_weekend'], axis=1)
    
    # Count final distribution
    true_count = (df['is_valid'] == 'TRUE').sum()
    false_count = (df['is_valid'] == 'FALSE').sum()
    
    print(f"\nFinal distribution:")
    print(f"TRUE (valid): {true_count} ({true_count/total_records*100:.1f}%)")
    print(f"FALSE (invalid): {false_count} ({false_count/total_records*100:.1f}%)")
    
    # Final cleanup and type conversion
    df['is_valid'] = df['is_valid'].map({True: 'TRUE', False: 'FALSE'}).fillna(df['is_valid'])
    
    # Save the updated data with UTF-8 encoding to preserve Hebrew
    output_file = csv_file_path
    df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"\nUpdated data saved to {output_file}")
    
    return df


def add_application_edge_cases(df, total_records):
    """
    Add comprehensive edge cases based on actual application validation logic
    and processing patterns from the maps link monitoring system.
    """
    
    # Edge Case 1: Numeric validation failures (based on processing.py validation logic)
    add_numeric_validation_edge_cases(df, total_records)
    
    # Edge Case 2: Timestamp and timezone edge cases
    add_timestamp_edge_cases(df, total_records)
    
    # Edge Case 3: Duplicate data scenarios
    add_duplicate_data_edge_cases(df, total_records)
    
    # Edge Case 4: Hebrew text and encoding edge cases
    add_hebrew_text_edge_cases(df, total_records)
    
    # Edge Case 5: Aggregation boundary conditions
    add_aggregation_edge_cases(df, total_records)
    
    # Edge Case 6: CSV format and parsing edge cases
    add_csv_format_edge_cases(df, total_records)
    
    # Edge Case 7: Memory and performance stress patterns
    add_performance_stress_patterns(df, total_records)
    
    return df


def add_numeric_validation_edge_cases(df, total_records):
    """
    Add edge cases for numeric range validation based on processing.py logic:
    - Duration out of reasonable bounds (negative, extremely high)
    - Distance validation failures (zero, negative, unrealistic values)
    - Speed calculation edge cases (zero distance, extreme speeds)
    """
    
    # Duration edge cases (typical valid range: 30 seconds to 2 hours)
    duration_edge_indices = random.sample(range(total_records), min(20, total_records // 50))
    for idx in duration_edge_indices:
        df.at[idx, 'is_valid'] = 'FALSE'
        # Simulate various duration validation failures
        edge_type = random.choice(['negative', 'zero', 'extreme_high', 'null'])
        if edge_type == 'negative':
            df.at[idx, 'Duration (seconds)'] = random.randint(-3600, -1)
        elif edge_type == 'zero':
            df.at[idx, 'Duration (seconds)'] = 0
        elif edge_type == 'extreme_high':
            df.at[idx, 'Duration (seconds)'] = random.randint(36000, 86400)  # 10-24 hours
        elif edge_type == 'null':
            df.at[idx, 'Duration (seconds)'] = np.nan
    
    # Distance edge cases (typical valid range: 100m to 100km)
    distance_edge_indices = random.sample(range(total_records), min(15, total_records // 60))
    for idx in distance_edge_indices:
        df.at[idx, 'is_valid'] = 'FALSE'
        edge_type = random.choice(['negative', 'zero', 'extreme_high', 'null'])
        if edge_type == 'negative':
            df.at[idx, 'Distance (meters)'] = random.randint(-50000, -1)
        elif edge_type == 'zero':
            df.at[idx, 'Distance (meters)'] = 0
        elif edge_type == 'extreme_high':
            df.at[idx, 'Distance (meters)'] = random.randint(500000, 1000000)  # 500km+
        elif edge_type == 'null':
            df.at[idx, 'Distance (meters)'] = np.nan
    
    # Speed edge cases (typical valid range: 1-200 km/h)
    speed_edge_indices = random.sample(range(total_records), min(25, total_records // 40))
    for idx in speed_edge_indices:
        df.at[idx, 'is_valid'] = 'FALSE'
        edge_type = random.choice(['negative', 'zero', 'extreme_high', 'null'])
        if edge_type == 'negative':
            df.at[idx, 'Speed (km/h)'] = random.uniform(-100, -0.1)
        elif edge_type == 'zero':
            df.at[idx, 'Speed (km/h)'] = 0
        elif edge_type == 'extreme_high':
            df.at[idx, 'Speed (km/h)'] = random.uniform(300, 1000)  # Unrealistic speeds
        elif edge_type == 'null':
            df.at[idx, 'Speed (km/h)'] = np.nan


def add_timestamp_edge_cases(df, total_records):
    """
    Add timestamp parsing and timezone edge cases:
    - DST transition times (ambiguous/non-existent)
    - Invalid timestamp formats
    - Timezone boundary conditions
    - Future/past extreme dates
    """
    
    timestamp_edge_indices = random.sample(range(total_records), min(10, total_records // 100))
    for idx in timestamp_edge_indices:
        df.at[idx, 'is_valid'] = 'FALSE'
        edge_type = random.choice(['dst_ambiguous', 'invalid_format', 'extreme_future', 'extreme_past'])
        
        if edge_type == 'dst_ambiguous':
            # Simulate DST transition times (typically around 2:00 AM)
            df.at[idx, 'RequestedTime'] = '02:30:00'
            df.at[idx, 'Timestamp'] = '2025-03-30 02:30:00'  # DST transition date
        elif edge_type == 'invalid_format':
            df.at[idx, 'Timestamp'] = 'invalid-timestamp-format'
        elif edge_type == 'extreme_future':
            df.at[idx, 'Timestamp'] = '2099-12-31 23:59:59'
        elif edge_type == 'extreme_past':
            df.at[idx, 'Timestamp'] = '1900-01-01 00:00:00'


def add_duplicate_data_edge_cases(df, total_records):
    """
    Add duplicate data scenarios to test deduplication logic:
    - Exact DataID duplicates
    - Same link + timestamp combinations
    - Near-duplicate records with slight variations
    """
    
    # Create exact DataID duplicates
    if total_records > 50:
        duplicate_indices = random.sample(range(total_records // 2), min(5, total_records // 100))
        for base_idx in duplicate_indices:
            if base_idx + 25 < total_records:
                duplicate_idx = base_idx + 25
                df.at[duplicate_idx, 'DataID'] = df.at[base_idx, 'DataID']
                df.at[duplicate_idx, 'is_valid'] = 'FALSE'  # Mark duplicate as invalid
    
    # Create link + timestamp duplicates
    if total_records > 100:
        link_dup_indices = random.sample(range(total_records // 2), min(3, total_records // 150))
        for base_idx in link_dup_indices:
            if base_idx + 50 < total_records:
                duplicate_idx = base_idx + 50
                df.at[duplicate_idx, 'Name'] = df.at[base_idx, 'Name']
                df.at[duplicate_idx, 'Timestamp'] = df.at[base_idx, 'Timestamp']
                df.at[duplicate_idx, 'is_valid'] = 'FALSE'


def add_hebrew_text_edge_cases(df, total_records):
    """
    Add Hebrew text and encoding edge cases:
    - Invalid Hebrew day names
    - Mixed encoding issues
    - Corrupted Hebrew characters
    - Invalid DayType values
    """
    
    hebrew_edge_indices = random.sample(range(total_records), min(8, total_records // 125))
    for idx in hebrew_edge_indices:
        df.at[idx, 'is_valid'] = 'FALSE'
        edge_type = random.choice(['invalid_day', 'corrupted_encoding', 'invalid_daytype'])
        
        if edge_type == 'invalid_day':
            df.at[idx, 'DayInWeek'] = 'יום ח'  # Invalid day (8th day)
        elif edge_type == 'corrupted_encoding':
            df.at[idx, 'DayInWeek'] = '???'  # Corrupted encoding
        elif edge_type == 'invalid_daytype':
            df.at[idx, 'DayType'] = 'יום לא ידוע'  # Unknown day type


def add_aggregation_edge_cases(df, total_records):
    """
    Add edge cases for hourly aggregation and weekly profile generation:
    - Hours with single records
    - Hours with all invalid data
    - Extreme metric values that affect aggregation
    - Missing time periods
    """
    
    # Create hours with extreme values for aggregation testing
    agg_edge_indices = random.sample(range(total_records), min(12, total_records // 80))
    for idx in agg_edge_indices:
        edge_type = random.choice(['single_record_hour', 'extreme_values', 'boundary_time'])
        
        if edge_type == 'single_record_hour':
            # Create isolated records for specific hours
            df.at[idx, 'RequestedTime'] = '23:59:00'  # Edge of day boundary
        elif edge_type == 'extreme_values':
            # Keep valid but with extreme values for aggregation testing
            df.at[idx, 'Duration (seconds)'] = 7200  # 2 hours (high but valid)
            df.at[idx, 'Speed (km/h)'] = 199.9  # High but valid speed
        elif edge_type == 'boundary_time':
            df.at[idx, 'RequestedTime'] = '00:00:00'  # Start of day boundary


def add_csv_format_edge_cases(df, total_records):
    """
    Add CSV format and parsing edge cases:
    - Records with embedded commas/semicolons
    - Decimal separator variations
    - Encoding issues in text fields
    - Special characters in URLs and polylines
    """
    
    csv_edge_indices = random.sample(range(total_records), min(6, total_records // 150))
    for idx in csv_edge_indices:
        edge_type = random.choice(['embedded_comma', 'special_chars', 'encoding_issue'])
        
        if edge_type == 'embedded_comma':
            # Add commas to text fields that might break CSV parsing
            df.at[idx, 'Name'] = 's_653,655'  # Comma in name field
        elif edge_type == 'special_chars':
            # Add special characters to URL field
            df.at[idx, 'Url'] = 'https://tdr.mpayer.co.il/external/recording?s=1185048&d=287208545&a=1&du=2446&special=ñáéíóú'
        elif edge_type == 'encoding_issue':
            # Simulate encoding issues in polyline
            df.at[idx, 'Polyline'] = 'corrupted_polyline_data_with_special_chars_ñáéíóú'


def add_performance_stress_patterns(df, total_records):
    """
    Add patterns that stress memory usage and processing performance:
    - Concentrated data bursts
    - Large polyline data
    - High-frequency timestamp clusters
    - Memory-intensive aggregation scenarios
    """
    
    # Create timestamp clusters for stress testing chunked processing
    if total_records > 1000:
        cluster_start = random.randint(100, total_records - 500)
        cluster_size = min(100, total_records // 20)
        
        base_timestamp = '2025-07-01 08:00:00'
        for i in range(cluster_size):
            if cluster_start + i < total_records:
                # Create high-frequency cluster (same minute, different seconds)
                seconds = i % 60
                df.at[cluster_start + i, 'Timestamp'] = f'2025-07-01 08:00:{seconds:02d}'
                df.at[cluster_start + i, 'RequestedTime'] = f'08:00:{seconds:02d}'
    
    # Create large polyline data for memory stress testing
    large_data_indices = random.sample(range(total_records), min(3, total_records // 200))
    for idx in large_data_indices:
        # Generate large polyline string (simulate complex route)
        large_polyline = '_oxwD{_wtE' + 'oAlCe@vFq@ha@c@~X_@fOcD~S' * 50  # Repeat pattern
        df.at[idx, 'Polyline'] = large_polyline


if __name__ == "__main__":
    # Handle command line arguments
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
        # Add test_data/ prefix if not already present
        if not csv_file.startswith('test_data/'):
            csv_file = f"test_data/{csv_file}"
    else:
        csv_file = "test_data/data_test_small.csv"  # Default to small test file
    
    print(f"Processing file: {csv_file}")
    result_df = populate_is_valid_field(csv_file)
    
    print("\nTest scenarios created:")
    print("✓ Peak hour failures (7-9 AM, 5-7 PM)")
    print("✓ Weekend vs weekday variations")
    print("✓ Consecutive failures (server downtime simulation)")
    print("✓ Hourly failure clusters (rate limiting simulation)")
    print("✓ Alternating patterns (intermittent issues)")
    print("✓ Random scattered failures")
    print(f"\nYour test data in {csv_file} is now ready for comprehensive edge case testing!")