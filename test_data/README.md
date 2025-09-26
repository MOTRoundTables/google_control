# Test Data Documentation

This directory contains sample data for testing and validating the Google Maps Link Monitoring System.

## Directory Structure

```
test_data/
├── control/                        # Dataset Control & Validation test data
│   ├── original_test_data_full.csv # Small validation dataset (985 rows)
│   └── data.csv                    # Large test dataset (714,385 rows)
└── google_results_to_golan_17_8_25/
    ├── google_results_to_golan_17_8_25.shp  # Reference shapefile
    ├── google_results_to_golan_17_8_25.shx  # Shapefile index
    ├── google_results_to_golan_17_8_25.dbf  # Shapefile attributes
    └── google_results_to_golan_17_8_25.prj  # Projection information
```

## Dataset Descriptions

### Control Validation Data

#### `original_test_data_full.csv`
- **Size**: 985 rows
- **Purpose**: Small dataset for quick validation testing
- **Coverage**: 3 links with multiple route alternatives
- **Time Period**: 2025-06-29 to 2025-07-01 (3 days)
- **Validation Results**: 574 exact matches (Hausdorff = 0), 411 failed (>5m threshold)

#### `data.csv`
- **Size**: 714,385 rows
- **Purpose**: Large dataset for performance and scalability testing
- **Coverage**: 2,432 links total, with observations for subset of links
- **Time Period**: Multi-day sample covering various traffic patterns
- **Validation Results**: 698,223 passed Hausdorff (≤5m), 16,162 failed

### Reference Shapefile

#### `google_results_to_golan_17_8_25.*`
- **Type**: ESRI Shapefile package
- **Links**: 2,432 road links with From/To node IDs
- **Geometry**: LineString features representing road segments
- **CRS**: Automatically reprojected to EPSG:2039 during processing
- **Join Rule**: Links matched as `s_{From}-{To}`

## Data Characteristics

### Validation Patterns
- **High-Quality Routes**: Most Google routes match reference geometry within 5m
- **Route Alternatives**: Multiple route options for same origin-destination pairs
- **Temporal Coverage**: Comprehensive timestamp coverage for completeness analysis
- **Geometric Accuracy**: Reference geometry derived from consistent source

### Known Test Scenarios
1. **Exact Matches**: Routes with Hausdorff distance = 0.000m
2. **Near Matches**: Routes within 1-5m of reference geometry
3. **Failed Validation**: Routes exceeding 5m Hausdorff threshold
4. **Missing Observations**: Gaps in temporal coverage for completeness testing
5. **Multiple Alternatives**: Links with 2-3 route alternatives per timestamp

## Usage Examples

### Dataset Control Testing
```bash
# Quick validation test (985 rows)
# Upload: test_data/control/original_test_data_full.csv
# Shapefile: test_data/google_results_to_golan_17_8_25.zip

# Large-scale validation (714k rows)
# Upload: test_data/control/data.csv
# Shapefile: test_data/google_results_to_golan_17_8_25.zip
```

### Expected Results
- **Small Dataset**: ~571 valid, ~414 failed validations
- **Large Dataset**: ~698k valid, ~16k failed validations
- **Missing Observations**: Minimal gaps (system correctly identifies temporal coverage)
- **No-Data Links**: Links in shapefile but absent from CSV data

## Data Quality Notes

### Encoding
- CSV files use various encodings (UTF-8, cp1255 for Hebrew)
- System auto-detects and handles encoding properly
- Hebrew day names and text preserved correctly

### Coordinate Systems
- Input geometries in WGS84 (EPSG:4326)
- Processing uses EPSG:2039 (Israel TM Grid) for metric calculations
- Automatic CRS conversion during validation

### Performance Benchmarks
- **Small Dataset**: < 30 seconds validation time
- **Large Dataset**: 10-15 minutes with optimizations (previously hours)
- **Memory Usage**: Efficient chunked processing for large files

## Creating Custom Test Data

If you need to create your own test data:

1. **CSV Format**: Include Name, Timestamp, Polyline columns at minimum
2. **Shapefile**: Ensure From/To fields create valid `s_From-To` link IDs
3. **Geometry**: Use consistent CRS (system handles reprojection)
4. **Coverage**: Include temporal gaps for completeness analysis testing

## Troubleshooting

### Common Issues
1. **File Not Found**: Ensure test_data directory exists after cloning
2. **Encoding Errors**: System should auto-detect; check logs if issues persist
3. **Memory Issues**: Use smaller datasets or enable chunked processing
4. **Performance**: Large dataset processing requires adequate RAM (8GB+)

### Validation
- Check that link IDs in CSV match shapefile naming pattern
- Verify timestamp formats are parseable
- Ensure polylines are valid Google Maps encoded strings
- Confirm shapefile has proper projection information