# Control Test Data

This directory contains test datasets specifically designed for validating the Dataset Control and Validation component (`components/control/`).

## Test Files Overview

### Core Test Data
- **`data.csv`** - Main control validation test dataset with mixed validation scenarios
- **`data.zip`** - Compressed version of the main test data
- **`google_results_to_golan_17_8_25.zip`** - Reference shapefile data for geometric validation

### Scenario-Specific Test Files
- **`test_perfect_scenario.csv`** - All observations pass validation (baseline test)
- **`test_failed_observations.csv`** - All observations fail validation (error handling test)
- **`test_missing_observations.csv`** - Missing data scenarios and edge cases
- **`test_multiple_alternatives.csv`** - Multiple route alternatives per link+timestamp
- **`test_mixed_scenarios.csv`** - Mixed valid/invalid observations
- **`test_edge_cases.csv`** - Boundary conditions and special cases

### Historical Test Data
- **`original_‏‏‏‏data_test_control_s_9054-99_s_653-656.csv`** - Original test subset for specific links
- **`original_test_data_full.csv`** - Full original test dataset

## Test Data Structure

All CSV files follow the standard Google Maps monitoring format:
```
DataID, Name, SegmentID, RouteAlternative, RequestedTime, Timestamp,
DayInWeek, DayType, Duration (seconds), Distance (meters), Speed (km/h),
Url, Polyline
```

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

## Usage

These test files are used by:
- **Control Component Tests**: `tests/control/`
- **Integration Tests**: `tests/integration/`
- **Manual Validation**: Through the control UI at `/control`

## Test Execution

Run control validation tests:
```bash
pytest tests/control/
```

Run with specific test data:
```bash
python -m components.control.page --test-file test_data/control/test_perfect_scenario.csv
```

## Data Sources

- **Geometric Reference**: Based on Golan Heights road network (EPSG 2039)
- **Google Maps Data**: Real polyline encodings from Google Maps API
- **Temporal Coverage**: Multi-day datasets with 15-minute intervals
- **Link Coverage**: Representative sample of network links

## Maintenance

- **Update Frequency**: Test data updated when validation methodology changes
- **Version Control**: All test files tracked in Git (control branch)
- **Quality Assurance**: Each test file validates specific control scenarios

For detailed validation methodology, see: `components/control/methodology.md`