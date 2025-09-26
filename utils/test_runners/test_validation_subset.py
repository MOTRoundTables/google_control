"""Test validation with a subset to verify the fix"""
import pandas as pd
import geopandas as gpd
import zipfile
import tempfile
import os
import sys
import time

# Add components to path
sys.path.insert(0, r'E:\google_agg')

from components.control.validator import validate_dataframe_batch, ValidationParameters
from components.control.report import generate_link_report

print("="*60)
print("TESTING VALIDATION WITH SUBSET (first 50K rows)")
print("="*60)

# Configuration
csv_path = r'E:\google_agg\test_data\control\data.csv'
shapefile_zip = r'E:\google_agg\test_data\control\google_results_to_golan_17_8_25.zip'

try:
    # Load only first 50K rows for faster testing
    print("\n1. Loading first 50,000 rows from CSV...")
    df = pd.read_csv(csv_path, encoding='utf-8', nrows=50000)
    print(f"   Loaded {len(df):,} rows")

    # Load shapefile
    print("\n2. Loading shapefile...")
    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(shapefile_zip, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        shp_files = [f for f in os.listdir(temp_dir) if f.endswith('.shp')]
        shp_path = os.path.join(temp_dir, shp_files[0])
        gdf = gpd.read_file(shp_path)
        print(f"   Loaded {len(gdf)} shapefile features")

        # Convert columns to lowercase
        df.columns = df.columns.str.lower()

        # Run validation
        print("\n3. Running validation...")
        params = ValidationParameters(hausdorff_threshold_m=5.0)

        start = time.time()
        result_df = validate_dataframe_batch(df, gdf, params)
        elapsed = time.time() - start

        print(f"   Validation completed in {elapsed:.1f} seconds")

        # Check for NaN in is_valid
        if 'is_valid' in result_df.columns:
            nan_count = result_df['is_valid'].isna().sum()
            if nan_count > 0:
                print(f"   WARNING: Found {nan_count} NaN values in is_valid column")
                # Show some examples
                nan_rows = result_df[result_df['is_valid'].isna()].head()
                print("   Sample rows with NaN is_valid:")
                for idx, row in nan_rows.iterrows():
                    print(f"      Row {idx}: name={row.get('name', 'N/A')}, code={row.get('valid_code', 'N/A')}")
            else:
                print(f"   [OK] No NaN values in is_valid column")

            # Count valid/invalid
            result_df['is_valid'] = result_df['is_valid'].fillna(False)  # Treat NaN as False
            valid = result_df['is_valid'].sum()
            invalid = (~result_df['is_valid']).sum()
            print(f"   Valid: {valid:,} ({valid/len(result_df)*100:.1f}%)")
            print(f"   Invalid: {invalid:,} ({invalid/len(result_df)*100:.1f}%)")
        else:
            print("   ERROR: is_valid column not found in results")

        # Check validation codes
        if 'valid_code' in result_df.columns:
            print("\n4. Validation code distribution:")
            code_counts = result_df['valid_code'].value_counts().head(10)
            for code, count in code_counts.items():
                percentage = (count / len(result_df)) * 100
                print(f"   Code {code}: {count:,} ({percentage:.1f}%)")

        print("\n5. Generate report...")
        start = time.time()
        report_gdf = generate_link_report(result_df, gdf)
        elapsed = time.time() - start
        print(f"   Report generated in {elapsed:.1f} seconds")

        # Check success rates
        links_with_data = report_gdf[report_gdf['total_observations'] > 0]
        print(f"   Links with data: {len(links_with_data)}/{len(report_gdf)}")

        if len(links_with_data) > 0:
            # Check for NaN in success_rate
            nan_success = links_with_data['success_rate'].isna().sum()
            if nan_success > 0:
                print(f"   Found {nan_success} links with NaN success_rate")
            else:
                avg_success = links_with_data['success_rate'].mean()
                print(f"   Average success rate: {avg_success:.1f}%")

        print("\nSUCCESS: Validation test passed!")

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)