# Debug Scripts for Control Component

This directory contains debug scripts used during development of the transparent metrics system.

## Scripts

### Hausdorff Distance Debugging
- `debug_actual_hausdorff.py` - Calculate actual Hausdorff distances for specific links
- `debug_hausdorff_distances.py` - Test Hausdorff distance calculations with detailed output
- `debug_single_validation.py` - Debug single validation operations

### Link Analysis
- `debug_s653_655_failure.py` - Investigate why s_653-655 shows 0% success rate
- `debug_report_joining.py` - Debug link report generation and joining logic

## Purpose

These scripts were created to:
1. Debug the critical Hausdorff distance calculation bug (degrees vs meters)
2. Investigate validation failures and success rates
3. Test the improved timestamp-based aggregation logic
4. Verify geometric validation is working correctly

## Usage

These scripts use the test data from `test_data/control/` and require the control component modules to be importable.

Most scripts can be run with:
```bash
cd E:\google_agg
python tests/control/debug/script_name.py
```

## Historical Context

These scripts were instrumental in:
- Fixing the Hausdorff distance bug that returned distances in degrees instead of meters
- Implementing the new transparent metrics system
- Replacing confusing result codes with clear statistics