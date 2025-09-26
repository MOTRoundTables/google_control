#!/usr/bin/env python3
"""
Debug geometry-only validation to see why we're getting code 90.
"""

import pandas as pd
import sys
import os

# Add project directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from control_validator import validate_dataframe_batch, ValidationParameters, ValidCode
import geopandas as gpd


def debug_geometric_validation():
    """Debug geometry-only validation step by step."""
    print("DEBUGGING GEOMETRY-ONLY VALIDATION")
    print("=" * 50)

    try:
        # Create minimal test data with known working link
        test_data = pd.DataFrame({
            'name': ['s_653-655'],
            'polyline': ['_oxwD{_wtEoAlCe@vFq@ha@c@~X_@fOcD~S_@fByAjDaBrBoE|BsKzC_OfE_FhBcFjE}BdEqAfE[vBKjIb@vI|AjXObGs@vCeApB_C|BsGtCaL~B}EvA_CnBeAhBgEzL}IrX_DrLkB~TiBpHgB~CeCxBiElAoEMiA]yKaGcMkHyBe@cCJkChAwEvCeC|@gBTyOj@yZd@mATy@p@]~@OvEIvEa@vFIxF]nD\\lBYfDDxEClAc@hAeAhE[Vo@I_DUwJbDqKtDsL~DuLdEaDrAyEnEkMjK}B~@_Db@_DIgWuCsEkA_EsBsB}AkHuFaViSaWgVoBuAgCgAoJsB}J}C}WmJ}DsAaCg@yBCcMjAiQ~BmGfCyDtCuGfHwJ`LsFjG{ClEmEdN}BvGcAlAmAn@iDn@cCJwHrAgJlCsVxCms@jIa^|DyiCbZogEbf@mkCnZqLzAmNfDmGvAwABcCk@iA_Aw@{Ae@eDLyQYyFk@mAaBsAeBk@_JuAwBm@mDmCsCgCuBg@kAJuAt@}@hB[tCUlJUtHm@lEcCrFmC`F}@j@q@I_@a@GmBdBqC\\sAEcHWmDiAmEaAqAuDwAkKiAqBw@eByAq@y@wAuDgAaM_AcGaCiDmNaLcDy@qC^yAhAmAfCwDxNmAfBoCtB_Cp@oAF_H@cSQmSuAyCLkA^kHbEeHbE{H|EqIxL_NzUeCpGiB`FqAlFb@tKu@lDcBxCoAzCeBxLw@fF_A~BmCvBeCV}KuAyRmCqDIyA`@aGnCyMzFgFb@cFPwB^eEzBcU`OoIpEsJhDwKfDeM~C_VnD{HbDmJ|EeCxBmBnEm@bH[vFy@zRrBlUVl]o@xDk@vA}BrCkMnLcFxHwA~BiA`A{Ed@mJTsD~@mIzCgFvAoBEeAa@{D}DoB_CyFwEuK_IoBwBuAsDsCiLiA}DkAyAaB_AiBSkADiBj@qEpCqDvByChCyCvDsCxBsFtBmAjAi@lA[pCHzLa@vIoC|LcMbYiHfScBfEuBnCwCjBmD|AyDlDaAbByKrVuAnBkFrDkMjGiRvQgApBq@pC]xFc@vEyB|GwBrHuAdJ}AdGcGlIwQbUqJdK}MzLmAnC]|DeBlt@}@l]?pDZjDh@pBlC|FpFhJtDfElGpBf@r@OdAo@b@{LqBs@JCt@pJzCLp@i@VuGsAkCYGt@rErArBhAx@pBxCxCtChApAp@lBbGfA~DtBbGjJdLhJTnSvBbFbA~@h@d@xBcB|DkCpDcAv@QT[t@gF|B'],
            'timestamp': ['2025-01-01 10:00:00']
        })

        print(f"Test data shape: {test_data.shape}")
        print(f"Test data columns: {list(test_data.columns)}")
        print(f"Has route_alternative: {'route_alternative' in test_data.columns}")
        print(f"Sample row: {test_data.iloc[0]['name']}")

        # Load shapefile
        shapefile_path = "test_data/google_results_to_golan_17_8_25/google_results_to_golan_17_8_25.shp"
        shapefile_gdf = gpd.read_file(shapefile_path)
        print(f"Loaded shapefile: {len(shapefile_gdf)} features")

        # Test with simple Hausdorff validation
        params = ValidationParameters(
            use_hausdorff=True,
            use_length_check=False,
            use_coverage_check=False,
            hausdorff_threshold_m=10.0
        )

        print(f"\nValidation parameters:")
        print(f"  use_hausdorff: {params.use_hausdorff}")
        print(f"  use_length_check: {params.use_length_check}")
        print(f"  use_coverage_check: {params.use_coverage_check}")

        result = validate_dataframe_batch(test_data, shapefile_gdf, params)

        print(f"\nValidation result:")
        print(f"Result shape: {result.shape}")
        print(f"Result columns: {list(result.columns)}")
        if len(result) > 0:
            print(f"Valid codes: {result['valid_code'].tolist()}")
            print(f"First row result: {result.iloc[0].to_dict()}")
        else:
            print("No results returned!")

        # Check what the context should be
        has_route_alt = 'route_alternative' in test_data.columns
        print(f"\nContext analysis:")
        print(f"  Has route_alternative column: {has_route_alt}")
        print(f"  Expected context: {'route alternative' if has_route_alt else 'geometry only'}")
        print(f"  Expected code range: {'20-34' if has_route_alt else '0-4'}")

        return True

    except Exception as e:
        print(f"Error in debug test: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    debug_geometric_validation()