"""
Dataset Control Validator - Row-level validation logic for Google Maps polyline data.

This module handles validation of individual CSV rows against reference shapefiles
using geometric similarity metrics.
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import Tuple, Optional, Dict, Any
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



def _precompute_shapefile_lookup(shapefile_gdf: gpd.GeoDataFrame) -> Dict[str, Any]:
    """
    Precompute shapefile join keys and create lookup dictionary.

    Args:
        shapefile_gdf: Reference shapefile GeoDataFrame

    Returns:
        Dictionary mapping join_key -> geometry
    """
    lookup = {}
    for idx, row in shapefile_gdf.iterrows():
        join_key = 's_' + str(row['From']) + '-' + str(row['To'])
        lookup[join_key] = row['geometry']
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


def decode_polyline(encoded: str, precision: int = 5) -> Optional[LineString]:
    """
    Decode Google Maps encoded polyline.

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


def calculate_hausdorff(line1: LineString, line2: LineString, crs: str = "EPSG:2039") -> float:
    """
    Calculate Hausdorff distance between two lines in meters.

    Args:
        line1: First geometry (assumed to be in EPSG:4326 if no CRS specified)
        line2: Second geometry (assumed to be in EPSG:4326 if no CRS specified)
        crs: Target metric CRS for calculation (default: EPSG:2039)

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

        # Use cached transformer for CRS conversion
        transformer = get_transformer("EPSG:4326", crs)

        # Transform geometries directly using shapely.ops.transform
        geom1_metric = transform(transformer.transform, line1)
        geom2_metric = transform(transformer.transform, line2)

        # Check if reprojected geometries are valid
        if not geom1_metric.is_valid or not geom2_metric.is_valid:
            geom1_metric = geom1_metric.buffer(0) if not geom1_metric.is_valid else geom1_metric
            geom2_metric = geom2_metric.buffer(0) if not geom2_metric.is_valid else geom2_metric

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

        tolerance = max(spacing, 1e-6)
        buffered_poly = polyline_geom.buffer(tolerance, cap_style=2)
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


def _map_row_columns(row: pd.Series, col_map: dict) -> pd.Series:
    """
    Map row columns from actual names to expected names for validation.
    """
    mapped_data = {}
    for expected, actual in col_map.items():
        if actual is not None and actual in row.index:
            mapped_data[expected] = row[actual]
        else:
            mapped_data[expected] = None
    return pd.Series(mapped_data)


def validate_dataframe_batch(
    df: pd.DataFrame,
    shapefile_gdf: gpd.GeoDataFrame,
    params: ValidationParameters
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

    # OPTIMIZATION: Precompute shapefile join keys once
    shapefile_lookup = _precompute_shapefile_lookup(shapefile_gdf)

    # Check for required columns using column mapping
    required_cols = ['name', 'timestamp']
    missing_cols = [col for col in required_cols if col_map[col] is None]

    # Check if route_alternative column is missing - if so, use geometry-only validation
    if missing_cols or col_map['route_alternative'] is None:
        # Geometry-only validation when route_alternative is missing
        results = []
        for idx, row in df.iterrows():
            # Create mapped row for validation
            mapped_row = _map_row_columns(row, col_map)
            core_result = _validate_single_row_core(mapped_row, shapefile_gdf, params,
                                                    require_route_alternative=False,
                                                    shapefile_lookup=shapefile_lookup)

            # Set context to geometry-only
            if core_result['valid_code'] not in [90, 91, 92, 93]:  # Not a data error
                core_result['valid_code'] = ValidCode.NO_ROUTE_ALTERNATIVE
            results.append(core_result)

        result_df = pd.DataFrame(results)
        return pd.concat([df, result_df], axis=1)

    # Separate rows with and without timestamps
    df_with_timestamps = df[df[col_map['timestamp']].notna()]
    df_without_timestamps = df[df[col_map['timestamp']].isna()]

    results = []

    # Handle rows without timestamps first (they get REQUIRED_FIELDS_MISSING)
    for idx, row in df_without_timestamps.iterrows():
        result = {
            'index': idx,
            'is_valid': False,
            'valid_code': ValidCode.REQUIRED_FIELDS_MISSING,
            'hausdorff_distance': None,
            'hausdorff_pass': False
        }
        # Add length and coverage fields only if those tests are enabled
        if params.use_length_check:
            result['length_ratio'] = None
            result['length_pass'] = False
        if params.use_coverage_check:
            result['coverage_percent'] = None
            result['coverage_pass'] = False
        results.append(result)

    # Group rows with timestamps by link and timestamp to detect single vs multi alternatives
    if len(df_with_timestamps) > 0:
        grouped = df_with_timestamps.groupby([col_map['name'], col_map['timestamp']])

        for (link_name, timestamp), group in grouped:
            # Determine context: single or multi alternative
            group_size = len(group)
            is_single_alternative = (group_size == 1)
            context = 'single_alt' if is_single_alternative else 'multi_alt'

            # Process each row in the group individually
            for idx, row in group.iterrows():
                # Create mapped row for validation
                mapped_row = _map_row_columns(row, col_map)
                # Get core validation result
                core_result = _validate_single_row_core(mapped_row, shapefile_gdf, params,
                                                        shapefile_lookup=shapefile_lookup)

                # Set context based on group size
                if core_result['valid_code'] not in [90, 91, 92, 93]:  # Not a data error
                    if is_single_alternative:
                        core_result['valid_code'] = ValidCode.SINGLE_ROUTE_ALTERNATIVE
                    else:
                        core_result['valid_code'] = ValidCode.MULTI_ROUTE_ALTERNATIVE

                # Add index for sorting
                core_result['index'] = idx
                results.append(core_result)

    # Sort results by original DataFrame index
    results_sorted = sorted(results, key=lambda x: x['index'])

    # Create result DataFrame with individual test results
    result_data = []
    for r in results_sorted:
        row_result = {
            'is_valid': r['is_valid'],
            'valid_code': r['valid_code']
        }
        # Add individual test results (only include fields that were actually tested)
        if 'hausdorff_distance' in r:
            row_result['hausdorff_distance'] = r['hausdorff_distance']
            row_result['hausdorff_pass'] = r['hausdorff_pass']
        if 'length_ratio' in r:
            row_result['length_ratio'] = r['length_ratio']
            row_result['length_pass'] = r['length_pass']
        if 'coverage_percent' in r:
            row_result['coverage_percent'] = r['coverage_percent']
            row_result['coverage_pass'] = r['coverage_pass']
        result_data.append(row_result)

    result_df = pd.DataFrame(result_data)

    # Combine with original data
    combined_df = pd.concat([df.reset_index(drop=True), result_df], axis=1)

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
        if shapefile_lookup is not None:
            reference_geom = shapefile_lookup.get(join_key)
            if reference_geom is None:
                result['valid_code'] = ValidCode.LINK_NOT_IN_SHAPEFILE
                return result
        else:
            # Fallback to old method if no lookup provided (for backwards compatibility)
            shapefile_copy = shapefile_gdf.copy()
            shapefile_copy['join_key'] = 's_' + shapefile_copy['From'].astype(str) + '-' + shapefile_copy['To'].astype(str)

            matching_links = shapefile_copy[shapefile_copy['join_key'] == join_key]
            if len(matching_links) == 0:
                result['valid_code'] = ValidCode.LINK_NOT_IN_SHAPEFILE
                return result

            reference_geom = matching_links.iloc[0]['geometry']

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
            hausdorff_distance = calculate_hausdorff(decoded_geom, reference_geom, params.crs_metric)
            hausdorff_pass = (hausdorff_distance <= params.hausdorff_threshold_m)

            # Always include Hausdorff results
            result['hausdorff_distance'] = hausdorff_distance
            result['hausdorff_pass'] = hausdorff_pass

            if not hausdorff_pass:
                all_tests_pass = False
        except Exception:
            result['hausdorff_distance'] = float('inf')
            result['hausdorff_pass'] = False
            all_tests_pass = False

        # Step 7: Prepare geometries for length/coverage tests if needed
        poly_geom_metric = decoded_geom
        ref_geom_metric = reference_geom

        if params.use_length_check or params.use_coverage_check:
            try:
                decoded_gdf = gpd.GeoDataFrame([1], geometry=[decoded_geom], crs="EPSG:4326")
                ref_gdf = gpd.GeoDataFrame([1], geometry=[reference_geom])
                if ref_gdf.crs is None:
                    ref_gdf = ref_gdf.set_crs("EPSG:4326")

                decoded_metric = decoded_gdf.to_crs(params.crs_metric)
                ref_metric = ref_gdf.to_crs(params.crs_metric)

                poly_geom_metric = decoded_metric.geometry.iloc[0]
                ref_geom_metric = ref_metric.geometry.iloc[0]
            except Exception:
                # Keep original geometries if transformation fails
                pass

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