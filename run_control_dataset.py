import time
from pathlib import Path
import pandas as pd
import geopandas as gpd

from components.control.validator import validate_dataframe_batch, ValidationParameters
from components.control.report import generate_link_report
from components.control.page import save_validation_results
from components.processing.pipeline import detect_file_encoding

csv_path = Path(r"test_data/control/data.csv")
shapefile_zip = Path(r"test_data/control/google_results_to_golan_17_8_25.zip")
shp_name = "google_results_to_golan_17_8_25.shp"
output_dir = Path(r"control_output/test_cli_run")
output_dir.mkdir(parents=True, exist_ok=True)

print(f"[INFO] Loading CSV: {csv_path}")
encoding = detect_file_encoding(str(csv_path))
print(f"[INFO] Detected encoding: {encoding}")
start = time.time()
df = pd.read_csv(csv_path, encoding=encoding)
load_csv_time = time.time()
print(f"[INFO] CSV loaded with {len(df):,} rows in {load_csv_time - start:.2f}s")

print(f"[INFO] Loading shapefile: {shapefile_zip} -> {shp_name}")
shapefile_path = f"zip://{shapefile_zip}!{shp_name}"
shapefile_gdf = gpd.read_file(shapefile_path)
load_shp_time = time.time()
print(f"[INFO] Shapefile loaded with {len(shapefile_gdf):,} features in {load_shp_time - load_csv_time:.2f}s")

params = ValidationParameters(
    use_hausdorff=True,
    use_length_check=False,
    use_coverage_check=False,
    hausdorff_threshold_m=5.0,
    length_check_mode='ratio',
    length_ratio_min=0.90,
    length_ratio_max=1.10,
    epsilon_length_m=0.5,
    min_link_length_m=20.0,
    coverage_min=0.85,
    coverage_spacing_m=1.0,
    crs_metric='EPSG:2039',
    polyline_precision=5,
)

print("[INFO] Running batch validation...")
result_df = validate_dataframe_batch(df, shapefile_gdf, params)
validation_time = time.time()
print(f"[INFO] Validation completed in {validation_time - load_shp_time:.2f}s")

print("[INFO] Generating link report...")
report_gdf = generate_link_report(result_df, shapefile_gdf)
report_time = time.time()
print(f"[INFO] Link report generated in {report_time - validation_time:.2f}s")

print(f"[INFO] Saving outputs to {output_dir}")
output_files = save_validation_results(
    result_df=result_df,
    report_gdf=report_gdf,
    output_dir=str(output_dir),
    generate_shapefile=True,
    completeness_params=None
)
save_time = time.time()
print(f"[INFO] Outputs saved in {save_time - report_time:.2f}s")

print("[INFO] Output file keys:")
for key, path_str in output_files.items():
    print(f"  - {key}: {path_str}")

print(f"[INFO] Total elapsed time: {save_time - start:.2f}s")
