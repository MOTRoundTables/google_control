# Test Data - Maps and Aggregation

This directory contains reference data and test files for the Maps visualization and Aggregation pipeline components.

## Directory Structure

```
test_data/aggregation/
├── google_results_to_golan_17_8_25/    # Reference shapefile package for maps
│   ├── google_results_to_golan_17_8_25.shp  # Reference shapefile geometry
│   ├── google_results_to_golan_17_8_25.shx  # Shapefile spatial index
│   ├── google_results_to_golan_17_8_25.dbf  # Shapefile attribute data
│   ├── google_results_to_golan_17_8_25.prj  # Coordinate system information
│   └── google_results_to_golan_17_8_25.qmd  # Metadata file
├── data_test_small.csv              # Small aggregation test dataset
└── README.md                        # This documentation file
```

## Dataset Descriptions

### Aggregation Test Data

#### `data_test_small.csv`
- **Size**: Small sample dataset
- **Purpose**: Testing aggregation pipeline functionality
- **Coverage**: Representative traffic data for aggregation testing
- **Time Period**: Sample time range for testing temporal aggregation
- **Usage**: Quick testing of aggregation algorithms and output generation

### Maps Reference Shapefile

#### `google_results_to_golan_17_8_25.*`
- **Type**: ESRI Shapefile package
- **Purpose**: Reference geometry for map visualization and spatial analysis
- **Links**: 2,432 road links with From/To node IDs
- **Geometry**: LineString features representing road network segments
- **CRS**: Automatically reprojected to EPSG:2039 during map processing
- **Join Rule**: Links matched as `s_{From}-{To}` for aggregation data overlay

## Data Characteristics

### Map Visualization Features
- **Network Coverage**: Complete road network for spatial visualization
- **Link Attributes**: From/To node information for data joining
- **Geometric Accuracy**: High-quality reference geometry for traffic overlay
- **CRS Compatibility**: Proper projection handling for Israeli grid system

### Aggregation Pipeline Features
- **Temporal Data**: Sample traffic observations for hourly/weekly aggregation
- **Link Coverage**: Representative set of links for testing aggregation algorithms
- **Data Quality**: Clean test data for reliable aggregation testing
- **Output Generation**: Suitable for testing hourly_agg.csv and weekly_profile.csv outputs

## Usage Examples

### Aggregation Pipeline Testing
```bash
# Test aggregation pipeline functionality
# Upload: test_data/aggregation/data_test_small.csv
# Output: ./output/aggregation/[subfolder]/
```

### Maps Visualization Testing
```bash
# Test map visualization with reference shapefile
# Shapefile: test_data/aggregation/google_results_to_golan_17_8_25/
# Auto-detect: Maps component will automatically find this reference data
```

### Expected Outputs
- **Aggregation**: hourly_agg.csv and weekly_hourly_profile.csv files
- **Maps Integration**: Automatic loading of reference shapefile for visualization
- **File Organization**: Clean output structure in timestamped folders

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