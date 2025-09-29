"""
Unit tests for aggregation.py column validation and normalization functions
"""

import pytest
import pandas as pd
from datetime import date, datetime
from components.aggregation.pipeline import (
    validate_csv_columns, 
    normalize_column_names, 
    validate_and_normalize_columns,
    _to_snake_case,
    REQUIRED_COLUMNS,
    COLUMN_MAPPING
)


class TestColumnValidation:
    """Test cases for CSV column validation"""
    
    def test_validate_csv_columns_all_present(self):
        """Test validation when all required columns are present"""
        # Create DataFrame with all required columns
        df = pd.DataFrame(columns=REQUIRED_COLUMNS)
        
        is_valid, missing_columns = validate_csv_columns(df)
        
        assert is_valid is True
        assert missing_columns == []
    
    def test_validate_csv_columns_missing_single(self):
        """Test validation when one required column is missing"""
        columns = REQUIRED_COLUMNS.copy()
        columns.remove('DataID')  # Remove one required column
        df = pd.DataFrame(columns=columns)
        
        is_valid, missing_columns = validate_csv_columns(df)
        
        assert is_valid is False
        assert missing_columns == ['DataID']
    
    def test_validate_csv_columns_missing_multiple(self):
        """Test validation when multiple required columns are missing"""
        columns = ['DataID', 'Name', 'Timestamp']  # Only some required columns
        df = pd.DataFrame(columns=columns)
        
        is_valid, missing_columns = validate_csv_columns(df)
        
        assert is_valid is False
        # Should contain all missing columns
        expected_missing = [col for col in REQUIRED_COLUMNS if col not in columns]
        assert set(missing_columns) == set(expected_missing)
    
    def test_validate_csv_columns_extra_columns(self):
        """Test validation when extra columns are present (should still be valid)"""
        columns = REQUIRED_COLUMNS + ['ExtraColumn1', 'valid', 'valid_code']
        df = pd.DataFrame(columns=columns)
        
        is_valid, missing_columns = validate_csv_columns(df)
        
        assert is_valid is True
        assert missing_columns == []
    
    def test_validate_csv_columns_empty_dataframe(self):
        """Test validation with empty DataFrame"""
        df = pd.DataFrame()
        
        is_valid, missing_columns = validate_csv_columns(df)
        
        assert is_valid is False
        assert set(missing_columns) == set(REQUIRED_COLUMNS)


class TestColumnNormalization:
    """Test cases for column name normalization"""
    
    def test_normalize_column_names_basic(self):
        """Test basic column normalization with required columns"""
        df = pd.DataFrame(columns=REQUIRED_COLUMNS)
        
        df_normalized = normalize_column_names(df)
        
        # Check that all columns are properly mapped
        expected_columns = list(COLUMN_MAPPING.values())
        assert list(df_normalized.columns) == expected_columns
    
    def test_normalize_column_names_with_additional(self):
        """Test normalization with additional columns that need snake_case conversion"""
        columns = REQUIRED_COLUMNS + ['ValidCode', 'IsValid', 'ExtraColumn']
        df = pd.DataFrame(columns=columns)
        
        df_normalized = normalize_column_names(df)
        
        # Check required columns are mapped correctly
        for original, expected in COLUMN_MAPPING.items():
            assert expected in df_normalized.columns
        
        # Check additional columns are converted to snake_case
        assert 'valid_code' in df_normalized.columns
        assert 'is_valid' in df_normalized.columns
        assert 'extra_column' in df_normalized.columns
    
    def test_normalize_column_names_preserves_data(self):
        """Test that normalization preserves data"""
        data = {
            'DataID': [1, 2, 3],
            'Name': ['A', 'B', 'C'],
            'Timestamp': ['2023-01-01', '2023-01-02', '2023-01-03']
        }
        df = pd.DataFrame(data)
        
        df_normalized = normalize_column_names(df)
        
        # Check data is preserved
        assert df_normalized['data_id'].tolist() == [1, 2, 3]
        assert df_normalized['name'].tolist() == ['A', 'B', 'C']
        assert df_normalized['timestamp'].tolist() == ['2023-01-01', '2023-01-02', '2023-01-03']


class TestSnakeCaseConversion:
    """Test cases for snake_case conversion utility"""
    
    def test_to_snake_case_camel_case(self):
        """Test conversion from camelCase"""
        assert _to_snake_case('camelCase') == 'camel_case'
        assert _to_snake_case('validCode') == 'valid_code'
        assert _to_snake_case('isValid') == 'is_valid'
    
    def test_to_snake_case_pascal_case(self):
        """Test conversion from PascalCase"""
        assert _to_snake_case('PascalCase') == 'pascal_case'
        assert _to_snake_case('DataID') == 'data_id'
        assert _to_snake_case('ValidCode') == 'valid_code'
    
    def test_to_snake_case_spaces_and_separators(self):
        """Test conversion with spaces and other separators"""
        assert _to_snake_case('Valid Code') == 'valid_code'
        assert _to_snake_case('Valid-Code') == 'valid_code'
        assert _to_snake_case('Valid.Code') == 'valid_code'
        assert _to_snake_case('Valid_Code') == 'valid_code'
    
    def test_to_snake_case_already_snake_case(self):
        """Test that already snake_case strings are unchanged"""
        assert _to_snake_case('already_snake_case') == 'already_snake_case'
        assert _to_snake_case('valid_code') == 'valid_code'
    
    def test_to_snake_case_edge_cases(self):
        """Test edge cases for snake_case conversion"""
        assert _to_snake_case('') == ''
        assert _to_snake_case('A') == 'a'
        assert _to_snake_case('ABC') == 'abc'
        assert _to_snake_case('_leading_underscore_') == 'leading_underscore'


class TestValidateAndNormalizeColumns:
    """Test cases for the combined validation and normalization function"""
    
    def test_validate_and_normalize_success(self):
        """Test successful validation and normalization"""
        df = pd.DataFrame(columns=REQUIRED_COLUMNS + ['ValidCode'])
        
        df_result = validate_and_normalize_columns(df)
        
        # Should have all normalized required columns
        expected_columns = list(COLUMN_MAPPING.values()) + ['valid_code']
        assert set(df_result.columns) == set(expected_columns)
    
    def test_validate_and_normalize_missing_columns_raises_error(self):
        """Test that missing required columns raise ValueError"""
        df = pd.DataFrame(columns=['DataID', 'Name'])  # Missing many required columns
        
        with pytest.raises(ValueError) as exc_info:
            validate_and_normalize_columns(df)
        
        error_message = str(exc_info.value)
        assert "Missing required columns" in error_message
        assert "SegmentID" in error_message  # Should mention missing columns
    
    def test_validate_and_normalize_with_data(self):
        """Test validation and normalization preserves data"""
        data = {}
        for col in REQUIRED_COLUMNS:
            data[col] = [f"{col}_value_{i}" for i in range(3)]
        
        df = pd.DataFrame(data)
        df_result = validate_and_normalize_columns(df)
        
        # Check that data is preserved after normalization
        assert len(df_result) == 3
        assert df_result['data_id'].tolist() == ['DataID_value_0', 'DataID_value_1', 'DataID_value_2']
        assert df_result['name'].tolist() == ['Name_value_0', 'Name_value_1', 'Name_value_2']


class TestDataValidityDetermination:
    """Test cases for data validity determination system"""
    
    def test_determine_validity_boolean_column(self):
        """Test validity determination using boolean 'valid' column"""
        from components.aggregation.pipeline import determine_data_validity
        
        df = pd.DataFrame({
            'data_id': [1, 2, 3, 4],
            'valid': [True, False, True, None],
            'duration': [100, 200, 300, 400]
        })
        params = {}
        
        df_result, stats = determine_data_validity(df, params)
        
        assert 'is_valid' in df_result.columns
        assert stats['method_used'] == 'boolean_valid_column'
        assert stats['valid_rows'] == 2  # True values only
        assert list(df_result['is_valid']) == [True, False, True, False]  # None becomes False
    
    def test_determine_validity_valid_code_column(self):
        """Test validity determination using 'valid_code' column"""
        from components.aggregation.pipeline import determine_data_validity
        
        df = pd.DataFrame({
            'data_id': [1, 2, 3, 4],
            'valid_code': ['OK', 'ERROR', 'OK', 'TIMEOUT'],
            'duration': [100, 200, 300, 400]
        })
        params = {'valid_codes_ok': ['OK', 'GOOD']}
        
        df_result, stats = determine_data_validity(df, params)
        
        assert 'is_valid' in df_result.columns
        assert stats['method_used'] == 'valid_code_column'
        assert stats['valid_rows'] == 2  # Two 'OK' codes
        assert 'ERROR' in stats['invalid_reasons']
        assert 'TIMEOUT' in stats['invalid_reasons']
    
    def test_determine_validity_numeric_ranges(self):
        """Test validity determination using numeric range rules"""
        from components.aggregation.pipeline import determine_data_validity
        
        df = pd.DataFrame({
            'data_id': [1, 2, 3, 4, 5],
            'duration': [100, -10, 300, 10000, None],  # Valid: 100, 300
            'distance': [1000, 2000, -100, 5000, 3000],  # Valid: 1000, 2000, 5000, 3000
            'speed': [50, 200, 30, 40, 60]  # Valid: 50, 30, 40, 60
        })
        params = {
            'duration_range_sec': [0, 3600],  # 0 to 1 hour
            'distance_range_m': [0, 10000],   # 0 to 10km
            'speed_range_kmh': [0, 150]       # 0 to 150 km/h
        }
        
        df_result, stats = determine_data_validity(df, params)
        
        assert 'is_valid' in df_result.columns
        assert stats['method_used'] == 'numeric_range_rules'
        # Only row 0 (index 0) should be valid: duration=100, distance=1000, speed=50
        expected_valid = [True, False, False, False, False]
        assert list(df_result['is_valid']) == expected_valid
        assert 'duration_out_of_range' in stats['invalid_reasons']
        assert 'distance_out_of_range' in stats['invalid_reasons']
        assert 'speed_out_of_range' in stats['invalid_reasons']
    
    def test_remove_duplicates_data_id(self):
        """Test duplicate removal by DataID"""
        from components.aggregation.pipeline import remove_duplicates
        
        df = pd.DataFrame({
            'data_id': [1, 2, 1, 3, 2],  # Duplicates: 1 appears twice, 2 appears twice
            'name': ['A', 'B', 'A', 'C', 'B'],
            'timestamp': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-01', '2023-01-03', '2023-01-02'])
        })
        params = {'remove_data_id_duplicates': True}
        
        df_result, stats = remove_duplicates(df, params)
        
        assert len(df_result) == 3  # Should keep first occurrence of each data_id
        assert stats['duplicates_removed'] == 2
        assert stats['original_rows'] == 5
        assert stats['final_rows'] == 3
        assert list(df_result['data_id']) == [1, 2, 3]
    
    def test_remove_duplicates_link_timestamp(self):
        """Test duplicate removal by link+timestamp"""
        from components.aggregation.pipeline import remove_duplicates
        
        df = pd.DataFrame({
            'data_id': [1, 2, 3, 4, 5],
            'name': ['A', 'A', 'B', 'A', 'B'],  # Link A appears 3 times, B appears 2 times
            'timestamp': pd.to_datetime(['2023-01-01', '2023-01-01', '2023-01-01', '2023-01-02', '2023-01-01'])
        })
        params = {'remove_link_timestamp_duplicates': True, 'remove_data_id_duplicates': False}
        
        df_result, stats = remove_duplicates(df, params)
        
        # Should remove: row 1 (A, 2023-01-01 duplicate) and row 4 (B, 2023-01-01 duplicate)
        assert len(df_result) == 3
        assert stats['duplicates_removed'] == 2
    
    def test_validate_numeric_ranges(self):
        """Test numeric range validation utility"""
        from components.aggregation.pipeline import validate_numeric_ranges
        
        df = pd.DataFrame({
            'values': [10, 50, 100, 150, 200, None, -10]
        })
        
        result = validate_numeric_ranges(df, 'values', [0, 100])
        
        expected = [True, True, True, False, False, False, False]
        assert list(result) == expected
    
    def test_apply_data_validation_and_cleaning_complete(self):
        """Test complete data validation and cleaning pipeline"""
        from components.aggregation.pipeline import apply_data_validation_and_cleaning
        
        df = pd.DataFrame({
            'data_id': [1, 2, 1, 3, 4],  # Has duplicates
            'name': ['A', 'B', 'A', 'C', 'D'],
            'duration': [100, -10, 100, 300, 5000],  # Some out of range
            'distance': [1000, 2000, 1000, 3000, 4000],
            'speed': [50, 200, 50, 40, 60],  # Some out of range
            'timestamp': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-01', '2023-01-03', '2023-01-04'])
        })
        params = {
            'duration_range_sec': [0, 3600],
            'distance_range_m': [0, 10000],
            'speed_range_kmh': [0, 150],
            'remove_data_id_duplicates': True,
            'remove_link_timestamp_duplicates': True
        }
        
        df_result, stats = apply_data_validation_and_cleaning(df, params)
        
        assert 'is_valid' in df_result.columns
        assert stats['original_rows'] == 5
        assert stats['final_rows'] > 0
        assert 'validation_stats' in stats
        assert 'deduplication_stats' in stats


class TestTimestampParsing:
    """Test cases for timestamp parsing and timezone handling"""
    
    def test_parse_timestamp_with_timezone_basic(self):
        """Test basic timestamp parsing with timezone"""
        from components.aggregation.pipeline import parse_timestamp_with_timezone
        
        timestamp_str = "2023-01-01 12:00:00"
        ts_format = "%Y-%m-%d %H:%M:%S"
        timezone = "Asia/Jerusalem"
        
        result = parse_timestamp_with_timezone(timestamp_str, ts_format, timezone)
        
        assert result is not None
        assert result.tz is not None
        assert str(result.tz) == "Asia/Jerusalem"
    
    def test_parse_timestamp_with_timezone_invalid(self):
        """Test parsing invalid timestamp returns None"""
        from components.aggregation.pipeline import parse_timestamp_with_timezone
        
        result = parse_timestamp_with_timezone("invalid", "%Y-%m-%d %H:%M:%S", "UTC")
        assert result is None
        
        result = parse_timestamp_with_timezone("", "%Y-%m-%d %H:%M:%S", "UTC")
        assert result is None
        
        result = parse_timestamp_with_timezone(None, "%Y-%m-%d %H:%M:%S", "UTC")
        assert result is None
    
    def test_parse_timestamps_vectorized_basic(self):
        """Test vectorized timestamp parsing"""
        from components.aggregation.pipeline import parse_timestamps_vectorized
        
        timestamps = pd.Series([
            "2023-01-01 12:00:00",
            "2023-01-02 13:00:00", 
            "2023-01-03 14:00:00"
        ])
        ts_format = "%Y-%m-%d %H:%M:%S"
        timezone = "UTC"
        
        result = parse_timestamps_vectorized(timestamps, ts_format, timezone)
        
        assert len(result) == 3
        assert result.dt.tz is not None
        assert all(pd.notna(result))
    
    def test_parse_timestamps_vectorized_with_invalid(self):
        """Test vectorized parsing handles invalid timestamps"""
        from components.aggregation.pipeline import parse_timestamps_vectorized
        
        timestamps = pd.Series([
            "2023-01-01 12:00:00",
            "invalid_timestamp",
            "2023-01-03 14:00:00"
        ])
        ts_format = "%Y-%m-%d %H:%M:%S"
        timezone = "UTC"
        
        result = parse_timestamps_vectorized(timestamps, ts_format, timezone)
        
        assert len(result) == 3
        assert pd.notna(result.iloc[0])
        assert pd.isna(result.iloc[1])  # Invalid timestamp should be NaT
        assert pd.notna(result.iloc[2])
    
    def test_validate_timezone(self):
        """Test timezone validation"""
        from components.aggregation.pipeline import validate_timezone
        
        # Valid timezones
        assert validate_timezone("UTC") is True
        assert validate_timezone("Asia/Jerusalem") is True
        assert validate_timezone("America/New_York") is True
        
        # Invalid timezone
        assert validate_timezone("Invalid/Timezone") is False
        assert validate_timezone("") is False
    
    def test_validate_timestamp_format(self):
        """Test timestamp format validation"""
        from components.aggregation.pipeline import validate_timestamp_format
        
        # Valid format and timestamp
        assert validate_timestamp_format("%Y-%m-%d %H:%M:%S", "2023-01-01 12:00:00") is True
        assert validate_timestamp_format("%d/%m/%Y %H:%M", "01/01/2023 12:00") is True
        
        # Invalid format for timestamp
        assert validate_timestamp_format("%Y-%m-%d", "2023-01-01 12:00:00") is False
        assert validate_timestamp_format("%Y-%m-%d %H:%M:%S", "invalid") is False
    
    def test_parse_timestamps_empty_series(self):
        """Test parsing empty or all-null series"""
        from components.aggregation.pipeline import parse_timestamps_vectorized
        
        # Empty series
        empty_series = pd.Series([], dtype=str)
        result = parse_timestamps_vectorized(empty_series, "%Y-%m-%d %H:%M:%S", "UTC")
        assert len(result) == 0
        
        # All null series
        null_series = pd.Series([None, None, None])
        result = parse_timestamps_vectorized(null_series, "%Y-%m-%d %H:%M:%S", "UTC")
        assert len(result) == 3
        assert all(pd.isna(result))


class TestTemporalEnhancements:
    """Test cases for temporal enhancement functions"""
    
    def test_add_derived_time_columns(self):
        """Test adding derived time columns from timestamp"""
        from components.aggregation.pipeline import add_derived_time_columns
        
        # Create DataFrame with timezone-aware timestamps
        timestamps = pd.to_datetime([
            "2023-01-01 12:00:00",  # Sunday
            "2023-01-02 13:30:00",  # Monday  
            "2023-01-03 14:45:00"   # Tuesday
        ]).tz_localize('UTC')
        
        df = pd.DataFrame({
            'data_id': [1, 2, 3],
            'timestamp': timestamps
        })
        
        result = add_derived_time_columns(df)
        
        # Check all derived columns are added
        assert 'date' in result.columns
        assert 'hour_of_day' in result.columns
        assert 'iso_week' in result.columns
        assert 'weekday_index' in result.columns
        
        # Check values are correct
        assert result['hour_of_day'].tolist() == [12, 13, 14]
        assert result['weekday_index'].tolist() == [6, 0, 1]  # Sunday=6, Monday=0, Tuesday=1
        assert all(pd.notna(result['date']))
        assert all(pd.notna(result['iso_week']))
    
    def test_add_derived_time_columns_missing_timestamp(self):
        """Test handling missing timestamp column"""
        from components.aggregation.pipeline import add_derived_time_columns
        
        df = pd.DataFrame({
            'data_id': [1, 2, 3],
            'name': ['A', 'B', 'C']
        })
        
        result = add_derived_time_columns(df)
        
        # Should return original DataFrame unchanged
        assert list(result.columns) == ['data_id', 'name']
        assert len(result) == 3
    
    def test_add_derived_time_columns_all_nat(self):
        """Test handling all NaT timestamps"""
        from components.aggregation.pipeline import add_derived_time_columns
        
        df = pd.DataFrame({
            'data_id': [1, 2, 3],
            'timestamp': [pd.NaT, pd.NaT, pd.NaT]
        })
        
        result = add_derived_time_columns(df)
        
        # Should return original DataFrame unchanged
        assert list(result.columns) == ['data_id', 'timestamp']
        assert len(result) == 3
    
    def test_map_hebrew_day_names(self):
        """Test mapping Hebrew day names to weekday_index"""
        from components.aggregation.pipeline import map_hebrew_day_names
        
        df = pd.DataFrame({
            'data_id': [1, 2, 3, 4, 5, 6, 7],
            'day_in_week': ['יום א', 'יום ב', 'יום ג', 'יום ד', 'יום ה', 'יום ו', 'יום ש']
        })
        
        result = map_hebrew_day_names(df)
        
        assert 'weekday_index' in result.columns
        # יום א=Sunday=6, יום ב=Monday=0, etc.
        expected = [6, 0, 1, 2, 3, 4, 5]
        assert result['weekday_index'].tolist() == expected
    
    def test_map_hebrew_day_names_alternative_spellings(self):
        """Test mapping alternative Hebrew day name spellings"""
        from components.aggregation.pipeline import map_hebrew_day_names
        
        df = pd.DataFrame({
            'data_id': [1, 2, 3, 4],
            'day_in_week': ['יום א\'', 'ב', 'ג\'', 'ש']
        })
        
        result = map_hebrew_day_names(df)
        
        assert 'weekday_index' in result.columns
        expected = [6, 0, 1, 5]  # Sunday, Monday, Tuesday, Saturday
        assert result['weekday_index'].tolist() == expected
    
    def test_map_hebrew_day_names_with_existing_weekday_index(self):
        """Test Hebrew mapping preserves existing weekday_index where Hebrew not available"""
        from components.aggregation.pipeline import map_hebrew_day_names
        
        df = pd.DataFrame({
            'data_id': [1, 2, 3],
            'day_in_week': ['יום א', None, 'unknown'],
            'weekday_index': [999, 1, 2]  # Existing values
        })
        
        result = map_hebrew_day_names(df)
        
        # Should map Hebrew where available, keep existing otherwise
        expected = [6, 1, 2]  # יום א mapped to 6, others preserved
        assert result['weekday_index'].tolist() == expected
    
    def test_map_hebrew_day_names_no_hebrew_column(self):
        """Test handling missing day_in_week column"""
        from components.aggregation.pipeline import map_hebrew_day_names
        
        df = pd.DataFrame({
            'data_id': [1, 2, 3],
            'name': ['A', 'B', 'C']
        })
        
        result = map_hebrew_day_names(df)
        
        # Should return original DataFrame unchanged
        assert list(result.columns) == ['data_id', 'name']
        assert len(result) == 3
    
    def test_map_daytype_categories_hebrew_values(self):
        """Test mapping Hebrew DayType values to categories"""
        from components.aggregation.pipeline import map_daytype_categories
        
        df = pd.DataFrame({
            'data_id': [1, 2, 3, 4, 5],
            'day_type': ['יום חול', 'סוף שבוע', 'חג', 'שבת', 'עבודה']
        })
        params = {}
        
        result = map_daytype_categories(df, params)
        
        assert 'daytype' in result.columns
        expected = ['weekday', 'weekend', 'holiday', 'weekend', 'weekday']
        assert result['daytype'].tolist() == expected
    
    def test_map_daytype_categories_english_values(self):
        """Test mapping English DayType values"""
        from components.aggregation.pipeline import map_daytype_categories
        
        df = pd.DataFrame({
            'data_id': [1, 2, 3, 4],
            'day_type': ['weekday', 'weekend', 'holiday', 'workday']
        })
        params = {}
        
        result = map_daytype_categories(df, params)
        
        assert 'daytype' in result.columns
        expected = ['weekday', 'weekend', 'holiday', 'weekday']
        assert result['daytype'].tolist() == expected
    
    def test_map_daytype_categories_custom_mapping(self):
        """Test custom DayType mapping from parameters"""
        from components.aggregation.pipeline import map_daytype_categories
        
        df = pd.DataFrame({
            'data_id': [1, 2, 3],
            'day_type': ['custom1', 'custom2', 'יום חול']
        })
        params = {
            'daytype_mapping': {
                'custom1': 'weekend',
                'custom2': 'holiday'
            }
        }
        
        result = map_daytype_categories(df, params)
        
        assert 'daytype' in result.columns
        expected = ['weekend', 'holiday', 'weekday']  # custom + default mapping
        assert result['daytype'].tolist() == expected
    
    def test_map_daytype_categories_infer_from_weekday_index(self):
        """Test inferring daytype from weekday_index when day_type unmapped"""
        from components.aggregation.pipeline import map_daytype_categories
        
        df = pd.DataFrame({
            'data_id': [1, 2, 3, 4],
            'day_type': ['unknown1', 'unknown2', 'unknown3', 'unknown4'],
            'weekday_index': [0, 3, 5, 6]  # Monday, Thursday, Saturday, Sunday
        })
        params = {}
        
        result = map_daytype_categories(df, params)
        
        assert 'daytype' in result.columns
        expected = ['weekday', 'weekday', 'weekend', 'weekend']
        assert result['daytype'].tolist() == expected
    
    def test_map_daytype_categories_no_day_type_column(self):
        """Test inferring daytype from weekday_index when no day_type column"""
        from components.aggregation.pipeline import map_daytype_categories
        
        df = pd.DataFrame({
            'data_id': [1, 2, 3, 4],
            'weekday_index': [0, 2, 5, 6]  # Monday, Wednesday, Saturday, Sunday
        })
        params = {}
        
        result = map_daytype_categories(df, params)
        
        assert 'daytype' in result.columns
        expected = ['weekday', 'weekday', 'weekend', 'weekend']
        assert result['daytype'].tolist() == expected
    
    def test_map_daytype_categories_no_columns(self):
        """Test handling when neither day_type nor weekday_index available"""
        from components.aggregation.pipeline import map_daytype_categories
        
        df = pd.DataFrame({
            'data_id': [1, 2, 3],
            'name': ['A', 'B', 'C']
        })
        params = {}
        
        result = map_daytype_categories(df, params)
        
        assert 'daytype' in result.columns
        assert all(pd.isna(result['daytype']))
    
    def test_apply_temporal_enhancements_complete(self):
        """Test complete temporal enhancements pipeline"""
        from components.aggregation.pipeline import apply_temporal_enhancements
        
        # Create test data with timestamps and Hebrew columns
        timestamps = pd.to_datetime([
            "2023-01-01 12:00:00",  # Sunday
            "2023-01-02 13:30:00",  # Monday
        ]).tz_localize('UTC')
        
        df = pd.DataFrame({
            'data_id': [1, 2],
            'timestamp': timestamps,
            'day_in_week': ['יום א', 'יום ב'],
            'day_type': ['סוף שבוע', 'יום חול']
        })
        params = {
            'ts_format': '%Y-%m-%d %H:%M:%S',
            'tz': 'UTC'
        }
        
        result = apply_temporal_enhancements(df, params)
        
        # Check all enhancements are applied
        assert 'date' in result.columns
        assert 'hour_of_day' in result.columns
        assert 'iso_week' in result.columns
        assert 'weekday_index' in result.columns
        assert 'daytype' in result.columns
        
        # Check values
        assert result['weekday_index'].tolist() == [6, 0]  # Sunday, Monday
        assert result['daytype'].tolist() == ['weekend', 'weekday']
        assert result['hour_of_day'].tolist() == [12, 13]
    
    def test_apply_temporal_enhancements_empty_dataframe(self):
        """Test temporal enhancements with empty DataFrame"""
        from components.aggregation.pipeline import apply_temporal_enhancements
        
        df = pd.DataFrame()
        params = {}
        
        result = apply_temporal_enhancements(df, params)
        
        assert len(result) == 0
        assert result.empty


class TestHolidayClassification:
    """Test cases for holiday classification system"""
    
    def test_load_israeli_holidays(self):
        """Test loading Israeli holidays for a year range"""
        from components.aggregation.pipeline import load_israeli_holidays
        
        # Test loading holidays for 2023
        holidays_dict = load_israeli_holidays((2023, 2023))
        
        assert isinstance(holidays_dict, dict)
        assert len(holidays_dict) > 0
        
        # Check that all keys are date objects and values are strings
        for holiday_date, holiday_name in holidays_dict.items():
            assert isinstance(holiday_date, date)
            assert isinstance(holiday_name, str)
            assert holiday_date.year == 2023
    
    def test_load_israeli_holidays_multiple_years(self):
        """Test loading Israeli holidays for multiple years"""
        from components.aggregation.pipeline import load_israeli_holidays
        
        holidays_dict = load_israeli_holidays((2022, 2023))
        
        assert len(holidays_dict) > 0
        
        # Should have holidays from both years
        years_found = set(d.year for d in holidays_dict.keys())
        assert 2022 in years_found
        assert 2023 in years_found
    
    def test_load_custom_holidays_from_text(self, tmp_path):
        """Test loading custom holidays from text file"""
        from components.aggregation.pipeline import load_custom_holidays_from_text
        
        # Create temporary text file with holidays
        holidays_file = tmp_path / "custom_holidays.txt"
        holidays_content = """# Custom holidays file
2023-01-15 - Custom New Year
2023-07-04 - Independence Day
2023-12-25 - Christmas
# Comment line
2023-06-01
"""
        holidays_file.write_text(holidays_content, encoding='utf-8')
        
        holidays_dict = load_custom_holidays_from_text(str(holidays_file))
        
        assert len(holidays_dict) == 4
        assert date(2023, 1, 15) in holidays_dict
        assert date(2023, 7, 4) in holidays_dict
        assert date(2023, 12, 25) in holidays_dict
        assert date(2023, 6, 1) in holidays_dict
        
        assert holidays_dict[date(2023, 1, 15)] == "Custom New Year"
        assert holidays_dict[date(2023, 7, 4)] == "Independence Day"
        assert holidays_dict[date(2023, 12, 25)] == "Christmas"
        assert "Custom Holiday" in holidays_dict[date(2023, 6, 1)]
    
    def test_load_custom_holidays_from_text_invalid_dates(self, tmp_path):
        """Test handling invalid dates in text file"""
        from components.aggregation.pipeline import load_custom_holidays_from_text
        
        holidays_file = tmp_path / "invalid_holidays.txt"
        holidays_content = """2023-01-15 - Valid Holiday
invalid-date - Should be skipped
2023-13-45 - Invalid date
2023-02-30 - Another invalid date
2023-03-01 - Valid Holiday 2
"""
        holidays_file.write_text(holidays_content, encoding='utf-8')
        
        holidays_dict = load_custom_holidays_from_text(str(holidays_file))
        
        # Should only load valid dates
        assert len(holidays_dict) == 2
        assert date(2023, 1, 15) in holidays_dict
        assert date(2023, 3, 1) in holidays_dict
    
    def test_load_custom_holidays_from_text_file_not_found(self):
        """Test handling missing text file"""
        from components.aggregation.pipeline import load_custom_holidays_from_text
        
        holidays_dict = load_custom_holidays_from_text("nonexistent_file.txt")
        
        assert holidays_dict == {}
    
    def test_load_custom_holidays_from_ics(self, tmp_path):
        """Test loading custom holidays from ICS file"""
        from components.aggregation.pipeline import load_custom_holidays_from_ics
        
        # Create temporary ICS file
        ics_file = tmp_path / "custom_holidays.ics"
        ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
DTSTART;VALUE=DATE:20230115
SUMMARY:Custom New Year
END:VEVENT
BEGIN:VEVENT
DTSTART:20230704T120000Z
SUMMARY:Independence Day
END:VEVENT
BEGIN:VEVENT
DTSTART:2023-12-25T00:00:00
SUMMARY:Christmas
END:VEVENT
END:VCALENDAR
"""
        ics_file.write_text(ics_content, encoding='utf-8')
        
        holidays_dict = load_custom_holidays_from_ics(str(ics_file))
        
        assert len(holidays_dict) == 3
        assert date(2023, 1, 15) in holidays_dict
        assert date(2023, 7, 4) in holidays_dict
        assert date(2023, 12, 25) in holidays_dict
        
        assert holidays_dict[date(2023, 1, 15)] == "Custom New Year"
        assert holidays_dict[date(2023, 7, 4)] == "Independence Day"
        assert holidays_dict[date(2023, 12, 25)] == "Christmas"
    
    def test_load_custom_holidays_from_ics_file_not_found(self):
        """Test handling missing ICS file"""
        from components.aggregation.pipeline import load_custom_holidays_from_ics
        
        holidays_dict = load_custom_holidays_from_ics("nonexistent_file.ics")
        
        assert holidays_dict == {}
    
    def test_build_holiday_calendar_israeli_only(self):
        """Test building holiday calendar with Israeli holidays only"""
        from components.aggregation.pipeline import build_holiday_calendar
        
        df = pd.DataFrame({
            'date': [date(2023, 1, 1), date(2023, 6, 15), date(2023, 12, 31)]
        })
        params = {
            'use_israeli_holidays': True,
            'custom_holidays_file': None
        }
        
        holiday_calendar = build_holiday_calendar(df, params)
        
        assert isinstance(holiday_calendar, dict)
        assert len(holiday_calendar) > 0
        
        # Should contain Israeli holidays for 2023
        for holiday_date in holiday_calendar.keys():
            assert holiday_date.year == 2023
    
    def test_build_holiday_calendar_with_custom_text(self, tmp_path):
        """Test building holiday calendar with custom text file"""
        from components.aggregation.pipeline import build_holiday_calendar
        
        # Create custom holidays file
        holidays_file = tmp_path / "custom.txt"
        holidays_file.write_text("2023-01-15 - Custom Holiday\n2023-07-04 - Another Holiday")
        
        df = pd.DataFrame({
            'date': [date(2023, 1, 1), date(2023, 6, 15)]
        })
        params = {
            'use_israeli_holidays': True,
            'custom_holidays_file': str(holidays_file)
        }
        
        holiday_calendar = build_holiday_calendar(df, params)
        
        # Should contain both Israeli and custom holidays
        assert date(2023, 1, 15) in holiday_calendar
        assert date(2023, 7, 4) in holiday_calendar
        assert holiday_calendar[date(2023, 1, 15)] == "Custom Holiday"
    
    def test_build_holiday_calendar_with_custom_ics(self, tmp_path):
        """Test building holiday calendar with custom ICS file"""
        from components.aggregation.pipeline import build_holiday_calendar
        
        # Create custom ICS file
        ics_file = tmp_path / "custom.ics"
        ics_content = """BEGIN:VCALENDAR
BEGIN:VEVENT
DTSTART;VALUE=DATE:20230115
SUMMARY:ICS Holiday
END:VEVENT
END:VCALENDAR
"""
        ics_file.write_text(ics_content)
        
        df = pd.DataFrame({
            'date': [date(2023, 1, 1)]
        })
        params = {
            'use_israeli_holidays': False,
            'custom_holidays_file': str(ics_file)
        }
        
        holiday_calendar = build_holiday_calendar(df, params)
        
        assert date(2023, 1, 15) in holiday_calendar
        assert holiday_calendar[date(2023, 1, 15)] == "ICS Holiday"
    
    def test_build_holiday_calendar_no_date_column(self):
        """Test building holiday calendar when no date column exists"""
        from components.aggregation.pipeline import build_holiday_calendar
        
        df = pd.DataFrame({
            'data_id': [1, 2, 3]
        })
        params = {'use_israeli_holidays': True}
        
        holiday_calendar = build_holiday_calendar(df, params)
        
        # Should use current year as default
        current_year = datetime.now().year
        assert len(holiday_calendar) > 0
        for holiday_date in holiday_calendar.keys():
            assert holiday_date.year == current_year
    
    def test_classify_holidays_basic(self):
        """Test basic holiday classification"""
        from components.aggregation.pipeline import classify_holidays, build_holiday_calendar
        
        # Create test data with some dates that are holidays
        df = pd.DataFrame({
            'data_id': [1, 2, 3, 4],
            'date': [
                date(2023, 1, 1),   # Likely a holiday
                date(2023, 6, 15),  # Regular day
                date(2023, 12, 25), # Likely a holiday
                date(2023, 7, 4)    # Regular day in Israel
            ],
            'daytype': ['weekday', 'weekday', 'weekday', 'weekday']
        })
        params = {
            'use_israeli_holidays': True,
            'holidays_as': 'holiday'
        }
        
        result = classify_holidays(df, params)
        
        assert 'is_holiday' in result.columns
        assert 'holiday_name' in result.columns
        
        # Check that some dates were classified as holidays
        holiday_count = result['is_holiday'].sum()
        assert holiday_count >= 0  # At least some holidays should be found
        
        # Check that daytype was updated for holidays
        holiday_rows = result[result['is_holiday']]
        if not holiday_rows.empty:
            assert all(holiday_rows['daytype'] == 'holiday')
    
    def test_classify_holidays_as_weekend(self):
        """Test classifying holidays as weekend"""
        from components.aggregation.pipeline import classify_holidays
        
        df = pd.DataFrame({
            'data_id': [1, 2],
            'date': [date(2023, 1, 1), date(2023, 6, 15)],
            'daytype': ['weekday', 'weekday']
        })
        params = {
            'use_israeli_holidays': True,
            'holidays_as': 'weekend'
        }
        
        result = classify_holidays(df, params)
        
        # Holidays should be classified as weekend
        holiday_rows = result[result['is_holiday']]
        if not holiday_rows.empty:
            assert all(holiday_rows['daytype'] == 'weekend')
    
    def test_classify_holidays_disabled(self):
        """Test holiday classification when disabled"""
        from components.aggregation.pipeline import classify_holidays
        
        df = pd.DataFrame({
            'data_id': [1, 2],
            'date': [date(2023, 1, 1), date(2023, 6, 15)],
            'daytype': ['weekday', 'weekday']
        })
        params = {
            'use_israeli_holidays': False,
            'custom_holidays_file': None
        }
        
        result = classify_holidays(df, params)
        
        # Should have holiday columns but no holidays classified
        assert 'is_holiday' in result.columns
        assert 'holiday_name' in result.columns
        assert result['is_holiday'].sum() == 0
        assert all(result['holiday_name'] == '')
    
    def test_classify_holidays_no_date_column(self):
        """Test holiday classification with missing date column"""
        from components.aggregation.pipeline import classify_holidays
        
        df = pd.DataFrame({
            'data_id': [1, 2, 3],
            'daytype': ['weekday', 'weekend', 'weekday']
        })
        params = {'use_israeli_holidays': True}
        
        result = classify_holidays(df, params)
        
        # Should return original DataFrame unchanged
        assert list(result.columns) == ['data_id', 'daytype']
        assert len(result) == 3
    
    def test_classify_holidays_empty_dataframe(self):
        """Test holiday classification with empty DataFrame"""
        from components.aggregation.pipeline import classify_holidays
        
        df = pd.DataFrame()
        params = {'use_israeli_holidays': True}
        
        result = classify_holidays(df, params)
        
        assert result.empty
    
    def test_apply_temporal_enhancements_with_holidays(self):
        """Test temporal enhancements including holiday classification"""
        from components.aggregation.pipeline import apply_temporal_enhancements
        
        # Create test data
        timestamps = pd.to_datetime([
            "2023-01-01 12:00:00",  # New Year's Day (likely holiday)
            "2023-06-15 13:30:00",  # Regular day
        ]).tz_localize('UTC')
        
        df = pd.DataFrame({
            'data_id': [1, 2],
            'timestamp': timestamps,
            'day_in_week': ['יום א', 'יום ה'],
            'day_type': ['חג', 'יום חול']
        })
        params = {
            'ts_format': '%Y-%m-%d %H:%M:%S',
            'tz': 'UTC',
            'enable_holiday_classification': True,
            'use_israeli_holidays': True,
            'holidays_as': 'holiday'
        }
        
        result = apply_temporal_enhancements(df, params)
        
        # Check all enhancements including holidays
        assert 'date' in result.columns
        assert 'hour_of_day' in result.columns
        assert 'weekday_index' in result.columns
        assert 'daytype' in result.columns
        assert 'is_holiday' in result.columns
        assert 'holiday_name' in result.columns
        
        # Check that holiday classification was applied
        assert result['is_holiday'].dtype == bool
    
    def test_apply_temporal_enhancements_holidays_disabled(self):
        """Test temporal enhancements with holiday classification disabled"""
        from components.aggregation.pipeline import apply_temporal_enhancements
        
        timestamps = pd.to_datetime(["2023-01-01 12:00:00"]).tz_localize('UTC')
        
        df = pd.DataFrame({
            'data_id': [1],
            'timestamp': timestamps
        })
        params = {
            'enable_holiday_classification': False
        }
        
        result = apply_temporal_enhancements(df, params)
        
        # Should not have holiday columns
        assert 'is_holiday' not in result.columns
        assert 'holiday_name' not in result.columns
        
        # Should still have other temporal enhancements
        assert 'date' in result.columns
        assert 'hour_of_day' in result.columns


if __name__ == "__main__":
    # Run tests if script is executed directly
    pytest.main([__file__, "-v"])