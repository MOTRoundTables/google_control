# Control Output Comparison

| File | Metric | New Run (02_17_29_09) | Baseline (17_47_28_9) | Difference |
| --- | --- | --- | --- | --- |
| validated_data.csv | exists | True | True | 0 |
| validated_data.csv | size_mb | 259.569 | 259.569 | 0 |
| validated_data.csv | row_count | 714385 | 714385 | 0 |
| validated_data.csv | is_valid_sum | 698223 | 698223 | 0 |
| validated_data.csv | valid_code_counts | {2: 688779, 3: 25606} | {2: 688779, 3: 25606} | match |
| best_valid_observations.csv | exists | True | True | 0 |
| best_valid_observations.csv | size_mb | 254.903 | 254.903 | 0 |
| best_valid_observations.csv | row_count | 697334 | 697334 | 0 |
| best_valid_observations.csv | is_valid_sum | 697334 | 697334 | 0 |
| best_valid_observations.csv | valid_code_counts | {2: 686062, 3: 11272} | {2: 686062, 3: 11272} | match |
| failed_observations.csv | exists | True | True | 0 |
| failed_observations.csv | size_mb | 2.117 | 2.117 | 0 |
| failed_observations.csv | row_count | 3490 | 3490 | 0 |
| failed_observations.csv | is_valid_sum | 0 | 0 | 0 |
| failed_observations.csv | valid_code_counts | {2: 2717, 3: 773} | {2: 2717, 3: 773} | match |
| missing_observations.csv | exists | True | True | 0 |
| missing_observations.csv | size_mb | 0.0 | 0.0 | 0 |
| missing_observations.csv | row_count | 2 | 2 | 0 |
| missing_observations.csv | is_valid_sum | 0 | 0 | 0 |
| missing_observations.csv | valid_code_counts | {94: 2} | {94: 2} | match |
| no_data_links.csv | exists | True | True | 0 |
| no_data_links.csv | size_mb | 0.0 | 0.0 | 0 |
| no_data_links.csv | row_count | 0 | 0 | 0 |
| no_data_links.csv | is_valid_sum | 0 | 0 | 0 |
| link_report.csv | exists | True | True | 0 |
| link_report.csv | size_mb | 0.132 | 0.132 | 0 |
| link_report.csv | row_count | 2432 | 2432 | 0 |
| link_report.csv | link_report_sums | {'total_observations': 700414.0, 'successful_observations': 697334.0, 'failed_observations': 3080.0} | {'total_observations': 700414.0, 'successful_observations': 697334.0, 'failed_observations': 3080.0} | match |

## Shapefile Packages

Both runs produced the following ZIP artifacts:
- New Run (02_17_29_09): best_valid_observations.csv.zip, failed_observations_reference_shapefile.zip, failed_observations_shapefile.zip, link_report_shapefile.zip, missing_observations_shapefile.zip, no_data_links_shapefile.zip, validated_data.csv.zip
- Baseline (17_47_28_9): best_valid_observations.csv.zip, failed_observations_reference_shapefile.zip, failed_observations_shapefile.zip, link_report_shapefile.zip, missing_observations_shapefile.zip, no_data_links_shapefile.zip, validated_data.csv.zip

✅ All metrics and validation outputs match exactly between the two runs.