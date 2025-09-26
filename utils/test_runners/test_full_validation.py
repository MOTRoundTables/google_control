"""Test full validation with progress tracking and error handling"""
import pandas as pd
import geopandas as gpd
import zipfile
import tempfile
import os
import sys
import time
import traceback
from datetime import datetime

# Add components to path
sys.path.insert(0, r'E:\google_agg')

from components.control.validator import validate_dataframe_batch, ValidationParameters
from components.control.report import generate_link_report

print("="*60)
print("TESTING FULL VALIDATION WITH PROGRESS TRACKING")
print("="*60)

# Configuration
csv_path = r'E:\google_agg\test_data\control\data.csv'
shapefile_zip = r'E:\google_agg\test_data\control\google_results_to_golan_17_8_25.zip'
output_dir = r'E:\google_agg\test_output'

# Create output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

print(f"\nStarting at: {datetime.now()}")
print(f"Output directory: {output_dir}")

try:
    # Step 1: Load CSV
    print("\n1. Loading CSV file...")
    start = time.time()
    df = pd.read_csv(csv_path, encoding='utf-8')
    print(f"   [OK] Loaded {len(df):,} rows in {time.time()-start:.1f} seconds")
    print(f"   Memory usage: {df.memory_usage(deep=True).sum() / 1024**2:.1f} MB")

    # Step 2: Load shapefile
    print("\n2. Loading shapefile...")
    start = time.time()
    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(shapefile_zip, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        shp_files = [f for f in os.listdir(temp_dir) if f.endswith('.shp')]
        shp_path = os.path.join(temp_dir, shp_files[0])
        gdf = gpd.read_file(shp_path)
        print(f"   [OK] Loaded {len(gdf)} shapefile features in {time.time()-start:.1f} seconds")

        # Step 3: Run validation
        print("\n3. Running validation...")
        print("   This may take several minutes for 714K rows...")

        # Convert columns to lowercase for validator
        df.columns = df.columns.str.lower()

        # Process in batches to show progress
        batch_size = 10000
        total_batches = (len(df) + batch_size - 1) // batch_size
        results = []

        params = ValidationParameters(hausdorff_threshold_m=5.0)

        start_validation = time.time()
        for i in range(0, len(df), batch_size):
            batch_num = i // batch_size + 1
            end_idx = min(i + batch_size, len(df))
            batch_df = df.iloc[i:end_idx]

            print(f"   Processing batch {batch_num}/{total_batches} (rows {i+1:,}-{end_idx:,})...", end="")
            sys.stdout.flush()

            try:
                batch_result = validate_dataframe_batch(batch_df, gdf, params)
                results.append(batch_result)
                # Handle potential NaN values in is_valid column
                if 'is_valid' in batch_result.columns:
                    # Fill NaN with False (treat as invalid)
                    batch_result['is_valid'] = batch_result['is_valid'].fillna(False)
                    valid = batch_result['is_valid'].sum()
                    invalid = (~batch_result['is_valid']).sum()
                else:
                    valid = 0
                    invalid = len(batch_result)
                print(f" Valid: {valid}, Invalid: {invalid}")

            except Exception as e:
                print(f"\n   [ERROR] Batch {batch_num} failed: {e}")
                print(f"   Batch details: {len(batch_df)} rows")
                # Show sample of problematic batch
                print(f"   Sample names: {batch_df['name'].head().tolist()}")
                if 'polyline' in batch_df.columns:
                    sample_polyline = batch_df['polyline'].dropna().iloc[0] if len(batch_df['polyline'].dropna()) > 0 else None
                    if sample_polyline:
                        print(f"   Sample polyline (first 50 chars): {sample_polyline[:50]}")
                raise

        # Combine results
        print("\n   Combining results...")
        result_df = pd.concat(results, ignore_index=True)
        validation_time = time.time() - start_validation
        print(f"   [OK] Validation completed in {validation_time:.1f} seconds")
        print(f"   Total results: {len(result_df):,} rows")
        print(f"   Valid: {result_df['is_valid'].sum():,}")
        print(f"   Invalid: {(~result_df['is_valid']).sum():,}")

        # Check validation codes
        if 'valid_code' in result_df.columns:
            print("\n   Validation code distribution:")
            code_counts = result_df['valid_code'].value_counts().head(10)
            for code, count in code_counts.items():
                percentage = (count / len(result_df)) * 100
                print(f"      Code {code}: {count:,} ({percentage:.1f}%)")

        # Step 4: Generate report
        print("\n4. Generating link report...")
        start = time.time()
        report_gdf = generate_link_report(result_df, gdf)
        print(f"   [OK] Report generated in {time.time()-start:.1f} seconds")
        print(f"   Report has {len(report_gdf)} links")

        # Step 5: Save results
        print("\n5. Saving results...")

        # Save validation results
        csv_output = os.path.join(output_dir, 'validation_results.csv')
        result_df.to_csv(csv_output, index=False)
        print(f"   [OK] Saved validation results to: {csv_output}")

        # Save report
        report_output = os.path.join(output_dir, 'link_report.csv')
        # Convert GeoDataFrame to DataFrame for CSV (drop geometry)
        report_df = pd.DataFrame(report_gdf.drop(columns=['geometry']))
        report_df.to_csv(report_output, index=False)
        print(f"   [OK] Saved link report to: {report_output}")

        # Show summary statistics
        print("\n6. Summary Statistics:")
        links_with_data = report_gdf[report_gdf['total_observations'] > 0]
        print(f"   Links with observations: {len(links_with_data):,} / {len(report_gdf):,}")

        if len(links_with_data) > 0:
            avg_success_rate = links_with_data['success_rate'].mean()
            print(f"   Average success rate: {avg_success_rate:.1f}%")

        print(f"\nCompleted at: {datetime.now()}")
        print("SUCCESS: Validation completed successfully!")

except MemoryError as e:
    print("\n[ERROR] Out of memory!")
    print("The dataset is too large. Try:")
    print("1. Process smaller batches")
    print("2. Use a machine with more RAM")
    print("3. Filter the data to fewer links")

except KeyboardInterrupt:
    print("\n[ERROR] Validation interrupted by user")

except Exception as e:
    print(f"\n[ERROR] Validation failed: {e}")
    print("\nFull error details:")
    traceback.print_exc()

    # Try to provide helpful debugging info
    print("\nDebugging suggestions:")
    if "name" in str(e).lower():
        print("- Check if 'Name' column exists in CSV")
    if "polyline" in str(e).lower():
        print("- Check if 'Polyline' column exists in CSV")
        print("- Check polyline encoding (should be Google-encoded polylines)")
    if "memory" in str(e).lower():
        print("- Dataset too large, try processing in smaller chunks")
    if "timeout" in str(e).lower():
        print("- Process is taking too long, try with fewer rows first")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)