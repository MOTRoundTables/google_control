"""
Dataset Control Report - Link-level reporting and shapefile generation.

This module handles aggregation of validation results and generation of
per-link reports with transparent metrics instead of confusing result codes.
"""

from typing import Dict, Any, Optional
import pandas as pd
import geopandas as gpd
from enum import IntEnum
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp
import os

from pathlib import Path
import shutil
import tempfile

# Legacy enum for backwards compatibility with tests
class ResultCode(IntEnum):
    """Legacy result codes for backwards compatibility."""
    SUCCESS = 0
    FAILED_HAUSDORFF = 1
    MISSING_POLYLINE = 2
    LINK_NOT_IN_SHAPEFILE = 3
    NO_OBSERVATIONS = 4
    # Single alternative codes
    SINGLE_ALT_ALL_VALID = 20
    SINGLE_ALT_PARTIAL = 21
    SINGLE_ALT_ALL_INVALID = 22
    # Multi alternative codes
    MULTI_ALT_ALL_VALID = 30
    MULTI_ALT_PARTIAL = 31
    MULTI_ALT_ALL_INVALID = 32
    # Not recorded
    NOT_RECORDED = 41
    ALL_VALID = SUCCESS
    PARTIAL = SINGLE_ALT_PARTIAL
    ALL_INVALID = SINGLE_ALT_ALL_INVALID
from datetime import date, datetime, timedelta
import numpy as np

try:
    import pyogrio  # type: ignore[import]
except ImportError:  # pragma: no cover - optional dependency
    pyogrio = None  # type: ignore[assignment]

def _parse_timestamp_series(series: pd.Series) -> pd.Series:
    """Coerce a timestamp-like series into timezone-naive datetimes with fallbacks."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return series

    parsed = pd.to_datetime(series, errors='coerce', dayfirst=True)

    if parsed.isna().any():
        parsed_dayfirst = pd.to_datetime(series, errors='coerce', dayfirst=True)
        parsed = parsed.fillna(parsed_dayfirst)

    if parsed.isna().any():
        try:
            parsed_iso = pd.to_datetime(series, errors='coerce', format='ISO8601')
            parsed = parsed.fillna(parsed_iso)
        except (TypeError, ValueError):
            pass

    if pd.api.types.is_datetime64tz_dtype(parsed.dtype):
        parsed = parsed.dt.tz_localize(None)

    return parsed


def determine_result_code(stats: Dict[str, Any]) -> tuple:
    """
    Legacy function to determine result code for a link.
    For backwards compatibility with existing tests.

    Args:
        stats: Dictionary with link statistics

    Returns:
        Tuple of (result_code, result_label, num percentage)
    """
    total_obs = stats.get('total_observations', 0)
    valid_obs = stats.get('valid_observations', 0)
    invalid_obs = stats.get('invalid_observations', total_obs - valid_obs)

    multi_alt = stats.get('multi_alternative_count', 0) or 0
    single_alt = stats.get('single_alternative_count', 0) or 0

    if total_obs == 0:
        return (ResultCode.NOT_RECORDED, "did not record", None)

    success_pct = (valid_obs / total_obs * 100) if total_obs else 0.0

    if multi_alt > 0:
        label = "RouteAlternative greater than one"
        if success_pct == 100:
            return (ResultCode.MULTI_ALT_ALL_VALID, label, 100.0)
        if success_pct > 0:
            return (ResultCode.MULTI_ALT_PARTIAL, label, success_pct)
        return (ResultCode.MULTI_ALT_ALL_INVALID, label, 0.0)

    label_single_partial = "no RouteAlternative"
    label_single_invalid = "no RouteAlternative and all invalid"

    if success_pct == 100:
        return (ResultCode.ALL_VALID, "valid", 100.0)
    if success_pct > 0:
        return (ResultCode.SINGLE_ALT_PARTIAL, label_single_partial, success_pct)
    return (ResultCode.SINGLE_ALT_ALL_INVALID, label_single_invalid, 0.0)


def calculate_expected_observations(start_date: date, end_date: date, interval_minutes: int) -> int:
    """
    Calculate expected number of observations based on recording schedule.

    Args:
        start_date: Recording start date
        end_date: Recording end date
        interval_minutes: Minutes between observations

    Returns:
        Expected number of observations (24/7 recording)
    """
    if not start_date or not end_date:
        return 0

    # Validate date range
    if start_date > end_date:
        return 0  # Invalid range

    # Convert to datetime (inclusive date range)
    start_dt = datetime.combine(start_date, datetime.min.time())
    # For end date, include the full end date by going to 00:00 of next day
    end_dt = datetime.combine(end_date + timedelta(days=1), datetime.min.time())

    # Calculate total minutes
    total_minutes = (end_dt - start_dt).total_seconds() / 60

    # Calculate expected observations (every interval_minutes within the time range)
    expected_observations = int(total_minutes / interval_minutes)

    return expected_observations


def deduplicate_observations(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove duplicate observations by link_id, timestamp, polyline.

    Args:
        df: Input DataFrame

    Returns:
        Deduplicated DataFrame
    """
    if df.empty:
        return df

    # Ensure required columns exist
    required_cols = ['link_id', 'timestamp', 'polyline']
    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        # If missing required columns, return original DataFrame
        return df

    # Remove duplicates based on the combination of link_id, timestamp, and polyline
    deduplicated = df.drop_duplicates(subset=['link_id', 'timestamp', 'polyline'], keep='first')

    return deduplicated.reset_index(drop=True)


def _process_link_chunk(chunk_data):
    """
    Worker function to process a chunk of shapefile rows in parallel.

    Args:
        chunk_data: Tuple containing (chunk_indices, stats_by_link, completeness_params, empty_stats)

    Returns:
        Dictionary mapping index to computed statistics
    """
    chunk_indices, chunk_join_keys, stats_by_link, completeness_params, empty_stats = chunk_data

    # Import here to avoid pickle issues in multiprocessing
    import numpy as np

    results = {}

    for idx, link_join_key in zip(chunk_indices, chunk_join_keys):
        # Aggregate statistics for this link
        stats = stats_by_link.get(link_join_key, empty_stats)

        # Assign transparent metrics directly from stats
        total_observations = stats.get('total_observations', 0)
        successful_observations = stats.get('successful_observations', 0)

        # Calculate derived metrics
        failed_observations = total_observations - successful_observations

        row_updates = {}

        # Backwards compatibility fields (for tests)
        row_updates['success_rate'] = stats.get('success_rate', 0.0) if total_observations > 0 else np.nan
        row_updates['total_timestamps'] = stats.get('total_timestamps', 0)
        row_updates['successful_timestamps'] = stats.get('successful_timestamps', 0)
        row_updates['failed_timestamps'] = stats.get('failed_timestamps', 0)

        # 1. Performance breakdown percentages (start with these)
        row_updates['perfect_match_percent'] = stats.get('perfect_match_percent', 0.0) if total_observations > 0 else np.nan
        row_updates['threshold_pass_percent'] = stats.get('threshold_pass_percent', 0.0) if total_observations > 0 else np.nan
        row_updates['failed_percent'] = stats.get('failed_percent', 0.0) if total_observations > 0 else np.nan
        row_updates['total_success_rate'] = stats.get('total_success_rate', 0.0) if total_observations > 0 else np.nan

        # 2. Basic observation counts
        row_updates['total_observations'] = total_observations
        row_updates['successful_observations'] = successful_observations
        row_updates['failed_observations'] = failed_observations
        row_updates['total_routes'] = stats.get('total_routes', 0)

        # 3. Data completeness (if enabled)
        if completeness_params:
            from datetime import datetime, timedelta  # Import here for multiprocessing

            def calculate_expected_observations_local(start_date, end_date, interval_minutes):
                if not start_date or not end_date or start_date > end_date:
                    return 0
                start_dt = datetime.combine(start_date, datetime.min.time())
                end_dt = datetime.combine(end_date + timedelta(days=1), datetime.min.time())
                total_minutes = (end_dt - start_dt).total_seconds() / 60
                return int(total_minutes / interval_minutes)

            expected_observations = calculate_expected_observations_local(
                completeness_params['start_date'],
                completeness_params['end_date'],
                completeness_params['interval_minutes']
            )
            missing_observations = max(0, expected_observations - total_observations)
            data_coverage_percent = (total_observations / expected_observations * 100) if expected_observations > 0 else 0.0

            row_updates['expected_observations'] = expected_observations
            row_updates['missing_observations'] = missing_observations
            row_updates['data_coverage_percent'] = data_coverage_percent

        # 4. Route alternative breakdown (at the end)
        row_updates['single_route_observations'] = stats.get('single_route_observations', 0)
        row_updates['multi_route_observations'] = stats.get('multi_route_observations', 0)
        # Legacy fields for backwards compatibility
        row_updates['single_alt_timestamps'] = stats.get('single_alt_timestamps', 0)
        row_updates['multi_alt_timestamps'] = stats.get('multi_alt_timestamps', 0)

        # Determine result code for legacy tests
        legacy_stats = {
            'total_observations': total_observations,
            'valid_observations': successful_observations,
            'invalid_observations': stats.get('invalid_observations', failed_observations),
            'single_alternative_count': stats.get('single_alternative_count', stats.get('single_route_observations', 0)),
            'multi_alternative_count': stats.get('multi_alternative_count', stats.get('multi_route_observations', 0))
        }
        result_code, result_label, num = determine_result_code(legacy_stats)
        row_updates['result_code'] = result_code
        row_updates['result_label'] = result_label
        row_updates['num'] = num

        results[idx] = row_updates

    return results


def aggregate_link_statistics(link_data: pd.DataFrame) -> Dict[str, Any]:
    """
    Aggregate validation statistics using improved timestamp-based logic.

    Key insight: Route alternatives are ALTERNATIVES for the same routing request.
    If any alternative is valid for a timestamp, that timestamp is successful for the link.

    Args:
        link_data: Filtered DataFrame for one link

    Returns:
        Dictionary with improved aggregated statistics
    """
    if link_data.empty:
        return {
            'total_timestamps': 0,
            'successful_timestamps': 0,
            'failed_timestamps': 0,
            'success_rate': 0.0,
            'total_observations': 0,
            'successful_observations': 0,
            'invalid_observations': 0,
            'valid_observations': 0,
            'valid_timestamps': 0,
            'total_routes': 0,
            'single_route_observations': 0,
            'multi_route_observations': 0,
            'single_alt_timestamps': 0,
            'multi_alt_timestamps': 0,
            'single_alternative_count': 0,
            'multi_alternative_count': 0,
            'perfect_match_observations': 0,
            'threshold_pass_observations': 0,
            'perfect_match_percent': 0.0,
            'threshold_pass_percent': 0.0,
            'failed_percent': 0.0,
            'total_success_rate': 0.0
        }

    timestamp_col = 'timestamp' if 'timestamp' in link_data.columns else ('Timestamp' if 'Timestamp' in link_data.columns else None)
    drop_temp_timestamp = False

    if timestamp_col is None:
        link_data = link_data.copy()
        link_data['__synthetic_timestamp__'] = range(len(link_data))
        timestamp_col = '__synthetic_timestamp__'
        drop_temp_timestamp = True

    grouped = link_data.groupby(timestamp_col, sort=False)
    total_timestamps = grouped.ngroups
    valid_timestamps = 0
    single_alt_timestamps = 0
    multi_alt_timestamps = 0
    single_alternative_count = 0
    multi_alternative_count = 0

    perfect_match_timestamps = 0
    threshold_pass_timestamps = 0

    for _, group in grouped:
        row_count = len(group)
        is_single_alternative = (row_count == 1)

        if 'is_valid' in group.columns:
            timestamp_has_valid_alt = group['is_valid'].any()
        else:
            timestamp_has_valid_alt = False

        if timestamp_has_valid_alt:
            valid_timestamps += 1
            if 'hausdorff_distance' in group.columns:
                valid_routes = group[group['is_valid'] == True]
                if not valid_routes.empty:
                    min_hausdorff = valid_routes['hausdorff_distance'].min()
                    epsilon = 1e-6
                    if min_hausdorff < epsilon:
                        perfect_match_timestamps += 1
                    else:
                        threshold_pass_timestamps += 1

        if is_single_alternative:
            single_alt_timestamps += 1
            single_alternative_count += row_count
        else:
            multi_alt_timestamps += 1
            multi_alternative_count += row_count

    if single_alternative_count == 0 and multi_alternative_count == 0 and len(link_data) > 0:
        if 'route_alternative' in link_data.columns:
            unique_alts = link_data['route_alternative'].dropna().unique()
            if len(unique_alts) <= 1:
                single_alternative_count = len(link_data)
            else:
                multi_alternative_count = len(link_data)
        else:
            single_alternative_count = len(link_data)

    if multi_alt_timestamps == 0 and 'route_alternative' in link_data.columns:
        unique_alts = link_data['route_alternative'].dropna().unique()
        if len(unique_alts) > 1:
            single_alternative_count = 0
            multi_alternative_count = len(link_data)

    if 'route_alternative' in link_data.columns:
        non_null_alts = link_data['route_alternative'].dropna()
        if not non_null_alts.empty and non_null_alts.max() > 1 and multi_alternative_count == 0:
            single_alternative_count = 0
            multi_alternative_count = len(link_data)

    if drop_temp_timestamp:
        link_data = link_data.drop(columns=['__synthetic_timestamp__'])

    failed_timestamps = total_timestamps - valid_timestamps
    success_rate = (valid_timestamps / total_timestamps * 100) if total_timestamps > 0 else 0.0
    perfect_match_percent = (perfect_match_timestamps / total_timestamps * 100) if total_timestamps > 0 else 0.0
    threshold_pass_percent = (threshold_pass_timestamps / total_timestamps * 100) if total_timestamps > 0 else 0.0
    failed_percent = (failed_timestamps / total_timestamps * 100) if total_timestamps > 0 else 0.0
    total_success_rate = perfect_match_percent + threshold_pass_percent

    total_observations = total_timestamps
    successful_observations = valid_timestamps
    invalid_observations = total_observations - successful_observations

    return {
        'total_timestamps': total_timestamps,
        'successful_timestamps': valid_timestamps,
        'failed_timestamps': failed_timestamps,
        'success_rate': success_rate,
        'total_observations': total_observations,
        'successful_observations': successful_observations,
        'invalid_observations': invalid_observations,
        'valid_observations': successful_observations,
        'valid_timestamps': valid_timestamps,
        'total_routes': len(link_data),
        'single_route_observations': single_alt_timestamps,
        'multi_route_observations': multi_alt_timestamps,
        'single_alt_timestamps': single_alt_timestamps,
        'multi_alt_timestamps': multi_alt_timestamps,
        'single_alternative_count': single_alternative_count,
        'multi_alternative_count': multi_alternative_count,
        'perfect_match_observations': perfect_match_timestamps,
        'threshold_pass_observations': threshold_pass_timestamps,
        'perfect_match_percent': perfect_match_percent,
        'threshold_pass_percent': threshold_pass_percent,
        'failed_percent': failed_percent,
        'total_success_rate': total_success_rate
    }


def generate_link_report(
    validated_df: pd.DataFrame,
    shapefile_gdf: gpd.GeoDataFrame,
    date_filter: Optional[Dict] = None,
    completeness_params: Optional[Dict] = None
) -> gpd.GeoDataFrame:
    """
    Generate comprehensive per-link validation report with result codes and statistics.

    This function aggregates row-level validation results into link-level statistics,
    applies date filtering if specified, and generates result codes based on validation
    patterns. The report provides a summary view of data quality per link.

    The function performs these steps:
    1. Apply optional date filtering to observations
    2. Deduplicate observations by link_id, timestamp, and polyline
    3. Create shapefile join keys using s_From-To format
    4. Aggregate validation statistics per link
    5. Determine result codes based on alternative patterns and validity rates
    6. Add result fields to shapefile geometry

    Args:
        validated_df: DataFrame with validation results containing:
            - link_id or Name: Link identifier (will be standardized to link_id)
            - is_valid: Boolean validation result from validate_row()
            - valid_code: Integer validation code from ValidCode enum
            - route_alternative: Route alternative number
            - timestamp: Observation timestamp (required for date filtering)
            - polyline: Encoded polyline (used for deduplication)
        shapefile_gdf: Reference shapefile GeoDataFrame with:
            - From: Origin node identifier (used for s_From-To join key)
            - To: Destination node identifier
            - geometry: LineString geometries (preserved in output)
        date_filter: Optional dictionary for temporal filtering:
            - {'specific_day': date} for single day filtering
            - {'start_date': date, 'end_date': date} for range filtering
            - None to include all data

    Returns:
        GeoDataFrame with original shapefile geometry plus added transparent metrics:
        - perfect_match_percent: Percentage of timestamps with exact geometry match (Hausdorff = 0)
        - threshold_pass_percent: Percentage of timestamps passing threshold (0 < Hausdorff ≤ threshold)
        - failed_percent: Percentage of timestamps where all alternatives failed
        - total_observations: Number of unique timestamps observed
        - successful_observations: Number of timestamps with ≥1 valid alternative
        - failed_observations: Number of timestamps with all alternatives invalid
        - total_routes: Total validation rows (including all alternatives)
        - expected_observations: Expected observations based on recording schedule (if completeness enabled)
        - missing_observations: Missing observations count (if completeness enabled)
        - data_coverage_percent: Actual vs expected coverage percentage (if completeness enabled)
        - single_route_observations: Number of timestamps with one alternative
        - multi_route_observations: Number of timestamps with multiple alternatives

    Transparent Metrics Benefits:
        - Shows detailed performance breakdown (perfect/threshold/failed)
        - Reveals data coverage (total_observations vs expected)
        - Distinguishes between performance and data availability
        - No confusing labels or codes to interpret

    Examples:
        >>> import pandas as pd
        >>> import geopandas as gpd
        >>> from datetime import date
        >>>
        >>> # Create validated data
        >>> validated_df = pd.DataFrame({
        ...     'link_id': ['s_653-655', 's_653-655', 's_655-657'],
        ...     'is_valid': [True, False, True],
        ...     'valid_code': [1, 2, 1],
        ...     'route_alternative': [1, 1, 1],
        ...     'timestamp': ['2025-01-01 10:00', '2025-01-01 11:00', '2025-01-01 10:00']
        ... })
        >>>
        >>> # Create reference shapefile
        >>> shapefile = gpd.GeoDataFrame({
        ...     'From': ['653', '655'],
        ...     'To': ['655', '657'],
        ...     'geometry': [line1, line2]
        ... })
        >>>
        >>> # Generate report
        >>> report = generate_link_report(validated_df, shapefile)
        >>> print(report[['From', 'To', 'perfect_match_percent', 'total_observations', 'successful_observations']])

        >>> # With date filtering
        >>> date_filter = {'specific_day': date(2025, 1, 1)}
        >>> report = generate_link_report(validated_df, shapefile, date_filter)

    Note:
        - Links not present in validation data have performance percentages=None and total_observations=0
        - Deduplication prevents double-counting of identical observations
        - Date filtering is applied before aggregation and deduplication
        - Transparent metrics show raw percentages without arbitrary binning
        - The function preserves all original shapefile attributes and geometry
    """
    # Start with copy of shapefile
    report_gdf = shapefile_gdf.copy()

    # Ensure we have a link_id column for joining
    if 'link_id' not in validated_df.columns:
        validated_df = validated_df.copy()
        if 'Name' in validated_df.columns:
            validated_df['link_id'] = validated_df['Name']
        elif 'name' in validated_df.columns:
            validated_df['link_id'] = validated_df['name']

    # Apply date filtering if specified
    filtered_df = validated_df.copy()
    if date_filter:
        if 'timestamp' in filtered_df.columns:
            # Convert timestamp to datetime if needed
            if not pd.api.types.is_datetime64_any_dtype(filtered_df['timestamp']):
                filtered_df['timestamp'] = pd.to_datetime(filtered_df['timestamp'])

            if 'specific_day' in date_filter:
                target_date = pd.to_datetime(date_filter['specific_day']).date()
                filtered_df = filtered_df[filtered_df['timestamp'].dt.date == target_date]

            elif 'start_date' in date_filter and 'end_date' in date_filter:
                start_date = pd.to_datetime(date_filter['start_date'])
                end_date = pd.to_datetime(date_filter['end_date'])
                filtered_df = filtered_df[
                    (filtered_df['timestamp'] >= start_date) &
                    (filtered_df['timestamp'] <= end_date)
                ]

    # Deduplicate observations
    filtered_df = deduplicate_observations(filtered_df)

    # Create shapefile join keys
    report_gdf['join_key'] = 's_' + report_gdf['From'].astype(str) + '-' + report_gdf['To'].astype(str)

    # Initialize columns in logical order as requested

    # Backwards compatibility fields (for tests)
    report_gdf['success_rate'] = np.nan  # Use NaN instead of None for numeric dtype
    report_gdf['total_timestamps'] = 0
    report_gdf['successful_timestamps'] = 0
    report_gdf['failed_timestamps'] = 0

    # 1. Performance breakdown percentages (start with these)
    report_gdf['perfect_match_percent'] = np.nan  # Use NaN instead of None
    report_gdf['threshold_pass_percent'] = np.nan  # Use NaN instead of None
    report_gdf['failed_percent'] = np.nan  # Use NaN instead of None
    report_gdf['total_success_rate'] = np.nan  # Use NaN instead of None

    # 2. Basic observation counts
    report_gdf['total_observations'] = 0
    report_gdf['successful_observations'] = 0
    report_gdf['failed_observations'] = 0
    report_gdf['total_routes'] = 0

    # 3. Data completeness (if enabled)
    if completeness_params:
        report_gdf['expected_observations'] = 0
        report_gdf['missing_observations'] = 0
        report_gdf['data_coverage_percent'] = np.nan  # Use NaN instead of None

    # 4. Route alternative breakdown (at the end)
    report_gdf['single_route_observations'] = 0
    report_gdf['multi_route_observations'] = 0
    # Legacy fields for backwards compatibility
    report_gdf['single_alt_timestamps'] = 0
    report_gdf['multi_alt_timestamps'] = 0
    report_gdf['result_code'] = 0
    report_gdf['result_label'] = ''
    report_gdf['num'] = 0.0

    # Prepare per-link statistics once to avoid repeated DataFrame scans
    empty_stats = aggregate_link_statistics(pd.DataFrame())
    if 'link_id' in filtered_df.columns and not filtered_df.empty:
        stats_by_link = {
            link_id: aggregate_link_statistics(group)
            for link_id, group in filtered_df.groupby('link_id', sort=False, observed=True)
        }
    else:
        stats_by_link = {}

    # Process links in parallel for better performance
    cpu_count = os.cpu_count() or 1
    max_workers = min(8, max(2, cpu_count))

    # Determine optimal chunk size based on dataset size
    total_links = len(report_gdf)
    if total_links <= 100:
        # Small datasets: use single-threaded processing
        chunk_size = total_links
        max_workers = 1
    else:
        # Large datasets: use parallel processing
        chunk_size = max(50, total_links // (max_workers * 2))

    if max_workers == 1:
        # Single-threaded processing for small datasets
        for idx, shapefile_row in report_gdf.iterrows():
            link_join_key = shapefile_row['join_key']
            stats = stats_by_link.get(link_join_key, empty_stats)

            total_observations = stats.get('total_observations', 0)
            successful_observations = stats.get('successful_observations', 0)
            failed_observations = total_observations - successful_observations

            # Apply all the statistics updates (same logic as worker function)
            report_gdf.at[idx, 'success_rate'] = stats.get('success_rate', 0.0) if total_observations > 0 else np.nan
            report_gdf.at[idx, 'total_timestamps'] = stats.get('total_timestamps', 0)
            report_gdf.at[idx, 'successful_timestamps'] = stats.get('successful_timestamps', 0)
            report_gdf.at[idx, 'failed_timestamps'] = stats.get('failed_timestamps', 0)
            report_gdf.at[idx, 'perfect_match_percent'] = stats.get('perfect_match_percent', 0.0) if total_observations > 0 else np.nan
            report_gdf.at[idx, 'threshold_pass_percent'] = stats.get('threshold_pass_percent', 0.0) if total_observations > 0 else np.nan
            report_gdf.at[idx, 'failed_percent'] = stats.get('failed_percent', 0.0) if total_observations > 0 else np.nan
            report_gdf.at[idx, 'total_success_rate'] = stats.get('total_success_rate', 0.0) if total_observations > 0 else np.nan
            report_gdf.at[idx, 'total_observations'] = total_observations
            report_gdf.at[idx, 'successful_observations'] = successful_observations
            report_gdf.at[idx, 'failed_observations'] = failed_observations
            report_gdf.at[idx, 'total_routes'] = stats.get('total_routes', 0)

            if completeness_params:
                expected_observations = calculate_expected_observations(
                    completeness_params['start_date'], completeness_params['end_date'], completeness_params['interval_minutes']
                )
                missing_observations = max(0, expected_observations - total_observations)
                data_coverage_percent = (total_observations / expected_observations * 100) if expected_observations > 0 else 0.0
                report_gdf.at[idx, 'expected_observations'] = expected_observations
                report_gdf.at[idx, 'missing_observations'] = missing_observations
                report_gdf.at[idx, 'data_coverage_percent'] = data_coverage_percent

            report_gdf.at[idx, 'single_route_observations'] = stats.get('single_route_observations', 0)
            report_gdf.at[idx, 'multi_route_observations'] = stats.get('multi_route_observations', 0)
            report_gdf.at[idx, 'single_alt_timestamps'] = stats.get('single_alt_timestamps', 0)
            report_gdf.at[idx, 'multi_alt_timestamps'] = stats.get('multi_alt_timestamps', 0)

            legacy_stats = {
                'total_observations': total_observations, 'valid_observations': successful_observations,
                'invalid_observations': stats.get('invalid_observations', failed_observations),
                'single_alternative_count': stats.get('single_alternative_count', stats.get('single_route_observations', 0)),
                'multi_alternative_count': stats.get('multi_alternative_count', stats.get('multi_route_observations', 0))
            }
            result_code, result_label, num = determine_result_code(legacy_stats)
            report_gdf.at[idx, 'result_code'] = result_code
            report_gdf.at[idx, 'result_label'] = result_label
            report_gdf.at[idx, 'num'] = num
    else:
        # Parallel processing for large datasets
        indices = list(report_gdf.index)
        join_keys = [report_gdf.at[idx, 'join_key'] for idx in indices]

        # Create chunks
        chunks = []
        for i in range(0, len(indices), chunk_size):
            chunk_indices = indices[i:i + chunk_size]
            chunk_join_keys = join_keys[i:i + chunk_size]
            chunks.append((chunk_indices, chunk_join_keys, stats_by_link, completeness_params, empty_stats))

        # Process chunks in parallel
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            future_to_chunk = {executor.submit(_process_link_chunk, chunk): chunk for chunk in chunks}

            for future in as_completed(future_to_chunk):
                chunk_results = future.result()

                # Apply results to the report_gdf
                for idx, row_updates in chunk_results.items():
                    for column, value in row_updates.items():
                        report_gdf.at[idx, column] = value

    # Clean up temporary join key
    report_gdf = report_gdf.drop(columns=['join_key'])

    return report_gdf


def _rename_dbf_field(dbf_path: Path, current: str, new: str) -> None:
    """Safely rename a DBF column without rewriting the whole shapefile."""
    try:
        with open(dbf_path, 'r+b') as dbf_file:
            dbf_file.seek(32)
            while True:
                descriptor = dbf_file.read(32)
                if not descriptor or descriptor[0] == 0x0D:
                    break
                name_bytes = descriptor[:11]
                name = name_bytes.split(b'\x00', 1)[0].decode('ascii', errors='ignore')
                if name.lower() == current.lower():
                    new_bytes = new.encode('ascii', errors='ignore')[:11]
                    new_bytes = new_bytes.ljust(11, b'\x00')
                    descriptor = new_bytes + descriptor[11:]
                    dbf_file.seek(-32, 1)
                    dbf_file.write(descriptor)
                    break
    except OSError:
        pass


def _write_shapefile(gdf: gpd.GeoDataFrame, output_path, driver: str = 'ESRI Shapefile') -> None:
    '''Write GeoDataFrame to disk preferring pyogrio for performance when available.'''
    output_path_str = str(output_path)

    if pyogrio is not None:
        try:
            pyogrio.write_dataframe(gdf, output_path_str, driver=driver)
            return
        except Exception:
            # Fall back to GeoPandas when pyogrio write fails
            pass

    gdf.to_file(output_path_str, driver=driver)


def write_shapefile_with_results(gdf: gpd.GeoDataFrame, output_path: str) -> None:
    """Write complete shapefile package with added transparent metrics fields."""
    tmp_dir = None
    try:
        output_gdf = gdf.copy()

        # Define the exact field order to match CSV report
        desired_order = [
            'From', 'To',
            'perfect_match_percent', 'threshold_pass_percent', 'failed_percent', 'total_success_rate',
            'total_observations', 'successful_observations', 'failed_observations', 'total_routes',
            'single_route_observations', 'multi_route_observations',
            'expected_observations', 'missing_observations', 'data_coverage_percent'
        ]

        # Column mapping for shapefile field name limits (10 chars max)
        column_mapping = {
            'perfect_match_percent': 'perfect_p',
            'threshold_pass_percent': 'thresh_p',
            'failed_percent': 'failed_p',
            'total_success_rate': 'total_succ',
            'total_observations': 'total_obs',
            'successful_observations': 'success_ob',
            'failed_observations': 'failed_obs',
            'total_routes': 'total_rts',
            'single_route_observations': 'single_obs',
            'multi_route_observations': 'multi_obs',
            'expected_observations': 'expect_obs',
            'missing_observations': 'missing_ob',
            'data_coverage_percent': 'coverage_p'
        }

        # Only keep the desired columns from the CSV report (no extra fields)
        available_cols = [col for col in desired_order if col in output_gdf.columns]
        # Only keep geometry and the desired columns - no extra fields
        final_order = available_cols + ['geometry']
        output_gdf = output_gdf[final_order]

        # Apply column mapping for field name truncation
        output_gdf = output_gdf.rename(columns=column_mapping)

        # Optimize data types for better shapefile performance
        for col in ['perfect_p', 'thresh_p', 'failed_p', 'total_succ', 'coverage_p']:
            if col in output_gdf.columns:
                output_gdf[col] = pd.to_numeric(output_gdf[col], errors='coerce').astype('float32')

        for col in ['total_obs', 'success_ob', 'failed_obs', 'total_rts', 'expect_obs', 'missing_ob', 'single_obs', 'multi_obs']:
            if col in output_gdf.columns:
                # Use int32 for better performance and smaller file size
                output_gdf[col] = output_gdf[col].astype('int32')

        if 'num' in output_gdf.columns:
            output_gdf['num'] = pd.to_numeric(output_gdf['num'], errors='coerce').astype('float32')

        # Optimize geometry for writing (simplify very small details if needed)
        if len(output_gdf) > 1000:  # Only for large shapefiles
            # Remove any invalid geometries
            output_gdf = output_gdf[output_gdf.geometry.is_valid]

        if output_gdf.crs is None:
            output_gdf = output_gdf.set_crs('EPSG:4326')

        output_path = Path(output_path)
        tmp_dir = Path(tempfile.mkdtemp(prefix='control_shp_', dir=output_path.parent))
        tmp_shp_path = tmp_dir / output_path.name

        _write_shapefile(output_gdf, tmp_shp_path, driver='ESRI Shapefile')

        required_files = ['.shp', '.shx', '.dbf']
        base_path = tmp_shp_path.with_suffix('')
        missing_files = [ext for ext in required_files if not base_path.with_suffix(ext).exists()]
        if missing_files:
            raise IOError(f"Shapefile creation incomplete. Missing files: {', '.join(missing_files)}")

        dbf_path = base_path.with_suffix('.dbf')
        _rename_dbf_field(dbf_path, 'result_cod', 'result_code')
        _rename_dbf_field(dbf_path, 'result_lab', 'result_label')

        prj_file = base_path.with_suffix('.prj')
        if not prj_file.exists():
            wgs84_prj = 'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]'
            prj_file.write_text(wgs84_prj)

        destination_base = output_path.with_suffix('')
        destination_base.parent.mkdir(parents=True, exist_ok=True)
        for ext in ['.shp', '.shx', '.dbf', '.prj', '.cpg']:
            tmp_file = base_path.with_suffix(ext)
            if tmp_file.exists():
                shutil.move(str(tmp_file), str(destination_base.with_suffix(ext)))

    except Exception as e:
        raise IOError(f"Failed to write complete shapefile package: {e}")
    finally:
        if tmp_dir and tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)


def extract_failed_observations(validated_df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract only failed observations where ALL alternatives for a timestamp failed.

    For timestamps with multiple route alternatives, includes all failed alternatives
    only when none of the alternatives for that timestamp are valid.

    Args:
        validated_df: DataFrame with validation results containing:
            - link_id or Name: Link identifier
            - timestamp: Observation timestamp
            - is_valid: Boolean validation result
            - route_alternative: Route alternative number (optional)
            - All other original columns preserved

    Returns:
        DataFrame containing only failed observations where:
        - Single alternative timestamps: The alternative is invalid
        - Multi-alternative timestamps: ALL alternatives are invalid
    """
    if validated_df.empty:
        return validated_df

    # Ensure we have a link_id column
    df = validated_df.copy()
    if 'link_id' not in df.columns:
        if 'Name' in df.columns:
            df['link_id'] = df['Name']
        elif 'name' in df.columns:
            df['link_id'] = df['name']

    # Get timestamp column name
    timestamp_col = 'timestamp' if 'timestamp' in df.columns else 'Timestamp'

    # Handle missing columns gracefully
    if 'link_id' not in df.columns or timestamp_col not in df.columns:
        return pd.DataFrame()  # Can't process without required columns

    # Group by link_id and timestamp
    failed_observations = []

    for (link_id, timestamp), group in df.groupby(['link_id', timestamp_col], sort=False):
        # Check if ALL alternatives for this timestamp failed
        if 'is_valid' in group.columns:
            all_failed = not group['is_valid'].any()  # True if NO alternative is valid

            if all_failed:
                # Include all rows from this group (all failed alternatives)
                failed_observations.append(group)

    # Combine all failed observations
    if failed_observations:
        result = pd.concat(failed_observations, ignore_index=True)
        # Sort by link_id, timestamp, and route_alternative if present
        sort_cols = ['link_id', timestamp_col]
        if 'RouteAlternative' in result.columns:
            sort_cols.append('RouteAlternative')
        elif 'route_alternative' in result.columns:
            sort_cols.append('route_alternative')

        result = result.sort_values(sort_cols).reset_index(drop=True)
        return result
    else:
        # Return empty DataFrame with same columns as input
        return pd.DataFrame(columns=df.columns)


def extract_best_valid_observations(validated_df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract best valid observation per timestamp using weighted scoring.

    For single alternative timestamps: Keep if valid
    For multi-alternative timestamps: Select best valid based on weighted score

    Scoring weights (in order of importance):
    1. Hausdorff distance: Lower is better (weight: -1000)
    2. Length ratio deviation from 1.0: Smaller is better (weight: -100)
    3. Coverage percent: Higher is better (weight: +1)

    Args:
        validated_df: DataFrame with validation results containing:
            - link_id or Name: Link identifier
            - timestamp: Observation timestamp
            - is_valid: Boolean validation result
            - hausdorff_distance: Distance metric (lower is better)
            - length_ratio: Length ratio (closer to 1.0 is better) - optional
            - coverage_percent: Coverage percentage (higher is better) - optional
            - route_alternative: Route alternative number

    Returns:
        DataFrame containing best valid observation per timestamp:
        - One row per timestamp where at least one valid alternative exists
        - For multi-alternative timestamps: The alternative with best score
    """
    if validated_df.empty:
        return validated_df

    # Ensure we have a link_id column
    df = validated_df.copy()
    if 'link_id' not in df.columns:
        if 'Name' in df.columns:
            df['link_id'] = df['Name']
        elif 'name' in df.columns:
            df['link_id'] = df['name']

    # Convert link_id to categorical for faster groupby operations
    if 'link_id' in df.columns:
        df['link_id'] = df['link_id'].astype('category')

    # Get timestamp column name
    timestamp_col = 'timestamp' if 'timestamp' in df.columns else 'Timestamp'

    # Handle missing columns gracefully
    if 'link_id' not in df.columns or timestamp_col not in df.columns:
        return pd.DataFrame()  # Can't process without required columns

    # Calculate weighted scores for valid observations
    def calculate_score(row):
        """Calculate weighted score for a valid observation."""
        score = 0.0

        # Hausdorff distance (most important - lower is better)
        if 'hausdorff_distance' in row and pd.notna(row['hausdorff_distance']):
            score -= row['hausdorff_distance'] * 1000

        # Length ratio deviation (second priority - closer to 1.0 is better)
        if 'length_ratio' in row and pd.notna(row['length_ratio']):
            deviation = abs(row['length_ratio'] - 1.0)
            score -= deviation * 100

        # Coverage percent (third priority - higher is better)
        if 'coverage_percent' in row and pd.notna(row['coverage_percent']):
            score += row['coverage_percent'] * 1

        return score

    # Add score column for valid observations
    if 'is_valid' in df.columns:
        # Filter to valid observations only
        valid_df = df[df['is_valid'] == True].copy()
        if valid_df.empty:
            return pd.DataFrame(columns=df.columns)

        # Vectorized score calculation (much faster than apply)
        valid_df['selection_score'] = 0.0

        # Hausdorff distance (most important - lower is better)
        if 'hausdorff_distance' in valid_df.columns:
            mask = valid_df['hausdorff_distance'].notna()
            valid_df.loc[mask, 'selection_score'] -= valid_df.loc[mask, 'hausdorff_distance'] * 1000

        # Length ratio deviation (second priority - closer to 1.0 is better)
        if 'length_ratio' in valid_df.columns:
            mask = valid_df['length_ratio'].notna()
            valid_df.loc[mask, 'selection_score'] -= abs(valid_df.loc[mask, 'length_ratio'] - 1.0) * 100

        # Coverage percent (third priority - higher is better)
        if 'coverage_percent' in valid_df.columns:
            mask = valid_df['coverage_percent'].notna()
            valid_df.loc[mask, 'selection_score'] += valid_df.loc[mask, 'coverage_percent'] * 1

        # Use groupby with idxmax to get best alternative per group (much faster)
        grouped = valid_df.groupby(['link_id', timestamp_col], sort=False, observed=True)

        # Get indices of rows with maximum score per group
        best_indices = grouped['selection_score'].idxmax()

        # Extract best observations using the indices
        result = valid_df.loc[best_indices].copy()

        # Remove temporary score column
        result = result.drop(columns=['selection_score'])

        # Sort by link_id, timestamp, and route_alternative if present
        sort_cols = ['link_id', timestamp_col]
        if 'RouteAlternative' in result.columns:
            sort_cols.append('RouteAlternative')
        elif 'route_alternative' in result.columns:
            sort_cols.append('route_alternative')

        result = result.sort_values(sort_cols).reset_index(drop=True)
        return result
    else:
        # Return empty DataFrame with same columns as input (minus score column)
        result_cols = [col for col in df.columns if col != 'selection_score']
        return pd.DataFrame(columns=result_cols)


def extract_missing_observations(
    validated_df: pd.DataFrame,
    completeness_params: Dict,
    shapefile_gdf: gpd.GeoDataFrame
) -> pd.DataFrame:
    """
    Extract missing observations by finding RequestedTime gaps for links with actual data.

    Creates synthetic rows for missing RequestedTime intervals with:
    - link_id: From links that have actual data
    - RequestedTime: Missing RequestedTime interval
    - is_valid: False
    - valid_code: 94 (MISSING_OBSERVATION)
    - All other fields: None/empty

    Args:
        validated_df: DataFrame with actual validation results
        completeness_params: Dict with start_date, end_date, interval_minutes
        shapefile_gdf: Reference shapefile for all possible links

    Returns:
        DataFrame containing synthetic rows for missing RequestedTime intervals
    """
    if not completeness_params or validated_df.empty or shapefile_gdf.empty:
        return pd.DataFrame()

    from datetime import datetime, timedelta
    import pandas as pd

    # Extract parameters
    start_date = completeness_params['start_date']
    end_date = completeness_params['end_date']
    interval_minutes = completeness_params['interval_minutes']

    # Generate all expected timestamps
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date + timedelta(days=1), datetime.min.time())

    expected_timestamps = []
    current_dt = start_dt
    while current_dt < end_dt:
        expected_timestamps.append(current_dt)
        current_dt += timedelta(minutes=interval_minutes)

    # Standardize validated_df columns
    df = validated_df.copy()
    if 'link_id' not in df.columns:
        if 'Name' in df.columns:
            df['link_id'] = df['Name']
        elif 'name' in df.columns:
            df['link_id'] = df['name']

    # Look for RequestedTime field (primary) or fall back to timestamp fields
    requested_time_col = None
    if 'RequestedTime' in df.columns:
        requested_time_col = 'RequestedTime'
    elif 'requested_time' in df.columns:
        requested_time_col = 'requested_time'
    elif 'Timestamp' in df.columns:
        requested_time_col = 'Timestamp'
    elif 'timestamp' in df.columns:
        requested_time_col = 'timestamp'

    if 'link_id' not in df.columns or requested_time_col is None:
        return pd.DataFrame()

    # Standardize to 'requested_time' column name
    if requested_time_col != 'requested_time':
        df['requested_time'] = df[requested_time_col]
        requested_time_col = 'requested_time'

    if 'requested_time' in df.columns and 'RequestedTime' not in df.columns:
        df['RequestedTime'] = df['requested_time']
    if 'RequestedTime' in df.columns and 'requested_time' not in df.columns:
        df['requested_time'] = df['RequestedTime']

    if not pd.api.types.is_datetime64_any_dtype(df[requested_time_col]):
        parsed = _parse_timestamp_series(df[requested_time_col])
        df[requested_time_col] = parsed

        if not pd.api.types.is_datetime64_any_dtype(df[requested_time_col]):
            try:
                df[requested_time_col] = pd.to_datetime(
                    completeness_params['start_date'].strftime('%Y-%m-%d') + ' ' + parsed.astype(str),
                    errors='coerce'
                )
            except Exception:
                df[requested_time_col] = parsed


    # Get link IDs that actually have data in the validated_df
    # Only check for missing observations in links that have some actual data
    links_with_data = set(df['link_id'].unique())

    # Normalize RequestedTime to interval boundaries for proper comparison
    def normalize_to_interval(ts, interval_minutes):
        """Round RequestedTime down to interval boundary"""
        if pd.isna(ts):
            return ts
        minutes = ts.minute
        normalized_minutes = (minutes // interval_minutes) * interval_minutes
        return ts.replace(minute=normalized_minutes, second=0, microsecond=0)

    # Normalize actual RequestedTime values to interval boundaries
    df['normalized_requested_time'] = df[requested_time_col].apply(
        lambda ts: normalize_to_interval(ts, interval_minutes)
    )

    # Find existing (link, normalized_requested_time) combinations
    existing_combinations = set(
        zip(df['link_id'], df['normalized_requested_time'])
    )

    # Find missing combinations correctly handling RequestedTime + Date combinations
    missing_observations = []

    for link_id in links_with_data:
        # Get this link's actual data
        link_df = df[df['link_id'] == link_id].copy()

        if link_df.empty:
            continue

        # For each expected date+time combination, check if it exists
        for expected_dt in expected_timestamps:
            expected_time_str = expected_dt.strftime('%H:%M:%S')
            expected_date = expected_dt.date()

            # Check if this link has data for this RequestedTime + Date combination
            # We need to check both RequestedTime match and date match
            matching_rows = link_df[
                (link_df['RequestedTime'] == expected_time_str) |
                (link_df['RequestedTime'] == expected_dt.strftime('%H:%M:%S'))
            ]

            # If we have timestamp/datetime data, also check date match
            if 'Timestamp' in link_df.columns or 'timestamp' in link_df.columns:
                timestamp_col = 'Timestamp' if 'Timestamp' in link_df.columns else 'timestamp'

                # Parse timestamp dates to compare
                try:
                    timestamp_dates = pd.to_datetime(link_df[timestamp_col], errors='coerce', dayfirst=True).dt.date
                    date_matches = timestamp_dates == expected_date

                    # Find rows that match both time and date
                    time_matches = (
                        (link_df['RequestedTime'] == expected_time_str) |
                        (link_df['RequestedTime'] == expected_dt.strftime('%H:%M:%S'))
                    )

                    # Must match both time AND date
                    matching_rows = link_df[time_matches & date_matches]

                except Exception:
                    # Fallback to just time matching if date parsing fails
                    pass

            # If no matching rows found, this is a missing observation
            if matching_rows.empty:
                missing_row = {
                    'Name': link_id,  # Use original column name
                    'link_id': link_id,
                    'RequestedTime': expected_time_str,  # Output as time string
                    'is_valid': False,
                    'valid_code': 94,  # Code for MISSING_OBSERVATION
                    'hausdorff_distance': None,
                    'hausdorff_pass': False,
                }

                # Add other common columns as None/empty
                for col in ['RouteAlternative', 'polyline', 'SegmentID', 'DataID']:
                    if col in df.columns:
                        missing_row[col] = None

                # Add length/coverage fields if they exist in original data
                for col in ['length_ratio', 'length_pass', 'coverage_percent', 'coverage_pass']:
                    if col in df.columns:
                        missing_row[col] = None

                missing_observations.append(missing_row)

    if missing_observations:
        result = pd.DataFrame(missing_observations)

        # Sort by link_id and RequestedTime
        sort_cols = ['link_id', 'RequestedTime']
        result = result.sort_values(sort_cols).reset_index(drop=True)

        return result
    else:
        # Return empty DataFrame with same structure as validated_df
        return pd.DataFrame(columns=df.columns)


def extract_no_data_links(
    validated_df: pd.DataFrame,
    shapefile_gdf: gpd.GeoDataFrame
) -> pd.DataFrame:
    """
    Extract links that exist in shapefile but have no observations in the CSV.

    Creates synthetic rows for no-data links with:
    - link_id: From shapefile
    - timestamp: None (no specific time)
    - is_valid: False
    - valid_code: 95 (NO_DATA_LINK)
    - All other fields: None/empty

    Args:
        validated_df: DataFrame with actual validation results
        shapefile_gdf: Reference shapefile for all possible links

    Returns:
        DataFrame containing synthetic rows for links with no data
    """
    # Define the expected structure for no_data_links DataFrame
    expected_columns = [
        'Name', 'link_id', 'timestamp', 'is_valid', 'valid_code',
        'hausdorff_distance', 'hausdorff_pass'
    ]

    if validated_df.empty or shapefile_gdf.empty:
        # Return empty DataFrame with expected structure
        return pd.DataFrame(columns=expected_columns)

    # Get all possible link IDs from shapefile
    shapefile_links = set('s_' + str(row['From']) + '-' + str(row['To'])
                         for _, row in shapefile_gdf.iterrows())

    # Standardize validated_df columns to get links with data
    df = validated_df.copy()
    if 'link_id' not in df.columns:
        if 'Name' in df.columns:
            df['link_id'] = df['Name']
        elif 'name' in df.columns:
            df['link_id'] = df['name']

    if 'link_id' not in df.columns:
        # If no link_id column, assume all shapefile links have no data
        links_with_data = set()
    else:
        links_with_data = set(df['link_id'].unique())

    # Find links in shapefile but not in data
    no_data_links = shapefile_links - links_with_data

    if not no_data_links:
        # Return empty DataFrame with expected structure when all links have data
        return pd.DataFrame(columns=expected_columns)

    # Create synthetic no-data rows
    no_data_observations = []

    for link_id in no_data_links:
        no_data_row = {
            'Name': link_id,  # Use original column name
            'link_id': link_id,
            'timestamp': None,  # No specific timestamp for no-data links
            'is_valid': False,
            'valid_code': 95,  # New code for NO_DATA_LINK
            'hausdorff_distance': None,
            'hausdorff_pass': False,
        }

        # Add other common columns as None/empty to match structure
        if 'RouteAlternative' in df.columns:
            no_data_row['RouteAlternative'] = None
        if 'polyline' in df.columns:
            no_data_row['polyline'] = None
        if 'SegmentID' in df.columns:
            no_data_row['SegmentID'] = None
        if 'DataID' in df.columns:
            no_data_row['DataID'] = None

        # Add length/coverage fields if they exist
        for col in ['length_ratio', 'length_pass', 'coverage_percent', 'coverage_pass']:
            if col in df.columns:
                no_data_row[col] = None

        no_data_observations.append(no_data_row)

    if no_data_observations:
        result = pd.DataFrame(no_data_observations)
        # Sort by link_id
        result = result.sort_values('link_id').reset_index(drop=True)
        return result
    else:
        # Return empty DataFrame with expected structure
        return pd.DataFrame(columns=expected_columns)


def create_csv_matching_shapefile(
    csv_df: pd.DataFrame,
    shapefile_gdf: gpd.GeoDataFrame,
    output_path: str,
    geometry_source: str = 'polyline'
) -> None:
    """
    Create a shapefile that exactly matches a CSV file with appropriate geometries.

    Args:
        csv_df: DataFrame from CSV file (failed_observations, missing_observations, etc.)
        shapefile_gdf: Original reference shapefile for fallback geometry
        output_path: Path for output shapefile
        geometry_source: 'polyline' for decoded polylines, 'shapefile' for original geometry
    """
    if csv_df.empty:
        print(f"Warning: Empty CSV data, skipping shapefile creation: {output_path}")
        return

    import polyline
    from shapely.geometry import LineString


    # Create shapefile lookup for fallback geometries
    shapefile_lookup = {
        f"s_{row.From}-{row.To}": row.geometry
        for row in shapefile_gdf.itertuples()
    }

    name_candidates = ('Name', 'name', 'link_id', 'linkId', 'linkID')
    name_col = next((col for col in name_candidates if col in csv_df.columns), None)

    polyline_col = None
    if geometry_source == 'polyline':
        for candidate in ('polyline', 'Polyline'):
            if candidate in csv_df.columns:
                polyline_col = candidate
                break

    geometries = []
    index_order = []
    decode_cache = {}

    for row in csv_df.itertuples(index=True, name='Row'):
        geometry = None
        link_id = getattr(row, name_col, None) if name_col else None

        try:
            if geometry_source == 'polyline' and polyline_col:
                encoded = getattr(row, polyline_col, None)
                if encoded is not None and not pd.isna(encoded):
                    key = str(encoded)
                    decoded_coords = decode_cache.get(key)
                    if decoded_coords is None:
                        try:
                            decoded_coords = polyline.decode(key)
                        except Exception as exc:
                            decoded_coords = None
                            print(f"Warning: Failed to decode polyline for row {row.Index}: {exc}")
                        decode_cache[key] = decoded_coords

                    if decoded_coords and len(decoded_coords) >= 2:
                        coords_lonlat = ((lon, lat) for lat, lon in decoded_coords)
                        geometry = LineString(coords_lonlat)
                    elif decoded_coords:
                        print(f"Warning: Insufficient coordinates in polyline for row {row.Index}")

            if geometry is None and link_id in shapefile_lookup:
                geometry = shapefile_lookup[link_id]

            if geometry is not None:
                geometries.append(geometry)
                index_order.append(row.Index)
            else:
                print(f"Warning: No geometry found for row {row.Index}, link {link_id}")

        except Exception as exc:
            print(f"Warning: Error processing row {row.Index}: {exc}")
            continue

    if not geometries:
        print(f"Warning: No valid geometries created for shapefile: {output_path}")
        return

    # Create GeoDataFrame with exact same columns as CSV
    result_gdf = gpd.GeoDataFrame(csv_df.loc[index_order].copy(), geometry=geometries)

    # Set CRS (WGS84 for polylines, original CRS for shapefile geometry)
    result_gdf.crs = 'EPSG:4326'  # WGS84 for consistency

    # Reproject to match original shapefile if needed
    if shapefile_gdf.crs and shapefile_gdf.crs != result_gdf.crs:
        try:
            result_gdf = result_gdf.to_crs(shapefile_gdf.crs)
        except Exception as e:
            print(f"Warning: CRS reprojection failed: {e}")

    # Save shapefile
    try:
        _write_shapefile(result_gdf, output_path, driver='ESRI Shapefile')
        print(f"Created shapefile matching CSV: {output_path}")
    except Exception as e:
        print(f"Error creating shapefile: {e}")


def create_failed_observations_shapefile(
    failed_observations_df: pd.DataFrame,
    shapefile_gdf: gpd.GeoDataFrame,
    output_path: str
) -> None:
    """
    Create a shapefile for failed observations that exactly matches the CSV.
    Uses decoded polyline geometries for each row.
    """
    create_csv_matching_shapefile(
        csv_df=failed_observations_df,
        shapefile_gdf=shapefile_gdf,
        output_path=output_path,
        geometry_source='polyline'
    )


def create_failed_observations_reference_shapefile(
    failed_observations_df: pd.DataFrame,
    shapefile_gdf: gpd.GeoDataFrame,
    output_path: str
) -> None:
    """
    Create a reference shapefile for failed observations with time period aggregation.

    This shapefile aggregates failed observations by link and time periods (not individual timestamps).
    Shows reference geometry with failure patterns across 5 time periods per day.

    Time periods (left-inclusive, right-exclusive):
    - 00:00-06:00 (night)
    - 06:00-11:00 (morning)
    - 11:00-15:00 (midday)
    - 15:00-20:00 (afternoon)
    - 20:00-00:00 (evening)

    Args:
        failed_observations_df: DataFrame with individual failed validation results
        shapefile_gdf: Reference shapefile for geometry
        output_path: Path for output shapefile
    """
    if failed_observations_df.empty:
        print(f"Warning: No failed observations to create reference shapefile: {output_path}")
        return

    # Create shapefile lookup for reference geometry
    shapefile_lookup = {}
    for _, row in shapefile_gdf.iterrows():
        link_id = f's_{row["From"]}-{row["To"]}'
        shapefile_lookup[link_id] = row

    # Standardize column names and convert timestamp
    df = failed_observations_df.copy()
    if 'Name' in df.columns and 'link_id' not in df.columns:
        df['link_id'] = df['Name']
    if 'Timestamp' in df.columns and 'timestamp' not in df.columns:
        df['timestamp'] = df['Timestamp']

    # Parse timestamps to extract hour and date
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['hour'] = df['timestamp'].dt.hour
    df['date'] = df['timestamp'].dt.date

    # Define time period mapping function
    def get_time_period(hour):
        if 0 <= hour < 6:
            return 'period_00_06'
        elif 6 <= hour < 11:
            return 'period_06_11'
        elif 11 <= hour < 15:
            return 'period_11_15'
        elif 15 <= hour < 20:
            return 'period_15_20'
        else:  # 20 <= hour <= 23
            return 'period_20_00'

    df['time_period'] = df['hour'].apply(get_time_period)

    # Group by link_id to create one row per link
    reference_rows = []
    geometries = []

    for link_id, link_group in df.groupby('link_id'):
        if link_id in shapefile_lookup:
            shapefile_row = shapefile_lookup[link_id]

            # Calculate overall metrics across all failed observations
            hausdorff_distances = link_group['hausdorff_distance'].dropna()

            reference_row = {
                # Core identifiers
                'link_id': link_id,
                'data_sourc': 'reference_shapefile',
                'valid_code': link_group['valid_code'].iloc[0] if not link_group.empty and 'valid_code' in link_group.columns else 92,

                # Hausdorff metrics (always present)
                'avg_hausdo': hausdorff_distances.mean() if not hausdorff_distances.empty else None,
                'best_hausd': hausdorff_distances.min() if not hausdorff_distances.empty else None,
                'worst_haus': hausdorff_distances.max() if not hausdorff_distances.empty else None,

                # Initialize time period failure counts (≤10 chars for DBF)
                '00_06_f_cn': 0,
                '06_11_f_cn': 0,
                '11_15_f_cn': 0,
                '15_20_f_cn': 0,
                '20_00_f_cn': 0,

                # Metadata
                'total_days': len(link_group['date'].unique()),
                'total_fail': len(link_group)
            }

            # Count failures by time period, averaged across ALL days (not just days with failures)
            total_days = len(link_group['date'].unique())
            period_totals = link_group.groupby('time_period').size()

            # Map period totals to average per day across all days
            period_mapping = {
                'period_00_06': '00_06_f_cn',
                'period_06_11': '06_11_f_cn',
                'period_11_15': '11_15_f_cn',
                'period_15_20': '15_20_f_cn',
                'period_20_00': '20_00_f_cn'
            }

            for period, field in period_mapping.items():
                if period in period_totals:
                    # Average = total failures in this period / total days analyzed
                    reference_row[field] = round(period_totals[period] / total_days, 2)
                # Field already initialized to 0 if no failures in this period

            # Add length metrics if present
            if 'length_ratio' in link_group.columns:
                length_ratios = link_group['length_ratio'].dropna()
                if not length_ratios.empty:
                    reference_row['avg_len_rt'] = length_ratios.mean()
                    reference_row['best_len'] = length_ratios.min()
                    reference_row['worst_len'] = length_ratios.max()

            # Add coverage metrics if present
            if 'coverage_percent' in link_group.columns:
                coverage_percents = link_group['coverage_percent'].dropna()
                if not coverage_percents.empty:
                    reference_row['avg_cover'] = coverage_percents.mean()
                    reference_row['best_cov'] = coverage_percents.max()
                    reference_row['worst_cov'] = coverage_percents.min()  # Lower coverage is worse

            reference_rows.append(reference_row)
            geometries.append(shapefile_row['geometry'])
        else:
            print(f"Warning: Link {link_id} not found in reference shapefile")

    if not reference_rows:
        print(f"Warning: No valid reference geometries found for failed observations: {output_path}")
        return

    # Create GeoDataFrame with reference geometries
    result_gdf = gpd.GeoDataFrame(reference_rows, geometry=geometries)

    # Set CRS to match original shapefile
    result_gdf.crs = shapefile_gdf.crs or 'EPSG:4326'

    # Save shapefile
    try:
        _write_shapefile(result_gdf, output_path, driver='ESRI Shapefile')
        print(f"Created failed observations reference shapefile: {output_path}")
        print(f"  - {len(result_gdf)} unique links with time-period aggregation")
        print(f"  - Total failed observations: {sum(row['total_fail'] for row in reference_rows)}")
        print(f"  - Time periods: 00-06, 06-11, 11-15, 15-20, 20-00 (average failures per day)")
        print(f"  - Use with failed_observations.shp for visual comparison")
    except Exception as e:
        print(f"Error creating failed observations reference shapefile: {e}")


def _determine_failure_reason(row: pd.Series) -> str:
    """Determine primary failure reason for a failed observation."""
    reasons = []

    if row.get('hausdorff_pass') == False:
        hausdorff_dist = row.get('hausdorff_distance')
        if hausdorff_dist is not None:
            reasons.append(f"Hausdorff: {hausdorff_dist:.1f}m")
        else:
            reasons.append("Hausdorff failed")

    if row.get('length_pass') == False:
        length_ratio = row.get('length_ratio')
        if length_ratio is not None:
            reasons.append(f"Length: {length_ratio:.2f}x")
        else:
            reasons.append("Length failed")

    if row.get('coverage_pass') == False:
        coverage_pct = row.get('coverage_percent')
        if coverage_pct is not None:
            reasons.append(f"Coverage: {coverage_pct:.1f}%")
        else:
            reasons.append("Coverage failed")

    if not reasons:
        valid_code = row.get('valid_code')
        if valid_code == 90:
            reasons.append("Missing fields")
        elif valid_code == 91:
            reasons.append("Name parse error")
        elif valid_code == 92:
            reasons.append("Link not in shapefile")
        elif valid_code == 93:
            reasons.append("Invalid polyline")
        else:
            reasons.append("Unknown failure")

    return "; ".join(reasons)

