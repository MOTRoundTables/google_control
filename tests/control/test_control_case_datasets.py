import pandas as pd
import geopandas as gpd
import pytest

from components.control.validator import validate_dataframe_batch, ValidationParameters

CASES = {
    "case_all_valid": {
        "path": "test_data/control/cases/case_all_valid.csv",
        "expected_codes": [2, 2, 2],
        "expected_valid": [True, True, True],
    },
    "case_multi_alt_mixed": {
        "path": "test_data/control/cases/case_multi_alt_mixed.csv",
        "expected_codes": [3, 3],
        "expected_valid": [True, False],
    },
    "case_missing_timestamp": {
        "path": "test_data/control/cases/case_missing_timestamp.csv",
        "expected_codes": [2, 2, 90],
        "expected_valid": [True, True, False],
    },
    "case_no_route_alternative": {
        "path": "test_data/control/cases/case_no_route_alternative.csv",
        "expected_codes": [1, 1, 1],
        "expected_valid": [True, True, True],
    },
    "case_unknown_link": {
        "path": "test_data/control/cases/case_unknown_link.csv",
        "expected_codes": [92],
        "expected_valid": [False],
    },
    "case_bad_polyline": {
        "path": "test_data/control/cases/case_bad_polyline.csv",
        "expected_codes": [93],
        "expected_valid": [False],
    },
}

SHAPEFILE_PATH = "test_data/google_results_to_golan_17_8_25/google_results_to_golan_17_8_25.shp"

@pytest.fixture(scope="module")
def reference_shapefile():
    return gpd.read_file(SHAPEFILE_PATH)

@pytest.mark.parametrize("case_name,case_info", CASES.items())
def test_validation_cases(case_name, case_info, reference_shapefile):
    df = pd.read_csv(case_info["path"])
    params = ValidationParameters()
    result = validate_dataframe_batch(df, reference_shapefile, params)

    assert list(result["valid_code"]) == case_info["expected_codes"], (
        f"valid_code mismatch for {case_name}"
    )
    assert list(result["is_valid"]) == case_info["expected_valid"], (
        f"is_valid mismatch for {case_name}"
    )
