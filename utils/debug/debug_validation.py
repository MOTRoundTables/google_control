"""Debug validation failure with data.csv"""
import pandas as pd
import geopandas as gpd
import zipfile
import tempfile
import os
import sys
import traceback

# Add components to path
sys.path.insert(0, r'E:\google_agg')

from components.control.validator import validate_dataframe_batch, ValidationParameters
from components.control.report import generate_link_report

print("="*60)
print("DEBUGGING VALIDATION FAILURE")
print("="*60)

# Load the CSV file
csv_path = r'E:\google_agg\test_data\control\data.csv'
print(f"\n1. Loading CSV: {csv_path}")

try:
    # Try different encodings
    for encoding in ['utf-8', 'latin-1', 'cp1255', 'cp1252']:
        try:
            df = pd.read_csv(csv_path, encoding=encoding)
            print(f"   [OK] Successfully loaded with encoding: {encoding}")
            print(f"   Rows: {len(df)}")
            print(f"   Columns: {list(df.columns)}")
            break
        except UnicodeDecodeError:
            continue
    else:
        print("   [ERROR] Failed to load with any encoding")
        sys.exit(1)

except Exception as e:
    print(f"   [ERROR] Error loading CSV: {e}")
    traceback.print_exc()
    sys.exit(1)

# Check for required columns
print("\n2. Checking required columns:")
required_cols = ['Name', 'Polyline', 'Timestamp']
optional_cols = ['RouteAlternative']

for col in required_cols:
    if col in df.columns:
        print(f"   [OK] {col}: Found")
        # Show sample values
        non_null = df[col].dropna()
        if len(non_null) > 0:
            print(f"      Sample: {non_null.iloc[0]}")
        else:
            print(f"      WARNING: All values are null!")
    else:
        print(f"   [ERROR] {col}: MISSING")

for col in optional_cols:
    if col in df.columns:
        print(f"   [OK] {col}: Found (optional)")
        print(f"      Unique values: {df[col].unique()[:10]}")
    else:
        print(f"   [WARNING] {col}: Missing (optional)")

# Check data quality
print("\n3. Data quality check:")
print(f"   Total rows: {len(df)}")
print(f"   Rows with Name: {df['Name'].notna().sum() if 'Name' in df.columns else 0}")
print(f"   Rows with Polyline: {df['Polyline'].notna().sum() if 'Polyline' in df.columns else 0}")
print(f"   Rows with Timestamp: {df['Timestamp'].notna().sum() if 'Timestamp' in df.columns else 0}")

# Check unique links
if 'Name' in df.columns:
    unique_links = df['Name'].unique()
    print(f"   Unique links: {len(unique_links)}")
    print(f"   Sample links: {list(unique_links[:5])}")

# Load shapefile
print("\n4. Loading shapefile:")
shapefile_zip = r'E:\google_agg\test_data\control\google_results_to_golan_17_8_25.zip'

try:
    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(shapefile_zip, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        shp_files = [f for f in os.listdir(temp_dir) if f.endswith('.shp')]
        if shp_files:
            shp_path = os.path.join(temp_dir, shp_files[0])
            gdf = gpd.read_file(shp_path)
            print(f"   [OK] Loaded {len(gdf)} features")

            # Check shapefile structure
            print(f"   Columns: {list(gdf.columns)}")

            # Check for required shapefile columns
            for col in ['From', 'To']:
                if col in gdf.columns:
                    print(f"   [OK] {col}: Found")
                else:
                    print(f"   [ERROR] {col}: MISSING")

            # Try validation with a small sample
            print("\n5. Testing validation with first 10 rows:")

            try:
                # Prepare sample data
                sample_df = df.head(10).copy()

                # Ensure column names are lowercase for validator
                sample_df.columns = sample_df.columns.str.lower()

                # Check if required columns exist after lowercasing
                print("   Columns after lowercasing:", list(sample_df.columns))

                params = ValidationParameters(hausdorff_threshold_m=5.0)
                result = validate_dataframe_batch(sample_df, gdf, params)

                print(f"   [OK] Validation succeeded!")
                print(f"   Results: {len(result)} rows")
                print(f"   Valid: {result['is_valid'].sum() if 'is_valid' in result.columns else 0}")
                print(f"   Invalid: {(~result['is_valid']).sum() if 'is_valid' in result.columns else 0}")

                # Check validation codes
                if 'valid_code' in result.columns:
                    print(f"   Validation codes: {result['valid_code'].value_counts().to_dict()}")

                    # Check for specific error codes
                    error_codes = {
                        90: 'REQUIRED_FIELDS_MISSING',
                        91: 'NAME_PARSE_FAILURE',
                        92: 'LINK_NOT_IN_SHAPEFILE',
                        93: 'POLYLINE_DECODE_FAILURE'
                    }

                    for code, desc in error_codes.items():
                        count = (result['valid_code'] == code).sum()
                        if count > 0:
                            print(f"   [WARNING] {desc} (code {code}): {count} rows")
                            # Show sample row with this error
                            sample_error = result[result['valid_code'] == code].iloc[0]
                            if 'name' in sample_error:
                                print(f"      Example: {sample_error['name']}")

            except Exception as e:
                print(f"   [ERROR] Validation failed: {e}")
                traceback.print_exc()

                # Try to understand the error
                print("\n   Debugging the error:")

                # Check if it's a column name issue
                if "name" in str(e).lower() or "polyline" in str(e).lower():
                    print("   → Likely a column naming issue")
                    print("   Original columns:", list(df.columns))
                    print("   After lowercase:", list(df.columns.str.lower()))

                # Check if it's an encoding issue
                if "decode" in str(e).lower() or "utf" in str(e).lower():
                    print("   → Likely an encoding issue with polylines")
                    if 'Polyline' in df.columns:
                        sample_polyline = df['Polyline'].dropna().iloc[0] if len(df['Polyline'].dropna()) > 0 else None
                        if sample_polyline:
                            print(f"   Sample polyline (first 100 chars): {sample_polyline[:100]}")

        else:
            print("   [ERROR] No .shp file found in zip")

except Exception as e:
    print(f"   [ERROR] Error with shapefile: {e}")
    traceback.print_exc()

print("\n" + "="*60)
print("DEBUGGING COMPLETE")
print("="*60)