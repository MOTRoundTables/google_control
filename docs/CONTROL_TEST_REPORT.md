# Control Validation Regression Cases

This suite introduces focused CSV fixtures derived from the large control dataset (`test_data/control/data.csv`) so we can quickly vet the validator without uploading the 240 MB source file. All cases reuse the reference shapefile in `test_data/google_results_to_golan_17_8_25.zip`.

## Scenario Matrix

| Case | CSV Path | Purpose | Expected Result | Key `valid_code` Values | Notes |
| --- | --- | --- | --- | --- | --- |
| All Valid | `test_data/control/cases/case_all_valid.csv` | Baseline happy-path rows that should all pass | 3/3 rows valid | `2` | Data copied from production sample |
| Mixed Alternatives | `test_data/control/cases/case_multi_alt_mixed.csv` | Same link/timestamp with one failing alternative | 1/2 rows valid | `3` | Confirms grouping marks timestamp as successful because one alternative is valid |
| Missing Timestamp | `test_data/control/cases/case_missing_timestamp.csv` | Records missing timestamp metadata | 2/3 rows valid | `90` on malformed row | Also exercises fallback handling for missing `RequestedTime` |
| No Route Alternative Column | `test_data/control/cases/case_no_route_alternative.csv` | Dataset without `RouteAlternative` column | 3/3 rows valid | `1` | Triggers geometry-only validation mode |
| Unknown Link | `test_data/control/cases/case_unknown_link.csv` | Link absent from shapefile | 0/1 rows valid | `92` | Ensures missing reference geometry is surfaced correctly |
| Bad Polyline | `test_data/control/cases/case_bad_polyline.csv` | Corrupted polyline encoding | 0/1 rows valid | `93` | Confirms polyline decode failure path |

Validation snapshots were generated with the default `ValidationParameters` (`hausdorff_threshold_m=5`).

## Automated Test

A focused pytest module (`tests/control/test_control_case_datasets.py`) executes each case against the real validator and checks the expected `is_valid` and `valid_code` sequences. To run only this suite without loading third-party pytest plugins, execute:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
pytest tests/control/test_control_case_datasets.py -q
```

The test currently reports these aggregates:

| Case | Rows | Valid | Invalid | `valid_code` counts |
| --- | --- | --- | --- | --- |
| case_all_valid | 3 | 3 | 0 | `{2: 3}` |
| case_multi_alt_mixed | 2 | 1 | 1 | `{3: 2}` |
| case_missing_timestamp | 3 | 2 | 1 | `{2: 2, 90: 1}` |
| case_no_route_alternative | 3 | 3 | 0 | `{1: 3}` |
| case_unknown_link | 1 | 0 | 1 | `{92: 1}` |
| case_bad_polyline | 1 | 0 | 1 | `{93: 1}` |

## How to Use the Fixtures

1. Pick a CSV from `test_data/control/cases/` and run it through the control validation UI (or call `save_validation_results`).
2. Compare the Streamlit metrics and generated artifacts with the expectations above. The pytest module offers a quick automated check for regression testing.
3. When iterating on validation logic, extend this catalogue with new edge cases to keep the coverage representative.

These fixtures give us a fast, repeatable safety net while preserving the behavior of the full 240 MB control run.
