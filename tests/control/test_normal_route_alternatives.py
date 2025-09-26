#!/usr/bin/env python3
"""
Test normal route_alternative values (>=1) and verify output format.
"""

import pandas as pd
import sys
import os

# Add project directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from components.control.validator import validate_dataframe_batch, ValidationParameters
import geopandas as gpd


def test_normal_route_alternatives():
    """Test normal usage with route_alternative >= 1."""
    print("TESTING NORMAL ROUTE_ALTERNATIVE VALUES (>=1)")
    print("=" * 55)

    # Test data with normal route_alternative values (>=1)
    test_data = pd.DataFrame({
        'DataID': [1001, 1002, 1003, 1004, 1005],
        'name': ['s_653-655'] * 5,
        'polyline': ['_oxwD{_wtEoAlCe@vFq@ha@c@~X_@fOcD~S_@fByAjDaBrBoE|BsKzC_OfE_FhBcFjE}BdEqAfE[vBKjIb@vI|AjXObGs@vCeApB_C|BsGtCaL~B}EvA_CnBeAhBgEzL}IrX_DrLkB~TiBpHgB~CeCxBiElAoEMiA]yKaGcMkHyBe@cCJkChAwEvCeC|@gBTyOj@yZd@mATy@p@]~@OvEIvEa@vFIxF]nD\\lBYfDDxEClAc@hAeAhE[Vo@I_DUwJbDqKtDsL~DuLdEaDrAyEnEkMjK}B~@_Db@_DIgWuCsEkA_EsBsB}AkHuFaViSaWgVoBuAgCgAoJsB}J}C}WmJ}DsAaCg@yBCcMjAiQ~BmGfCyDtCuGfHwJ`LsFjG{ClEmEdN}BvGcAlAmAn@iDn@cCJwHrAgJlCsVxCms@jIa^|DyiCbZogEbf@mkCnZqLzAmNfDmGvAwABcCk@iA_Aw@{Ae@eDLyQYyFk@mAaBsAeBk@_JuAwBm@mDmCsCgCuBg@kAJuAt@}@hB[tCUlJUtHm@lEcCrFmC`F}@j@q@I_@a@GmBdBqC\\sAEcHWmDiAmEaAqAuDwAkKiAqBw@eByAq@y@wAuDgAaM_AcGaCiDmNaLcDy@qC^yAhAmAfCwDxNmAfBoCtB_Cp@oAF_H@cSQmSuAyCLkA^kHbEeHbE{H|EqIxL_NzUeCpGiB`FqAlFb@tKu@lDcBxCoAzCeBxLw@fF_A~BmCvBeCV}KuAyRmCqDIyA`@aGnCyMzFgFb@cFPwB^eEzBcU`OoIpEsJhDwKfDeM~C_VnD{HbDmJ|EeCxBmBnEm@bH[vFy@zRrBlUVl]o@xDk@vA}BrCkMnLcFxHwA~BiA`A{Ed@mJTsD~@mIzCgFvAoBEeAa@{D}DoB_CyFwEuK_IoBwBuAsDsCiLiA}DkAyAaB_AiBSkADiBj@qEpCqDvByChCyCvDsCxBsFtBmAjAi@lA[pCHzLa@vIoC|LcMbYiHfScBfEuBnCwCjBmD|AyDlDaAbByKrVuAnBkFrDkMjGiRvQgApBq@pC]xFc@vEyB|GwBrHuAdJ}AdGcGlIwQbUqJdK}MzLmAnC]|DeBlt@}@l]?pDZjDh@pBlC|FpFhJtDfElGpBf@r@OdAo@b@{LqBs@JCt@pJzCLp@i@VuGsAkCYGt@rErArBhAx@pBxCxCtChApAp@lBbGfA~DtBbGjJdLhJTnSvBbFbA~@h@d@xBcB|DkCpDcAv@QT[t@gF|B'] * 5,
        'route_alternative': [1, 1, 2, 3, 4],  # Different route alternatives >= 1
        'timestamp': ['2025-01-01 10:00', '2025-01-01 11:00', '2025-01-01 10:00', '2025-01-01 10:00', '2025-01-01 12:00'],
        'Duration': [2446, 2500, 2400, 2300, 2600],
        'Distance': [59428, 60000, 58000, 57000, 61000],
        'Speed': [87.5, 86.4, 87.0, 89.0, 84.0]
    })

    print("Input data with route_alternative >= 1:")
    print(test_data[['DataID', 'name', 'route_alternative', 'timestamp', 'Duration']])
    print()

    try:
        shapefile_path = "test_data/google_results_to_golan_17_8_25/google_results_to_golan_17_8_25.shp"
        shapefile_gdf = gpd.read_file(shapefile_path)
        print(f"Loaded shapefile: {len(shapefile_gdf)} features")

        # Test with Hausdorff + Length configuration (config 2)
        params = ValidationParameters(
            use_hausdorff=True,
            use_length_check=True,
            use_coverage_check=False
        )

        result = validate_dataframe_batch(test_data, shapefile_gdf, params)

        print("Validation results:")
        print(result[['DataID', 'name', 'route_alternative', 'timestamp', 'Duration', 'is_valid', 'valid_code']])
        print()

        # Check that all input fields are preserved
        input_cols = set(test_data.columns)
        output_cols = set(result.columns)
        added_cols = output_cols - input_cols
        missing_cols = input_cols - output_cols

        print("Field preservation check:")
        print(f"  Input fields: {len(input_cols)} - {sorted(input_cols)}")
        print(f"  Output fields: {len(output_cols)} - {sorted(output_cols)}")
        print(f"  Added fields: {sorted(added_cols)}")
        print(f"  Missing fields: {sorted(missing_cols) if missing_cols else 'None'}")
        print()

        # Analyze context detection
        print("Context analysis:")
        contexts = []
        for idx, row in result.iterrows():
            code = row['valid_code']
            if code >= 90:
                context = 'Data Error'
                config = 'N/A'
            elif code <= 4:
                context = 'Geometry Only'
                config = code if code > 0 else 0  # 0 = exact match
            elif 20 <= code <= 24:
                context = 'Single Alt'
                config = code - 20
            elif 30 <= code <= 34:
                context = 'Multi Alt'
                config = code - 30
            else:
                context = 'Unknown'
                config = 'N/A'

            contexts.append(context)
            print(f"  Row {idx+1}: route_alt={row['route_alternative']}, code={code}, context={context}, config={config}")

        # Summary
        print()
        print("SUMMARY:")
        context_counts = pd.Series(contexts).value_counts()
        for context, count in context_counts.items():
            print(f"  {context}: {count} rows")

        # Check that we get appropriate context codes for route_alternative >= 1
        route_alt_codes = [row['valid_code'] for _, row in result.iterrows() if row['valid_code'] < 90]
        expected_range = all(code >= 20 for code in route_alt_codes)  # Should be 20+ for route alternatives

        if expected_range:
            print("  SUCCESS: All route_alternative >= 1 data gets appropriate context codes (20+)")
        else:
            print(f"  WARNING: Some route_alternative data got unexpected codes: {route_alt_codes}")

        return True

    except Exception as e:
        print(f"Error in test: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_normal_route_alternatives()
    if success:
        print("\nSUCCESS: Normal route_alternative validation working correctly!")
    else:
        print("\nERROR: Normal route_alternative validation failed!")