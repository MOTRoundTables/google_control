"""
Google Maps Link Monitoring CSV Processor - Core Processing Engine

This module contains the core data processing logic for handling large-scale
traffic monitoring datasets with optimized pandas operations.
"""

import pandas as pd
import numpy as np
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple, Union
import holidays
from pathlib import Path
import json
import logging
import re
import pytz
from zoneinfo import ZoneInfo
import warnings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Required CSV columns as specified in requirements (flexible matching)
REQUIRED_COLUMNS = [
    'DataID', 'Name', 'SegmentID', 'RouteAlternative', 'RequestedTime',
    'Timestamp', 'DayInWeek', 'DayType', 'Duration', 'Distance', 'Speed',
    'Url', 'Polyline'
]

# Column name mapping to snake_case (handles variations with spaces/units)
COLUMN_MAPPING = {
    'DataID': 'data_id',
    'Name': 'name',  # Used as link_id
    'SegmentID': 'segment_id', 
    'RouteAlternative': 'route_alternative',
    'RequestedTime': 'requested_time',
    'Timestamp': 'timestamp',
    'DayInWeek': 'day_in_week',
    'DayType': 'day_type',
    'Duration': 'duration',
    'Duration (seconds)': 'duration',  # Handle test data format
    'Distance': 'distance',
    'Distance (meters)': 'distance',  # Handle test data format
    'Speed': 'speed',
    'Speed (km/h)': 'speed',  # Handle test data format
    'Url': 'url',
    'Polyline': 'polyline'
}


def validate_csv_columns(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Validate that required CSV columns exist in the DataFrame (flexible matching)
    
    Args:
        df: Input DataFrame to validate
        
    Returns:
        Tuple of (is_valid, missing_columns_list)
    """
    missing_columns = []
    df_columns = set(df.columns)
    
    # Create a mapping of base column names to possible variations
    column_variations = {
        'Duration': ['Duration', 'Duration (seconds)'],
        'Distance': ['Distance', 'Distance (meters)'],
        'Speed': ['Speed', 'Speed (km/h)']
    }
    
    for required_col in REQUIRED_COLUMNS:
        # Check if exact match exists
        if required_col in df_columns:
            continue
            
        # Check for variations
        variations = column_variations.get(required_col, [required_col])
        found = False
        for variation in variations:
            if variation in df_columns:
                found = True
                break
        
        if not found:
            missing_columns.append(required_col)
    
    is_valid = len(missing_columns) == 0
    return is_valid, missing_columns


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize column names to snake_case using predefined mapping
    
    Args:
        df: Input DataFrame with original column names
        
    Returns:
        DataFrame with normalized column names
    """
    # Create a copy to avoid modifying the original
    df_normalized = df.copy()
    
    # Apply the column mapping
    df_normalized = df_normalized.rename(columns=COLUMN_MAPPING)
    
    # Also handle any additional columns that might exist (like 'valid', 'valid_code')
    # by converting them to snake_case
    additional_columns = {}
    for col in df_normalized.columns:
        if col not in COLUMN_MAPPING.values():
            snake_case_col = _to_snake_case(col)
            if snake_case_col != col:
                additional_columns[col] = snake_case_col
    
    if additional_columns:
        df_normalized = df_normalized.rename(columns=additional_columns)
    
    return df_normalized


def _to_snake_case(name: str) -> str:
    """
    Convert a string to snake_case
    
    Args:
        name: Input string to convert
        
    Returns:
        String in snake_case format
    """
    # Handle camelCase and PascalCase
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
    
    # Replace spaces and other separators with underscores
    s3 = re.sub(r'[\s\-\.]+', '_', s2)
    
    # Convert to lowercase and remove multiple underscores
    s4 = re.sub(r'_+', '_', s3.lower())
    
    # Remove leading/trailing underscores
    return s4.strip('_')


def parse_timestamp_with_timezone(timestamp_str: str, ts_format: str, timezone: str) -> Optional[pd.Timestamp]:
    """
    Parse a timestamp string to timezone-aware datetime
    
    Args:
        timestamp_str: String representation of timestamp
        ts_format: Format string for parsing (e.g., '%Y-%m-%d %H:%M:%S')
        timezone: Timezone string (e.g., 'Asia/Jerusalem')
        
    Returns:
        Timezone-aware pandas Timestamp or None if parsing fails
    """
    if pd.isna(timestamp_str) or timestamp_str == '':
        return None
    
    try:
        # Parse the timestamp string
        dt = datetime.strptime(str(timestamp_str), ts_format)
        
        # Get timezone object
        tz = ZoneInfo(timezone)
        
        # If datetime is naive, localize it to the specified timezone
        if dt.tzinfo is None:
            try:
                # Try to localize the naive datetime
                dt_aware = dt.replace(tzinfo=tz)
                return pd.Timestamp(dt_aware)
            except Exception as e:
                # Handle ambiguous times during DST transitions
                logger.warning(f"Ambiguous time during DST transition: {timestamp_str} in {timezone}. Error: {e}")
                # For ambiguous times, assume standard time (is_dst=False)
                try:
                    dt_localized = pytz.timezone(timezone).localize(dt, is_dst=False)
                    return pd.Timestamp(dt_localized)
                except:
                    # If still fails, return None
                    logger.error(f"Failed to handle ambiguous time: {timestamp_str}")
                    return None
        else:
            # Already timezone-aware, convert to target timezone if different
            dt_aware = dt.astimezone(tz)
            return pd.Timestamp(dt_aware)
            
    except ValueError as e:
        logger.warning(f"Failed to parse timestamp '{timestamp_str}' with format '{ts_format}': {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error parsing timestamp '{timestamp_str}': {e}")
        return None


def parse_timestamps_vectorized(timestamps: pd.Series, ts_format: str, timezone: str) -> pd.Series:
    """
    Parse a series of timestamps to timezone-aware datetimes using vectorized operations
    
    Args:
        timestamps: Series of timestamp strings
        ts_format: Format string for parsing
        timezone: Timezone string
        
    Returns:
        Series of timezone-aware pandas Timestamps
    """
    logger.info(f"Parsing {len(timestamps)} timestamps with format '{ts_format}' to timezone '{timezone}'")
    
    # Handle empty or all-null series
    if timestamps.empty or timestamps.isna().all():
        return pd.Series(dtype='datetime64[ns, UTC]')
    
    # Clean timestamp strings first - remove leading/trailing whitespace
    cleaned_timestamps = timestamps.astype(str).str.strip()
    
    # Log sample timestamps for debugging
    logger.debug(f"Sample timestamps to parse: {cleaned_timestamps.head(3).tolist()}")
    
    try:
        # Try multiple timestamp formats for better compatibility
        timestamp_formats = [
            ts_format,  # User-specified format
            '%d/%m/%Y %H:%M',  # European format DD/MM/YYYY HH:MM (common)
            '%Y-%m-%d %H:%M:%S',  # Default format YYYY-MM-DD HH:MM:SS
            '%d/%m/%Y %H:%M:%S',  # European format DD/MM/YYYY HH:MM:SS
            '%m/%d/%Y %H:%M',  # US format MM/DD/YYYY HH:MM
            '%m/%d/%Y %H:%M:%S',  # US format MM/DD/YYYY HH:MM:SS
            '%Y-%m-%d %H:%M',  # ISO format without seconds
            '%Y-%m-%d %H:%M:%S.%f',  # With microseconds
            '%d-%m-%Y %H:%M:%S',  # European with dashes
            '%d-%m-%Y %H:%M',  # European with dashes, no seconds
        ]
        
        parsed_series = None
        successful_format = None
        failed_count = len(timestamps)
        
        # Try each format until we find one that works well
        for fmt in timestamp_formats:
            try:
                test_parsed = pd.to_datetime(cleaned_timestamps, format=fmt, errors='coerce')
                test_failed_count = test_parsed.isna().sum() - timestamps.isna().sum()
                success_rate = (len(timestamps) - test_failed_count) / len(timestamps)
                
                if success_rate > 0.5:  # At least 50% success rate
                    parsed_series = test_parsed
                    failed_count = test_failed_count
                    successful_format = fmt
                    if success_rate > 0.9:  # Very good success rate, use this format
                        break
            except Exception as e:
                logger.debug(f"Format {fmt} failed: {e}")
                continue
        
        # Fallback to automatic parsing if no format worked well
        if parsed_series is None or failed_count > len(timestamps) * 0.5:
            logger.warning(f"Trying automatic timestamp parsing as fallback")
            parsed_series = pd.to_datetime(cleaned_timestamps, errors='coerce')
            failed_count = parsed_series.isna().sum() - timestamps.isna().sum()
            successful_format = "automatic"
        
        if failed_count > 0:
            logger.warning(f"{failed_count} timestamps failed to parse and were set to NaT (format: {successful_format})")
            
            # Log some failed examples for debugging
            failed_mask = parsed_series.isna() & timestamps.notna()
            if failed_mask.any():
                failed_examples = cleaned_timestamps[failed_mask].head(3).tolist()
                logger.warning(f"Failed timestamp examples: {failed_examples}")
        else:
            logger.info(f"Successfully parsed all timestamps using format: {successful_format}")
        
        # Localize to timezone if naive
        if parsed_series.dt.tz is None:
            try:
                # Try to localize all at once
                parsed_series = parsed_series.dt.tz_localize(timezone)
            except pytz.AmbiguousTimeError:
                # Handle DST transitions by processing individually
                logger.warning("Detected ambiguous times during DST transition, processing individually")
                parsed_series = parsed_series.apply(
                    lambda x: _handle_dst_transition(x, timezone) if pd.notna(x) else x
                )
            except pytz.NonExistentTimeError:
                # Handle non-existent times (spring forward)
                logger.warning("Detected non-existent times during DST transition, processing individually")
                parsed_series = parsed_series.apply(
                    lambda x: _handle_dst_transition(x, timezone) if pd.notna(x) else x
                )
        else:
            # Convert to target timezone if already timezone-aware
            parsed_series = parsed_series.dt.tz_convert(timezone)
        
        success_count = len(parsed_series) - parsed_series.isna().sum()
        logger.info(f"Successfully parsed {success_count} timestamps")
        return parsed_series
        
    except Exception as e:
        logger.error(f"Failed to parse timestamps vectorized, falling back to individual parsing: {e}")
        # Fallback to individual parsing
        return cleaned_timestamps.apply(lambda x: parse_timestamp_with_timezone(x, ts_format, timezone))


def _handle_dst_transition(dt: pd.Timestamp, timezone: str) -> pd.Timestamp:
    """
    Handle DST transition edge cases for individual timestamps
    
    Args:
        dt: Naive pandas Timestamp
        timezone: Target timezone string
        
    Returns:
        Timezone-aware pandas Timestamp
    """
    try:
        tz = pytz.timezone(timezone)
        # Convert to python datetime for pytz handling
        py_dt = dt.to_pydatetime()
        # Localize with DST handling (assume standard time for ambiguous)
        localized = tz.localize(py_dt, is_dst=False)
        return pd.Timestamp(localized)
    except pytz.AmbiguousTimeError:
        # Time exists twice (fall back), choose standard time
        logger.warning(f"Ambiguous time {dt} in {timezone}, choosing standard time")
        tz = pytz.timezone(timezone)
        py_dt = dt.to_pydatetime()
        localized = tz.localize(py_dt, is_dst=False)
        return pd.Timestamp(localized)
    except pytz.NonExistentTimeError:
        # Time doesn't exist (spring forward), shift forward
        logger.warning(f"Non-existent time {dt} in {timezone}, shifting forward 1 hour")
        tz = pytz.timezone(timezone)
        py_dt = dt.to_pydatetime()
        # Add 1 hour and localize
        shifted_dt = py_dt.replace(hour=py_dt.hour + 1)
        localized = tz.localize(shifted_dt, is_dst=True)
        return pd.Timestamp(localized)
    except Exception as e:
        logger.error(f"Failed to handle DST transition for {dt}: {e}")
        return pd.NaT


def validate_timezone(timezone: str) -> bool:
    """
    Validate that a timezone string is valid
    
    Args:
        timezone: Timezone string to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        ZoneInfo(timezone)
        return True
    except Exception:
        try:
            pytz.timezone(timezone)
            return True
        except Exception:
            return False


def validate_timestamp_format(ts_format: str, sample_timestamp: str) -> bool:
    """
    Validate that a timestamp format string works with a sample timestamp
    
    Args:
        ts_format: Format string to validate
        sample_timestamp: Sample timestamp to test parsing
        
    Returns:
        True if format works, False otherwise
    """
    try:
        datetime.strptime(sample_timestamp, ts_format)
        return True
    except Exception:
        return False


def determine_data_validity(df: pd.DataFrame, params: dict) -> Tuple[pd.DataFrame, dict]:
    """
    Determine data validity using available validity columns or numeric range rules
    
    Args:
        df: DataFrame with normalized column names
        params: Dictionary containing validation parameters
        
    Returns:
        Tuple of (DataFrame with is_valid column, validity_stats dict)
    """
    df_with_validity = df.copy()
    validity_stats = {
        'method_used': None,
        'total_rows': len(df),
        'valid_rows': 0,
        'invalid_reasons': {}
    }
    
    # Method 1: Use boolean 'valid' or 'is_valid' column if present
    if 'valid' in df.columns:
        logger.info("Using boolean 'valid' column for validity determination")
        df_with_validity['is_valid'] = df['valid'].fillna(False).astype(bool)
        validity_stats['method_used'] = 'boolean_valid_column'
        validity_stats['valid_rows'] = df_with_validity['is_valid'].sum()
        return df_with_validity, validity_stats
    
    # Method 1b: Use 'is_valid' column if present (common in CSV files)
    if 'is_valid' in df.columns:
        logger.info("Using boolean 'is_valid' column for validity determination")
        # Handle string TRUE/FALSE values
        if df['is_valid'].dtype == 'object':
            # Convert string TRUE/FALSE to boolean
            df_with_validity['is_valid'] = df['is_valid'].astype(str).str.upper().isin(['TRUE', '1', 'YES']).fillna(False)
        else:
            df_with_validity['is_valid'] = df['is_valid'].fillna(False).astype(bool)
        validity_stats['method_used'] = 'boolean_is_valid_column'
        validity_stats['valid_rows'] = df_with_validity['is_valid'].sum()
        return df_with_validity, validity_stats
    
    # Method 2: Use 'valid_code' column if present
    if 'valid_code' in df.columns:
        logger.info("Using 'valid_code' column for validity determination")
        valid_codes_ok = params.get('valid_codes_ok', [])
        if not valid_codes_ok:
            logger.warning("No valid codes specified, treating all as invalid")
            df_with_validity['is_valid'] = False
        else:
            df_with_validity['is_valid'] = df['valid_code'].isin(valid_codes_ok)
        
        validity_stats['method_used'] = 'valid_code_column'
        validity_stats['valid_rows'] = df_with_validity['is_valid'].sum()
        
        # Count invalid reasons by code
        invalid_codes = df[~df_with_validity['is_valid']]['valid_code'].value_counts()
        validity_stats['invalid_reasons'] = invalid_codes.to_dict()
        
        return df_with_validity, validity_stats
    
    # Method 3: Use numeric range validation rules
    logger.info("Using numeric range validation rules for validity determination")
    validity_stats['method_used'] = 'numeric_range_rules'
    
    # Initialize validity as True for all rows
    df_with_validity['is_valid'] = True
    invalid_reasons = {}
    
    # Duration validation
    duration_range = params.get('duration_range_sec', [0, float('inf')])
    if len(duration_range) == 2:
        # Ensure duration column is not categorical for comparison
        if pd.api.types.is_categorical_dtype(df['duration']):
            df['duration'] = df['duration'].astype(float)
        
        duration_invalid = (
            (df['duration'] < duration_range[0]) | 
            (df['duration'] > duration_range[1]) |
            pd.isna(df['duration'])
        )
        df_with_validity.loc[duration_invalid, 'is_valid'] = False
        invalid_reasons['duration_out_of_range'] = duration_invalid.sum()
    
    # Distance validation
    distance_range = params.get('distance_range_m', [0, float('inf')])
    if len(distance_range) == 2:
        # Ensure distance column is not categorical for comparison
        if pd.api.types.is_categorical_dtype(df['distance']):
            df['distance'] = df['distance'].astype(float)
        
        distance_invalid = (
            (df['distance'] < distance_range[0]) | 
            (df['distance'] > distance_range[1]) |
            pd.isna(df['distance'])
        )
        df_with_validity.loc[distance_invalid, 'is_valid'] = False
        invalid_reasons['distance_out_of_range'] = distance_invalid.sum()
    
    # Speed validation
    speed_range = params.get('speed_range_kmh', [0, float('inf')])
    if len(speed_range) == 2:
        # Ensure speed column is not categorical for comparison
        if pd.api.types.is_categorical_dtype(df['speed']):
            df['speed'] = df['speed'].astype(float)
        
        speed_invalid = (
            (df['speed'] < speed_range[0]) | 
            (df['speed'] > speed_range[1]) |
            pd.isna(df['speed'])
        )
        df_with_validity.loc[speed_invalid, 'is_valid'] = False
        invalid_reasons['speed_out_of_range'] = speed_invalid.sum()
    
    validity_stats['valid_rows'] = df_with_validity['is_valid'].sum()
    validity_stats['invalid_reasons'] = invalid_reasons
    
    return df_with_validity, validity_stats


def remove_duplicates(df: pd.DataFrame, params: dict) -> Tuple[pd.DataFrame, dict]:
    """
    Remove duplicates based on DataID or link+timestamp combinations
    
    Args:
        df: DataFrame to deduplicate
        params: Dictionary containing deduplication parameters
        
    Returns:
        Tuple of (deduplicated DataFrame, deduplication_stats dict)
    """
    df_dedup = df.copy()
    dedup_stats = {
        'original_rows': len(df),
        'duplicates_removed': 0,
        'final_rows': len(df),
        'method_used': []
    }
    
    # Method 1: Remove exact duplicates by DataID
    if params.get('remove_data_id_duplicates', True) and 'data_id' in df.columns:
        logger.info("Removing duplicates by DataID")
        initial_count = len(df_dedup)
        df_dedup = df_dedup.drop_duplicates(subset=['data_id'], keep='first')
        data_id_duplicates = initial_count - len(df_dedup)
        dedup_stats['duplicates_removed'] += data_id_duplicates
        dedup_stats['method_used'].append(f'data_id_duplicates: {data_id_duplicates}')
        logger.info(f"Removed {data_id_duplicates} DataID duplicates")
    
    # Method 2: Remove duplicates by link+timestamp
    if params.get('remove_link_timestamp_duplicates', True):
        if 'name' in df.columns and 'timestamp' in df.columns:
            logger.info("Removing duplicates by link+timestamp")
            initial_count = len(df_dedup)
            df_dedup = df_dedup.drop_duplicates(subset=['name', 'timestamp'], keep='first')
            link_timestamp_duplicates = initial_count - len(df_dedup)
            dedup_stats['duplicates_removed'] += link_timestamp_duplicates
            dedup_stats['method_used'].append(f'link_timestamp_duplicates: {link_timestamp_duplicates}')
            logger.info(f"Removed {link_timestamp_duplicates} link+timestamp duplicates")
        else:
            logger.warning("Cannot remove link+timestamp duplicates: missing 'name' or 'timestamp' columns")
    
    dedup_stats['final_rows'] = len(df_dedup)
    
    return df_dedup, dedup_stats


def validate_numeric_ranges(df: pd.DataFrame, column: str, valid_range: List[float]) -> pd.Series:
    """
    Validate that numeric values fall within specified range
    
    Args:
        df: DataFrame containing the column to validate
        column: Column name to validate
        valid_range: List of [min_value, max_value]
        
    Returns:
        Boolean Series indicating which rows are valid
    """
    if column not in df.columns:
        logger.warning(f"Column '{column}' not found for range validation")
        return pd.Series([True] * len(df), index=df.index)
    
    if len(valid_range) != 2:
        logger.warning(f"Invalid range specification for {column}: {valid_range}")
        return pd.Series([True] * len(df), index=df.index)
    
    min_val, max_val = valid_range
    
    # Check for valid numeric values within range
    # Ensure column is not categorical for comparison
    col_data = df[column]
    if pd.api.types.is_categorical_dtype(col_data):
        col_data = col_data.astype(float)
    
    is_valid = (
        pd.notna(col_data) &
        (col_data >= min_val) &
        (col_data <= max_val)
    )
    
    return is_valid


def apply_data_validation_and_cleaning(df: pd.DataFrame, params: dict) -> Tuple[pd.DataFrame, dict]:
    """
    Apply complete data validation and cleaning pipeline
    
    Args:
        df: DataFrame with normalized columns
        params: Dictionary containing all validation parameters
        
    Returns:
        Tuple of (cleaned DataFrame, processing_stats dict)
    """
    processing_stats = {
        'original_rows': len(df),
        'validation_stats': {},
        'deduplication_stats': {},
        'final_rows': 0
    }
    
    logger.info(f"Starting data validation and cleaning for {len(df)} rows")
    
    # Step 1: Determine data validity
    df_with_validity, validity_stats = determine_data_validity(df, params)
    processing_stats['validation_stats'] = validity_stats
    
    # Step 2: Remove duplicates
    df_cleaned, dedup_stats = remove_duplicates(df_with_validity, params)
    processing_stats['deduplication_stats'] = dedup_stats
    
    processing_stats['final_rows'] = len(df_cleaned)
    
    logger.info(f"Data validation and cleaning completed: {processing_stats['original_rows']} -> {processing_stats['final_rows']} rows")
    logger.info(f"Valid rows: {validity_stats['valid_rows']}/{validity_stats['total_rows']} ({validity_stats['valid_rows']/validity_stats['total_rows']*100:.1f}%)")
    
    return df_cleaned, processing_stats


def validate_and_normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validate required columns exist and normalize all column names
    
    Args:
        df: Input DataFrame to validate and normalize
        
    Returns:
        DataFrame with validated and normalized columns
        
    Raises:
        ValueError: If required columns are missing
    """
    # First validate that required columns exist
    is_valid, missing_columns = validate_csv_columns(df)
    
    if not is_valid:
        missing_cols_str = ', '.join(missing_columns)
        error_msg = (
            f"Missing required columns in CSV file: {missing_cols_str}. "
            f"Required columns are: {', '.join(REQUIRED_COLUMNS)}"
        )
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Normalize column names
    df_normalized = normalize_column_names(df)
    
    logger.info(f"Successfully validated and normalized {len(df.columns)} columns")
    return df_normalized


def optimize_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Optimize DataFrame dtypes for memory efficiency and performance
    
    Args:
        df: DataFrame to optimize
        
    Returns:
        DataFrame with optimized dtypes
    """
    df_optimized = df.copy()
    
    # Optimize numeric columns
    for col in df_optimized.select_dtypes(include=['int64']).columns:
        col_min = df_optimized[col].min()
        col_max = df_optimized[col].max()
        
        if col_min >= 0:  # Unsigned integers
            if col_max < 255:
                df_optimized[col] = df_optimized[col].astype('uint8')
            elif col_max < 65535:
                df_optimized[col] = df_optimized[col].astype('uint16')
            elif col_max < 4294967295:
                df_optimized[col] = df_optimized[col].astype('uint32')
        else:  # Signed integers
            if col_min >= -128 and col_max <= 127:
                df_optimized[col] = df_optimized[col].astype('int8')
            elif col_min >= -32768 and col_max <= 32767:
                df_optimized[col] = df_optimized[col].astype('int16')
            elif col_min >= -2147483648 and col_max <= 2147483647:
                df_optimized[col] = df_optimized[col].astype('int32')
    
    # Optimize float columns
    for col in df_optimized.select_dtypes(include=['float64']).columns:
        # Check if we can use float32 without losing precision
        if df_optimized[col].notna().any():
            try:
                float32_version = df_optimized[col].astype('float32')
                # Check if conversion is lossless for non-null values
                mask = df_optimized[col].notna()
                if np.allclose(df_optimized.loc[mask, col], float32_version.loc[mask], equal_nan=True):
                    df_optimized[col] = float32_version
            except (ValueError, OverflowError):
                # Keep as float64 if conversion fails
                pass
    
    # Optimize string columns to category if they have low cardinality
    # Exclude columns that are used in filtering operations to avoid categorical comparison issues
    exclude_from_categorical = {
        'day_in_week', 'day_type', 'daytype', 'link_id', 'name',
        'duration', 'distance', 'speed', 'date', 'timestamp',  # Numeric/date columns
        'data_id', 'segment_id', 'route_alternative'  # ID columns that might be filtered
    }
    
    for col in df_optimized.select_dtypes(include=['object']).columns:
        if df_optimized[col].dtype == 'object' and col not in exclude_from_categorical:
            unique_count = df_optimized[col].nunique()
            total_count = len(df_optimized[col])
            
            # Convert to category if cardinality is less than 50% of total rows
            # Also ensure the column doesn't contain numeric-like data that might be compared
            if unique_count < total_count * 0.5 and unique_count > 1:
                try:
                    df_optimized[col] = df_optimized[col].astype('category')
                except Exception as e:
                    logger.debug(f"Failed to convert {col} to category: {e}")
                    # Keep as object if conversion fails
    
    logger.info("DataFrame dtypes optimized for memory efficiency")
    return df_optimized




def resolve_hebrew_encoding(raw_data: bytes, detected_encoding: Optional[str]) -> str:
    """Normalize detector output for Hebrew datasets frequently misclassified as Greek."""
    if not detected_encoding:
        return 'cp1255'

    normalized = detected_encoding.lower().replace('_', '-')
    greek_aliases = {'iso-8859-7', 'iso8859-7', 'windows-1253', 'cp1253', 'greek'}

    if normalized in greek_aliases:
        hebrew_text = raw_data.decode('cp1255', errors='ignore')
        greek_text = raw_data.decode(detected_encoding, errors='ignore')
        hebrew_chars = sum(1 for ch in hebrew_text if 0x0590 <= ord(ch) <= 0x05FF)
        greek_chars = sum(1 for ch in greek_text if 0x0370 <= ord(ch) <= 0x03FF)

        if hebrew_chars and hebrew_chars >= greek_chars:
            logger.info(
                "Overriding detected encoding '%s' with cp1255 based on Hebrew character frequency",
                detected_encoding
            )
            return 'cp1255'

    return detected_encoding

def detect_file_encoding(file_path: str, sample_size: int = 8192) -> str:
    """
    Detect file encoding by trying common encodings
    
    Args:
        file_path: Path to file
        sample_size: Number of bytes to read for detection
        
    Returns:
        Detected encoding string
    """
    # Common encodings to try, in order of preference
    encodings_to_try = [
        'utf-8',
        'utf-8-sig',  # UTF-8 with BOM
        'cp1255',     # Hebrew Windows encoding
        'iso-8859-8', # Hebrew ISO encoding
        'cp1252',     # Western European Windows encoding
        'latin1',     # Fallback that accepts any byte sequence
    ]
    
    # Try to detect using chardet if available
    try:
        import chardet
        with open(file_path, 'rb') as f:
            raw_data = f.read(sample_size)
        
        detected = chardet.detect(raw_data)
        if detected and detected.get('encoding'):
            candidate = detected['encoding']
            confidence = detected.get('confidence') or 0.0
            resolved = resolve_hebrew_encoding(raw_data, candidate)

            if resolved.lower() != candidate.lower():
                logger.info(
                    "Detected encoding %s (confidence %.2f) overridden to %s for Hebrew dataset",
                    candidate, confidence, resolved
                )
                return resolved

            if confidence > 0.7:
                logger.info("Detected encoding: %s (confidence: %.2f)", resolved, confidence)
                return resolved
    except ImportError:
        logger.debug("chardet not available, using fallback encoding detection")
    except Exception as e:
        logger.debug(f"chardet detection failed: {e}")
    
    # Fallback: try encodings manually
    for encoding in encodings_to_try:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                # Try to read a sample
                sample = f.read(sample_size)
                # If we can read without errors, this encoding works
                logger.info(f"Using encoding: {encoding}")
                return encoding
        except UnicodeDecodeError:
            continue
        except Exception:
            continue
    
    # Last resort: use latin1 which accepts any byte sequence
    logger.warning("Could not detect encoding reliably, using latin1 as fallback")
    return 'latin1'


def detect_csv_format(file_path: str, sample_size: int = 1000) -> dict:
    """
    Detect CSV format parameters (decimal separator, delimiter, encoding) from file sample
    
    Args:
        file_path: Path to CSV file
        sample_size: Number of bytes to sample for detection
        
    Returns:
        Dictionary with detected format parameters
    """
    format_params = {
        'delimiter': ',',
        'decimal': '.',
        'encoding': 'utf-8'
    }
    
    # First, detect encoding
    encoding = detect_file_encoding(file_path)
    format_params['encoding'] = encoding
    
    try:
        # Read a small sample of the file with detected encoding
        with open(file_path, 'r', encoding=encoding, errors='replace') as f:
            sample = f.read(sample_size)
        
        # Count potential delimiters
        delimiter_counts = {
            ',': sample.count(','),
            ';': sample.count(';'),
            '\t': sample.count('\t'),
            '|': sample.count('|')
        }
        
        # Choose delimiter with highest count
        best_delimiter = max(delimiter_counts, key=delimiter_counts.get)
        if delimiter_counts[best_delimiter] > 0:
            format_params['delimiter'] = best_delimiter
        
        # Detect decimal separator by looking for patterns
        # Look for numbers with decimal points vs commas
        import re
        decimal_point_pattern = r'\d+\.\d+'
        decimal_comma_pattern = r'\d+,\d+'
        
        decimal_points = len(re.findall(decimal_point_pattern, sample))
        decimal_commas = len(re.findall(decimal_comma_pattern, sample))
        
        # If we find more decimal commas and delimiter is not comma, use comma as decimal
        if decimal_commas > decimal_points and format_params['delimiter'] != ',':
            format_params['decimal'] = ','
        
        logger.info(f"Detected CSV format: delimiter='{format_params['delimiter']}', decimal='{format_params['decimal']}'")
        
    except Exception as e:
        logger.warning(f"Could not detect CSV format, using defaults: {e}")
    
    return format_params


def configure_chunk_size(file_path: str, available_memory_gb: float = 2.0) -> int:
    """
    Calculate optimal chunk size based on file size and available memory
    
    Args:
        file_path: Path to CSV file
        available_memory_gb: Available memory in GB for processing
        
    Returns:
        Recommended chunk size in rows
    """
    try:
        # Get file size
        file_size_bytes = Path(file_path).stat().st_size
        file_size_mb = file_size_bytes / (1024 * 1024)
        
        # Estimate rows per MB (rough estimate: ~1000 rows per MB for typical CSV)
        estimated_rows_per_mb = 1000
        estimated_total_rows = int(file_size_mb * estimated_rows_per_mb)
        
        # Calculate chunk size to use ~25% of available memory
        memory_budget_mb = available_memory_gb * 1024 * 0.25
        chunk_size = int((memory_budget_mb / file_size_mb) * estimated_total_rows)
        
        # Set reasonable bounds
        min_chunk_size = 1000
        max_chunk_size = 100000
        
        chunk_size = max(min_chunk_size, min(chunk_size, max_chunk_size))
        
        logger.info(f"File size: {file_size_mb:.1f}MB, Estimated rows: {estimated_total_rows:,}, Recommended chunk size: {chunk_size:,}")
        
        return chunk_size
        
    except Exception as e:
        logger.warning(f"Could not calculate optimal chunk size: {e}")
        return 10000  # Default fallback


def read_csv_chunked(file_path: str, params: dict) -> Tuple[pd.DataFrame, dict]:
    """
    Read CSV file using chunked processing for memory efficiency
    
    Args:
        file_path: Path to CSV file
        params: Dictionary containing CSV reading parameters
        
    Returns:
        Tuple of (combined DataFrame from all chunks, validation_stats dict)
    """
    logger.info(f"Starting chunked CSV reading from: {file_path}")
    
    # Get CSV format parameters
    csv_format = detect_csv_format(file_path)
    
    # Override with user-specified parameters
    delimiter = params.get('delimiter', csv_format['delimiter'])
    decimal = params.get('decimal', csv_format['decimal'])
    encoding = params.get('encoding', csv_format['encoding'])
    
    # Get chunk size
    chunk_size = params.get('chunk_size')
    if chunk_size is None:
        available_memory = params.get('available_memory_gb', 2.0)
        chunk_size = configure_chunk_size(file_path, available_memory)
    
    logger.info(f"Reading CSV with: delimiter='{delimiter}', decimal='{decimal}', chunk_size={chunk_size:,}")
    
    # Initialize list to store processed chunks and validation stats
    processed_chunks = []
    total_rows_processed = 0
    chunk_count = 0
    combined_validation_stats = {
        'total_rows': 0,
        'valid_rows': 0,
        'invalid_reasons': {},
        'method_used': None,
        'chunks_processed': 0
    }
    
    try:
        # Read CSV in chunks
        chunk_reader = pd.read_csv(
            file_path,
            delimiter=delimiter,
            decimal=decimal,
            encoding=encoding,
            chunksize=chunk_size,
            low_memory=False,  # Let pandas infer dtypes
            na_values=['', 'NA', 'NULL', 'null', 'NaN', 'nan'],
            keep_default_na=True
        )
        
        for chunk_num, chunk in enumerate(chunk_reader, 1):
            logger.info(f"Processing chunk {chunk_num}: {len(chunk):,} rows")
            
            # Validate and normalize columns for this chunk
            try:
                # Step 1: Validate and normalize column names
                chunk_normalized = validate_and_normalize_columns(chunk)
                
                # Step 2: Apply data validation and cleaning (skip column validation since already done)
                chunk_with_validity, validity_stats = determine_data_validity(chunk_normalized, params)
                chunk_cleaned, dedup_stats = remove_duplicates(chunk_with_validity, params)
                
                # Accumulate validation statistics
                combined_validation_stats['total_rows'] += validity_stats['total_rows']
                combined_validation_stats['valid_rows'] += validity_stats['valid_rows']
                combined_validation_stats['method_used'] = validity_stats['method_used']
                combined_validation_stats['chunks_processed'] += 1
                
                # Merge invalid reasons
                for reason, count in validity_stats.get('invalid_reasons', {}).items():
                    combined_validation_stats['invalid_reasons'][reason] = (
                        combined_validation_stats['invalid_reasons'].get(reason, 0) + count
                    )
                
                # Step 3: Apply temporal enhancements
                chunk_enhanced = apply_temporal_enhancements(chunk_cleaned, params)
                
                # Step 4: Optimize dtypes for memory efficiency
                chunk_optimized = optimize_dtypes(chunk_enhanced)
                
                processed_chunks.append(chunk_optimized)
                total_rows_processed += len(chunk_optimized)
                chunk_count += 1
                
                logger.info(f"Chunk {chunk_num} processed: {len(chunk_optimized):,} rows after cleaning")
                
            except Exception as e:
                logger.error(f"Error processing chunk {chunk_num}: {e}")
                # Continue with next chunk rather than failing completely
                continue
        
        # Combine all processed chunks
        if processed_chunks:
            logger.info(f"Combining {len(processed_chunks)} processed chunks...")
            combined_df = pd.concat(processed_chunks, ignore_index=True)
            
            # Final dtype optimization on combined data
            combined_df = optimize_dtypes(combined_df)
            
            logger.info(f"Chunked CSV reading completed: {total_rows_processed:,} total rows processed")
            logger.info(f"Validation summary: {combined_validation_stats['valid_rows']:,}/{combined_validation_stats['total_rows']:,} valid rows ({combined_validation_stats['valid_rows']/combined_validation_stats['total_rows']*100:.1f}%)")
            return combined_df, combined_validation_stats
        else:
            logger.error("No chunks were successfully processed")
            return pd.DataFrame(), combined_validation_stats
            
    except Exception as e:
        logger.error(f"Error during chunked CSV reading: {e}")
        raise


def run_pipeline(params: dict) -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Main processing pipeline function that integrates all processing components
    
    Args:
        params: Dictionary containing all processing parameters including:
            - input_file_path: Path to input CSV file
            - output_dir: Directory for output files
            - All other processing parameters for validation, filtering, aggregation
        
    Returns:
        tuple: (hourly_df, weekly_df, output_files_dict)
        
    Raises:
        ValueError: If required parameters are missing
        FileNotFoundError: If input file doesn't exist
        Exception: For other processing errors with proper context
    """
    processing_start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("PROCESSING PIPELINE STARTED")
    logger.info("=" * 60)
    
    # Initialize return values
    hourly_df = pd.DataFrame()
    weekly_df = pd.DataFrame()
    output_files = {}
    raw_df = pd.DataFrame()
    validation_stats = {}
    
    try:
        # Step 1: Validate required parameters
        logger.info("Step 1: Validating parameters...")
        _validate_pipeline_parameters(params)
        
        file_path = params['input_file_path']
        output_dir = params.get('output_dir', '.')
        
        # Ensure output directory exists
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directory: {output_dir}")
        
        # Step 2: Read and process CSV data using chunked reading
        logger.info("Step 2: Reading and processing CSV data...")
        logger.info(f"Input file: {file_path}")
        
        if not Path(file_path).exists():
            raise FileNotFoundError(f"Input file not found: {file_path}")
        
        # Read CSV data with chunked processing and validation
        raw_df, validation_stats = read_csv_chunked(file_path, params)
        
        if raw_df.empty:
            logger.warning("No data loaded from CSV file")
            return pd.DataFrame(), pd.DataFrame(), {}
        
        logger.info(f"Loaded {len(raw_df):,} rows from CSV file")
        
        # Step 3: Apply filtering and data selection
        logger.info("Step 3: Applying filtering and data selection...")
        df_filtered = apply_filtering_and_selection(raw_df, params)
        
        if df_filtered.empty:
            logger.warning("No data remaining after filtering")
            return pd.DataFrame(), pd.DataFrame(), {}
        
        logger.info(f"After filtering: {len(df_filtered):,} rows remaining ({len(df_filtered)/len(raw_df)*100:.1f}% retained)")
        
        # Step 4: Create hourly aggregation
        logger.info("Step 4: Creating hourly aggregation...")
        hourly_df = create_hourly_aggregation(df_filtered, params)
        
        if hourly_df.empty:
            logger.warning("No hourly aggregation data generated")
        else:
            logger.info(f"Created hourly aggregation: {len(hourly_df):,} hour-link combinations")
        
        # Step 5: Create weekly hourly profile
        logger.info("Step 5: Creating weekly hourly profile...")
        if not hourly_df.empty:
            weekly_df = create_weekly_profile(hourly_df, params)
            if weekly_df.empty:
                logger.warning("No weekly profile data generated")
            else:
                logger.info(f"Created weekly profile: {len(weekly_df):,} weekly patterns")
        else:
            logger.warning("Skipping weekly profile creation - no hourly data available")
        
        # Step 6: Write all output files
        logger.info("Step 6: Writing output files...")
        output_files = write_all_output_files(
            raw_df=raw_df,
            hourly_df=hourly_df, 
            weekly_df=weekly_df,
            validation_stats=validation_stats,
            params=params,
            processing_start_time=processing_start_time,
            output_dir=output_dir
        )
        
        processing_end_time = datetime.now()
        processing_duration = processing_end_time - processing_start_time
        
        logger.info("=" * 60)
        logger.info("PROCESSING PIPELINE COMPLETED SUCCESSFULLY")
        logger.info(f"Total processing time: {processing_duration}")
        logger.info(f"Output files generated: {len(output_files)}")
        for file_type, file_path in output_files.items():
            logger.info(f"  - {file_type}: {file_path}")
        logger.info("=" * 60)
        
        return hourly_df, weekly_df, output_files
        
    except Exception as e:
        processing_end_time = datetime.now()
        processing_duration = processing_end_time - processing_start_time
        
        logger.error("=" * 60)
        logger.error("PROCESSING PIPELINE FAILED")
        logger.error(f"Error: {str(e)}")
        logger.error(f"Processing time before failure: {processing_duration}")
        logger.error("=" * 60)
        
        # Try to write error log if possible
        try:
            output_dir = params.get('output_dir', '.')
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            error_log_path = Path(output_dir) / 'processing_error.log'
            
            with open(error_log_path, 'w') as f:
                f.write(f"Processing Pipeline Error Report\n")
                f.write(f"Generated: {datetime.now().isoformat()}\n")
                f.write(f"Processing duration: {processing_duration}\n")
                f.write(f"Error: {str(e)}\n")
                f.write(f"Error type: {type(e).__name__}\n")
                
                # Add context information
                f.write(f"\nContext Information:\n")
                f.write(f"Input file: {params.get('input_file_path', 'Not specified')}\n")
                f.write(f"Output directory: {params.get('output_dir', 'Not specified')}\n")
                f.write(f"Raw data rows: {len(raw_df) if not raw_df.empty else 0}\n")
                f.write(f"Hourly data rows: {len(hourly_df) if not hourly_df.empty else 0}\n")
                f.write(f"Weekly data rows: {len(weekly_df) if not weekly_df.empty else 0}\n")
            
            logger.info(f"Error log written to: {error_log_path}")
            
        except Exception as log_error:
            logger.error(f"Failed to write error log: {log_error}")
        
        # Re-raise the original exception
        raise


def _validate_pipeline_parameters(params: dict) -> None:
    """
    Validate that all required pipeline parameters are present and valid
    
    Args:
        params: Dictionary of parameters to validate
        
    Raises:
        ValueError: If required parameters are missing or invalid
    """
    required_params = ['input_file_path']
    missing_params = [param for param in required_params if param not in params or params[param] is None]
    
    if missing_params:
        raise ValueError(f"Missing required parameters: {', '.join(missing_params)}")
    
    # Validate file path exists
    input_file = params['input_file_path']
    if not isinstance(input_file, (str, Path)):
        raise ValueError(f"input_file_path must be a string or Path, got {type(input_file)}")
    
    # Validate output directory is writable if specified
    output_dir = params.get('output_dir', '.')
    try:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise ValueError(f"Cannot create or access output directory '{output_dir}': {e}")
    
    # Validate numeric parameters if present
    numeric_params = {
        'chunk_size': (int, 1, 1000000),
        'min_valid_per_hour': (int, 0, 1000),
        'available_memory_gb': (float, 0.1, 100.0)
    }
    
    for param_name, (param_type, min_val, max_val) in numeric_params.items():
        if param_name in params and params[param_name] is not None:
            value = params[param_name]
            if not isinstance(value, param_type):
                raise ValueError(f"{param_name} must be {param_type.__name__}, got {type(value)}")
            if not (min_val <= value <= max_val):
                raise ValueError(f"{param_name} must be between {min_val} and {max_val}, got {value}")
    
    # Validate timezone if specified
    if 'tz' in params and params['tz']:
        if not validate_timezone(params['tz']):
            raise ValueError(f"Invalid timezone: {params['tz']}")
    
    logger.info("All pipeline parameters validated successfully")


def write_all_output_files(raw_df: pd.DataFrame, hourly_df: pd.DataFrame, weekly_df: pd.DataFrame,
                          validation_stats: dict, params: dict, processing_start_time: datetime,
                          output_dir: str) -> Dict[str, str]:
    """
    Write all required and optional output files to specified output directory
    
    Args:
        raw_df: Original processed DataFrame
        hourly_df: Hourly aggregation DataFrame
        weekly_df: Weekly profile DataFrame
        validation_stats: Statistics from data validation
        params: Processing parameters
        processing_start_time: When processing started
        output_dir: Directory to write output files
        
    Returns:
        Dictionary mapping output type to file path for GUI download links
    """
    output_files = {}
    processing_end_time = datetime.now()
    
    logger.info(f"Writing output files to: {output_dir}")
    
    try:
        # Required Output 1: hourly_agg.csv
        if not hourly_df.empty:
            hourly_output_path = Path(output_dir) / 'hourly_agg.csv'
            if write_hourly_aggregation_csv(hourly_df, str(hourly_output_path)):
                output_files['hourly_agg'] = str(hourly_output_path)
                logger.info(f"Written: hourly_agg.csv ({len(hourly_df):,} rows)")
            else:
                logger.error("✗ Failed to write hourly_agg.csv")
        else:
            logger.warning("Skipping hourly_agg.csv - no data available")
        
        # Required Output 2: weekly_hourly_profile.csv
        if not weekly_df.empty:
            weekly_output_path = Path(output_dir) / 'weekly_hourly_profile.csv'
            if write_weekly_hourly_profile_csv(weekly_df, str(weekly_output_path)):
                output_files['weekly_hourly_profile'] = str(weekly_output_path)
                logger.info(f"Written: weekly_hourly_profile.csv ({len(weekly_df):,} rows)")
            else:
                logger.error("✗ Failed to write weekly_hourly_profile.csv")
        else:
            logger.warning("Skipping weekly_hourly_profile.csv - no data available")
        
        # Optional Output 3: Quality reports (if enabled)
        if params.get('generate_quality_reports', True) and not raw_df.empty and not hourly_df.empty:
            try:
                quality_files = write_quality_reports(raw_df, hourly_df, validation_stats, output_dir)
                output_files.update(quality_files)
                logger.info(f"Written: {len(quality_files)} quality report files")
            except Exception as e:
                logger.error(f"✗ Failed to write quality reports: {e}")
        
        # Optional Output 4: Processing log and configuration
        try:
            log_config_files = write_processing_log_and_config(
                raw_df, hourly_df, weekly_df, validation_stats, params,
                processing_start_time, processing_end_time, output_dir
            )
            output_files.update(log_config_files)
            logger.info(f"Written: processing log and configuration files")
        except Exception as e:
            logger.error(f"✗ Failed to write processing log/config: {e}")
        
        # Optional Output 5: Parquet files for faster downstream processing
        if params.get('write_parquet_output', False):
            try:
                parquet_files = write_parquet_outputs(hourly_df, weekly_df, output_dir)
                output_files.update(parquet_files)
                logger.info(f"Written: {len(parquet_files)} Parquet files")
            except Exception as e:
                logger.error(f"✗ Failed to write Parquet files: {e}")
        
        # Optional Output 6: Data preview files for GUI
        if params.get('write_preview_files', True):
            try:
                preview_files = write_preview_files(raw_df, hourly_df, weekly_df, output_dir)
                output_files.update(preview_files)
                logger.info(f"Written: {len(preview_files)} preview files")
            except Exception as e:
                logger.error(f"✗ Failed to write preview files: {e}")
        
        logger.info(f"Output file writing completed: {len(output_files)} files generated")
        return output_files
        
    except Exception as e:
        logger.error(f"Error during output file writing: {e}")
        # Return whatever files were successfully written
        return output_files


def write_parquet_outputs(hourly_df: pd.DataFrame, weekly_df: pd.DataFrame, output_dir: str) -> Dict[str, str]:
    """
    Write Parquet files for faster downstream processing
    
    Args:
        hourly_df: Hourly aggregation DataFrame
        weekly_df: Weekly profile DataFrame
        output_dir: Output directory
        
    Returns:
        Dictionary of written Parquet file paths
    """
    parquet_files = {}
    
    try:
        # Write hourly aggregation as Parquet
        if not hourly_df.empty:
            hourly_parquet_path = Path(output_dir) / 'hourly_agg.parquet'
            hourly_df.to_parquet(hourly_parquet_path, index=False, engine='pyarrow')
            parquet_files['hourly_agg_parquet'] = str(hourly_parquet_path)
        
        # Write weekly profile as Parquet
        if not weekly_df.empty:
            weekly_parquet_path = Path(output_dir) / 'weekly_hourly_profile.parquet'
            weekly_df.to_parquet(weekly_parquet_path, index=False, engine='pyarrow')
            parquet_files['weekly_hourly_profile_parquet'] = str(weekly_parquet_path)
        
    except ImportError:
        logger.warning("PyArrow not available, skipping Parquet output")
    except Exception as e:
        logger.error(f"Error writing Parquet files: {e}")
    
    return parquet_files


def write_preview_files(raw_df: pd.DataFrame, hourly_df: pd.DataFrame, weekly_df: pd.DataFrame, 
                       output_dir: str, preview_rows: int = 100) -> Dict[str, str]:
    """
    Write preview CSV files with limited rows for GUI display
    
    Args:
        raw_df: Raw processed DataFrame
        hourly_df: Hourly aggregation DataFrame
        weekly_df: Weekly profile DataFrame
        output_dir: Output directory
        preview_rows: Number of rows to include in preview
        
    Returns:
        Dictionary of written preview file paths
    """
    preview_files = {}
    
    try:
        # Write raw data preview
        if not raw_df.empty:
            raw_preview_path = Path(output_dir) / 'raw_data_preview.csv'
            preview_df = raw_df.head(preview_rows)
            preview_df.to_csv(raw_preview_path, index=False)
            preview_files['raw_data_preview'] = str(raw_preview_path)
        
        # Write hourly aggregation preview
        if not hourly_df.empty:
            hourly_preview_path = Path(output_dir) / 'hourly_agg_preview.csv'
            preview_df = hourly_df.head(preview_rows)
            preview_df.to_csv(hourly_preview_path, index=False)
            preview_files['hourly_agg_preview'] = str(hourly_preview_path)
        
        # Write weekly profile preview
        if not weekly_df.empty:
            weekly_preview_path = Path(output_dir) / 'weekly_profile_preview.csv'
            preview_df = weekly_df.head(preview_rows)
            preview_df.to_csv(weekly_preview_path, index=False)
            preview_files['weekly_profile_preview'] = str(weekly_preview_path)
        
    except Exception as e:
        logger.error(f"Error writing preview files: {e}")
    
    return preview_files


def apply_filtering_and_selection(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """
    Apply filtering and data selection based on configured parameters
    
    Args:
        df: DataFrame to filter
        params: Dictionary containing filtering parameters
        
    Returns:
        Filtered DataFrame
    """
    if df.empty:
        return df
    
    logger.info(f"Starting filtering and selection on {len(df):,} rows")
    df_filtered = df.copy()
    
    # Apply date range filtering
    df_filtered = apply_date_range_filter(df_filtered, params)
    
    # Apply weekday filtering
    df_filtered = apply_weekday_filter(df_filtered, params)
    
    # Apply hour filtering
    df_filtered = apply_hour_filter(df_filtered, params)
    
    # Apply link filtering (whitelist/blacklist)
    df_filtered = apply_link_filter(df_filtered, params)
    
    # Apply quick preset filters
    df_filtered = apply_preset_filters(df_filtered, params)
    
    logger.info(f"Filtering completed: {len(df):,} -> {len(df_filtered):,} rows ({len(df_filtered)/len(df)*100:.1f}% retained)")
    
    return df_filtered


def apply_date_range_filter(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """
    Filter data by date range (start_date, end_date inclusive)
    
    Args:
        df: DataFrame with date column
        params: Parameters containing start_date and end_date
        
    Returns:
        Filtered DataFrame
    """
    if 'date' not in df.columns:
        logger.warning("Cannot apply date range filter: 'date' column not found")
        return df
    
    df_filtered = df.copy()
    initial_count = len(df_filtered)
    
    # Apply start_date filter
    start_date = params.get('start_date')
    if start_date is not None:
        if isinstance(start_date, str):
            start_date = pd.to_datetime(start_date).date()
        # Ensure date column is not categorical for comparison
        if pd.api.types.is_categorical_dtype(df_filtered['date']):
            df_filtered['date'] = pd.to_datetime(df_filtered['date']).dt.date
        df_filtered = df_filtered[df_filtered['date'] >= start_date]
        logger.info(f"Applied start_date filter ({start_date}): {len(df_filtered):,} rows remaining")
    
    # Apply end_date filter
    end_date = params.get('end_date')
    if end_date is not None:
        if isinstance(end_date, str):
            end_date = pd.to_datetime(end_date).date()
        # Ensure date column is not categorical for comparison
        if pd.api.types.is_categorical_dtype(df_filtered['date']):
            df_filtered['date'] = pd.to_datetime(df_filtered['date']).dt.date
        df_filtered = df_filtered[df_filtered['date'] <= end_date]
        logger.info(f"Applied end_date filter ({end_date}): {len(df_filtered):,} rows remaining")
    
    if start_date or end_date:
        filtered_count = len(df_filtered)
        logger.info(f"Date range filtering: {initial_count:,} -> {filtered_count:,} rows")
    
    return df_filtered


def apply_weekday_filter(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """
    Filter data by weekday indices (Monday=0, Sunday=6)
    
    Args:
        df: DataFrame with weekday_index column
        params: Parameters containing weekday_include list
        
    Returns:
        Filtered DataFrame
    """
    weekday_include = params.get('weekday_include')
    if weekday_include is None or 'weekday_index' not in df.columns:
        return df
    
    if not isinstance(weekday_include, (list, tuple)):
        logger.warning(f"weekday_include must be a list, got {type(weekday_include)}")
        return df
    
    # Validate weekday indices (0-6)
    valid_weekdays = [w for w in weekday_include if isinstance(w, int) and 0 <= w <= 6]
    if len(valid_weekdays) != len(weekday_include):
        logger.warning(f"Invalid weekday indices filtered out. Valid range: 0-6 (Monday-Sunday)")
    
    if not valid_weekdays:
        logger.warning("No valid weekday indices specified")
        return df
    
    initial_count = len(df)
    df_filtered = df[df['weekday_index'].isin(valid_weekdays)]
    
    weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    included_names = [weekday_names[i] for i in valid_weekdays]
    
    logger.info(f"Weekday filtering ({', '.join(included_names)}): {initial_count:,} -> {len(df_filtered):,} rows")
    
    return df_filtered


def apply_hour_filter(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """
    Filter data by hour of day (0-23)
    
    Args:
        df: DataFrame with hour_of_day column
        params: Parameters containing hours_include list
        
    Returns:
        Filtered DataFrame
    """
    hours_include = params.get('hours_include')
    if hours_include is None or 'hour_of_day' not in df.columns:
        return df
    
    if not isinstance(hours_include, (list, tuple)):
        logger.warning(f"hours_include must be a list, got {type(hours_include)}")
        return df
    
    # Validate hour indices (0-23)
    valid_hours = [h for h in hours_include if isinstance(h, int) and 0 <= h <= 23]
    if len(valid_hours) != len(hours_include):
        logger.warning(f"Invalid hour indices filtered out. Valid range: 0-23")
    
    if not valid_hours:
        logger.warning("No valid hour indices specified")
        return df
    
    initial_count = len(df)
    df_filtered = df[df['hour_of_day'].isin(valid_hours)]
    
    logger.info(f"Hour filtering (hours {min(valid_hours)}-{max(valid_hours)}): {initial_count:,} -> {len(df_filtered):,} rows")
    
    return df_filtered


def apply_link_filter(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """
    Apply link whitelist/blacklist filtering
    
    Args:
        df: DataFrame with name column (used as link_id)
        params: Parameters containing whitelist_links and blacklist_links
        
    Returns:
        Filtered DataFrame
    """
    if 'name' not in df.columns:
        logger.warning("Cannot apply link filter: 'name' column not found")
        return df
    
    df_filtered = df.copy()
    initial_count = len(df_filtered)
    
    # Apply whitelist (include only specified links)
    whitelist_links = params.get('whitelist_links')
    if whitelist_links:
        if isinstance(whitelist_links, str):
            # Parse comma-separated string
            whitelist_links = [link.strip() for link in whitelist_links.split(',') if link.strip()]
        
        if whitelist_links:
            df_filtered = df_filtered[df_filtered['name'].isin(whitelist_links)]
            logger.info(f"Whitelist filtering ({len(whitelist_links)} links): {initial_count:,} -> {len(df_filtered):,} rows")
            initial_count = len(df_filtered)
    
    # Apply blacklist (exclude specified links)
    blacklist_links = params.get('blacklist_links')
    if blacklist_links:
        if isinstance(blacklist_links, str):
            # Parse comma-separated string
            blacklist_links = [link.strip() for link in blacklist_links.split(',') if link.strip()]
        
        if blacklist_links:
            df_filtered = df_filtered[~df_filtered['name'].isin(blacklist_links)]
            logger.info(f"Blacklist filtering ({len(blacklist_links)} links): {initial_count:,} -> {len(df_filtered):,} rows")
    
    return df_filtered


def apply_preset_filters(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """
    Apply quick preset filters (weekday_only, weekend_only, holiday_only)
    
    Args:
        df: DataFrame with daytype or weekday_index columns
        params: Parameters containing preset filter flags
        
    Returns:
        Filtered DataFrame
    """
    df_filtered = df.copy()
    initial_count = len(df_filtered)
    
    # Apply weekday_only preset
    if params.get('weekday_only', False):
        if 'daytype' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['daytype'] == 'weekday']
            logger.info(f"Weekday-only preset: {initial_count:,} -> {len(df_filtered):,} rows")
        elif 'weekday_index' in df_filtered.columns:
            # Monday=0 to Friday=4
            df_filtered = df_filtered[df_filtered['weekday_index'].isin([0, 1, 2, 3, 4])]
            logger.info(f"Weekday-only preset (Mon-Fri): {initial_count:,} -> {len(df_filtered):,} rows")
        else:
            logger.warning("Cannot apply weekday_only preset: no daytype or weekday_index column")
        initial_count = len(df_filtered)
    
    # Apply weekend_only preset
    if params.get('weekend_only', False):
        if 'daytype' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['daytype'] == 'weekend']
            logger.info(f"Weekend-only preset: {initial_count:,} -> {len(df_filtered):,} rows")
        elif 'weekday_index' in df_filtered.columns:
            # Saturday=5, Sunday=6
            df_filtered = df_filtered[df_filtered['weekday_index'].isin([5, 6])]
            logger.info(f"Weekend-only preset (Sat-Sun): {initial_count:,} -> {len(df_filtered):,} rows")
        else:
            logger.warning("Cannot apply weekend_only preset: no daytype or weekday_index column")
        initial_count = len(df_filtered)
    
    # Apply holiday_only preset
    if params.get('holiday_only', False):
        if 'daytype' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['daytype'] == 'holiday']
            logger.info(f"Holiday-only preset: {initial_count:,} -> {len(df_filtered):,} rows")
        else:
            logger.warning("Cannot apply holiday_only preset: no daytype column")
    
    return df_filtered


def validate_and_clean_data(df_chunk: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Apply validation rules and data cleaning to a chunk"""
    # Step 1: Validate and normalize column names
    df_normalized = validate_and_normalize_columns(df_chunk)
    
    # Step 2: Apply data validation and cleaning
    df_cleaned, processing_stats = apply_data_validation_and_cleaning(df_normalized, params)
    
    return df_cleaned


def apply_temporal_enhancements(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Add time-based columns and holiday classifications"""
    if df.empty:
        return df
    
    df_enhanced = df.copy()
    
    # Ensure timestamp column exists and is parsed
    if 'timestamp' not in df_enhanced.columns:
        logger.warning("No timestamp column found for temporal enhancements")
        return df_enhanced
    
    # Parse timestamps if not already done
    if not pd.api.types.is_datetime64_any_dtype(df_enhanced['timestamp']):
        ts_format = params.get('ts_format', '%Y-%m-%d %H:%M:%S')
        timezone = params.get('tz', 'Asia/Jerusalem')
        df_enhanced['timestamp'] = parse_timestamps_vectorized(
            df_enhanced['timestamp'], ts_format, timezone
        )
    
    # Add derived time columns
    df_enhanced = add_derived_time_columns(df_enhanced)
    
    # Map Hebrew day names to weekday_index
    df_enhanced = map_hebrew_day_names(df_enhanced)
    
    # Map DayType to weekday/weekend/holiday categories
    df_enhanced = map_daytype_categories(df_enhanced, params)
    
    # Apply holiday classification system
    if params.get('enable_holiday_classification', True):
        df_enhanced = classify_holidays(df_enhanced, params)
    
    logger.info("Temporal enhancements completed")
    return df_enhanced


def create_hourly_aggregation(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """
    Generate hourly aggregated metrics using vectorized operations
    
    Args:
        df: DataFrame with processed data including validity flags
        params: Dictionary containing aggregation parameters
        
    Returns:
        DataFrame with hourly aggregations
    """
    if df.empty:
        logger.warning("Cannot create hourly aggregation: empty DataFrame")
        return pd.DataFrame()
    
    # Validate required columns
    required_cols = ['name', 'date', 'hour_of_day', 'daytype', 'is_valid']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        logger.error(f"Missing required columns for hourly aggregation: {missing_cols}")
        return pd.DataFrame()
    
    logger.info(f"Creating hourly aggregation from {len(df):,} rows")
    
    # Get minimum valid rows threshold per hour
    min_valid_per_hour = params.get('min_valid_per_hour', 1)
    
    # Group by link_id (name), date, hour_of_day, daytype using vectorized operations
    groupby_cols = ['name', 'date', 'hour_of_day', 'daytype']
    
    # Create aggregation dictionary for all metrics
    agg_dict = {
        # Count total and valid rows
        'is_valid': ['count', 'sum'],
        # Metrics from valid rows only - will be computed separately
    }
    
    # Add duration, distance, speed columns if they exist
    metric_cols = []
    if 'duration' in df.columns:
        metric_cols.append('duration')
    if 'distance' in df.columns:
        metric_cols.append('distance') 
    if 'speed' in df.columns:
        metric_cols.append('speed')
    
    # Perform initial groupby for counts
    logger.info("Performing hourly groupby aggregation...")
    hourly_groups = df.groupby(groupby_cols).agg(agg_dict).reset_index()
    
    # Flatten column names
    hourly_groups.columns = [
        '_'.join(col).strip('_') if isinstance(col, tuple) and col[1] else col[0] if isinstance(col, tuple) else col
        for col in hourly_groups.columns
    ]
    
    # Rename columns to match requirements
    hourly_groups = hourly_groups.rename(columns={
        'name': 'link_id',
        'is_valid_count': 'n_total',
        'is_valid_sum': 'n_valid'
    })
    
    # Calculate valid_hour flag based on minimum threshold
    hourly_groups['valid_hour'] = hourly_groups['n_valid'] >= min_valid_per_hour
    hourly_groups['no_valid_hour'] = (~hourly_groups['valid_hour']).astype(int)
    
    logger.info(f"Initial hourly aggregation: {len(hourly_groups):,} hour-link combinations")
    
    # Now compute metrics from valid rows only
    if metric_cols:
        logger.info("Computing hourly metrics from valid rows...")
        
        # Filter to valid rows only for metrics calculation
        valid_df = df[df['is_valid']].copy()
        
        if not valid_df.empty:
            # Group valid data and compute metrics
            valid_agg_dict = {}
            
            if 'duration' in metric_cols:
                valid_agg_dict['duration'] = ['mean', 'std']
            if 'distance' in metric_cols:
                valid_agg_dict['distance'] = ['mean']
            if 'speed' in metric_cols:
                valid_agg_dict['speed'] = ['mean']
            
            valid_groups = valid_df.groupby(groupby_cols).agg(valid_agg_dict).reset_index()
            
            # Flatten column names for valid metrics
            valid_groups.columns = [
                '_'.join(col).strip('_') if isinstance(col, tuple) and col[1] else col[0] if isinstance(col, tuple) else col
                for col in valid_groups.columns
            ]
            
            # Rename to match requirements
            rename_dict = {'name': 'link_id'}
            if 'duration_mean' in valid_groups.columns:
                rename_dict['duration_mean'] = 'avg_duration_sec'
            if 'duration_std' in valid_groups.columns:
                rename_dict['duration_std'] = 'std_duration_sec'
            if 'distance_mean' in valid_groups.columns:
                rename_dict['distance_mean'] = 'avg_distance_m'
            if 'speed_mean' in valid_groups.columns:
                rename_dict['speed_mean'] = 'avg_speed_kmh'
            
            valid_groups = valid_groups.rename(columns=rename_dict)
            
            # Merge metrics back to main hourly aggregation
            merge_cols = ['link_id', 'date', 'hour_of_day', 'daytype']
            hourly_groups = hourly_groups.merge(
                valid_groups, 
                on=merge_cols, 
                how='left'
            )
            
            logger.info("Merged valid row metrics into hourly aggregation")
        else:
            logger.warning("No valid rows found for metrics calculation")
    
    # Ensure all required metric columns exist (set to None for hours with no valid data)
    required_metric_cols = ['avg_duration_sec', 'std_duration_sec', 'avg_distance_m', 'avg_speed_kmh']
    for col in required_metric_cols:
        if col not in hourly_groups.columns:
            hourly_groups[col] = None
    
    # Handle hours with zero valid rows - metrics should be Null but hour kept in output
    zero_valid_mask = hourly_groups['n_valid'] == 0
    if zero_valid_mask.any():
        logger.info(f"Setting metrics to Null for {zero_valid_mask.sum()} hours with zero valid rows")
        for col in required_metric_cols:
            hourly_groups.loc[zero_valid_mask, col] = None
    
    # Ensure exact column order as specified in requirements
    final_columns = [
        'link_id', 'date', 'hour_of_day', 'daytype', 
        'n_total', 'n_valid', 'valid_hour', 'no_valid_hour',
        'avg_duration_sec', 'std_duration_sec', 'avg_distance_m', 'avg_speed_kmh'
    ]
    
    # Reorder columns and ensure all exist
    for col in final_columns:
        if col not in hourly_groups.columns:
            hourly_groups[col] = None
    
    hourly_groups = hourly_groups[final_columns]
    
    # Log aggregation statistics
    total_hours = len(hourly_groups)
    valid_hours = hourly_groups['valid_hour'].sum()
    unique_links = hourly_groups['link_id'].nunique()
    
    logger.info(f"Hourly aggregation completed:")
    logger.info(f"  - Total hour-link combinations: {total_hours:,}")
    logger.info(f"  - Valid hours (>= {min_valid_per_hour} valid rows): {valid_hours:,} ({valid_hours/total_hours*100:.1f}%)")
    logger.info(f"  - Unique links: {unique_links:,}")
    
    # Log n_valid distribution
    if not hourly_groups.empty:
        n_valid_stats = hourly_groups['n_valid'].describe()
        logger.info(f"  - n_valid distribution: min={n_valid_stats['min']:.0f}, mean={n_valid_stats['mean']:.1f}, max={n_valid_stats['max']:.0f}")
    
    return hourly_groups


def add_derived_time_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add derived time columns from timestamp
    
    Args:
        df: DataFrame with timestamp column
        
    Returns:
        DataFrame with additional time columns: date, hour_of_day, iso_week, weekday_index
    """
    df_with_time = df.copy()
    
    # Skip if timestamp column is all NaT or missing
    if 'timestamp' not in df_with_time.columns or df_with_time['timestamp'].isna().all():
        logger.warning("Cannot add derived time columns: timestamp column missing or all NaT")
        return df_with_time
    
    # Extract date (YYYY-MM-DD)
    df_with_time['date'] = df_with_time['timestamp'].dt.date
    
    # Extract hour_of_day (0-23)
    df_with_time['hour_of_day'] = df_with_time['timestamp'].dt.hour
    
    # Extract ISO week number
    df_with_time['iso_week'] = df_with_time['timestamp'].dt.isocalendar().week
    
    # Extract weekday_index (Monday=0, Sunday=6)
    df_with_time['weekday_index'] = df_with_time['timestamp'].dt.weekday
    
    logger.info("Added derived time columns: date, hour_of_day, iso_week, weekday_index")
    return df_with_time


def map_hebrew_day_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Map Hebrew day names to weekday_index with default mappings
    
    Args:
        df: DataFrame with day_in_week column containing Hebrew day names
        
    Returns:
        DataFrame with mapped weekday_index values
    """
    df_mapped = df.copy()
    
    # Default Hebrew day name mapping (יום א=Sunday=6, יום ב=Monday=0, etc.)
    # Note: In Hebrew calendar, Sunday is the first day, but we use Monday=0 as per ISO standard
    hebrew_day_mapping = {
        'יום א': 6,  # Sunday
        'יום ב': 0,  # Monday  
        'יום ג': 1,  # Tuesday
        'יום ד': 2,  # Wednesday
        'יום ה': 3,  # Thursday
        'יום ו': 4,  # Friday
        'יום ש': 5,  # Saturday (Shabbat)
        # Alternative spellings with apostrophe
        'יום א\'': 6,
        'יום ב\'': 0,
        'יום ג\'': 1,
        'יום ד\'': 2,
        'יום ה\'': 3,
        'יום ו\'': 4,
        'יום ש\'': 5,
        # Short forms
        'א': 6,
        'ב': 0,
        'ג': 1,
        'ד': 2,
        'ה': 3,
        'ו': 4,
        'ש': 5,
        # Short forms with apostrophe
        'א\'': 6,
        'ב\'': 0,
        'ג\'': 1,
        'ד\'': 2,
        'ה\'': 3,
        'ו\'': 4,
        'ש\'': 5
    }
    
    # If day_in_week column exists and contains Hebrew names, map them
    if 'day_in_week' in df_mapped.columns:
        # Only map if weekday_index is not already correctly set from timestamp
        hebrew_values = df_mapped['day_in_week'].dropna()
        if not hebrew_values.empty:
            # Check if any values match Hebrew patterns
            has_hebrew = hebrew_values.astype(str).str.contains('יום|א|ב|ג|ד|ה|ו|ש', na=False).any()
            
            if has_hebrew:
                logger.info("Mapping Hebrew day names to weekday_index")
                
                # Clean Hebrew text: replace non-breaking spaces and other whitespace issues
                cleaned_hebrew = df_mapped['day_in_week'].astype(str).str.replace('\xa0', ' ').str.strip()
                
                # Create mapping series
                hebrew_mapped = cleaned_hebrew.map(hebrew_day_mapping)
                
                # Use Hebrew mapping where available, otherwise keep existing weekday_index
                if 'weekday_index' in df_mapped.columns:
                    df_mapped['weekday_index'] = hebrew_mapped.fillna(df_mapped['weekday_index'])
                else:
                    df_mapped['weekday_index'] = hebrew_mapped
                
                # Log mapping statistics
                mapped_count = hebrew_mapped.notna().sum()
                total_hebrew = hebrew_values.notna().sum()
                logger.info(f"Mapped {mapped_count}/{total_hebrew} Hebrew day names to weekday_index")
                
                # Warn about unmapped values
                unmapped = df_mapped[df_mapped['day_in_week'].notna() & df_mapped['weekday_index'].isna()]
                if not unmapped.empty:
                    unique_unmapped = unmapped['day_in_week'].unique()
                    logger.warning(f"Could not map Hebrew day names: {list(unique_unmapped)}")
    
    return df_mapped


def map_daytype_categories(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """
    Map DayType values to weekday/weekend/holiday categories
    
    Args:
        df: DataFrame with day_type column
        params: Parameters containing daytype mapping configuration
        
    Returns:
        DataFrame with normalized daytype values
    """
    df_mapped = df.copy()
    
    # Default Hebrew DayType mapping
    default_daytype_mapping = {
        # Hebrew weekday terms
        'יום חול': 'weekday',
        'חול': 'weekday', 
        'יום עבודה': 'weekday',
        'עבודה': 'weekday',
        
        # Hebrew weekend terms  
        'סוף שבוע': 'weekend',
        'סופש': 'weekend',
        'שבת': 'weekend',
        'יום שבת': 'weekend',
        'יום שישי': 'weekend',  # Friday often considered weekend in Israel
        
        # Hebrew holiday terms
        'חג': 'holiday',
        'יום חג': 'holiday',
        'חגים': 'holiday',
        'מועד': 'holiday',
        'יום טוב': 'holiday',
        
        # English equivalents
        'weekday': 'weekday',
        'weekend': 'weekend', 
        'holiday': 'holiday',
        'workday': 'weekday',
        'work': 'weekday'
    }
    
    # Get custom mapping from parameters, merge with defaults
    custom_daytype_mapping = params.get('daytype_mapping', {})
    
    # Flatten nested daytype mapping from GUI
    flattened_custom_mapping = {}
    if isinstance(custom_daytype_mapping, dict):
        for category, values in custom_daytype_mapping.items():
            if isinstance(values, list):
                for value in values:
                    flattened_custom_mapping[value] = category
            else:
                flattened_custom_mapping[values] = category
    
    daytype_mapping = {**default_daytype_mapping, **flattened_custom_mapping}
    
    # Apply mapping if day_type column exists
    if 'day_type' in df_mapped.columns:
        logger.info("Mapping DayType values to weekday/weekend/holiday categories")
        
        # Clean DayType text: replace non-breaking spaces and other whitespace issues
        cleaned_daytype = df_mapped['day_type'].astype(str).str.replace('\xa0', ' ').str.strip()
        
        # Apply the mapping
        original_values = df_mapped['day_type'].copy()
        df_mapped['daytype'] = cleaned_daytype.map(daytype_mapping)
        
        # For unmapped values, try to infer from weekday_index if available
        if 'weekday_index' in df_mapped.columns:
            unmapped_mask = df_mapped['daytype'].isna() & df_mapped['day_type'].notna()
            if unmapped_mask.any():
                logger.info("Inferring daytype from weekday_index for unmapped values")
                
                # Infer based on weekday_index (0-4=weekday, 5-6=weekend)
                inferred_daytype = df_mapped.loc[unmapped_mask, 'weekday_index'].apply(
                    lambda x: 'weekday' if x < 5 else 'weekend' if pd.notna(x) else None
                )
                df_mapped.loc[unmapped_mask, 'daytype'] = inferred_daytype
        
        # Log mapping statistics
        mapped_count = (df_mapped['daytype'].notna() & df_mapped['day_type'].notna()).sum()
        total_daytype = df_mapped['day_type'].notna().sum()
        logger.info(f"Mapped {mapped_count}/{total_daytype} DayType values")
        
        # Warn about still unmapped values
        still_unmapped = df_mapped[df_mapped['day_type'].notna() & df_mapped['daytype'].isna()]
        if not still_unmapped.empty:
            unique_unmapped = still_unmapped['day_type'].unique()
            logger.warning(f"Could not map DayType values: {list(unique_unmapped)}")
    
    else:
        # If no day_type column, infer from weekday_index
        if 'weekday_index' in df_mapped.columns:
            logger.info("Inferring daytype from weekday_index (no day_type column found)")
            df_mapped['daytype'] = df_mapped['weekday_index'].apply(
                lambda x: 'weekday' if x < 5 else 'weekend' if pd.notna(x) else None
            )
        else:
            logger.warning("Cannot determine daytype: no day_type or weekday_index columns available")
            df_mapped['daytype'] = None
    
    return df_mapped


def load_israeli_holidays(year_range: Tuple[int, int]) -> Dict[date, str]:
    """
    Load Israeli holidays for the specified year range using holidays library
    
    Args:
        year_range: Tuple of (start_year, end_year) inclusive
        
    Returns:
        Dictionary mapping date objects to holiday names
    """
    israeli_holidays = {}
    
    start_year, end_year = year_range
    for year in range(start_year, end_year + 1):
        try:
            # Get Israeli holidays for the year
            year_holidays = holidays.Israel(years=year)
            
            # Convert to date objects and add to our dictionary
            for holiday_date, holiday_name in year_holidays.items():
                israeli_holidays[holiday_date] = holiday_name
                
        except Exception as e:
            logger.warning(f"Failed to load Israeli holidays for year {year}: {e}")
    
    logger.info(f"Loaded {len(israeli_holidays)} Israeli holidays for years {start_year}-{end_year}")
    return israeli_holidays


def load_custom_holidays_from_text(file_path: str) -> Dict[date, str]:
    """
    Load custom holidays from a text file containing ISO dates
    
    Args:
        file_path: Path to text file with ISO dates (YYYY-MM-DD), one per line
        
    Returns:
        Dictionary mapping date objects to holiday names
    """
    custom_holidays = {}
    
    try:
        encoding = detect_file_encoding(file_path)
        with open(file_path, 'r', encoding=encoding) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):  # Skip empty lines and comments
                    continue
                
                try:
                    # Try to parse as ISO date
                    if len(line) >= 10:  # YYYY-MM-DD format
                        date_str = line[:10]  # Take first 10 characters
                        holiday_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        
                        # Use rest of line as holiday name, or default name
                        holiday_name = line[10:].strip()
                        if holiday_name.startswith('-') or holiday_name.startswith(','):
                            holiday_name = holiday_name[1:].strip()
                        if not holiday_name:
                            holiday_name = f"Custom Holiday {date_str}"
                        
                        custom_holidays[holiday_date] = holiday_name
                        
                except ValueError as e:
                    logger.warning(f"Invalid date format on line {line_num} in {file_path}: '{line}' - {e}")
                    continue
                    
    except FileNotFoundError:
        logger.error(f"Custom holidays file not found: {file_path}")
    except Exception as e:
        logger.error(f"Error reading custom holidays file {file_path}: {e}")
    
    logger.info(f"Loaded {len(custom_holidays)} custom holidays from {file_path}")
    return custom_holidays


def load_custom_holidays_from_ics(file_path: str) -> Dict[date, str]:
    """
    Load custom holidays from an ICS (iCalendar) file
    
    Args:
        file_path: Path to ICS file
        
    Returns:
        Dictionary mapping date objects to holiday names
    """
    custom_holidays = {}
    
    try:
        encoding = detect_file_encoding(file_path)
        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()
        
        # Simple ICS parser - look for VEVENT blocks
        events = []
        current_event = {}
        in_event = False
        
        for line in content.split('\n'):
            line = line.strip()
            
            if line == 'BEGIN:VEVENT':
                in_event = True
                current_event = {}
            elif line == 'END:VEVENT':
                if in_event and current_event:
                    events.append(current_event)
                in_event = False
                current_event = {}
            elif in_event and ':' in line:
                key, value = line.split(':', 1)
                current_event[key] = value
        
        # Process events to extract dates and names
        for event in events:
            try:
                # Look for DTSTART (date start)
                dtstart = event.get('DTSTART', '')
                summary = event.get('SUMMARY', 'Custom Holiday')
                
                if dtstart:
                    # Handle different date formats
                    if ';VALUE=DATE:' in dtstart:
                        date_str = dtstart.split(';VALUE=DATE:')[1][:8]  # YYYYMMDD
                        holiday_date = datetime.strptime(date_str, '%Y%m%d').date()
                    elif len(dtstart) >= 8 and dtstart.isdigit():
                        # YYYYMMDD format
                        holiday_date = datetime.strptime(dtstart[:8], '%Y%m%d').date()
                    elif 'T' in dtstart:
                        # ISO format with time
                        date_part = dtstart.split('T')[0]
                        if '-' in date_part:
                            holiday_date = datetime.strptime(date_part, '%Y-%m-%d').date()
                        else:
                            holiday_date = datetime.strptime(date_part, '%Y%m%d').date()
                    else:
                        continue
                    
                    custom_holidays[holiday_date] = summary
                    
            except ValueError as e:
                logger.warning(f"Failed to parse ICS event: {event} - {e}")
                continue
                
    except FileNotFoundError:
        logger.error(f"Custom holidays ICS file not found: {file_path}")
    except Exception as e:
        logger.error(f"Error reading custom holidays ICS file {file_path}: {e}")
    
    logger.info(f"Loaded {len(custom_holidays)} custom holidays from ICS file {file_path}")
    return custom_holidays


def build_holiday_calendar(df: pd.DataFrame, params: dict) -> Dict[date, str]:
    """
    Build a comprehensive holiday calendar from Israeli holidays and custom files
    
    Args:
        df: DataFrame containing date information to determine year range
        params: Parameters containing holiday configuration
        
    Returns:
        Dictionary mapping date objects to holiday names
    """
    holiday_calendar = {}
    
    # Determine year range from data
    if 'date' in df.columns and not df['date'].isna().all():
        dates = pd.to_datetime(df['date']).dropna()
        if not dates.empty:
            start_year = dates.dt.year.min()
            end_year = dates.dt.year.max()
        else:
            # Default to current year if no valid dates
            current_year = datetime.now().year
            start_year = end_year = current_year
    else:
        # Default to current year if no date column
        current_year = datetime.now().year
        start_year = end_year = current_year
    
    logger.info(f"Building holiday calendar for years {start_year}-{end_year}")
    
    # Load Israeli holidays if enabled
    if params.get('use_israeli_holidays', True):
        israeli_holidays = load_israeli_holidays((start_year, end_year))
        holiday_calendar.update(israeli_holidays)
    
    # Load custom holidays from text file if provided
    custom_holidays_file = params.get('custom_holidays_file')
    if custom_holidays_file:
        file_path = Path(custom_holidays_file)
        if file_path.exists():
            if file_path.suffix.lower() == '.ics':
                custom_holidays = load_custom_holidays_from_ics(str(file_path))
            else:
                custom_holidays = load_custom_holidays_from_text(str(file_path))
            
            # Custom holidays override Israeli holidays
            holiday_calendar.update(custom_holidays)
            logger.info(f"Custom holidays override: {len(custom_holidays)} holidays from {file_path}")
        else:
            logger.warning(f"Custom holidays file not found: {custom_holidays_file}")
    
    return holiday_calendar


def classify_holidays(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """
    Classify dates as holidays and update daytype accordingly
    
    Args:
        df: DataFrame with date column
        params: Parameters containing holiday configuration
        
    Returns:
        DataFrame with holiday classifications applied to daytype
    """
    if df.empty or 'date' not in df.columns:
        logger.warning("Cannot classify holidays: missing date column")
        return df
    
    df_with_holidays = df.copy()
    
    # Build holiday calendar
    holiday_calendar = build_holiday_calendar(df, params)
    
    if not holiday_calendar:
        logger.info("No holidays to classify")
        return df_with_holidays
    
    # Create holiday lookup series
    df_with_holidays['is_holiday'] = df_with_holidays['date'].apply(
        lambda x: x in holiday_calendar if pd.notna(x) else False
    )
    
    # Add holiday name column for reference
    df_with_holidays['holiday_name'] = df_with_holidays['date'].apply(
        lambda x: holiday_calendar.get(x, '') if pd.notna(x) else ''
    )
    
    # Update daytype based on holiday treatment configuration
    holidays_as = params.get('holidays_as', 'holiday')  # 'holiday', 'weekend', or 'weekday'
    
    if holidays_as == 'holiday':
        # Keep holidays as separate category
        df_with_holidays.loc[df_with_holidays['is_holiday'], 'daytype'] = 'holiday'
    elif holidays_as == 'weekend':
        # Treat holidays as weekend
        df_with_holidays.loc[df_with_holidays['is_holiday'], 'daytype'] = 'weekend'
    elif holidays_as == 'weekday':
        # Treat holidays as weekday (rare case)
        df_with_holidays.loc[df_with_holidays['is_holiday'], 'daytype'] = 'weekday'
    
    # Log holiday classification results
    holiday_count = df_with_holidays['is_holiday'].sum()
    total_dates = df_with_holidays['date'].notna().sum()
    
    logger.info(f"Holiday classification completed: {holiday_count}/{total_dates} dates classified as holidays")
    logger.info(f"Holiday treatment: {holidays_as}")
    
    if holiday_count > 0:
        unique_holidays = df_with_holidays[df_with_holidays['is_holiday']]['holiday_name'].value_counts()
        logger.info(f"Holidays found: {dict(unique_holidays.head(10))}")  # Show top 10
    
    return df_with_holidays


def write_hourly_aggregation_csv(hourly_df: pd.DataFrame, output_path: str) -> bool:
    """
    Write hourly aggregation DataFrame to CSV with exact schema requirements
    
    Args:
        hourly_df: DataFrame with hourly aggregation data
        output_path: Path where to write the CSV file
        
    Returns:
        True if successful, False otherwise
    """
    if hourly_df.empty:
        logger.warning("Cannot write hourly aggregation CSV: empty DataFrame")
        return False
    
    try:
        logger.info(f"Writing hourly aggregation CSV to: {output_path}")
        
        # Validate exact column order as specified in requirements
        required_columns = [
            'link_id', 'date', 'hour_of_day', 'daytype', 
            'n_total', 'n_valid', 'valid_hour', 'no_valid_hour',
            'avg_duration_sec', 'std_duration_sec', 'avg_distance_m', 'avg_speed_kmh'
        ]
        
        # Check that all required columns exist
        missing_cols = [col for col in required_columns if col not in hourly_df.columns]
        if missing_cols:
            logger.error(f"Missing required columns in hourly DataFrame: {missing_cols}")
            return False
        
        # Create output DataFrame with exact column order
        output_df = hourly_df[required_columns].copy()
        
        # Validate data types and handle Null values properly
        # Convert boolean columns to proper format
        output_df['valid_hour'] = output_df['valid_hour'].astype(bool)
        output_df['no_valid_hour'] = output_df['no_valid_hour'].astype(int)
        
        # Ensure numeric columns are properly formatted
        numeric_cols = ['n_total', 'n_valid', 'hour_of_day']
        for col in numeric_cols:
            output_df[col] = pd.to_numeric(output_df[col], errors='coerce').astype('Int64')
        
        # Handle metric columns - keep as float with proper Null handling
        metric_cols = ['avg_duration_sec', 'std_duration_sec', 'avg_distance_m', 'avg_speed_kmh']
        for col in metric_cols:
            if col in output_df.columns:
                output_df[col] = pd.to_numeric(output_df[col], errors='coerce')
        
        # Sort by link_id, date, hour_of_day for consistent output
        output_df = output_df.sort_values(['link_id', 'date', 'hour_of_day'])
        
        # Write to CSV with proper formatting
        output_df.to_csv(
            output_path,
            index=False,
            na_rep='',  # Empty string for Null values
            date_format='%Y-%m-%d',  # Ensure consistent date format
            float_format='%.6f'  # Consistent float precision
        )
        
        # Validate the written file
        validation_result = validate_hourly_aggregation_output(output_path, len(output_df))
        
        if validation_result:
            logger.info(f"Successfully wrote hourly aggregation CSV: {len(output_df):,} rows")
            return True
        else:
            logger.error("Hourly aggregation CSV validation failed")
            return False
            
    except Exception as e:
        logger.error(f"Failed to write hourly aggregation CSV: {e}")
        return False


def validate_hourly_aggregation_output(file_path: str, expected_rows: int) -> bool:
    """
    Validate that the written hourly aggregation CSV matches exact schema requirements
    
    Args:
        file_path: Path to the CSV file to validate
        expected_rows: Expected number of data rows
        
    Returns:
        True if validation passes, False otherwise
    """
    try:
        logger.info(f"Validating hourly aggregation output: {file_path}")
        
        # Read the file back to validate with proper encoding
        encoding = detect_file_encoding(file_path)
        validation_df = pd.read_csv(file_path, encoding=encoding)
        
        # Check row count
        if len(validation_df) != expected_rows:
            logger.error(f"Row count mismatch: expected {expected_rows}, got {len(validation_df)}")
            return False
        
        # Check exact column order and names
        required_columns = [
            'link_id', 'date', 'hour_of_day', 'daytype', 
            'n_total', 'n_valid', 'valid_hour', 'no_valid_hour',
            'avg_duration_sec', 'std_duration_sec', 'avg_distance_m', 'avg_speed_kmh'
        ]
        
        if list(validation_df.columns) != required_columns:
            logger.error(f"Column order/names mismatch:")
            logger.error(f"  Expected: {required_columns}")
            logger.error(f"  Got: {list(validation_df.columns)}")
            return False
        
        # Validate data types and ranges
        validation_errors = []
        
        # Check hour_of_day range (0-23)
        if 'hour_of_day' in validation_df.columns:
            invalid_hours = validation_df[
                (validation_df['hour_of_day'] < 0) | 
                (validation_df['hour_of_day'] > 23)
            ]
            if not invalid_hours.empty:
                validation_errors.append(f"Invalid hour_of_day values: {len(invalid_hours)} rows")
        
        # Check that n_valid <= n_total
        if 'n_total' in validation_df.columns and 'n_valid' in validation_df.columns:
            invalid_counts = validation_df[validation_df['n_valid'] > validation_df['n_total']]
            if not invalid_counts.empty:
                validation_errors.append(f"n_valid > n_total in {len(invalid_counts)} rows")
        
        # Check that valid_hour is consistent with n_valid
        if 'valid_hour' in validation_df.columns and 'n_valid' in validation_df.columns:
            # This would require knowing the min_valid_per_hour parameter, so we'll skip this check
            pass
        
        # Check for required non-null columns
        required_non_null = ['link_id', 'date', 'hour_of_day', 'daytype', 'n_total', 'n_valid']
        for col in required_non_null:
            if col in validation_df.columns:
                null_count = validation_df[col].isna().sum()
                if null_count > 0:
                    validation_errors.append(f"Null values in required column '{col}': {null_count} rows")
        
        # Report validation results
        if validation_errors:
            logger.error("Hourly aggregation validation errors:")
            for error in validation_errors:
                logger.error(f"  - {error}")
            return False
        else:
            logger.info("Hourly aggregation output validation passed")
            return True
            
    except Exception as e:
        logger.error(f"Error validating hourly aggregation output: {e}")
        return False


def create_weekly_profile(hourly_df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """
    Generate weekly hourly profiles from valid hours
    
    Args:
        hourly_df: DataFrame with hourly aggregations including valid_hour flag
        params: Dictionary containing weekly profile parameters
        
    Returns:
        DataFrame with weekly hourly profiles
    """
    if hourly_df.empty:
        logger.warning("Cannot create weekly profile: empty hourly DataFrame")
        return pd.DataFrame()
    
    # Validate required columns
    required_cols = ['link_id', 'hour_of_day', 'valid_hour', 'n_valid', 'avg_duration_sec', 'avg_distance_m', 'avg_speed_kmh']
    missing_cols = [col for col in required_cols if col not in hourly_df.columns]
    if missing_cols:
        logger.error(f"Missing required columns for weekly profile: {missing_cols}")
        return pd.DataFrame()
    
    logger.info(f"Creating weekly profile from {len(hourly_df):,} hourly records")
    
    # Step 1: Filter to only use hours where valid_hour is true
    valid_hours_df = hourly_df[hourly_df['valid_hour'] == True].copy()
    
    if valid_hours_df.empty:
        logger.warning("No valid hours found for weekly profile generation")
        return pd.DataFrame()
    
    logger.info(f"Using {len(valid_hours_df):,} valid hours for weekly profile ({len(valid_hours_df)/len(hourly_df)*100:.1f}% of total hours)")
    
    # Step 2: Determine grouping columns based on configuration
    weekly_grouping = params.get('weekly_grouping', 'daytype')  # 'daytype' or 'weekday_index'
    
    if weekly_grouping == 'weekday_index':
        if 'weekday_index' not in valid_hours_df.columns:
            logger.error("weekday_index column not found, cannot group by weekday_index")
            return pd.DataFrame()
        groupby_cols = ['link_id', 'weekday_index', 'hour_of_day']
        logger.info("Grouping weekly profile by (link_id, weekday_index, hour_of_day)")
    else:
        if 'daytype' not in valid_hours_df.columns:
            logger.error("daytype column not found, cannot group by daytype")
            return pd.DataFrame()
        groupby_cols = ['link_id', 'daytype', 'hour_of_day']
        logger.info("Grouping weekly profile by (link_id, daytype, hour_of_day)")
    
    # Step 3: Calculate weekly metrics using vectorized operations
    logger.info("Computing weekly metrics from valid hours...")
    
    # Calculate total invalid observations for each hour
    valid_hours_df['n_invalid'] = valid_hours_df['n_total'] - valid_hours_df['n_valid']
    
    # Group by the specified columns and calculate aggregations
    agg_dict = {
        'n_valid': ['mean', 'sum'],  # avgnvalid - mean of n_valid values, total_valid_n - sum of n_valid values
        'n_invalid': 'sum',  # total_not_valid - sum of invalid observations
        'avg_duration_sec': 'mean',  # avgdur - mean of avg_duration_sec values
        'avg_distance_m': 'mean',  # avgdist - mean of avg_distance_m values  
        'avg_speed_kmh': 'mean',  # avgspeed - mean of avg_speed_kmh values
        'date': 'nunique'  # n_days - count of distinct dates
    }
    
    # Perform the groupby aggregation
    weekly_groups = valid_hours_df.groupby(groupby_cols).agg(agg_dict).reset_index()
    
    # Flatten multi-level column names from aggregation
    weekly_groups.columns = ['_'.join(col).strip('_') if isinstance(col, tuple) else col for col in weekly_groups.columns]
    
    # Rename columns to match requirements
    weekly_groups = weekly_groups.rename(columns={
        'n_valid_mean': 'avg_n_valid',
        'n_valid_sum': 'total_valid_n',
        'n_invalid_sum': 'total_not_valid',
        'avg_duration_sec_mean': 'avg_dur',
        'avg_distance_m_mean': 'avg_dist',
        'avg_speed_kmh_mean': 'avg_speed',
        'date_nunique': 'n_days'
    })
    
    # Step 4: Calculate standard deviation based on configuration
    recompute_std_from_raw = params.get('recompute_std_from_raw', False)
    
    if recompute_std_from_raw:
        logger.info("Computing std_dur from pooled raw valid rows with ddof=1")
        weekly_groups['std_dur'] = _compute_std_from_raw_data(valid_hours_df, groupby_cols, params)
    else:
        logger.info("Computing std_dur as mean of hourly std_duration_sec values")
        # Use mean of hourly std_duration_sec values
        if 'std_duration_sec' in valid_hours_df.columns:
            std_groups = valid_hours_df.groupby(groupby_cols)['std_duration_sec'].mean().reset_index()
            std_groups = std_groups.rename(columns={'std_duration_sec': 'std_dur'})
            
            # Merge std_dur back to weekly_groups
            weekly_groups = weekly_groups.merge(std_groups, on=groupby_cols, how='left')
        else:
            logger.warning("std_duration_sec column not found, setting std_dur to None")
            weekly_groups['std_dur'] = None
    
    # Log weekly profile statistics
    total_profiles = len(weekly_groups)
    unique_links = weekly_groups['link_id'].nunique()
    
    logger.info(f"Weekly profile completed:")
    logger.info(f"  - Total weekly profiles: {total_profiles:,}")
    logger.info(f"  - Unique links: {unique_links:,}")
    
    if not weekly_groups.empty:
        avg_n_valid_stats = weekly_groups['avg_n_valid'].describe()
        n_days_stats = weekly_groups['n_days'].describe()
        logger.info(f"  - avg_n_valid distribution: min={avg_n_valid_stats['min']:.1f}, mean={avg_n_valid_stats['mean']:.1f}, max={avg_n_valid_stats['max']:.1f}")
        logger.info(f"  - n_days distribution: min={n_days_stats['min']:.0f}, mean={n_days_stats['mean']:.1f}, max={n_days_stats['max']:.0f}")
    
    return weekly_groups


def _compute_std_from_raw_data(valid_hours_df: pd.DataFrame, groupby_cols: List[str], params: dict) -> pd.Series:
    """
    Compute standard deviation from pooled raw valid rows with ddof=1
    
    Args:
        valid_hours_df: DataFrame with valid hours data
        groupby_cols: List of columns to group by
        params: Parameters dictionary containing raw data access
        
    Returns:
        Series with std_dur values indexed by groupby_cols
    """
    # This is a complex operation that requires access to the original raw data
    # For now, we'll implement a simplified version that uses the hourly std values
    # In a full implementation, this would need to access the original raw data
    # and recompute standard deviation from all valid rows pooled together
    
    logger.warning("recompute_std_from_raw not fully implemented - using mean of hourly std values as fallback")
    
    if 'std_duration_sec' in valid_hours_df.columns:
        std_groups = valid_hours_df.groupby(groupby_cols)['std_duration_sec'].mean()
        return std_groups
    else:
        # Return None values for all groups
        group_indices = valid_hours_df.groupby(groupby_cols).size().index
        return pd.Series([None] * len(group_indices), index=group_indices)


def write_weekly_hourly_profile_csv(weekly_df: pd.DataFrame, output_path: str) -> bool:
    """
    Write weekly hourly profile to CSV with proper column structure
    
    Args:
        weekly_df: DataFrame with weekly profile data
        output_path: Path where to write the CSV file
        
    Returns:
        True if successful, False otherwise
    """
    if weekly_df.empty:
        logger.warning("Cannot write weekly profile CSV: empty DataFrame")
        return False
    
    try:
        logger.info(f"Writing weekly hourly profile to: {output_path}")
        
        # Ensure proper column order based on grouping type
        if 'weekday_index' in weekly_df.columns:
            # Grouping by weekday_index
            expected_columns = [
                'link_id', 'weekday_index', 'hour_of_day', 
                'avg_n_valid', 'total_valid_n', 'total_not_valid', 'avg_dur', 'std_dur', 'avg_dist', 'avg_speed', 'n_days'
            ]
        else:
            # Grouping by daytype
            expected_columns = [
                'link_id', 'daytype', 'hour_of_day',
                'avg_n_valid', 'total_valid_n', 'total_not_valid', 'avg_dur', 'std_dur', 'avg_dist', 'avg_speed', 'n_days'
            ]
        
        # Ensure all expected columns exist
        output_df = weekly_df.copy()
        for col in expected_columns:
            if col not in output_df.columns:
                output_df[col] = None
        
        # Reorder columns
        output_df = output_df[expected_columns]
        
        # Handle numeric formatting
        numeric_cols = ['avg_n_valid', 'total_valid_n', 'total_not_valid', 'avg_dur', 'std_dur', 'avg_dist', 'avg_speed']
        for col in numeric_cols:
            if col in output_df.columns:
                # Convert to appropriate type and handle None/NaN values
                if col in ['total_valid_n', 'total_not_valid']:
                    # Integer columns
                    output_df[col] = pd.to_numeric(output_df[col], errors='coerce').astype('Int64')
                else:
                    # Float columns
                    output_df[col] = pd.to_numeric(output_df[col], errors='coerce')
        
        # Write to CSV
        output_df.to_csv(output_path, index=False, na_rep='')
        
        logger.info(f"Successfully wrote {len(output_df):,} weekly profiles to {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to write weekly profile CSV to {output_path}: {e}")
        return False


def generate_quality_by_link_report(raw_df: pd.DataFrame, hourly_df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate quality_by_link.csv with data quality metrics per link
    
    Args:
        raw_df: Original processed DataFrame with validity flags
        hourly_df: Hourly aggregation DataFrame
        
    Returns:
        DataFrame with quality metrics per link
    """
    if raw_df.empty or hourly_df.empty:
        logger.warning("Cannot generate quality by link report: empty input DataFrames")
        return pd.DataFrame()
    
    logger.info("Generating quality by link report...")
    
    # Initialize quality metrics per link
    quality_metrics = []
    
    # Get unique links from raw data
    if 'name' in raw_df.columns:
        unique_links = raw_df['name'].unique()
    else:
        logger.error("Cannot generate quality report: 'name' column not found in raw data")
        return pd.DataFrame()
    
    for link_id in unique_links:
        # Filter data for this link
        link_raw_data = raw_df[raw_df['name'] == link_id]
        link_hourly_data = hourly_df[hourly_df['link_id'] == link_id]
        
        # Calculate basic validity metrics
        total_rows = len(link_raw_data)
        if 'is_valid' in link_raw_data.columns:
            valid_rows = link_raw_data['is_valid'].sum()
            percent_valid = (valid_rows / total_rows * 100) if total_rows > 0 else 0
        else:
            valid_rows = total_rows  # Assume all valid if no validity column
            percent_valid = 100.0
        
        # Calculate hour-level metrics from hourly data
        total_hours = len(link_hourly_data)
        if 'valid_hour' in link_hourly_data.columns:
            valid_hours = link_hourly_data['valid_hour'].sum()
            dropped_hours = total_hours - valid_hours
            percent_valid_hours = (valid_hours / total_hours * 100) if total_hours > 0 else 0
        else:
            valid_hours = total_hours
            dropped_hours = 0
            percent_valid_hours = 100.0
        
        # Calculate days covered
        if 'date' in link_hourly_data.columns:
            days_covered = link_hourly_data['date'].nunique()
        else:
            days_covered = 0
        
        # Compile metrics for this link
        link_metrics = {
            'link_id': link_id,
            'percent_valid': round(percent_valid, 2),
            'hours_with_data': total_hours,
            'hours_valid': int(valid_hours),
            'hours_dropped': int(dropped_hours),
            'percent_valid_hours': round(percent_valid_hours, 2),
            'days_covered': int(days_covered)
        }
        
        quality_metrics.append(link_metrics)
    
    # Convert to DataFrame
    quality_df = pd.DataFrame(quality_metrics)
    
    # Sort by link_id for consistent output
    if not quality_df.empty:
        quality_df = quality_df.sort_values('link_id').reset_index(drop=True)
    
    logger.info(f"Generated quality report for {len(quality_df)} links")
    
    return quality_df


def generate_invalid_reason_counts_report(validation_stats: dict) -> pd.DataFrame:
    """
    Generate invalid_reason_counts.csv showing violation counts by reason when using rule-based validity
    
    Args:
        validation_stats: Dictionary containing validation statistics from processing
        
    Returns:
        DataFrame with invalid reason counts
    """
    logger.info("Generating invalid reason counts report...")
    
    # Extract invalid reasons from validation stats
    invalid_reasons = validation_stats.get('invalid_reasons', {})
    
    if not invalid_reasons:
        logger.info("No invalid reasons found - likely using boolean validity column")
        return pd.DataFrame(columns=['invalid_reason', 'count'])
    
    # Convert to DataFrame
    reason_counts = []
    for reason, count in invalid_reasons.items():
        reason_counts.append({
            'invalid_reason': reason,
            'count': int(count)
        })
    
    reason_counts_df = pd.DataFrame(reason_counts)
    
    # Sort by count descending for better readability
    if not reason_counts_df.empty:
        reason_counts_df = reason_counts_df.sort_values('count', ascending=False).reset_index(drop=True)
    
    logger.info(f"Generated invalid reason counts for {len(reason_counts_df)} reasons")
    
    return reason_counts_df


def write_quality_reports(raw_df: pd.DataFrame, hourly_df: pd.DataFrame, validation_stats: dict, output_dir: str) -> Dict[str, str]:
    """
    Write quality report CSV files to output directory
    
    Args:
        raw_df: Original processed DataFrame with validity flags
        hourly_df: Hourly aggregation DataFrame
        validation_stats: Dictionary containing validation statistics
        output_dir: Directory to write output files
        
    Returns:
        Dictionary mapping report type to file path
    """
    output_files = {}
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    try:
        # Generate and write quality_by_link.csv
        quality_by_link_df = generate_quality_by_link_report(raw_df, hourly_df)
        if not quality_by_link_df.empty:
            quality_by_link_path = output_path / 'quality_by_link.csv'
            quality_by_link_df.to_csv(quality_by_link_path, index=False)
            output_files['quality_by_link'] = str(quality_by_link_path)
            logger.info(f"Wrote quality_by_link.csv with {len(quality_by_link_df)} links")
        
        # Generate and write invalid_reason_counts.csv
        invalid_reason_counts_df = generate_invalid_reason_counts_report(validation_stats)
        if not invalid_reason_counts_df.empty:
            invalid_reason_counts_path = output_path / 'invalid_reason_counts.csv'
            invalid_reason_counts_df.to_csv(invalid_reason_counts_path, index=False)
            output_files['invalid_reason_counts'] = str(invalid_reason_counts_path)
            logger.info(f"Wrote invalid_reason_counts.csv with {len(invalid_reason_counts_df)} reasons")
        
    except Exception as e:
        logger.error(f"Error writing quality reports: {e}")
    
    return output_files


def generate_processing_log(raw_df: pd.DataFrame, hourly_df: pd.DataFrame, weekly_df: pd.DataFrame, 
                          validation_stats: dict, processing_start_time: datetime, processing_end_time: datetime) -> str:
    """
    Generate processing log with concise summary of processing results
    
    Args:
        raw_df: Original processed DataFrame
        hourly_df: Hourly aggregation DataFrame
        weekly_df: Weekly profile DataFrame
        validation_stats: Dictionary containing validation statistics
        processing_start_time: When processing started
        processing_end_time: When processing completed
        
    Returns:
        String containing the processing log content
    """
    logger.info("Generating processing log...")
    
    # Calculate processing duration
    processing_duration = processing_end_time - processing_start_time
    duration_seconds = processing_duration.total_seconds()
    
    # Basic row counts
    total_raw_rows = len(raw_df) if not raw_df.empty else 0
    total_hourly_rows = len(hourly_df) if not hourly_df.empty else 0
    total_weekly_rows = len(weekly_df) if not weekly_df.empty else 0
    
    # Validity statistics
    valid_rows = validation_stats.get('valid_rows', 0)
    total_validation_rows = validation_stats.get('total_rows', total_raw_rows)
    validity_percentage = (valid_rows / total_validation_rows * 100) if total_validation_rows > 0 else 0
    validation_method = validation_stats.get('method_used', 'unknown')
    
    # Distinct links
    distinct_links = 0
    if not raw_df.empty and 'name' in raw_df.columns:
        distinct_links = raw_df['name'].nunique()
    elif not hourly_df.empty and 'link_id' in hourly_df.columns:
        distinct_links = hourly_df['link_id'].nunique()
    
    # n_valid distribution from hourly data
    n_valid_stats = {}
    if not hourly_df.empty and 'n_valid' in hourly_df.columns:
        n_valid_series = hourly_df['n_valid']
        n_valid_stats = {
            'min': int(n_valid_series.min()),
            'mean': round(n_valid_series.mean(), 1),
            'max': int(n_valid_series.max()),
            'median': round(n_valid_series.median(), 1)
        }
    
    # Valid hours by daytype
    valid_hours_by_daytype = {}
    if not hourly_df.empty and 'valid_hour' in hourly_df.columns and 'daytype' in hourly_df.columns:
        daytype_stats = hourly_df[hourly_df['valid_hour']].groupby('daytype').size()
        valid_hours_by_daytype = daytype_stats.to_dict()
    
    # Build log content
    log_lines = [
        "=" * 60,
        "GOOGLE MAPS LINK MONITORING - PROCESSING LOG",
        "=" * 60,
        f"Processing completed: {processing_end_time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Processing duration: {duration_seconds:.1f} seconds",
        "",
        "ROW COUNTS:",
        f"  Raw data rows processed: {total_raw_rows:,}",
        f"  Hourly aggregation rows: {total_hourly_rows:,}",
        f"  Weekly profile rows: {total_weekly_rows:,}",
        "",
        "DATA VALIDITY:",
        f"  Validation method: {validation_method}",
        f"  Valid rows: {valid_rows:,} / {total_validation_rows:,} ({validity_percentage:.1f}%)",
        f"  Invalid rows: {total_validation_rows - valid_rows:,}",
        "",
        "LINK COVERAGE:",
        f"  Distinct links processed: {distinct_links:,}",
    ]
    
    # Add n_valid distribution if available
    if n_valid_stats:
        log_lines.extend([
            "",
            "N_VALID DISTRIBUTION (per hour):",
            f"  Min: {n_valid_stats['min']}",
            f"  Mean: {n_valid_stats['mean']}",
            f"  Median: {n_valid_stats['median']}",
            f"  Max: {n_valid_stats['max']}"
        ])
    
    # Add valid hours by daytype if available
    if valid_hours_by_daytype:
        log_lines.extend([
            "",
            "VALID HOURS BY DAYTYPE:"
        ])
        for daytype, count in sorted(valid_hours_by_daytype.items()):
            log_lines.append(f"  {daytype}: {count:,} hours")
    
    # Add invalid reasons if using rule-based validation
    invalid_reasons = validation_stats.get('invalid_reasons', {})
    if invalid_reasons:
        log_lines.extend([
            "",
            "INVALID REASONS (rule-based validation):"
        ])
        for reason, count in sorted(invalid_reasons.items(), key=lambda x: x[1], reverse=True):
            log_lines.append(f"  {reason}: {count:,} rows")
    
    log_lines.extend([
        "",
        "=" * 60
    ])
    
    log_content = "\n".join(log_lines)
    logger.info("Processing log generated")
    
    return log_content


def save_run_configuration(params: dict, output_dir: str) -> str:
    """
    Save run_config.json with all parameters used in the processing run
    
    Args:
        params: Dictionary containing all processing parameters
        output_dir: Directory to write the configuration file
        
    Returns:
        Path to the saved configuration file
    """
    logger.info("Saving run configuration...")
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    config_path = output_path / 'run_config.json'
    
    try:
        # Create a clean copy of parameters for JSON serialization
        config_data = {}
        
        for key, value in params.items():
            # Handle non-JSON-serializable types
            if isinstance(value, (str, int, float, bool, list, dict, type(None))):
                config_data[key] = value
            elif isinstance(value, Path):
                config_data[key] = str(value)
            elif hasattr(value, '__dict__'):
                # For complex objects, try to convert to dict
                try:
                    config_data[key] = str(value)
                except:
                    config_data[key] = f"<{type(value).__name__} object>"
            else:
                config_data[key] = str(value)
        
        # Add metadata
        config_data['_metadata'] = {
            'generated_at': datetime.now().isoformat(),
            'config_version': '1.0',
            'description': 'Google Maps Link Monitoring Processing Configuration'
        }
        
        # Write to JSON file with proper formatting
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False, sort_keys=True)
        
        logger.info(f"Saved run configuration to: {config_path}")
        return str(config_path)
        
    except Exception as e:
        logger.error(f"Failed to save run configuration: {e}")
        return ""


def write_processing_log_and_config(raw_df: pd.DataFrame, hourly_df: pd.DataFrame, weekly_df: pd.DataFrame,
                                   validation_stats: dict, params: dict, processing_start_time: datetime,
                                   processing_end_time: datetime, output_dir: str) -> Dict[str, str]:
    """
    Write processing log and configuration files to output directory
    
    Args:
        raw_df: Original processed DataFrame
        hourly_df: Hourly aggregation DataFrame
        weekly_df: Weekly profile DataFrame
        validation_stats: Dictionary containing validation statistics
        params: Dictionary containing all processing parameters
        processing_start_time: When processing started
        processing_end_time: When processing completed
        output_dir: Directory to write output files
        
    Returns:
        Dictionary mapping file type to file path
    """
    output_files = {}
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    try:
        # Generate and write processing log
        log_content = generate_processing_log(
            raw_df, hourly_df, weekly_df, validation_stats, 
            processing_start_time, processing_end_time
        )
        
        log_path = output_path / 'processing_log.txt'
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(log_content)
        
        output_files['processing_log'] = str(log_path)
        logger.info(f"Wrote processing log to: {log_path}")
        
        # Save run configuration
        config_path = save_run_configuration(params, output_dir)
        if config_path:
            output_files['run_config'] = config_path
        
    except Exception as e:
        logger.error(f"Error writing processing log and config: {e}")
    
    return output_files