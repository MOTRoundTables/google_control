# Quickstart Guide: Dataset Control and Reporting

## Overview
Validate Google Maps polyline data against reference shapefiles to ensure data quality and identify geometry mismatches.

## Quick Setup

### 1. Install Dependencies
```bash
pip install polyline
```

### 2. Test Data Locations
```
# Default test dataset
E:\google_agg\test_data\control\data_test_control.csv

# Reference shapefile
E:\google_agg\test_data\google_results_to_golan_17_8_25\google_results_to_golan_17_8_25.shp
```

## Basic Usage

### Via Streamlit UI
```bash
streamlit run app.py
# Navigate to "Dataset Control" page
```

### Via Python Script
```python
from control_validator import validate_row, ValidationParameters
from control_report import generate_link_report
import pandas as pd
import geopandas as gpd

# Load data
csv_df = pd.read_csv("test_data/control/data_test_control.csv")
shapefile_gdf = gpd.read_file("test_data/google_results_to_golan_17_8_25.shp")

# Configure parameters
params = ValidationParameters(
    hausdorff_threshold_m=5.0,
    length_check_mode="ratio",
    coverage_min=0.85
)

# Validate each row
for idx, row in csv_df.iterrows():
    is_valid, valid_code = validate_row(row, shapefile_gdf, params)
    csv_df.loc[idx, 'is_valid'] = is_valid
    csv_df.loc[idx, 'valid_code'] = valid_code

# Generate report
report_gdf = generate_link_report(csv_df, shapefile_gdf)
report_gdf.to_file("output_report.shp")
```

## Validation Scenarios

### Scenario 1: Default Validation
**Given**: CSV with polylines and reference shapefile
**When**: Run with default parameters
**Then**: Each row marked with is_valid and valid_code

```python
# Expected output
print(csv_df[['name', 'is_valid', 'valid_code']].head())
# name         is_valid  valid_code
# s_653-655    True      1 (within tolerance)
# s_653-656    False     92 (not in shapefile)
```

### Scenario 2: RouteAlternative Handling
**Given**: Observations with multiple route alternatives
**When**: At least one alternative matches
**Then**: Observation marked as valid

```python
# Filter multi-alternative observations
multi_alt = csv_df[csv_df['route_alternative'] > 1]
print(f"Multi-alternative validity: {multi_alt['is_valid'].mean():.2%}")
```

### Scenario 3: Parameter Sensitivity
**Given**: Adjustable validation thresholds
**When**: Change Hausdorff threshold from 5m to 10m
**Then**: More observations become valid

```python
# Strict validation
strict_params = ValidationParameters(hausdorff_threshold_m=2.0)
# Relaxed validation
relaxed_params = ValidationParameters(hausdorff_threshold_m=10.0)
```

### Scenario 4: Date Filtering
**Given**: Large dataset spanning multiple dates
**When**: Filter to specific date range
**Then**: Report only includes filtered period

```python
date_filter = {
    'start_date': '2025-07-01',
    'end_date': '2025-07-31'
}
report_gdf = generate_link_report(csv_df, shapefile_gdf, date_filter)
```

## Understanding Valid Codes

### Quick Reference
```
Data Issues (90-93):
  90 = Required fields missing
  91 = Cannot parse link name
  92 = Link not in shapefile
  93 = Polyline decode failed

Route Alternatives (20-24):
  20 = No alternatives, fail
  21 = One alternative, match
  22 = One alternative, fail
  23 = Multiple, at least one matches
  24 = Multiple, none match

Geometry Match (0-4):
  0 = Exact match
  1 = Within tolerance
  2 = Distance too large
  3 = Length mismatch
  4 = Insufficient coverage
```

## Report Interpretation

### Result Codes in Output Shapefile
```
0  = All observations valid (100%)
1  = Single route, partially valid
2  = Single route, all invalid (0%)
30 = Multiple routes, all valid (100%)
31 = Multiple routes, partially valid
32 = Multiple routes, all invalid (0%)
41 = Link not recorded in dataset
42 = Link partially recorded
```

### Example Report Analysis
```python
# Load report shapefile
report = gpd.read_file("output_report.shp")

# Summary statistics
print(f"Total links: {len(report)}")
print(f"Links with 100% validity: {(report['result_code'] == 0).sum()}")
print(f"Links not recorded: {(report['result_code'] == 41).sum()}")
print(f"Average validity: {report['num'].mean():.1f}%")
```

## Performance Tips

### Large Datasets
```python
# Process in chunks
chunk_size = 10000
for chunk in pd.read_csv(csv_path, chunksize=chunk_size):
    # Process chunk
    pass
```

### Memory Optimization
```python
# Use categorical for repeated strings
csv_df['name'] = csv_df['name'].astype('category')
csv_df['route_alternative'] = csv_df['route_alternative'].astype('int8')
```

### Parallel Processing (Advanced)
```python
from multiprocessing import Pool

def validate_chunk(chunk_data):
    chunk, gdf, params = chunk_data
    # Validation logic
    return validated_chunk

with Pool() as pool:
    results = pool.map(validate_chunk, chunk_iterator)
```

## Troubleshooting

### Common Issues

1. **Polyline decode errors (code 93)**
   - Check encoding format (Google uses precision 5)
   - Verify polyline field is not truncated

2. **Name parsing failures (code 91)**
   - Expected format: s_from-to or s_from_to
   - Check for special characters

3. **CRS mismatch**
   - System auto-reprojects to EPSG:2039
   - Verify shapefile has defined CRS

4. **Memory issues**
   - Reduce chunk size
   - Process date ranges separately

## Quick Test

Run this to verify installation:
```python
# Test imports
import polyline
import control_validator
import control_report

# Test polyline decoding
test_poly = "_p~iF~ps|U_ulLnnqC_mqNvxq`@"
decoded = polyline.decode(test_poly)
print(f"Decoded {len(decoded)} points")

# Test validation
print("Setup complete!")
```

## Next Steps

1. Review full specification in [spec.md](spec.md)
2. Check validation parameters for your use case
3. Run on sample data first
4. Monitor valid_code distribution to identify issues
5. Adjust thresholds based on data characteristics