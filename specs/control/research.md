# Research Findings: Dataset Control and Reporting

## 1. Polyline Decoding Library

**Decision**: Use the `polyline` Python library
**Rationale**:
- Industry standard for Google Maps encoded polyline format
- Well-maintained, pure Python implementation
- Handles precision parameter (default 5, configurable)
- Simple API: `polyline.decode(encoded_string, precision)`

**Alternatives considered**:
- Manual implementation: Too error-prone for edge cases
- googlemaps library: Heavier dependency for simple decoding
- flexpolyline: For HERE maps format, not Google

**Implementation notes**:
```python
import polyline
# Decode with precision 5 (Google default)
points = polyline.decode(encoded_polyline, 5)
# Returns list of (lat, lon) tuples
```

## 2. Hausdorff Distance Computation

**Decision**: Use `shapely.geometry.hausdorff_distance()`
**Rationale**:
- Built into shapely (already a dependency)
- Efficient C implementation via GEOS
- Handles LineString geometries directly
- Direction-agnostic by design

**Alternatives considered**:
- scipy.spatial.distance: Requires point arrays, less efficient
- Custom implementation: Reinventing the wheel
- PostGIS: Would require database dependency

**Implementation notes**:
```python
from shapely.geometry import LineString
distance = line1.hausdorff_distance(line2)
# Returns maximum distance between closest points
```

## 3. Coverage Calculation with Densification

**Decision**: Use shapely's `interpolate()` and `project()` methods
**Rationale**:
- Densification via interpolate at regular intervals
- Project to find nearest points on reference
- Calculate overlap length along reference line

**Alternatives considered**:
- Buffer-based intersection: Less accurate for linear features
- Vertex-only matching: Misses continuous coverage
- Grid-based approach: Too complex for line features

**Implementation notes**:
```python
# Densify both geometries to same spacing
def densify_line(line, spacing=1.0):
    distances = np.arange(0, line.length, spacing)
    points = [line.interpolate(d) for d in distances]
    return LineString(points)

# Calculate coverage with configurable spacing
def calculate_coverage(polyline_geom, reference_geom, spacing=1.0):
    densified_poly = densify_line(polyline_geom, spacing)
    densified_ref = densify_line(reference_geom, spacing)

    # Find overlapping segments
    overlap_length = 0
    for point in densified_poly.coords:
        projected = reference_geom.project(Point(point))
        if projected <= reference_geom.length:
            # Point projects onto reference
            overlap_length += spacing

    return overlap_length / reference_geom.length
```

**Parameter exposure**: Add coverage_spacing_m to UI and configuration as it directly affects coverage calculation precision vs performance.

## 4. Shapefile Field Addition

**Decision**: Use geopandas with field type mapping
**Rationale**:
- Geopandas handles schema preservation
- Automatic field type inference
- Maintains CRS and geometry integrity

**Alternatives considered**:
- Fiona direct: Lower level, more complex
- GDAL/OGR: Overkill for simple field addition
- PyShp: Doesn't handle CRS well

**Implementation notes**:
```python
# Add fields to GeoDataFrame
gdf['result_code'] = result_codes
gdf['result_label'] = result_labels
gdf['num'] = percentages

# Write with explicit schema
gdf.to_file(output_path, driver='ESRI Shapefile')
```

## 5. Efficient Processing Strategy

**Decision**: Process in chunks with spatial indexing
**Rationale**:
- Chunk processing for memory efficiency (proven in existing code)
- Build spatial index once for shapefile
- Cache decoded polylines to avoid re-decoding

**Alternatives considered**:
- Full in-memory: Won't scale to millions of rows
- Row-by-row: Too slow without batching
- Parallel processing: Adds complexity, marginal gains

**Implementation notes**:
```python
# Build spatial index once
shapefile_sindex = gdf.sindex

# Process CSV in chunks
for chunk in pd.read_csv(csv_path, chunksize=10000):
    # Decode polylines once per chunk
    chunk['decoded_geom'] = chunk['Polyline'].apply(decode_polyline)

    # Validate using vectorized operations where possible
    chunk[['is_valid', 'valid_code']] = chunk.apply(
        lambda row: validate_row(row, gdf, params),
        axis=1,
        result_type='expand'
    )
```

## 6. Name Field Parsing

**Decision**: Flexible regex pattern with fallbacks
**Rationale**:
- Handle variations: s_123_456, s_123-456, S_123_456
- Clear error code (91) for parse failures
- Extract from_id and to_id as strings to preserve leading zeros

**Implementation notes**:
```python
import re

def parse_link_name(name):
    # Pattern: optional s/S, underscore/dash, numbers, separator, numbers
    pattern = r'^[sS]?[_-]?(\d+)[_-](\d+)$'
    match = re.match(pattern, str(name).strip())

    if match:
        from_id, to_id = match.groups()
        return from_id, to_id
    return None, None
```

## 7. Performance Optimizations

**Decision**: Pre-compute and cache expensive operations
**Rationale**:
- Decode polylines once per observation
- Build shapefile spatial index once
- Cache Hausdorff distances for same geometries
- Vectorize where possible

**Key optimizations**:
1. Spatial index for join operations
2. Chunk-level polyline decoding
3. NumPy arrays for numeric operations
4. Early termination in validation hierarchy
5. Deduplication before aggregation

## Summary of Dependencies

**Required new packages**:
```python
polyline  # For Google Maps polyline decoding
```

**Existing packages leveraged**:
- pandas: Data processing (existing)
- geopandas: Spatial operations (existing)
- shapely: Geometry calculations (existing)
- pyproj: CRS transformations (existing)
- numpy: Numeric operations (existing)

All research items resolved - ready for Phase 1 design.