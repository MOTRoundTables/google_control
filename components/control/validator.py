"""
Dataset Control Validator - Row-level validation logic for Google Maps polyline data.

This module handles validation of individual CSV rows against reference shapefiles
using geometric similarity metrics.
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import Tuple, Optional, Dict, Any, Callable
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString, Point
import polyline
import numpy as np
import re
from pyproj import Transformer
from functools import lru_cache


@dataclass
class ValidationParameters:
    """Configuration object for validation thresholds and modes."""
    # Test Selection (default: only Hausdorff)
    use_hausdorff: bool = True
    use_length_check: bool = False
    use_coverage_check: bool = False

    # Hausdorff parameters
    hausdorff_threshold_m: float = 5.0

    # Length check parameters (when enabled)
    length_check_mode: str = "ratio"  # "ratio", "exact"
    length_ratio_min: float = 0.90
    length_ratio_max: float = 1.10
    epsilon_length_m: float = 0.5
    min_link_length_m: float = 20.0

    # Coverage parameters (when enabled)
    coverage_min: float = 0.85
    coverage_spacing_m: float = 1.0

    # System parameters
    crs_metric: str = "EPSG:2039"
    polyline_precision: int = 5


class ValidCode(IntEnum):
    """Simplified validation codes - context only."""

    # Context codes
    NO_ROUTE_ALTERNATIVE = 1           # Geometry only (no route_alternative field)
    SINGLE_ROUTE_ALTERNATIVE = 2       # Single route alternative
    MULTI_ROUTE_ALTERNATIVE = 3        # Multiple route alternatives

    # Data availability codes (90-94)
    REQUIRED_FIELDS_MISSING = 90
    NAME_PARSE_FAILURE = 91
    LINK_NOT_IN_SHAPEFILE = 92
    POLYLINE_DECODE_FAILURE = 93
    MISSING_OBSERVATION = 94



def _precompute_shapefile_lookup(shapefile_gdf: gpd.GeoDataFrame, target_crs: str = "EPSG:2039") -> Dict[str, Any]:
    """
    Precompute shapefile join keys and create lookup dictionary with geometries in target CRS.

    Args:
        shapefile_gdf: Reference shapefile GeoDataFrame
        target_crs: Target CRS for geometries (default: EPSG:2039)

    Returns:
        Dictionary mapping join_key -> (geometry_original, geometry_metric)
    """
    # Ensure shapefile is in target CRS for metric calculations
    if shapefile_gdf.crs is None:
        shapefile_gdf = shapefile_gdf.set_crs("EPSG:4326")

    shapefile_metric = shapefile_gdf.to_crs(target_crs)

    lookup = {}
    for idx, row in shapefile_gdf.iterrows():
        join_key = 's_' + str(row['From']) + '-' + str(row['To'])
        # Store both original and metric geometries
        lookup[join_key] = {
            'original': row['geometry'],
            'metric': shapefile_metric.loc[idx, 'geometry']
        }
    return lookup


def parse_link_name(name: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse link name to extract from_id and to_id.

    Args:
        name: Link identifier (e.g., "s_653-655")

    Returns:
        Tuple of (from_id, to_id) or (None, None) if parsing fails
    """
    if not name:
        return None, None

    try:
        # Pattern: optional s/S, underscore/dash, numbers, separator, numbers
        pattern = r'^[sS]?[_-]?(\d+)[_-](\d+)$'
        match = re.match(pattern, str(name).strip())

        if match:
            from_id, to_id = match.groups()
            return from_id, to_id
        return None, None
    except Exception:
        return None, None


@lru_cache(maxsize=10000)
def decode_polyline(encoded: str, precision: int = 5) -> Optional[LineString]:
    """
    Decode Google Maps encoded polyline with caching.

    Args:
        encoded: Encoded polyline string
        precision: Encoding precision (default 5)

    Returns:
        Shapely LineString or None if decoding fails
    """
    if not encoded:
        return None

    try:
        # Decode using polyline library
        points = polyline.decode(encoded, precision)

        if len(points) < 2:
            return None

        # Convert to LineString (points are in (lat, lon) format)
        # Note: Shapely expects (x, y) which is (lon, lat)
        coords = [(lon, lat) for lat, lon in points]
        return LineString(coords)

    except Exception:
        return None


@lru_cache(maxsize=4)
def get_transformer(from_crs: str, to_crs: str) -> Transformer:
    """
    Get a cached CRS transformer.

    Args:
        from_crs: Source CRS
        to_crs: Target CRS

    Returns:
        Cached pyproj Transformer
    """
    return Transformer.from_crs(from_crs, to_crs, always_xy=True)


def calculate_hausdorff(line1: LineString, line2: LineString, crs: str = "EPSG:2039",
                        line2_already_metric: bool = False) -> float:
    """
    Calculate Hausdorff distance between two lines in meters.

    Args:
        line1: First geometry (assumed to be in EPSG:4326)
        line2: Second geometry (in EPSG:4326 or already in metric CRS if line2_already_metric=True)
        crs: Target metric CRS for calculation (default: EPSG:2039)
        line2_already_metric: If True, line2 is already in the metric CRS

    Returns:
        Hausdorff distance in meters
    """
    import math
    from shapely.ops import transform

    try:
        # Validate geometries first
        if not line1.is_valid or not line2.is_valid:
            # Try to fix invalid geometries
            line1 = line1.buffer(0) if not line1.is_valid else line1
            line2 = line2.buffer(0) if not line2.is_valid else line2

        # Check for empty geometries
        if line1.is_empty or line2.is_empty:
            return float('inf')  # Treat empty geometries as infinite distance

        # Transform line1 (always in WGS84)
        transformer = get_transformer("EPSG:4326", crs)
        geom1_metric = transform(transformer.transform, line1)

        # Transform line2 only if needed
        if line2_already_metric:
            geom2_metric = line2
        else:
            geom2_metric = transform(transformer.transform, line2)

        # Check if reprojected geometries are valid
        if not geom1_metric.is_valid or not geom2_metric.is_valid:
            geom1_metric = geom1_metric.buffer(0) if not geom1_metric.is_valid else geom1_metric
            geom2_metric = geom2_metric.buffer(0) if not geom2_metric.is_valid else geom2_metric

        # Always compute exact Hausdorff distance
        distance = geom1_metric.hausdorff_distance(geom2_metric)

        # Check for nan result
        if math.isnan(distance):
            return float('inf')  # Treat nan as infinite distance

        return distance

    except Exception as e:
        # If CRS transformation fails, raise an error instead of silently returning wrong values
        # The old behavior was returning degree-based distances claiming they were meters
        raise ValueError(f"Failed to calculate Hausdorff distance in metric units: {e}")


def check_length_similarity(
    polyline_geom: LineString,
    reference_geom: LineString,
    mode: str,
    params: ValidationParameters
) -> bool:
    """
    Check if polyline length matches reference within tolerance.

    Args:
        polyline_geom: Decoded polyline geometry
        reference_geom: Reference link geometry
        mode: Check mode ("off", "ratio", "exact")
        params: Validation parameters

    Returns:
        True if length check passes
    """
    if mode == "off":
        return True

    try:
        poly_length = polyline_geom.length
        ref_length = reference_geom.length

        if ref_length <= 0:
            # Degenerate reference - treat as match only when the polyline is effectively zero as well
            return abs(poly_length) <= params.epsilon_length_m

        if mode == "ratio":
            ratio = poly_length / ref_length
            if ref_length < params.min_link_length_m:
                # Short links: widen tolerance slightly but still enforce bounds
                expanded_min = max(0.0, params.length_ratio_min - 0.05)
                expanded_max = params.length_ratio_max + 0.05
                return expanded_min <= ratio <= expanded_max
            return params.length_ratio_min <= ratio <= params.length_ratio_max

        elif mode == "exact":
            diff = abs(poly_length - ref_length)
            if ref_length < params.min_link_length_m:
                effective_epsilon = max(params.epsilon_length_m, 0.01 * params.min_link_length_m)
                return diff <= effective_epsilon
            return diff <= params.epsilon_length_m

        return False

    except Exception:
        return False


def calculate_coverage(
    polyline_geom: LineString,
    reference_geom: LineString,
    spacing: float = 1.0
) -> float:
    """
    Calculate coverage of reference by polyline.

    Args:
        polyline_geom: Decoded polyline geometry
        reference_geom: Reference link geometry
        spacing: Densification spacing in meters (configurable via coverage_spacing_m)

    Returns:
        Coverage fraction (0.0 to 1.0)
    """
    try:
        if reference_geom.length == 0:
            return 0.0

        overlap_length = reference_geom.intersection(polyline_geom).length
        if overlap_length == 0.0:
            tolerance = max(spacing, 1e-6)
            buffered_poly = polyline_geom.buffer(tolerance, cap_style=1)
            overlap = reference_geom.intersection(buffered_poly)
            overlap_length = overlap.length if not overlap.is_empty else 0.0

        coverage = overlap_length / reference_geom.length
        return float(max(0.0, min(coverage, 1.0)))

    except Exception:
        return 0.0


def _get_column_mapping(df: pd.DataFrame) -> dict:
    """
    Create column mapping to handle different naming conventions.
    Maps from expected names to actual column names in the dataframe.
    """
    # Define possible column name variations
    column_variations = {
        'name': ['name', 'Name'],
        'polyline': ['polyline', 'Polyline'],
        'timestamp': ['timestamp', 'Timestamp'],
        'route_alternative': ['route_alternative', 'RouteAlternative']
    }

    column_map = {}
    for expected, variations in column_variations.items():
        for variant in variations:
            if variant in df.columns:
                column_map[expected] = variant
                break
        else:
            column_map[expected] = None  # Column not found

    return column_map


def _map_row_columns(row, col_map: dict) -> dict:
    """Map row columns from actual names to expected names for validation."""
    if isinstance(row, pd.Series):
        accessor = row
        return {expected: accessor.get(actual) if actual is not None else None for expected, actual in col_map.items()}

    if isinstance(row, dict):
        accessor = row
        return {expected: accessor.get(actual) if actual is not None else None for expected, actual in col_map.items()}

    def _pull(value_key: str):
        if value_key is None:
            return None
        if hasattr(row, value_key):
            return getattr(row, value_key)
        try:
            return row[value_key]  # type: ignore[index]
        except (KeyError, TypeError, AttributeError):
            pass
        if hasattr(row, "_asdict"):
            cached = row._asdict()
            return cached.get(value_key)
        return None

    return {expected: _pull(actual) for expected, actual in col_map.items()}


def validate_dataframe_batch(
    df: pd.DataFrame,
    shapefile_gdf: gpd.GeoDataFrame,
    params: ValidationParameters,
    progress_callback: Optional[callable] = None
) -> pd.DataFrame:
    """
    Validate DataFrame with proper route alternative processing using new configuration codes.

    Each route alternative is tested individually and gets its own result code.
    The code indicates the test configuration attempted and whether it passed/failed.

    Args:
        df: DataFrame with observation rows
        shapefile_gdf: Reference shapefile
        params: Validation parameters

    Returns:
        DataFrame with added validation columns (is_valid, valid_code)
    """
    # Get column mapping to handle different naming conventions
    col_map = _get_column_mapping(df)

    # OPTIMIZATION: Convert name column to categorical for faster groupby
    if col_map['name'] is not None and col_map['name'] in df.columns:
        df[col_map['name']] = df[col_map['name']].astype('category')

    # OPTIMIZATION: Precompute shapefile join keys once
    shapefile_lookup = _precompute_shapefile_lookup(shapefile_gdf, params.crs_metric)

    # Check for required columns using column mapping
    required_cols = ['name', 'timestamp']
    missing_cols = [col for col in required_cols if col_map[col] is None]

    # Check if route_alternative column is missing - if so, use geometry-only validation
    if missing_cols or col_map['route_alternative'] is None:
        # Geometry-only validation when route_alternative is missing
        results = []
        for row in df.itertuples(index=True, name='Row'):
            mapped_row = _map_row_columns(row, col_map)
            core_result = _validate_single_row_core(mapped_row, shapefile_gdf, params,
                                                    require_route_alternative=False,
                                                    shapefile_lookup=shapefile_lookup)

            if core_result['valid_code'] not in [90, 91, 92, 93]:
                core_result['valid_code'] = ValidCode.NO_ROUTE_ALTERNATIVE
            results.append(core_result)

        result_df = pd.DataFrame(results, index=df.index)
        return pd.concat([df, result_df], axis=1)

    # Separate rows with and without timestamps
    df_with_timestamps = df[df[col_map['timestamp']].notna()]
    df_without_timestamps = df[df[col_map['timestamp']].isna()]

    result_records = {}

    # Handle rows without timestamps first (they get REQUIRED_FIELDS_MISSING)
    for idx in df_without_timestamps.index:
        result = {
            'is_valid': False,
            'valid_code': ValidCode.REQUIRED_FIELDS_MISSING,
            'hausdorff_distance': None,
            'hausdorff_pass': False,
        }
        if params.use_length_check:
            result['length_ratio'] = None
            result['length_pass'] = False
        if params.use_coverage_check:
            result['coverage_percent'] = None
            result['coverage_pass'] = False
        result_records[idx] = result

    # Group rows with timestamps by link and timestamp to detect single vs multi alternatives
    if len(df_with_timestamps) > 0:
        grouped = df_with_timestamps.groupby([col_map['name'], col_map['timestamp']], sort=False, observed=True)

        total_groups = len(grouped)
        group_count = 0

        for (link_name, timestamp), group in grouped:
            group_count += 1

            # Report progress every 100 groups or 5% of total groups
            if progress_callback and (group_count % 100 == 0 or group_count % max(1, total_groups // 20) == 0):
                progress_pct = int((group_count / total_groups) * 100)
                progress_callback(f"Processing validation: {progress_pct}% ({group_count:,}/{total_groups:,} groups)")

            group_size = len(group)
            is_single_alternative = group_size == 1

            for row in group.itertuples(index=True, name='Row'):
                mapped_row = _map_row_columns(row, col_map)
                core_result = _validate_single_row_core(
                    mapped_row,
                    shapefile_gdf,
                    params,
                    shapefile_lookup=shapefile_lookup,
                )

                if core_result['valid_code'] not in [90, 91, 92, 93]:
                    core_result['valid_code'] = (
                        ValidCode.SINGLE_ROUTE_ALTERNATIVE if is_single_alternative else ValidCode.MULTI_ROUTE_ALTERNATIVE
                    )

                result_records[row.Index] = core_result

    # Build result dataframe aligned to the original index order
    result_df = pd.DataFrame.from_dict(result_records, orient='index')
    result_df = result_df.reindex(df.index)

    # Combine with original data
    combined_df = pd.concat([df.reset_index(drop=True), result_df.reset_index(drop=True)], axis=1)

    # Sort final output by Name, Timestamp, RouteAlternative for consistent ordering
    col_map = _get_column_mapping(df)
    sort_columns = []
    if col_map['name']:
        sort_columns.append(col_map['name'])
    if col_map['timestamp']:
        sort_columns.append(col_map['timestamp'])
    if col_map['route_alternative']:
        sort_columns.append(col_map['route_alternative'])

    if sort_columns:
        combined_df = combined_df.sort_values(sort_columns).reset_index(drop=True)

    return combined_df


def _validate_chunk_worker(chunk_data):
    """
    Worker function for parallel validation of a data chunk.

    Args:
        chunk_data: Dictionary containing:
            - df_chunk: DataFrame chunk to validate
            - shapefile_data: Serialized shapefile data
            - params_dict: ValidationParameters as dict
            - col_map: Column mapping

    Returns:
        List of result dictionaries with original indices
    """
    import geopandas as gpd
    from shapely.geometry import Point, LineString

    # Reconstruct objects from serialized data
    df_chunk = chunk_data['df_chunk']
    shapefile_gdf = gpd.GeoDataFrame.from_features(
        chunk_data['shapefile_data']['features'],
        crs=chunk_data['shapefile_data']['crs']
    )

    # Reconstruct ValidationParameters
    params_dict = chunk_data['params_dict']
    params = ValidationParameters(**params_dict)

    col_map = chunk_data['col_map']

    # Precompute shapefile lookup for this worker
    shapefile_lookup = _precompute_shapefile_lookup(shapefile_gdf, params.crs_metric)

    results = []

    # Process each row in the chunk
    for row in df_chunk.itertuples(index=True, name='Row'):
        mapped_row = _map_row_columns(row, col_map)

        # Check for missing timestamp
        if col_map['timestamp'] is None or pd.isna(getattr(row, col_map['timestamp'], None)):
            result = {
                'original_index': row.Index,
                'is_valid': False,
                'valid_code': ValidCode.REQUIRED_FIELDS_MISSING,
                'hausdorff_distance': None,
                'hausdorff_pass': False,
            }
            if params.use_length_check:
                result['length_ratio'] = None
                result['length_pass'] = False
            if params.use_coverage_check:
                result['coverage_percent'] = None
                result['coverage_pass'] = False
            results.append(result)
            continue

        # Validate the row
        core_result = _validate_single_row_core(
            mapped_row,
            shapefile_gdf,
            params,
            shapefile_lookup=shapefile_lookup,
        )

        # Add original index for later sorting
        core_result['original_index'] = row.Index
        results.append(core_result)

    return results


def validate_dataframe_batch_parallel(
    df: pd.DataFrame,
    shapefile_gdf: gpd.GeoDataFrame,
    params: ValidationParameters,
    max_workers: Optional[int] = None,
    progress_callback: Optional[callable] = None
) -> pd.DataFrame:
    """
    Validate DataFrame using parallel processing with proper route alternative handling.

    Args:
        df: DataFrame with observation rows
        shapefile_gdf: Reference shapefile
        params: Validation parameters
        max_workers: Maximum number of worker processes (default: CPU count)
        progress_callback: Optional callback for progress updates

    Returns:
        DataFrame with added validation columns (is_valid, valid_code)
    """
    if max_workers is None:
        max_workers = min(8, max(2, os.cpu_count() or 1))

    # For small datasets, use sequential processing
    # Parallel overhead not worth it for small datasets
    if len(df) < 5000:
        return validate_dataframe_batch(df, shapefile_gdf, params, progress_callback)

    # Get column mapping
    col_map = _get_column_mapping(df)

    # Convert name column to categorical for faster groupby
    if col_map['name'] is not None and col_map['name'] in df.columns:
        df[col_map['name']] = df[col_map['name']].astype('category')

    # Prepare shapefile data for serialization
    shapefile_data = {
        'features': shapefile_gdf.__geo_interface__['features'],
        'crs': str(shapefile_gdf.crs) if shapefile_gdf.crs else 'EPSG:4326'
    }

    # Convert ValidationParameters to dict for serialization
    params_dict = {
        'use_hausdorff': params.use_hausdorff,
        'use_length_check': params.use_length_check,
        'use_coverage_check': params.use_coverage_check,
        'hausdorff_threshold_m': params.hausdorff_threshold_m,
        'length_check_mode': params.length_check_mode,
        'length_ratio_min': params.length_ratio_min,
        'length_ratio_max': params.length_ratio_max,
        'epsilon_length_m': params.epsilon_length_m,
        'min_link_length_m': params.min_link_length_m,
        'coverage_min': params.coverage_min,
        'coverage_spacing_m': params.coverage_spacing_m,
        'crs_metric': params.crs_metric,
        'polyline_precision': params.polyline_precision
    }

    # Split DataFrame into chunks by link_id for better load balancing
    if col_map['name'] is not None:
        link_groups = list(df.groupby(col_map['name'], observed=True))

        # Distribute link groups across workers for better load balancing
        chunks = [[] for _ in range(max_workers)]
        for i, (link_id, group) in enumerate(link_groups):
            chunks[i % max_workers].extend([group])

        # Combine groups into worker chunks
        worker_chunks = []
        for chunk_groups in chunks:
            if chunk_groups:
                worker_chunk = pd.concat(chunk_groups, ignore_index=False)
                worker_chunks.append(worker_chunk)
    else:
        # Fallback: split by rows if no name column
        chunk_size = max(100, len(df) // max_workers)
        worker_chunks = [df[i:i + chunk_size] for i in range(0, len(df), chunk_size)]

    # Prepare chunk data for workers
    chunk_data_list = []
    for chunk in worker_chunks:
        if not chunk.empty:
            chunk_data = {
                'df_chunk': chunk,
                'shapefile_data': shapefile_data,
                'params_dict': params_dict,
                'col_map': col_map
            }
            chunk_data_list.append(chunk_data)

    # Process chunks in parallel
    all_results = []
    completed_chunks = 0
    total_chunks = len(chunk_data_list)

    if progress_callback:
        progress_callback(f"Starting parallel validation with {max_workers} workers...")

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all chunks
        future_to_chunk = {
            executor.submit(_validate_chunk_worker, chunk_data): i
            for i, chunk_data in enumerate(chunk_data_list)
        }

        # Collect results as they complete
        for future in as_completed(future_to_chunk):
            try:
                chunk_results = future.result()
                all_results.extend(chunk_results)

                completed_chunks += 1
                if progress_callback and completed_chunks % max(1, total_chunks // 10) == 0:
                    progress_pct = int((completed_chunks / total_chunks) * 100)
                    progress_callback(f"Parallel validation: {progress_pct}% ({completed_chunks}/{total_chunks} chunks)")

            except Exception as e:
                chunk_idx = future_to_chunk[future]
                raise RuntimeError(f"Worker failed on chunk {chunk_idx}: {e}")

    if progress_callback:
        progress_callback("Combining parallel results...")

    # Convert results to DataFrame and sort by original index
    result_records = {result['original_index']: result for result in all_results}

    # Handle context codes and grouping for route alternatives
    df_with_timestamps = df[df[col_map['timestamp']].notna()] if col_map['timestamp'] else df

    if len(df_with_timestamps) > 0 and col_map['name'] and col_map['timestamp']:
        grouped = df_with_timestamps.groupby([col_map['name'], col_map['timestamp']], sort=False, observed=True)

        for (link_name, timestamp), group in grouped:
            group_size = len(group)
            is_single_alternative = group_size == 1

            # Update context codes for this group
            for idx in group.index:
                if idx in result_records and result_records[idx]['valid_code'] not in [90, 91, 92, 93]:
                    result_records[idx]['valid_code'] = (
                        ValidCode.SINGLE_ROUTE_ALTERNATIVE if is_single_alternative else ValidCode.MULTI_ROUTE_ALTERNATIVE
                    )

    # Build result DataFrame aligned to original index
    for result in result_records.values():
        result.pop('original_index', None)  # Remove helper field

    result_df = pd.DataFrame.from_dict(result_records, orient='index')
    result_df = result_df.reindex(df.index)

    # Combine with original data
    combined_df = pd.concat([df.reset_index(drop=True), result_df.reset_index(drop=True)], axis=1)

    # Sort final output
    sort_columns = []
    if col_map['name']:
        sort_columns.append(col_map['name'])
    if col_map['timestamp']:
        sort_columns.append(col_map['timestamp'])
    if col_map['route_alternative']:
        sort_columns.append(col_map['route_alternative'])

    if sort_columns:
        combined_df = combined_df.sort_values(sort_columns).reset_index(drop=True)

    return combined_df


def _validate_row_geometry_only(
    row: pd.Series,
    shapefile_gdf: gpd.GeoDataFrame,
    params: ValidationParameters
) -> Tuple[bool, int]:
    """
    Internal function: Validate row geometry without route alternative logic.
    Returns pure geometry test results (codes 0-4, 90-93).
    """
    # Use the existing validate_row logic but don't require route_alternative
    core_result = _validate_single_row_core(row, shapefile_gdf, params, require_route_alternative=False)
    return core_result['is_valid'], core_result['valid_code']


def _validate_single_row_core(
    row: pd.Series,
    shapefile_gdf: gpd.GeoDataFrame,
    params: ValidationParameters,
    require_route_alternative: bool = True,
    shapefile_lookup: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Core validation logic with individual test results.
    Returns dictionary with detailed test results and simplified context codes.
    """
    result = {
        'is_valid': False,
        'valid_code': ValidCode.NO_ROUTE_ALTERNATIVE
    }

    try:
        # Step 1: Data availability checks (codes 90-93)
        required_fields = ['name', 'polyline']
        if require_route_alternative:
            required_fields.append('route_alternative')

        for field in required_fields:
            if field not in row or pd.isna(row[field]):
                result['valid_code'] = ValidCode.REQUIRED_FIELDS_MISSING
                return result

        # Step 2: Parse link name
        from_id, to_id = parse_link_name(row['name'])
        if from_id is None or to_id is None:
            result['valid_code'] = ValidCode.NAME_PARSE_FAILURE
            return result

        # Step 3: Join to shapefile
        join_key = f"s_{from_id}-{to_id}"

        # Use precomputed lookup if available (much faster)
        if shapefile_lookup is None:
            shapefile_lookup = _precompute_shapefile_lookup(shapefile_gdf, params.crs_metric)

        geom_data = shapefile_lookup.get(join_key)
        if geom_data is None:
            result['valid_code'] = ValidCode.LINK_NOT_IN_SHAPEFILE
            return result

        # Extract both original and metric geometries
        reference_geom = geom_data['original'] if isinstance(geom_data, dict) else geom_data
        reference_geom_metric = geom_data.get('metric', reference_geom) if isinstance(geom_data, dict) else reference_geom

        # Step 4: Decode polyline
        decoded_geom = decode_polyline(row['polyline'], params.polyline_precision)
        if decoded_geom is None:
            result['valid_code'] = ValidCode.POLYLINE_DECODE_FAILURE
            return result

        # Step 5: Context code (will be updated by caller based on grouping)
        if require_route_alternative:
            result['valid_code'] = ValidCode.SINGLE_ROUTE_ALTERNATIVE  # Default, updated by caller
        else:
            result['valid_code'] = ValidCode.NO_ROUTE_ALTERNATIVE

        # Step 6: Individual test evaluations
        all_tests_pass = True

        # TEST 1: Hausdorff Distance (always tested)
        try:
            # Use the pre-cached metric geometry for reference (already in metric CRS)
            hausdorff_distance = calculate_hausdorff(
                decoded_geom, reference_geom_metric, params.crs_metric,
                line2_already_metric=True
            )
            hausdorff_pass = (hausdorff_distance <= params.hausdorff_threshold_m)

            result['hausdorff_distance'] = hausdorff_distance
            result['hausdorff_pass'] = hausdorff_pass

            if not hausdorff_pass:
                all_tests_pass = False
        except Exception as exc:
            raise ValueError(f"Hausdorff calculation failed for {join_key}: {exc}") from exc

        # Step 7: Prepare geometries for length/coverage tests if needed
        # Use the pre-cached metric geometry for reference
        ref_geom_metric = reference_geom_metric

        if params.use_length_check or params.use_coverage_check:
            try:
                # Only need to transform the decoded polyline geometry
                decoded_gdf = gpd.GeoDataFrame([1], geometry=[decoded_geom], crs="EPSG:4326")
                decoded_metric = decoded_gdf.to_crs(params.crs_metric)
                poly_geom_metric = decoded_metric.geometry.iloc[0]
            except Exception:
                # Keep original geometry if transformation fails
                poly_geom_metric = decoded_geom
        else:
            poly_geom_metric = decoded_geom

        # TEST 2: Length Check (if enabled)
        if params.use_length_check:
            try:
                poly_length = poly_geom_metric.length
                ref_length = ref_geom_metric.length

                # Skip for very short links
                if ref_length >= params.min_link_length_m:
                    if params.length_check_mode == "ratio":
                        length_ratio = poly_length / ref_length if ref_length > 0 else 0
                        length_pass = (params.length_ratio_min <= length_ratio <= params.length_ratio_max)
                        result['length_ratio'] = length_ratio
                    elif params.length_check_mode == "exact":
                        length_diff = abs(poly_length - ref_length)
                        length_pass = (length_diff <= params.epsilon_length_m)
                        result['length_diff'] = length_diff
                    else:
                        length_pass = True  # "off" mode
                else:
                    length_pass = True  # Short link - skip test

                result['length_pass'] = length_pass

                if not length_pass:
                    all_tests_pass = False
            except Exception:
                result['length_pass'] = False
                all_tests_pass = False

        # TEST 3: Coverage Check (if enabled)
        if params.use_coverage_check:
            try:
                coverage = calculate_coverage(poly_geom_metric, ref_geom_metric, params.coverage_spacing_m)
                coverage_percent = coverage * 100  # Convert to percentage
                coverage_pass = (coverage >= params.coverage_min)

                result['coverage_percent'] = coverage_percent
                result['coverage_pass'] = coverage_pass

                if not coverage_pass:
                    all_tests_pass = False
            except Exception:
                result['coverage_percent'] = 0.0
                result['coverage_pass'] = False
                all_tests_pass = False

        # Final is_valid determination - ALL enabled tests must pass
        result['is_valid'] = all_tests_pass

        return result

    except Exception:
        result['is_valid'] = False
        result['valid_code'] = ValidCode.REQUIRED_FIELDS_MISSING
        return result


def validate_row(
    row: pd.Series,
    shapefile_gdf: gpd.GeoDataFrame,
    params: ValidationParameters
) -> Tuple[bool, int]:
    """
    Validate a single observation row using new configuration-based codes.

    This function treats each row as a single alternative for backwards compatibility.
    For proper batch route alternative handling, use validate_dataframe_batch() instead.

    Returns configuration-based validation codes where the second digit represents
    the test configuration that was attempted.
    """
    # Create a single-row dataframe for column mapping
    temp_df = pd.DataFrame([row]).T.T
    col_map = _get_column_mapping(temp_df)
    mapped_row = _map_row_columns(row, col_map)

    # Get core validation result
    core_result = _validate_single_row_core(mapped_row, shapefile_gdf, params)
    is_valid = core_result['is_valid']
    base_code = core_result['valid_code']

    # Set context to single alternative
    if core_result['valid_code'] not in [90, 91, 92, 93]:  # Not a data error
        core_result['valid_code'] = ValidCode.SINGLE_ROUTE_ALTERNATIVE

    return core_result['is_valid'], core_result['valid_code']