# Internal Function Contracts

## control_validator.py

### Core Validation Function
```python
def validate_row(
    row: pd.Series,
    shapefile_gdf: gpd.GeoDataFrame,
    params: ValidationParameters
) -> Tuple[bool, int]:
    """
    Validate a single observation row against reference shapefile.

    Args:
        row: Pandas Series with required fields (name, polyline, route_alternative)
        shapefile_gdf: Reference shapefile as GeoDataFrame with From, To, geometry
        params: Validation parameters for thresholds and modes

    Returns:
        Tuple of (is_valid, valid_code)
        - is_valid: True if observation matches reference
        - valid_code: Integer code explaining validation result

    Raises:
        None - All errors return appropriate valid_code
    """
```

### Helper Functions
```python
def parse_link_name(name: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse link name to extract from_id and to_id.

    Args:
        name: Link identifier (e.g., "s_653-655")

    Returns:
        Tuple of (from_id, to_id) or (None, None) if parsing fails
    """

def decode_polyline(encoded: str, precision: int = 5) -> Optional[LineString]:
    """
    Decode Google Maps encoded polyline.

    Args:
        encoded: Encoded polyline string
        precision: Encoding precision (default 5)

    Returns:
        Shapely LineString or None if decoding fails
    """

def calculate_hausdorff(
    line1: LineString,
    line2: LineString,
    crs: str = "EPSG:2039"
) -> float:
    """
    Calculate Hausdorff distance between two lines.

    Args:
        line1: First geometry
        line2: Second geometry
        crs: Target CRS for calculation

    Returns:
        Hausdorff distance in meters
    """

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
```

## control_report.py

### Report Generation Function
```python
def generate_link_report(
    validated_df: pd.DataFrame,
    shapefile_gdf: gpd.GeoDataFrame,
    date_filter: Optional[Dict] = None
) -> gpd.GeoDataFrame:
    """
    Generate per-link validation report.

    Args:
        validated_df: DataFrame with validation results (is_valid, valid_code)
        shapefile_gdf: Reference shapefile to add report fields to
        date_filter: Optional date filtering (start_date, end_date, specific_day)

    Returns:
        GeoDataFrame with added fields: result_code, result_label, num
    """
```

### Aggregation Functions
```python
def aggregate_link_statistics(
    link_data: pd.DataFrame
) -> Dict[str, Any]:
    """
    Aggregate validation statistics for a single link.

    Args:
        link_data: Filtered DataFrame for one link

    Returns:
        Dictionary with aggregated statistics
    """

def determine_result_code(
    stats: Dict[str, Any]
) -> Tuple[int, str, Optional[float]]:
    """
    Determine result code, label, and percentage for link.

    Args:
        stats: Aggregated statistics dictionary

    Returns:
        Tuple of (result_code, result_label, num)
    """

def deduplicate_observations(
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    Remove duplicate observations by link_id, timestamp, polyline.

    Args:
        df: Input DataFrame

    Returns:
        Deduplicated DataFrame
    """

def write_shapefile_with_results(
    gdf: gpd.GeoDataFrame,
    output_path: str
) -> None:
    """
    Write shapefile with added result fields.

    Args:
        gdf: GeoDataFrame with result fields
        output_path: Output shapefile path

    Returns:
        None

    Raises:
        IOError: If write fails
    """
```

## Integration Functions (app.py)

### UI Integration
```python
def render_control_page() -> None:
    """
    Render Streamlit UI page for dataset control.

    Components:
        - File uploaders for CSV and shapefile
        - Parameter controls (sliders, selectboxes)
        - Run validation button
        - Generate report button
        - Download links for results
    """

def process_validation(
    csv_file: UploadedFile,
    shapefile: UploadedFile,
    params: Dict[str, Any]
) -> pd.DataFrame:
    """
    Process validation for uploaded files.

    Args:
        csv_file: Uploaded CSV file
        shapefile: Uploaded reference shapefile
        params: UI-configured parameters

    Returns:
        DataFrame with validation results
    """

def save_session_parameters(params: Dict[str, Any]) -> None:
    """
    Persist parameters in session state.

    Args:
        params: Parameter dictionary to save
    """

def load_session_parameters() -> Dict[str, Any]:
    """
    Load parameters from session state or defaults.

    Returns:
        Parameter dictionary
    """
```