# Test Data - Control & Validation

This directory contains test datasets specifically designed for validating the Dataset Control and Validation component (`components/control/`). These test files validate Google Maps polyline data against reference shapefiles using geometric similarity analysis.

## Test Files Overview

### Core Test Data
- **`data.csv`** - Main control validation test dataset with mixed validation scenarios (700k+ records)
- **`data.zip`** - Compressed version of the main test data
- **`original_test_data_full.csv`** - Complete original test dataset for validation testing
- **Reference Shapefile**: Located in `test_data/aggregation/google_results_to_golan_17_8_25/` (shared with maps component)

### Test Case Files
Located in the `cases/` subdirectory, organized by validation scenario:
- **`test_perfect_scenario.csv`** - All observations pass validation (baseline test)
- **`test_failed_observations.csv`** - All observations fail validation (error handling test)
- **`test_missing_observations.csv`** - Missing data scenarios and Code 94/95 analysis
- **`test_multiple_alternatives.csv`** - Multiple route alternatives per link+timestamp
- **`test_mixed_scenarios.csv`** - Mixed valid/invalid observations for comprehensive testing
- **`test_edge_cases.csv`** - Boundary conditions and special geometric cases

### Historical Test Data
- **`original_‏‏‏‏data_test_control_s_9054-99_s_653-656.csv`** - Original test subset for specific links
- **`original_test_data_full.csv`** - Full original test dataset

## Test Data Structure

### Control-Specific CSV Format
All CSV files include the minimum required columns for control validation:
```
Name, Polyline, Timestamp, RouteAlternative (optional)
```

### Full Format (for comprehensive testing):
```
DataID, Name, SegmentID, RouteAlternative, RequestedTime, Timestamp,
DayInWeek, DayType, Duration (seconds), Distance (meters), Speed (km/h),
Url, Polyline
```

### Expected Outputs
Control validation generates timestamped output folders in `./output/control/DD_MM_YY_HH_MM/`:
- `validated_data.csv` - All validation results with codes and metrics
- `failed_observations.csv` - Combined failure analysis
- `missing_observations.csv` - Code 94/95 temporal gap analysis
- `best_valid_observations.csv` - Best route for each link
- `link_report.csv` - Link-level summary statistics
- `link_report_shapefile.zip` - Complete spatial package for QGIS
- `failed_observations_shapefile.zip` - Failed observations spatial visualization

## Validation Test Coverage

### Geometric Validation Tests
- **Hausdorff Distance**: Tests polyline matching against reference shapefiles
- **Length Similarity**: Validates route length consistency
- **Coverage Analysis**: Tests spatial coverage along reference routes

### Data Quality Tests
- **Missing Fields**: Tests handling of incomplete records
- **Invalid Polylines**: Tests malformed Google Maps polyline encoding
- **Timestamp Validation**: Tests temporal data consistency
- **Link ID Mapping**: Tests s_From-To join rule validation

### Validation Code Coverage
Tests all validation codes from the control methodology:
- **0-4**: Geometry-only validation scenarios
- **20-24**: Single route alternative scenarios
- **30-34**: Multiple route alternatives scenarios
- **90-93**: Data availability error scenarios

## Usage Examples

### Control Component Testing
Access the control validation interface through the main application:
```bash
streamlit run app.py
# Navigate to "Dataset Control & Validation" page
# Upload test CSV file and reference shapefile
```

### Automated Testing
These test files are used by:
- **Control Component Tests**: `tests/control/`
- **Integration Tests**: `tests/integration/`
- **Validation Methodology Testing**: `tests/control/test_control_validator.py`

## Test Execution

### Automated Test Suite
```bash
# Run all control validation tests
pytest tests/control/

# Run specific control test files
pytest tests/control/test_control_validator.py
pytest tests/control/test_control_report.py

# Run with verbose output
pytest tests/control/ -v
```

### Manual Testing
```bash
# Launch the application and test manually
streamlit run app.py
# Use test files from this directory through the web interface
```

## Data Characteristics

### Spatial Coverage
- **Geographic Area**: Golan Heights road network (Israel)
- **Coordinate System**: EPSG:2039 (Israel TM Grid)
- **Network Size**: Representative sample of ~100 road links
- **Link Types**: Various road classifications and geometries

### Data Quality
- **Google Maps Data**: Real polyline encodings from Google Maps API
- **Temporal Coverage**: Multi-day datasets with 15-minute observation intervals
- **Route Alternatives**: Multiple routing options per link for comprehensive testing
- **Validation Coverage**: Tests all geometric validation scenarios (codes 0-4, 20-24, 30-34, 90-93)

### Expected Performance
- **Small Test Files**: < 5 seconds validation time
- **Main Dataset (data.csv)**: 30-60 seconds validation time
- **Memory Usage**: < 500MB for largest test files
- **Output Size**: ~5-10MB per validation run

## Quality Assurance

- **Validation Methodology**: See `components/control/methodology.md` for technical details
- **Test Coverage**: Each test file validates specific geometric and data quality scenarios
- **Version Control**: All test files tracked in Git repository
- **Update Protocol**: Test data refreshed when validation methodology changes

## Troubleshooting

### Common Test Issues
1. **Reference Shapefile**: Ensure shapefile is available in `test_data/aggregation/` directory
2. **Hebrew Encoding**: System auto-detects cp1255 encoding for Hebrew text
3. **Memory Issues**: Use smaller test files for development, main dataset for integration testing
4. **Validation Codes**: Check `methodology.md` for interpretation of validation result codes