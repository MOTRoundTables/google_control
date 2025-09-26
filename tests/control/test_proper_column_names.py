#!/usr/bin/env python3
"""
Test validation with proper input column names (uppercase).
"""

import pandas as pd
import sys
import os

# Add project directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from components.control.validator import validate_dataframe_batch, ValidationParameters
import geopandas as gpd


def test_proper_column_names():
    """Test validation with proper input column names."""
    print("TESTING PROPER INPUT COLUMN NAMES")
    print("=" * 50)

    # Test data with proper column names matching user's input format
    test_data = pd.DataFrame({
        'DataID': [1001, 1002, 1003, 1004, 1005],
        'Name': ['s_653-655'] * 5,
        'SegmentID': [1185048] * 5,
        'RouteAlternative': [1, 1, 2, 3, 4],
        'RequestedTime': ['13:45:00'] * 5,
        'Timestamp': ['01/07/2025 13:45', '01/07/2025 14:00', '01/07/2025 13:45', '01/07/2025 13:45', '01/07/2025 15:00'],
        'DayInWeek': ['יום ג'] * 5,
        'DayType': ['יום חול'] * 5,
        'Duration (seconds)': [2446, 2500, 2400, 2300, 2600],
        'Distance (meters)': [59428, 60000, 58000, 57000, 61000],
        'Speed (km/h)': [87.5, 86.4, 87.0, 89.0, 84.0],
        'Url': ['https://test.com'] * 5,
        'Polyline': ['_oxwD{_wtEoAlCe@vFq@ha@c@~X_@fOcD~S_@fByAjDaBrBoE|BsKzC_OfE_FhBcFjE}BdEqAfE[vBKjIb@vI|AjXObGs@vCeApB_C|BsGtCaL~B}EvA_CnBeAhBgEzL}IrX_DrLkB~TiBpHgB~CeCxBiElAoEMiA]yKaGcMkHyBe@cCJkChAwEvCeC|@gBTyOj@yZd@mATy@p@]~@OvEIvEa@vFIxF]nD\\lBYfDDxEClAc@hAeAhE[Vo@I_DUwJbDqKtDsL~DuLdEaDrAyEnEkMjK}B~@_Db@_DIgWuCsEkA_EsBsB}AkHuFaViSaWgVoBuAgCgAoJsB}J}C}WmJ}DsAaCg@yBCcMjAiQ~BmGfCyDtCuGfHwJ`LsFjG{ClEmEdN}BvGcAlAmAn@iDn@cCJwHrAgJlCsVxCms@jIa^|DyiCbZogEbf@mkCnZqLzAmNfDmGvAwABcCk@iA_Aw@{Ae@eDLyQYyFk@mAaBsAeBk@_JuAwBm@mDmCsCgCuBg@kAJuAt@}@hB[tCUlJUtHm@lEcCrFmC`F}@j@q@I_@a@GmBdBqC\\sAEcHWmDiAmEaAqAuDwAkKiAqBw@eByAq@y@wAuDgAaM_AcGaCiDmNaLcDy@qC^yAhAmAfCwDxNmAfBoCtB_Cp@oAF_H@cSQmSuAyCLkA^kHbEeHbE{H|EqIxL_NzUeCpGiB`FqAlFb@tKu@lDcBxCoAzCeBxLw@fF_A~BmCvBeCV}KuAyRmCqDIyA`@aGnCyMzFgFb@cFPwB^eEzBcU`OoIpEsJhDwKfDeM~C_VnD{HbDmJ|EeCxBmBnEm@bH[vFy@zRrBlUVl]o@xDk@vA}BrCkMnLcFxHwA~BiA`A{Ed@mJTsD~@mIzCgFvAoBEeAa@{D}DoB_CyFwEuK_IoBwBuAsDsCiLiA}DkAyAaB_AiBSkADiBj@qEpCqDvByChCyCvDsCxBsFtBmAjAi@lA[pCHzLa@vIoC|LcMbYiHfScBfEuBnCwCjBmD|AyDlDaAbByKrVuAnBkFrDkMjGiRvQgApBq@pC]xFc@vEyB|GwBrHuAdJ}AdGcGlIwQbUqJdK}MzLmAnC]|DeBlt@}@l]?pDZjDh@pBlC|FpFhJtDfElGpBf@r@OdAo@b@{LqBs@JCt@pJzCLp@i@VuGsAkCYGt@rErArBhAx@pBxCxCtChApAp@lBbGfA~DtBbGjJdLhJTnSvBbFbA~@h@d@xBcB|DkCpDcAv@QT[t@gF|B'] * 5
    })

    print("Input data with proper column names:")
    print(f"Columns: {list(test_data.columns)}")
    print()
    print("Sample data:")
    print(test_data[['DataID', 'Name', 'RouteAlternative', 'Timestamp', 'Duration (seconds)']].head(3))
    print()

    try:
        shapefile_path = "test_data/google_results_to_golan_17_8_25/google_results_to_golan_17_8_25.shp"
        shapefile_gdf = gpd.read_file(shapefile_path)
        print(f"Loaded shapefile: {len(shapefile_gdf)} features")

        # Test with Hausdorff + Length configuration
        params = ValidationParameters(
            use_hausdorff=True,
            use_length_check=True,
            use_coverage_check=False
        )

        print("Running validation...")
        result = validate_dataframe_batch(test_data, shapefile_gdf, params)
        print("Validation completed!")
        print()

        print("Output column names:")
        print(f"Columns: {list(result.columns)}")
        print()

        print("Validation results:")
        print(result[['DataID', 'Name', 'RouteAlternative', 'Timestamp', 'Duration (seconds)', 'is_valid', 'valid_code']].head())
        print()

        # Check field preservation
        input_cols = set(test_data.columns)
        output_cols = set(result.columns)
        added_cols = output_cols - input_cols
        missing_cols = input_cols - output_cols

        print("Field preservation check:")
        print(f"  Input fields: {len(input_cols)}")
        print(f"  Output fields: {len(output_cols)}")
        print(f"  Added fields: {sorted(added_cols)}")
        print(f"  Missing fields: {sorted(missing_cols) if missing_cols else 'None'}")

        if not missing_cols:
            print("  SUCCESS: All input fields preserved with exact naming!")
        else:
            print("  ERROR: Some input fields were lost!")

        return len(missing_cols) == 0

    except Exception as e:
        print(f"Error in test: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_proper_column_names()
    if success:
        print("\nSUCCESS: Column name preservation working correctly!")
    else:
        print("\nERROR: Column name preservation failed!")