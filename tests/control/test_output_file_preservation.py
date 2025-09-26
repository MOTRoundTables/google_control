#!/usr/bin/env python3
"""
Test that output files preserve exact input field names.
"""

import pandas as pd
import sys
import os
import tempfile
import shutil
from pathlib import Path

# Add project directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from components.control.validator import validate_dataframe_batch, ValidationParameters
from components.control.report import generate_link_report
import geopandas as gpd


def test_output_file_preservation():
    """Test that output files preserve exact input field names."""
    print("TESTING OUTPUT FILE FIELD PRESERVATION")
    print("=" * 55)

    # Create test data with exact user field names
    test_data = pd.DataFrame({
        'DataID': [1001, 1002, 1003],
        'Name': ['s_653-655', 's_653-655', 's_999-888'],
        'SegmentID': [1185048, 1185048, 1185049],
        'RouteAlternative': [1, 2, 1],
        'RequestedTime': ['13:45:00', '13:45:00', '14:00:00'],
        'Timestamp': ['01/07/2025 13:45', '01/07/2025 13:45', '01/07/2025 14:00'],
        'DayInWeek': ['יום ג', 'יום ג', 'יום ג'],
        'DayType': ['יום חול', 'יום חול', 'יום חול'],
        'Duration (seconds)': [2446, 2400, 2500],
        'Distance (meters)': [59428, 58000, 60000],
        'Speed (km/h)': [87.5, 87.0, 86.0],
        'Url': ['https://test.com'] * 3,
        'Polyline': ['_oxwD{_wtEoAlCe@vFq@ha@c@~X_@fOcD~S_@fByAjDaBrBoE|BsKzC_OfE_FhBcFjE}BdEqAfE[vBKjIb@vI|AjXObGs@vCeApB_C|BsGtCaL~B}EvA_CnBeAhBgEzL}IrX_DrLkB~TiBpHgB~CeCxBiElAoEMiA]yKaGcMkHyBe@cCJkChAwEvCeC|@gBTyOj@yZd@mATy@p@]~@OvEIvEa@vFIxF]nD\\lBYfDDxEClAc@hAeAhE[Vo@I_DUwJbDqKtDsL~DuLdEaDrAyEnEkMjK}B~@_Db@_DIgWuCsEkA_EsBsB}AkHuFaViSaWgVoBuAgCgAoJsB}J}C}WmJ}DsAaCg@yBCcMjAiQ~BmGfCyDtCuGfHwJ`LsFjG{ClEmEdN}BvGcAlAmAn@iDn@cCJwHrAgJlCsVxCms@jIa^|DyiCbZogEbf@mkCnZqLzAmNfDmGvAwABcCk@iA_Aw@{Ae@eDLyQYyFk@mAaBsAeBk@_JuAwBm@mDmCsCgCuBg@kAJuAt@}@hB[tCUlJUtHm@lEcCrFmC`F}@j@q@I_@a@GmBdBqC\\sAEcHWmDiAmEaAqAuDwAkKiAqBw@eByAq@y@wAuDgAaM_AcGaCiDmNaLcDy@qC^yAhAmAfCwDxNmAfBoCtB_Cp@oAF_H@cSQmSuAyCLkA^kHbEeHbE{H|EqIxL_NzUeCpGiB`FqAlFb@tKu@lDcBxCoAzCeBxLw@fF_A~BmCvBeCV}KuAyRmCqDIyA`@aGnCyMzFgFb@cFPwB^eEzBcU`OoIpEsJhDwKfDeM~C_VnD{HbDmJ|EeCxBmBnEm@bH[vFy@zRrBlUVl]o@xDk@vA}BrCkMnLcFxHwA~BiA`A{Ed@mJTsD~@mIzCgFvAoBEeAa@{D}DoB_CyFwEuK_IoBwBuAsDsCiLiA}DkAyAaB_AiBSkADiBj@qEpCqDvByChCyCvDsCxBsFtBmAjAi@lA[pCHzLa@vIoC|LcMbYiHfScBfEuBnCwCjBmD|AyDlDaAbByKrVuAnBkFrDkMjGiRvQgApBq@pC]xFc@vEyB|GwBrHuAdJ}AdGcGlIwQbUqJdK}MzLmAnC]|DeBlt@}@l]?pDZjDh@pBlC|FpFhJtDfElGpBf@r@OdAo@b@{LqBs@JCt@pJzCLp@i@VuGsAkCYGt@rErArBhAx@pBxCxCtChApAp@lBbGfA~DtBbGjJdLhJTnSvBbFbA~@h@d@xBcB|DkCpDcAv@QT[t@gF|B'] * 3
    })

    print("Input field names:")
    print(f"  {list(test_data.columns)}")
    print()

    try:
        # Load shapefile
        shapefile_path = "test_data/google_results_to_golan_17_8_25/google_results_to_golan_17_8_25.shp"
        shapefile_gdf = gpd.read_file(shapefile_path)

        # Run validation
        params = ValidationParameters(use_hausdorff=True, use_length_check=True, use_coverage_check=False)
        result_df = validate_dataframe_batch(test_data, shapefile_gdf, params)

        print("Validation result field names:")
        print(f"  {list(result_df.columns)}")
        print()

        # Test the output file creation logic
        with tempfile.TemporaryDirectory() as temp_dir:
            # Simulate the output file creation logic from app.py
            validated_csv_path = Path(temp_dir) / "validated_data.csv"

            # Use the same sorting logic as in app.py
            name_col = 'Name' if 'Name' in result_df.columns else ('name' if 'name' in result_df.columns else None)
            timestamp_col = 'Timestamp' if 'Timestamp' in result_df.columns else ('timestamp' if 'timestamp' in result_df.columns else None)
            requested_time_col = 'RequestedTime' if 'RequestedTime' in result_df.columns else ('requested_time' if 'requested_time' in result_df.columns else None)

            if name_col and timestamp_col:
                result_df_sorted = result_df.sort_values([name_col, timestamp_col])
                print(f"Sorted by: [{name_col}, {timestamp_col}]")
            elif name_col and requested_time_col:
                result_df_sorted = result_df.sort_values([name_col, requested_time_col])
                print(f"Sorted by: [{name_col}, {requested_time_col}]")
            elif name_col:
                result_df_sorted = result_df.sort_values([name_col])
                print(f"Sorted by: [{name_col}]")
            else:
                result_df_sorted = result_df
                print("No sorting applied")

            # Write to CSV
            result_df_sorted.to_csv(validated_csv_path, index=False)
            print(f"Output file created: {validated_csv_path}")

            # Read back and verify field preservation
            output_df = pd.read_csv(validated_csv_path)
            print()
            print("Output file field names:")
            print(f"  {list(output_df.columns)}")

            # Compare field names
            input_cols = set(test_data.columns)
            output_cols = set(output_df.columns)
            validation_cols = {'is_valid', 'valid_code'}

            preserved_cols = input_cols & output_cols
            missing_cols = input_cols - output_cols
            extra_cols = output_cols - input_cols

            print()
            print("Field preservation analysis:")
            print(f"  Input fields: {len(input_cols)}")
            print(f"  Preserved fields: {len(preserved_cols)}")
            print(f"  Missing fields: {len(missing_cols)} {sorted(missing_cols) if missing_cols else ''}")
            print(f"  Added fields: {len(extra_cols)} {sorted(extra_cols)}")

            # Verify all input fields preserved
            all_preserved = (len(missing_cols) == 0)
            validation_added = extra_cols == validation_cols

            print()
            if all_preserved and validation_added:
                print("SUCCESS: All input fields preserved with exact naming!")
                print("SUCCESS: Only validation columns (is_valid, valid_code) added!")

                # Show sample of sorted output
                print()
                print("Sample sorted output:")
                display_cols = ['DataID', 'Name', 'RouteAlternative', 'Timestamp', 'is_valid', 'valid_code']
                print(output_df[display_cols])

                return True
            else:
                print("ERROR: Field preservation failed!")
                if not all_preserved:
                    print(f"  Missing input fields: {missing_cols}")
                if not validation_added:
                    print(f"  Unexpected extra fields: {extra_cols - validation_cols}")
                return False

    except Exception as e:
        print(f"Error in test: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_output_file_preservation()
    if success:
        print("\nSUCCESS: Output file field preservation working correctly!")
    else:
        print("\nERROR: Output file field preservation failed!")

    sys.exit(0 if success else 1)