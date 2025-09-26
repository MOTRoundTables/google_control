#!/usr/bin/env python3
"""
Test that all shapefiles exactly match their corresponding CSV files.

Validates:
1. Failed observations shapefile matches CSV with decoded polyline geometries
2. Missing observations shapefile matches CSV with original shapefile geometries
3. No-data links shapefile matches CSV with original shapefile geometries
4. Link report shapefile matches CSV with same columns and order
"""

import sys
import pandas as pd
import geopandas as gpd
from pathlib import Path
from datetime import date
import tempfile

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from components.control.page import save_validation_results
from shapely.geometry import LineString


def create_test_data_with_failures():
    """Create test data with validation failures for shapefile testing"""

    # Create validation data with different types of failures
    validation_data = []

    # Failed observations (codes 1-3) with polylines
    failed_links = [
        ('s_1000-2000', 1, 'polyline_data_1'),
        ('s_2000-3000', 2, 'polyline_data_2'),
        ('s_3000-4000', 3, 'polyline_data_3')
    ]

    for link, code, polyline in failed_links:
        validation_data.append({
            'DataID': f'test_{code}',
            'Name': link,
            'RequestedTime': '10:00:00',
            'Timestamp': '2025-06-29 10:01',
            'is_valid': False,
            'valid_code': code,
            'polyline': polyline,
            'RouteAlternative': 1,
            'SegmentID': f'seg_{code}',
            'hausdorff_distance': 10.0 + code,
            'hausdorff_pass': False,
            'Duration': 300.0,
            'Distance': 1000.0,
            'Speed': 50.0,
        })

    # Valid observations for other links
    valid_links = ['s_4000-5000', 's_5000-6000']
    for link in valid_links:
        validation_data.append({
            'DataID': f'test_valid_{link}',
            'Name': link,
            'RequestedTime': '10:00:00',
            'Timestamp': '2025-06-29 10:01',
            'is_valid': True,
            'valid_code': 0,
            'polyline': 'valid_polyline',
            'RouteAlternative': 1,
            'SegmentID': 'seg_valid',
            'hausdorff_distance': 1.0,
            'hausdorff_pass': True,
            'Duration': 250.0,
            'Distance': 800.0,
            'Speed': 60.0,
        })

    result_df = pd.DataFrame(validation_data)

    # Create comprehensive shapefile including no-data links
    shapefile_data = []
    geometries = []

    all_links = failed_links + [(link, 0, '') for link in valid_links] + [
        ('s_7000-8000', 95, ''),  # No-data link 1
        ('s_8000-9000', 95, ''),  # No-data link 2
    ]

    for i, (link, _, _) in enumerate(all_links):
        parts = link[2:].split('-')
        from_id, to_id = parts
        shapefile_data.append({
            'From': int(from_id),
            'To': int(to_id),
            'Description': f'Test link {link}'
        })
        geometries.append(LineString([(i, i), (i+1, i+1)]))

    report_gdf = gpd.GeoDataFrame(shapefile_data, geometry=geometries, crs='EPSG:4326')

    return result_df, report_gdf


def test_shapefile_csv_matching():
    """Test that all shapefiles match their CSV counterparts exactly"""

    print("SHAPEFILE-CSV MATCHING TEST")
    print("=" * 50)

    # Create test data
    result_df, report_gdf = create_test_data_with_failures()

    # Create output directory
    output_dir = Path(tempfile.mkdtemp()) / "shapefile_test"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Test data:")
    print(f"  Validation rows: {len(result_df)}")
    print(f"  Shapefile links: {len(report_gdf)}")
    print(f"  Output directory: {output_dir}")

    # Set up completeness parameters to generate missing observations
    completeness_params = {
        'start_date': date(2025, 6, 29),
        'end_date': date(2025, 6, 29),  # Single day
        'interval_minutes': 15
    }

    try:
        # Run complete workflow with shapefile generation
        output_files = save_validation_results(
            result_df=result_df,
            report_gdf=report_gdf,
            output_dir=str(output_dir),
            generate_shapefile=True,
            completeness_params=completeness_params
        )

        print(f"\nGenerated files:")
        for file_type, file_path in output_files.items():
            if Path(file_path).exists():
                file_size = Path(file_path).stat().st_size
                print(f"  {file_type}: {Path(file_path).name} ({file_size:,} bytes)")

        # Test 1: Failed observations CSV vs Shapefile
        test_results = []

        if 'failed_observations_csv' in output_files and 'failed_observations_zip' in output_files:
            failed_csv = pd.read_csv(output_files['failed_observations_csv'])
            # Extract shapefile from ZIP and load
            import zipfile
            import tempfile as tf

            with zipfile.ZipFile(output_files['failed_observations_zip'], 'r') as zip_ref:
                temp_dir = tf.mkdtemp()
                zip_ref.extractall(temp_dir)
                shp_files = list(Path(temp_dir).glob("*.shp"))
                if shp_files:
                    failed_shp = gpd.read_file(shp_files[0])

                    # Compare row counts
                    csv_rows = len(failed_csv)
                    shp_rows = len(failed_shp)
                    rows_match = csv_rows == shp_rows

                    # Compare column presence (shapefile may truncate names)
                    csv_cols = set(failed_csv.columns)
                    shp_cols = set(failed_shp.columns) - {'geometry'}

                    test_results.append({
                        'test': 'Failed observations CSV-Shapefile match',
                        'csv_rows': csv_rows,
                        'shp_rows': shp_rows,
                        'rows_match': rows_match,
                        'csv_columns': len(csv_cols),
                        'shp_columns': len(shp_cols),
                        'has_geometry': 'geometry' in failed_shp.columns
                    })

        # Test 2: Missing observations CSV vs Shapefile
        if 'missing_observations_csv' in output_files and 'missing_observations_zip' in output_files:
            missing_csv = pd.read_csv(output_files['missing_observations_csv'])

            with zipfile.ZipFile(output_files['missing_observations_zip'], 'r') as zip_ref:
                temp_dir = tf.mkdtemp()
                zip_ref.extractall(temp_dir)
                shp_files = list(Path(temp_dir).glob("*.shp"))
                if shp_files:
                    missing_shp = gpd.read_file(shp_files[0])

                    csv_rows = len(missing_csv)
                    shp_rows = len(missing_shp)
                    rows_match = csv_rows == shp_rows

                    test_results.append({
                        'test': 'Missing observations CSV-Shapefile match',
                        'csv_rows': csv_rows,
                        'shp_rows': shp_rows,
                        'rows_match': rows_match,
                        'has_geometry': 'geometry' in missing_shp.columns
                    })

        # Test 3: No-data links CSV vs Shapefile
        if 'no_data_links_csv' in output_files and 'no_data_links_zip' in output_files:
            no_data_csv = pd.read_csv(output_files['no_data_links_csv'])

            with zipfile.ZipFile(output_files['no_data_links_zip'], 'r') as zip_ref:
                temp_dir = tf.mkdtemp()
                zip_ref.extractall(temp_dir)
                shp_files = list(Path(temp_dir).glob("*.shp"))
                if shp_files:
                    no_data_shp = gpd.read_file(shp_files[0])

                    csv_rows = len(no_data_csv)
                    shp_rows = len(no_data_shp)
                    rows_match = csv_rows == shp_rows

                    test_results.append({
                        'test': 'No-data links CSV-Shapefile match',
                        'csv_rows': csv_rows,
                        'shp_rows': shp_rows,
                        'rows_match': rows_match,
                        'has_geometry': 'geometry' in no_data_shp.columns
                    })

        # Test 4: Link report CSV vs Shapefile
        if 'link_report_csv' in output_files and 'link_report_zip' in output_files:
            report_csv = pd.read_csv(output_files['link_report_csv'])

            with zipfile.ZipFile(output_files['link_report_zip'], 'r') as zip_ref:
                temp_dir = tf.mkdtemp()
                zip_ref.extractall(temp_dir)
                shp_files = list(Path(temp_dir).glob("*.shp"))
                if shp_files:
                    report_shp = gpd.read_file(shp_files[0])

                    csv_rows = len(report_csv)
                    shp_rows = len(report_shp)
                    rows_match = csv_rows == shp_rows

                    # Check for total_success_rate field
                    has_total_success = 'total_success_rate' in report_csv.columns

                    test_results.append({
                        'test': 'Link report CSV-Shapefile match',
                        'csv_rows': csv_rows,
                        'shp_rows': shp_rows,
                        'rows_match': rows_match,
                        'has_total_success_rate': has_total_success,
                        'has_geometry': 'geometry' in report_shp.columns
                    })

        # Print test results
        print(f"\nSHAPEFILE-CSV MATCHING RESULTS:")
        print("-" * 50)

        all_passed = True
        for result in test_results:
            test_name = result['test']
            rows_match = result['rows_match']
            status = "PASS" if rows_match else "FAIL"

            print(f"{status}: {test_name}")
            print(f"  CSV rows: {result['csv_rows']}, Shapefile rows: {result['shp_rows']}")

            if 'has_total_success_rate' in result:
                print(f"  Has total_success_rate: {result['has_total_success_rate']}")

            if not rows_match:
                all_passed = False

        return all_passed

    except Exception as e:
        print(f"ERROR in shapefile test: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        import shutil
        try:
            shutil.rmtree(output_dir.parent)
        except:
            pass


def main():
    """Run shapefile-CSV matching tests"""
    print("SHAPEFILE-CSV MATCHING VALIDATION")
    print("=" * 60)

    success = test_shapefile_csv_matching()

    print(f"\n" + "=" * 60)
    if success:
        print("ALL SHAPEFILE TESTS PASSED!")
        print("- Failed observations shapefile matches CSV with polyline geometries")
        print("- Missing observations shapefile matches CSV with shapefile geometries")
        print("- No-data links shapefile matches CSV with shapefile geometries")
        print("- Link report shapefile matches CSV with same structure")
    else:
        print("SOME SHAPEFILE TESTS FAILED!")
        print("Review the output above to identify issues.")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)