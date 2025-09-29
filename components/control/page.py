"""
Dataset Control and Reporting page for the Google Maps Link Monitoring system.
This module provides the Streamlit UI for validating Google Maps polyline data against reference shapefiles.
"""

import streamlit as st
import pandas as pd
import geopandas as gpd
from pathlib import Path
import tempfile
import os
import shutil
import zipfile
import gc
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import suppress

# Import validation modules from the same component
from .validator import validate_dataframe_batch, validate_dataframe_batch_parallel, ValidationParameters
from .report import (
    generate_link_report,
    write_shapefile_with_results,
    create_failed_observations_reference_shapefile,
    extract_failed_observations,
    extract_best_valid_observations,
    extract_missing_observations,
    extract_no_data_links,
    create_failed_observations_shapefile,
    create_csv_matching_shapefile,
    _parse_timestamp_series,
    calculate_expected_observations,
)
from components.processing.pipeline import resolve_hebrew_encoding
from utils.icons import render_title_with_icon, render_subheader_with_icon, render_icon_text, get_icon_for_component

try:
    import chardet  # type: ignore[import]
    HAS_CHARDET = True
except ImportError:  # pragma: no cover - optional dependency
    HAS_CHARDET = False
    chardet = None  # type: ignore[assignment]


def control_page():
    """Dataset Control and Reporting page"""
    render_title_with_icon('dataset_control', 'Dataset Control and Reporting')
    st.markdown("Validate Google Maps polyline data against reference shapefiles using geometric similarity metrics")

    # Main layout
    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("Configuration")

        # Initialize session state for parameter persistence
        if 'control_params' not in st.session_state:
            st.session_state.control_params = {
                # Test Selection (default: only Hausdorff)
                'use_hausdorff': True,
                'use_length_check': False,
                'use_coverage_check': False,

                # Hausdorff parameters
                'hausdorff_threshold': 5.0,

                # Length check parameters
                'length_check_mode': 'ratio',
                'length_ratio_min': 0.90,
                'length_ratio_max': 1.10,
                'epsilon_length': 0.5,
                'min_link_length': 20.0,

                # Coverage parameters
                'coverage_min': 0.85,
                'coverage_spacing': 1.0,

                # System parameters
                'polyline_precision': 5,
                'crs_metric': 'EPSG:2039',

                # Data completeness parameters
                'enable_completeness_analysis': False,
                'completeness_interval_minutes': 15,
                'completeness_start_date': None,
                'completeness_end_date': None
            }

        # File Input Section
        render_subheader_with_icon('file_input', 'File Input')

        # CSV file upload
        csv_file = st.file_uploader(
            "Upload CSV file with Google Maps polyline data",
            type=['csv'],
            help="CSV file with columns: Name, Polyline, RouteAlternative, Timestamp, etc."
        )

        # Shapefile upload
        st.markdown("**Reference Shapefile Upload**")
        st.info("**How to upload shapefiles:**\n"
               "- **Option 1 (Recommended)**: Create a ZIP file containing all shapefile components (.shp, .shx, .dbf, .prj) with the same base name\n"
               "- **Option 2**: Upload individual .shp file (may work if companion files have standard names)\n\n"
               "**To create ZIP from folder**: Select all shapefile files (same base name, different extensions) → Right-click → 'Send to compressed folder' (Windows) or 'Compress' (Mac)")

        shapefile_file = st.file_uploader(
            "Choose shapefile (.shp) or ZIP package",
            type=['shp', 'zip'],
            help="Upload either a ZIP containing all shapefile components or an individual .shp file. ZIP format is recommended for complete compatibility."
        )

        # Output directory
        raw_output_dir = st.text_input(
            "Output directory",
            value="./output/control",
            help="Directory where validation results and reports will be saved"
        )

        output_dir_path = Path(raw_output_dir).expanduser()
        if not output_dir_path.is_absolute():
            output_dir_path = Path.cwd() / output_dir_path

        try:
            output_dir_path = output_dir_path.resolve()
        except OSError as exc:
            st.error(f"Unable to access output directory: {exc}")
            return

        workspace_root = Path.cwd().resolve()
        if not str(output_dir_path).startswith(str(workspace_root)):
            st.warning("Output directory adjusted to workspace for safety")
            output_dir_path = workspace_root / "output" / "control"

        output_dir = str(output_dir_path)

        # Validation Parameters Section
        render_subheader_with_icon('validation', 'Validation Parameters')

        # Test Selection Section
        render_icon_text('target', 'Select Validation Tests (tested in order)')
        test_col1, test_col2, test_col3 = st.columns(3)

        with test_col1:
            render_icon_text('shield-check', 'Hausdorff Distance')
            use_hausdorff = st.checkbox(
                "Enable Hausdorff Distance Test",
                value=st.session_state.control_params['use_hausdorff'],
                help="Test geometric similarity between routes",
                key="use_hausdorff_input"
            )
            st.session_state.control_params['use_hausdorff'] = use_hausdorff

        with test_col2:
            render_icon_text('ruler', 'Length Check')
            use_length_check = st.checkbox(
                "Enable Length Check Test",
                value=st.session_state.control_params['use_length_check'],
                help="Compare route lengths",
                key="use_length_check_input"
            )
            st.session_state.control_params['use_length_check'] = use_length_check

        with test_col3:
            render_icon_text('map', 'Coverage Analysis')
            use_coverage_check = st.checkbox(
                "Enable Coverage Analysis",
                value=st.session_state.control_params['use_coverage_check'],
                help="Check how much of reference route is covered",
                key="use_coverage_check_input"
            )
            st.session_state.control_params['use_coverage_check'] = use_coverage_check

            if use_coverage_check:
                st.warning("Coverage analysis is computationally intensive and may take several minutes for large datasets.")

        # Parameter Details Sections
        col_param1, col_param2 = st.columns(2)

        with col_param1:
            # Hausdorff Parameters
            if use_hausdorff:
                render_icon_text('shield-check', 'Hausdorff Distance Settings')
                hausdorff_threshold = st.number_input(
                    "Hausdorff threshold (meters)",
                    min_value=0.1,
                    max_value=1000.0,
                    value=st.session_state.control_params['hausdorff_threshold'],
                    step=0.5,
                    help="Maximum Hausdorff distance for geometry match",
                    key="hausdorff_threshold_input"
                )
                st.session_state.control_params['hausdorff_threshold'] = hausdorff_threshold

            # Length Check Parameters
            if use_length_check:
                render_icon_text('ruler', 'Length Check Settings')
                try:
                    mode_index = ["ratio", "exact"].index(st.session_state.control_params['length_check_mode'])
                except (ValueError, KeyError):
                    mode_index = 0  # Default to "ratio"

                length_check_mode = st.selectbox(
                    "Length check mode",
                    options=["ratio", "exact"],
                    index=mode_index,
                    help="How to compare polyline and reference lengths",
                    key="length_check_mode_input"
                )
                st.session_state.control_params['length_check_mode'] = length_check_mode

                if length_check_mode == "ratio":
                    length_ratio_min = st.number_input(
                        "Minimum length ratio",
                        min_value=0.1,
                        max_value=2.0,
                        value=st.session_state.control_params['length_ratio_min'],
                        step=0.05,
                        key="length_ratio_min_input"
                    )
                    st.session_state.control_params['length_ratio_min'] = length_ratio_min

                    length_ratio_max = st.number_input(
                        "Maximum length ratio",
                        min_value=0.1,
                        max_value=2.0,
                        value=st.session_state.control_params['length_ratio_max'],
                        step=0.05,
                        key="length_ratio_max_input"
                    )
                    st.session_state.control_params['length_ratio_max'] = length_ratio_max

                    # Set epsilon_length from session state for ratio mode
                    epsilon_length = st.session_state.control_params['epsilon_length']

                elif length_check_mode == "exact":
                    epsilon_length = st.number_input(
                        "Length tolerance (meters)",
                        min_value=0.1,
                        max_value=100.0,
                        value=st.session_state.control_params['epsilon_length'],
                        step=0.1,
                        key="epsilon_length_input"
                    )
                    st.session_state.control_params['epsilon_length'] = epsilon_length

                    # Set ratio parameters from session state for exact mode
                    length_ratio_min = st.session_state.control_params['length_ratio_min']
                    length_ratio_max = st.session_state.control_params['length_ratio_max']

                min_link_length = st.number_input(
                    "Minimum link length (meters)",
                    min_value=1.0,
                    max_value=1000.0,
                    value=st.session_state.control_params['min_link_length'],
                    step=5.0,
                    help="Skip length check for links shorter than this",
                    key="min_link_length_input"
                )
                st.session_state.control_params['min_link_length'] = min_link_length

        with col_param2:
            # Coverage Parameters
            if use_coverage_check:
                render_icon_text('map', 'Coverage Analysis Settings')
                coverage_min = st.number_input(
                    "Minimum coverage",
                    min_value=0.1,
                    max_value=1.0,
                    value=st.session_state.control_params['coverage_min'],
                    step=0.05,
                    help="Minimum coverage fraction required for match",
                    key="coverage_min_input"
                )
                st.session_state.control_params['coverage_min'] = coverage_min

                coverage_spacing = st.number_input(
                    "Coverage spacing (meters)",
                    min_value=0.1,
                    max_value=10.0,
                    value=st.session_state.control_params['coverage_spacing'],
                    step=0.1,
                    help="Point spacing for coverage calculation",
                    key="coverage_spacing_input"
                )
                st.session_state.control_params['coverage_spacing'] = coverage_spacing

            # System Settings
            render_icon_text('gear', 'System Settings')
            polyline_precision = st.number_input(
                "Polyline precision",
                min_value=1,
                max_value=10,
                value=st.session_state.control_params['polyline_precision'],
                help="Google Maps polyline encoding precision",
                key="polyline_precision_input"
            )
            st.session_state.control_params['polyline_precision'] = polyline_precision

            # Performance Settings
            render_icon_text('activity', 'Performance Settings')
            enable_parallel = st.checkbox(
                "Enable parallel processing",
                value=st.session_state.control_params.get('enable_parallel', True),
                help="Use multiple CPU cores for faster validation. "
                     "Recommended for datasets over 5000 rows. "
                     "Disable for debugging or memory-constrained systems.",
                key="enable_parallel_input"
            )
            st.session_state.control_params['enable_parallel'] = enable_parallel

            if enable_parallel:
                cpu_count = os.cpu_count() or 1
                max_workers = st.slider(
                    "CPU cores to use",
                    min_value=1,
                    max_value=cpu_count,
                    value=min(4, cpu_count),
                    help=f"System has {cpu_count} CPU cores available. "
                         f"More cores = faster processing but higher memory usage.",
                    key="max_workers_input"
                )
                st.session_state.control_params['max_workers'] = max_workers
            else:
                st.session_state.control_params['max_workers'] = 1

        # Set default values for disabled parameters
        if not use_hausdorff:
            hausdorff_threshold = st.session_state.control_params['hausdorff_threshold']
        if not use_length_check:
            length_check_mode = st.session_state.control_params['length_check_mode']
            length_ratio_min = st.session_state.control_params['length_ratio_min']
            length_ratio_max = st.session_state.control_params['length_ratio_max']
            epsilon_length = st.session_state.control_params['epsilon_length']
            min_link_length = st.session_state.control_params['min_link_length']
        if not use_coverage_check:
            coverage_min = st.session_state.control_params['coverage_min']
            coverage_spacing = st.session_state.control_params['coverage_spacing']

        # Date Filtering Section
        render_subheader_with_icon('calendar', 'Date Filtering (Optional)')

        use_date_filter = st.checkbox("Enable date filtering", value=False)

        # Initialize date_filter_params
        date_filter_params = None

        if use_date_filter:
            filter_mode = st.radio(
                "Filter mode",
                options=["Date range", "Specific day"],
                index=0
            )

            if filter_mode == "Date range":
                col_start, col_end = st.columns(2)
                with col_start:
                    start_date = st.date_input("Start date")
                with col_end:
                    end_date = st.date_input("End date")

                # Build explicit date filter params
                date_filter_params = {
                    'filter_mode': 'Date range',
                    'start_date': start_date,
                    'end_date': end_date
                }
            else:
                specific_day = st.date_input("Specific day")

                # Build explicit date filter params
                date_filter_params = {
                    'filter_mode': 'Specific day',
                    'specific_day': specific_day
                }

        # Data Completeness Analysis Section
        render_subheader_with_icon('analysis', 'Data Completeness Analysis (Optional)')

        enable_completeness = st.checkbox(
            "Enable data completeness analysis",
            value=st.session_state.control_params['enable_completeness_analysis'],
            help="Analyze missing timestamps based on expected recording schedule"
        )
        st.session_state.control_params['enable_completeness_analysis'] = enable_completeness

        if enable_completeness:
            col_interval, col_dates = st.columns([1, 2])

            with col_interval:
                options = [5, 10, 15, 30, 60]
                current_value = st.session_state.control_params['completeness_interval_minutes']
                try:
                    current_index = options.index(current_value)
                except ValueError:
                    current_index = 2  # Default to 15 minutes if current value not found

                interval_minutes = st.selectbox(
                    "Recording interval",
                    options=options,
                    index=current_index,
                    help="Expected minutes between observations"
                )
                st.session_state.control_params['completeness_interval_minutes'] = interval_minutes

            with col_dates:
                st.markdown("**Analysis Period (Auto-detected from CSV):**")

                # Auto-detect dates from uploaded CSV
                if csv_file is not None:
                    auto_start, auto_end, total_records = detect_date_range_from_csv(csv_file)

                    if auto_start and auto_end:
                        # Update session state with auto-detected dates
                        st.session_state.control_params['completeness_start_date'] = auto_start
                        st.session_state.control_params['completeness_end_date'] = auto_end

                        # Show detected range
                        st.info(f"**Auto-detected from {total_records:,} records:**\n"
                               f"**Period:** {auto_start.strftime('%Y-%m-%d')} to {auto_end.strftime('%Y-%m-%d')}\n"
                               f"**Duration:** {(auto_end - auto_start).days + 1} days")

                        start_date_comp = auto_start
                        end_date_comp = auto_end

                    else:
                        st.warning("Could not auto-detect dates from CSV. Please ensure your CSV has a 'Timestamp' column with valid dates.")

                        # Fallback to manual input
                        col_start_date, col_end_date = st.columns(2)

                        with col_start_date:
                            start_date_comp = st.date_input(
                                "Start date (manual)",
                                value=st.session_state.control_params['completeness_start_date'],
                                key="completeness_start_date_manual"
                            )
                            st.session_state.control_params['completeness_start_date'] = start_date_comp

                        with col_end_date:
                            end_date_comp = st.date_input(
                                "End date (manual)",
                                value=st.session_state.control_params['completeness_end_date'],
                                key="completeness_end_date_manual"
                            )
                            st.session_state.control_params['completeness_end_date'] = end_date_comp
                else:
                    st.info("Upload a CSV file to auto-detect the analysis period")
                    start_date_comp = st.session_state.control_params['completeness_start_date']
                    end_date_comp = st.session_state.control_params['completeness_end_date']

            if start_date_comp and end_date_comp:
                if start_date_comp > end_date_comp:
                    st.error("Start date must be before or equal to end date")
                else:
                    # Calculate and show expected observations (use same logic as report)
                    expected_observations = calculate_expected_observations(
                        start_date_comp, end_date_comp, interval_minutes
                    )

                    st.info(f"Expected observations per link: **{expected_observations:,}** "
                           f"({interval_minutes} min intervals, 24/7 from {start_date_comp} to {end_date_comp})")

        # Advanced Options
        with st.expander("Advanced Options", expanded=False):
            crs_metric = st.text_input(
                "Metric CRS",
                value=st.session_state.control_params['crs_metric'],
                help="Coordinate reference system for metric calculations",
                key="crs_metric_input"
            )
            st.session_state.control_params['crs_metric'] = crs_metric

            show_validation_details = st.checkbox(
                "Show validation details",
                value=False,
                help="Display detailed validation results for debugging"
            )

            generate_shapefile = st.checkbox(
                "Generate result shapefile",
                value=True,
                help="Create shapefile with validation results - shows your original shapefile with validation results added"
            )

    with col2:
        st.header("Validation")

        # Check if required files are uploaded
        can_validate = (csv_file is not None and shapefile_file is not None)

        if st.button("🚀 Run Validation", disabled=not can_validate, use_container_width=True):
            if can_validate:
                # Get completeness parameters
                completeness_params = None
                if st.session_state.control_params['enable_completeness_analysis']:
                    completeness_params = {
                        'interval_minutes': st.session_state.control_params['completeness_interval_minutes'],
                        'start_date': st.session_state.control_params['completeness_start_date'],
                        'end_date': st.session_state.control_params['completeness_end_date']
                    }

                run_control_validation(
                    csv_file, shapefile_file, output_dir,
                    use_hausdorff, hausdorff_threshold,
                    use_length_check, length_check_mode, length_ratio_min, length_ratio_max, epsilon_length, min_link_length,
                    use_coverage_check, coverage_min, coverage_spacing,
                    polyline_precision, st.session_state.control_params['crs_metric'],
                    use_date_filter, date_filter_params,
                    show_validation_details, generate_shapefile, completeness_params
                )
            else:
                st.error("Please upload both CSV and shapefile to run validation")

        if not can_validate:
            st.warning("Please upload both CSV file and reference shapefile")

        # Show file status
        if csv_file:
            st.success(f"✅ CSV: {csv_file.name}")
        else:
            st.info("📄 No CSV file uploaded")

        if shapefile_file:
            file_type = "ZIP" if shapefile_file.name.lower().endswith('.zip') else "SHP"
            st.success(f"✅ Shapefile ({file_type}): {shapefile_file.name}")
        else:
            st.info("🗺️ No shapefile uploaded (.shp or .zip)")

    # Results section will be added after validation runs
    if 'control_results' in st.session_state:
        display_control_results()


def run_control_validation(csv_file, shapefile_file, output_dir,
                          use_hausdorff, hausdorff_threshold,
                          use_length_check, length_check_mode, length_ratio_min, length_ratio_max, epsilon_length, min_link_length,
                          use_coverage_check, coverage_min, coverage_spacing,
                          polyline_precision, crs_metric, use_date_filter, date_filter_params,
                          show_validation_details, generate_shapefile, completeness_params=None):
    """Run the dataset control validation pipeline"""

    try:
        # Track timing for automatic logging
        from datetime import datetime
        start_time = datetime.now()

        # Show progress
        progress_bar = st.progress(0)
        status_text = st.empty()

        status_text.text("Preparing validation parameters...")
        progress_bar.progress(10)

        # Create validation parameters
        params = ValidationParameters(
            # Test selection
            use_hausdorff=use_hausdorff,
            use_length_check=use_length_check,
            use_coverage_check=use_coverage_check,

            # Hausdorff parameters
            hausdorff_threshold_m=hausdorff_threshold,

            # Length check parameters
            length_check_mode=length_check_mode,
            length_ratio_min=length_ratio_min,
            length_ratio_max=length_ratio_max,
            epsilon_length_m=epsilon_length,
            min_link_length_m=min_link_length,

            # Coverage parameters
            coverage_min=coverage_min,
            coverage_spacing_m=coverage_spacing,

            # System parameters
            crs_metric=crs_metric,
            polyline_precision=polyline_precision
        )

        status_text.text("Loading CSV data...")
        progress_bar.progress(20)

        # Load CSV data with proper encoding handling
        csv_df = load_csv_with_encoding(csv_file)

        # Check if CSV loading failed
        if csv_df is None:
            st.error("**CSV Loading Failed**")
            st.error("Could not read the uploaded CSV file with any supported encoding.")
            st.info("Please ensure your CSV file is properly formatted and uses a supported encoding (UTF-8, CP1255, etc.)")
            st.stop()

        # Fix Hebrew text encoding issues if needed
        csv_df = fix_hebrew_columns(csv_df)

        status_text.text("Loading shapefile...")
        progress_bar.progress(30)

        # Save and load shapefile
        try:
            temp_shp_path = save_shapefile_upload(shapefile_file)
            file_type = "ZIP" if shapefile_file.name.lower().endswith('.zip') else "SHP"
            st.success(f"{file_type} file processed successfully")
        except ValueError as e:
            st.error(f"Shapefile error: {e}")
            return
        except Exception as e:
            st.error(f"Unexpected error processing shapefile: {e}")
            return

        try:
            # Try to load shapefile with robust error handling
            shapefile_gdf = load_shapefile_robust(temp_shp_path)
            st.success(f"Loaded shapefile with {len(shapefile_gdf)} features")
        except Exception as e:
            st.error(f"Failed to load shapefile: {e}")
            cleanup_temp_shapefile(temp_shp_path)
            return

        status_text.text("Running validation...")
        progress_bar.progress(40)

        # Run batch validation with proper route alternative processing
        validation_msg = "Running batch validation with route alternative grouping..."
        if use_coverage_check:
            validation_msg += " (Coverage analysis enabled - this may take several minutes)"
        status_text.text(validation_msg)
        progress_bar.progress(50)

        # Use batch validation with progress tracking
        def progress_callback(message):
            status_text.text(f"Processing: {message}")

        # Choose parallel or sequential validation based on user settings
        enable_parallel = st.session_state.control_params.get('enable_parallel', True)
        max_workers = st.session_state.control_params.get('max_workers', 1)

        if enable_parallel and len(csv_df) >= 5000:
            status_text.text(f"Using parallel validation with {max_workers} CPU cores...")
            result_df = validate_dataframe_batch_parallel(
                csv_df, shapefile_gdf, params,
                max_workers=max_workers,
                progress_callback=progress_callback
            )
        else:
            if enable_parallel and len(csv_df) < 5000:
                status_text.text("Using sequential validation (dataset too small for parallel benefit)...")
            else:
                status_text.text("Using sequential validation...")
            result_df = validate_dataframe_batch(csv_df, shapefile_gdf, params, progress_callback=progress_callback)

        # Update progress
        progress_bar.progress(70)
        status_text.text("Batch validation completed with proper route alternative handling")

        # Track validation completion time
        validation_end_time = datetime.now()
        validation_time = (validation_end_time - start_time).total_seconds() / 60

        status_text.text("Generating link reports...")
        progress_bar.progress(80)

        # Prepare date filter if specified
        date_filter = None
        if use_date_filter and date_filter_params:
            if date_filter_params.get('filter_mode') == "Date range":
                date_filter = {
                    'start_date': date_filter_params.get('start_date'),
                    'end_date': date_filter_params.get('end_date')
                }
            else:
                date_filter = {
                    'specific_day': date_filter_params.get('specific_day')
                }

        # Generate link report
        report_gdf = generate_link_report(result_df, shapefile_gdf, date_filter, completeness_params)

        # Track report completion time
        report_end_time = datetime.now()
        report_time = (report_end_time - validation_end_time).total_seconds() / 60

        status_text.text("Saving results...")
        progress_bar.progress(90)

        # Create timestamped output directory
        from datetime import datetime
        timestamp = datetime.now().strftime("%d_%m_%y_%H_%M")
        timestamped_output_dir = Path(output_dir) / timestamp
        timestamped_output_dir.mkdir(parents=True, exist_ok=True)
        output_dir = str(timestamped_output_dir)

        # Save results
        output_files = save_validation_results(result_df, report_gdf, output_dir, generate_shapefile, completeness_params)

        # Create automatic performance and parameter log
        params_for_log = {
            'hausdorff_threshold_m': hausdorff_threshold,
            'use_hausdorff': use_hausdorff,
            'use_length_check': use_length_check,
            'use_coverage_check': use_coverage_check,
            'length_check_mode': length_check_mode,
            'length_ratio_min': length_ratio_min,
            'length_ratio_max': length_ratio_max,
            'coverage_min': coverage_min,
            'min_link_length_m': min_link_length,
            'crs_metric': crs_metric,
            'max_workers': max(1, min(8, os.cpu_count() or 1)) if len(csv_df) >= 5000 else 1,
            'chunk_size': len(csv_df)
        }

        log_file = create_performance_log(output_dir, start_time, validation_time, report_time, params_for_log)
        output_files['performance_log'] = log_file

        status_text.text("Validation completed!")
        progress_bar.progress(100)

        # Store results in session state
        st.session_state.control_results = {
            'validated_df': result_df,
            'report_gdf': report_gdf,
            'output_files': output_files,
            'params': params,
            'success': True,
            'error_message': None
        }

        # Clean up temporary shapefile
        cleanup_temp_shapefile(temp_shp_path)

        st.success("Validation completed successfully!")
        st.rerun()

    except Exception as e:
        st.error(f"Validation failed: {str(e)}")

        # Store error in session state
        st.session_state.control_results = {
            'validated_df': pd.DataFrame(),
            'report_gdf': gpd.GeoDataFrame(),
            'output_files': {},
            'params': None,
            'success': False,
            'error_message': str(e)
        }

        # Clean up temporary shapefile on error
        try:
            if 'temp_shp_path' in locals():
                cleanup_temp_shapefile(temp_shp_path)
        except:
            pass  # Ignore cleanup errors


LARGE_DOWNLOAD_THRESHOLD_MB = 64


def _maybe_add_zip_download(file_path: Path, key: str, output_files: dict, threshold_mb: int = LARGE_DOWNLOAD_THRESHOLD_MB) -> None:
    """Create a compressed copy when the payload is too large for in-browser downloads."""
    size_mb = file_path.stat().st_size / (1024 * 1024)
    if size_mb <= threshold_mb:
        return
    zip_path = file_path.with_suffix(file_path.suffix + '.zip')
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zip_file:
        zip_file.write(file_path, arcname=file_path.name)
    output_files[f"{key}_zip"] = str(zip_path)


def save_validation_results(result_df, report_gdf, output_dir, generate_shapefile, completeness_params=None,
                           progress_callback=None, status_callback=None):
    """Save validation results to files with progress tracking."""
    output_files: dict[str, str] = {}

    total_files = 0
    completed_files = 0

    def update_progress():
        nonlocal completed_files
        completed_files += 1
        if progress_callback and total_files > 0:
            progress_pct = int((completed_files / total_files) * 100)
            progress_callback(90 + (progress_pct * 10 // 100))

    validated_csv_path = Path(output_dir) / "validated_data.csv"

    name_col = 'Name' if 'Name' in result_df.columns else ('name' if 'name' in result_df.columns else None)
    timestamp_col = 'Timestamp' if 'Timestamp' in result_df.columns else ('timestamp' if 'timestamp' in result_df.columns else None)
    requested_time_col = 'RequestedTime' if 'RequestedTime' in result_df.columns else ('requested_time' if 'requested_time' in result_df.columns else None)

    if name_col and timestamp_col:
        result_df_sorted = result_df.sort_values([name_col, timestamp_col])
    elif name_col and requested_time_col:
        result_df_sorted = result_df.sort_values([name_col, requested_time_col])
    elif name_col:
        result_df_sorted = result_df.sort_values([name_col])
    else:
        result_df_sorted = result_df

    cpu_count = os.cpu_count() or 1
    max_workers = min(8, max(2, cpu_count))

    def _write_csv(dataframe, destination, columns=None, file_description=None):
        destination = Path(destination)
        if not dataframe.empty:
            sample_size = min(1000, len(dataframe))
            sample_df = dataframe.head(sample_size)
            sample_csv = sample_df.to_csv(index=False, columns=columns, float_format='%.6g')
            avg_row_size = len(sample_csv.encode('utf-8')) / sample_size
            size_mb = (avg_row_size * len(dataframe)) / (1024 * 1024)
        else:
            size_mb = 0.1

        if status_callback and file_description:
            status_callback(f"💾 Saving {file_description} ({size_mb:.1f}MB estimated)...")

        if not dataframe.empty:
            for col in dataframe.select_dtypes(include=['category']):
                dataframe[col] = dataframe[col].astype(str)
            for col in dataframe.select_dtypes(include=['int64']):
                if dataframe[col].min() >= 0 and dataframe[col].max() <= 2**31 - 1:
                    dataframe[col] = dataframe[col].astype('int32')
            for col in dataframe.select_dtypes(include=['float64']):
                if dataframe[col].notna().any():
                    max_val = dataframe[col].abs().max()
                    if max_val <= 3.4e+38:
                        dataframe[col] = dataframe[col].astype('float32')

        dataframe.to_csv(
            destination,
            index=False,
            encoding='utf-8-sig',
            columns=columns,
            lineterminator='\n',
            float_format='%.6g'
        )

        actual_size_mb = destination.stat().st_size / (1024 * 1024)
        if status_callback and file_description:
            status_callback(f"✅ Saved {file_description} ({actual_size_mb:.1f}MB)")

        return str(destination)

    best_valid_df = extract_best_valid_observations(result_df_sorted)

    validation_failed_df = extract_failed_observations(result_df_sorted)
    if not validation_failed_df.empty:
        validation_failed_df = validation_failed_df[
            validation_failed_df.get('valid_code', 0).between(1, 3)
        ].copy()

    missing_observations_df = pd.DataFrame()
    if completeness_params:
        missing_observations_df = extract_missing_observations(result_df_sorted, completeness_params, report_gdf)

    no_data_links_df = extract_no_data_links(result_df_sorted, report_gdf)
    report_with_stats_gdf = report_gdf.copy()

    drop_for_csv = {
        'geometry',
        'single_alt_timestamps',
        'multi_alt_timestamps',
        'result_code',
        'result_label',
        'num',
        'total_timestamps',
        'successful_timestamps',
        'failed_timestamps',
        'success_rate',
    }

    metric_order = [
        'perfect_match_percent',
        'threshold_pass_percent',
        'failed_percent',
        'total_success_rate',
        'total_observations',
        'successful_observations',
        'failed_observations',
        'total_routes',
        'single_route_observations',
        'multi_route_observations',
        'expected_observations',
        'missing_observations',
        'data_coverage_percent',
    ]
    metric_set = set(metric_order)

    base_cols = [
        col for col in report_with_stats_gdf.columns
        if col not in metric_set and col not in drop_for_csv
    ]
    ordered_cols = []
    for ident in ('From', 'To'):
        if ident in base_cols:
            ordered_cols.append(ident)
            base_cols.remove(ident)
    ordered_cols.extend([
        col for col in metric_order
        if col in report_with_stats_gdf.columns and col not in drop_for_csv
    ])
    ordered_cols.extend([col for col in base_cols if col not in ordered_cols])

    best_csv_path = Path(output_dir) / "best_valid_observations.csv"
    failed_csv_path = Path(output_dir) / "failed_observations.csv"
    missing_csv_path = Path(output_dir) / "missing_observations.csv"
    no_data_csv_path = Path(output_dir) / "no_data_links.csv"
    report_csv_path = Path(output_dir) / "link_report.csv"

    csv_jobs = [
        ('validated_csv', result_df_sorted, validated_csv_path, 'validated_data.csv', None),
        ('best_valid_observations_csv', best_valid_df, best_csv_path, 'best_valid_observations.csv', None),
        ('no_data_links_csv', no_data_links_df, no_data_csv_path, 'no_data_links.csv', None),
        ('link_report_csv', report_with_stats_gdf, report_csv_path, 'link_report.csv', ordered_cols),
    ]

    if not validation_failed_df.empty:
        csv_jobs.append(('failed_observations_csv', validation_failed_df, failed_csv_path, 'failed_observations.csv', None))

    if completeness_params:
        csv_jobs.append(('missing_observations_csv', missing_observations_df, missing_csv_path, 'missing_observations.csv', None))

    total_files = len(csv_jobs)

    if generate_shapefile:
        shapefile_steps = 2  # link report create + zip
        if not validation_failed_df.empty:
            shapefile_steps += 3  # failed create + zip + reference zip
        if completeness_params and not missing_observations_df.empty:
            shapefile_steps += 2  # missing create + zip
        shapefile_steps += 2  # no-data create + zip
        total_files += shapefile_steps

    total_files = max(total_files, 1)

    future_to_job: dict = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        def submit_csv(key, dataframe, destination, description, columns=None):
            future = executor.submit(_write_csv, dataframe, destination, columns, description)
            future_to_job[future] = (key, description)

        for key, dataframe, destination, description, columns in csv_jobs:
            submit_csv(key, dataframe, destination, description, columns)

        for future in as_completed(tuple(future_to_job.keys())):
            key, description = future_to_job.pop(future)
            path_str = future.result()
            path_obj = Path(path_str)
            output_files[key] = path_str
            _maybe_add_zip_download(path_obj, key, output_files)
            update_progress()
            if status_callback:
                status_callback(f"✅ Completed {description} ({completed_files}/{total_files})")

    if generate_shapefile:
        zip_compresslevel = 3

        if status_callback:
            status_callback("🗺️ Creating link report shapefile...")

        report_shp_path = Path(output_dir) / "link_report.shp"
        try:
            write_shapefile_with_results(report_with_stats_gdf, str(report_shp_path))
            update_progress()
            if status_callback:
                file_size_mb = report_shp_path.stat().st_size / (1024 * 1024)
                status_callback(f"✅ Created link report shapefile ({file_size_mb:.1f}MB)")
        except Exception as e:
            print(f"Warning: Failed to create link report shapefile: {e}")
            if status_callback:
                status_callback(f"❌ Failed to create link report shapefile: {e}")
        else:
            shapefile_zip_path = create_shapefile_zip_package(str(report_shp_path), output_dir, compresslevel=zip_compresslevel)
            output_files['link_report_zip'] = str(shapefile_zip_path)
            update_progress()
            if status_callback:
                zip_size_mb = Path(shapefile_zip_path).stat().st_size / (1024 * 1024)
                status_callback(f"✅ Packaged link report shapefile ({zip_size_mb:.1f}MB)")

        if not validation_failed_df.empty:
            if status_callback:
                status_callback("🗺️ Creating failed observations shapefile...")

            failed_shp_path = Path(output_dir) / "failed_observations.shp"
            try:
                create_failed_observations_shapefile(
                    validation_failed_df,
                    report_gdf,
                    str(failed_shp_path)
                )
                update_progress()
                if status_callback:
                    file_size_mb = failed_shp_path.stat().st_size / (1024 * 1024)
                    status_callback(f"✅ Created failed observations shapefile ({file_size_mb:.1f}MB)")

                failed_shapefile_zip_path = create_shapefile_zip_package(str(failed_shp_path), output_dir, compresslevel=zip_compresslevel)
                output_files['failed_observations_zip'] = str(failed_shapefile_zip_path)
                update_progress()
                if status_callback:
                    zip_size_mb = Path(failed_shapefile_zip_path).stat().st_size / (1024 * 1024)
                    status_callback(f"✅ Packaged failed observations shapefile ({zip_size_mb:.1f}MB)")
            except Exception as e:
                print(f"Warning: Failed to create failed observations shapefile: {e}")
                if status_callback:
                    status_callback(f"❌ Failed to create failed observations shapefile: {e}")
                try:
                    failed_shp_path.unlink(missing_ok=True)
                except Exception:
                    pass

            failed_ref_shp_path = Path(output_dir) / "failed_observations_reference.shp"
            try:
                create_failed_observations_reference_shapefile(
                    validation_failed_df,
                    report_gdf,
                    str(failed_ref_shp_path)
                )
                failed_ref_shapefile_zip_path = create_shapefile_zip_package(str(failed_ref_shp_path), output_dir, compresslevel=zip_compresslevel)
                output_files['failed_observations_reference_zip'] = str(failed_ref_shapefile_zip_path)
            except Exception as e:
                print(f"Warning: Failed to create failed observations reference shapefile: {e}")

        if completeness_params and not missing_observations_df.empty:
            missing_shp_path = Path(output_dir) / "missing_observations.shp"
            try:
                create_csv_matching_shapefile(
                    missing_observations_df,
                    report_gdf,
                    str(missing_shp_path),
                    geometry_source='shapefile'
                )
                missing_shapefile_zip_path = create_shapefile_zip_package(str(missing_shp_path), output_dir, compresslevel=zip_compresslevel)
                output_files['missing_observations_zip'] = str(missing_shapefile_zip_path)
                update_progress()
            except Exception as e:
                print(f"Warning: Failed to create missing observations shapefile: {e}")

        no_data_shp_path = Path(output_dir) / "no_data_links.shp"
        try:
            if not no_data_links_df.empty:
                create_csv_matching_shapefile(
                    no_data_links_df,
                    report_gdf,
                    str(no_data_shp_path),
                    geometry_source='shapefile'
                )
            else:
                empty_gdf = gpd.GeoDataFrame(columns=['link_id', 'Name', 'is_valid', 'valid_code'], geometry=[])
                empty_gdf.crs = report_gdf.crs
                empty_gdf.to_file(str(no_data_shp_path))
            no_data_shapefile_zip_path = create_shapefile_zip_package(str(no_data_shp_path), output_dir, compresslevel=zip_compresslevel)
            output_files['no_data_links_zip'] = str(no_data_shapefile_zip_path)
            update_progress()
        except Exception as e:
            print(f"Warning: Failed to create no-data links shapefile: {e}")

    del best_valid_df
    del missing_observations_df
    del no_data_links_df
    del report_with_stats_gdf
    if 'validation_failed_df' in locals():
        del validation_failed_df
    gc.collect()

    return output_files

def create_performance_log(output_dir, start_time, validation_time, report_time, params):
    """Create performance and parameter log file"""
    from datetime import datetime
    import os

    log_path = Path(output_dir) / "performance_and_parameters_log.txt"

    # Calculate timings
    current_time = datetime.now()
    total_time = (current_time - start_time).total_seconds() / 60  # minutes

    log_content = f"""CONTROL VALIDATION PERFORMANCE & PARAMETERS LOG
========================================================
Run Date: {start_time.strftime('%Y-%m-%d')}
Start Time: {start_time.strftime('%H:%M:%S')}
End Time: {current_time.strftime('%H:%M:%S')}
System: {os.cpu_count()} CPU cores

TIMING BREAKDOWN:
================
Validation Time: {validation_time:.1f} minutes
Report Generation: {report_time:.1f} minutes
Total Processing: {total_time:.1f} minutes

VALIDATION PARAMETERS:
=====================
Hausdorff Threshold: {params.get('hausdorff_threshold_m', 'N/A')}m
Use Hausdorff: {params.get('use_hausdorff', 'N/A')}
Use Length Check: {params.get('use_length_check', 'N/A')}
Use Coverage Check: {params.get('use_coverage_check', 'N/A')}
Length Check Mode: {params.get('length_check_mode', 'N/A')}
Length Ratio Range: {params.get('length_ratio_min', 'N/A')}-{params.get('length_ratio_max', 'N/A')}
Coverage Minimum: {params.get('coverage_min', 'N/A')}
Minimum Link Length: {params.get('min_link_length_m', 'N/A')}m
Metric CRS: {params.get('crs_metric', 'N/A')}

PROCESSING DETAILS:
==================
Parallel Processing: {'Yes' if params.get('max_workers', 1) > 1 else 'No'}
Max Workers: {params.get('max_workers', 1)}
Chunk Size: {params.get('chunk_size', 'N/A')}

OUTPUT FILES:
============
Generated at: {output_dir}
"""

    with open(log_path, 'w', encoding='utf-8') as f:
        f.write(log_content)

    return str(log_path)

    # Count total files to be created
    file_operations = [
        ('validated_csv', result_df_sorted, validated_csv_path, 'validated_data.csv'),
    ]

    # Add conditional files to count
    best_valid_df = extract_best_valid_observations(result_df_sorted)
    if not best_valid_df.empty:
        file_operations.append(('best_valid_observations_csv', best_valid_df,
                               Path(output_dir) / "best_valid_observations.csv", 'best_valid_observations.csv'))

    validation_failed_df = extract_failed_observations(result_df_sorted)
    if not validation_failed_df.empty:
        validation_failed_df = validation_failed_df[
            validation_failed_df.get('valid_code', 0).between(1, 3)
        ].copy()
        if not validation_failed_df.empty:
            file_operations.append(('failed_observations_csv', validation_failed_df,
                                   Path(output_dir) / "failed_observations.csv", 'failed_observations.csv'))

    total_files = len(file_operations) + (6 if generate_shapefile else 0)  # Estimate shapefiles

    future_to_job = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        def submit_csv(key, dataframe, destination, description, columns=None):
            future = executor.submit(_write_csv, dataframe, destination, columns, description)
            future_to_job[future] = (key, description)

        submit_csv('validated_csv', result_df_sorted, validated_csv_path, 'validated_data.csv')

        # Extract best valid observations
        best_valid_df = extract_best_valid_observations(result_df_sorted)
        best_csv_path = Path(output_dir) / "best_valid_observations.csv"
        submit_csv('best_valid_observations_csv', best_valid_df, best_csv_path, 'best_valid_observations.csv')

        # FAILED OBSERVATIONS
        validation_failed_df = extract_failed_observations(result_df_sorted)
        if not validation_failed_df.empty:
            validation_failed_df = validation_failed_df[
                validation_failed_df.get('valid_code', 0).between(1, 3)
            ].copy()
            failed_csv_path = Path(output_dir) / "failed_observations.csv"
            submit_csv('failed_observations_csv', validation_failed_df, failed_csv_path, 'failed_observations.csv')
        else:
            failed_csv_path = None

        # MISSING OBSERVATIONS
        missing_observations_df = pd.DataFrame()
        if completeness_params:
            missing_observations_df = extract_missing_observations(result_df_sorted, completeness_params, report_gdf)
            missing_csv_path = Path(output_dir) / "missing_observations.csv"
            submit_csv('missing_observations_csv', missing_observations_df, missing_csv_path, 'missing_observations.csv')
        else:
            missing_csv_path = None

        # NO-DATA LINKS
        no_data_links_df = extract_no_data_links(result_df_sorted, report_gdf)
        no_data_csv_path = Path(output_dir) / "no_data_links.csv"
        submit_csv('no_data_links_csv', no_data_links_df, no_data_csv_path, 'no_data_links.csv')

        # Generate link report with statistics
        report_with_stats_gdf = report_gdf.copy()

        report_csv_path = Path(output_dir) / "link_report.csv"
        drop_for_csv = {
            'geometry',
            'single_alt_timestamps',
            'multi_alt_timestamps',
            'result_code',
            'result_label',
            'num',
            'total_timestamps',
            'successful_timestamps',
            'failed_timestamps',
            'success_rate',
        }

        metric_order = [
            'perfect_match_percent',
            'threshold_pass_percent',
            'failed_percent',
            'total_success_rate',
            'total_observations',
            'successful_observations',
            'failed_observations',
            'total_routes',
            'single_route_observations',
            'multi_route_observations',
            'expected_observations',
            'missing_observations',
            'data_coverage_percent',
        ]
        metric_set = set(metric_order)

        base_cols = [
            col for col in report_with_stats_gdf.columns
            if col not in metric_set and col not in drop_for_csv
        ]
        ordered_cols = []
        for ident in ('From', 'To'):
            if ident in base_cols:
                ordered_cols.append(ident)
                base_cols.remove(ident)
        ordered_cols.extend([
            col for col in metric_order
            if col in report_with_stats_gdf.columns and col not in drop_for_csv
        ])
        ordered_cols.extend([col for col in base_cols if col not in ordered_cols])

        submit_csv('link_report_csv', report_with_stats_gdf, report_csv_path, 'link_report.csv', columns=ordered_cols)

        # Wait for CSV jobs and register outputs
        for future in as_completed(tuple(future_to_job.keys())):
            key, description = future_to_job.pop(future)
            path_str = future.result()
            path_obj = Path(path_str)
            output_files[key] = path_str
            _maybe_add_zip_download(path_obj, key, output_files)
            update_progress()
            if status_callback:
                status_callback(f"Completed {description} ({completed_files}/{total_files})")

    # Generate shapefiles when requested
    if generate_shapefile:
        if status_callback:
            status_callback(f"Creating link report shapefile...")

        report_shp_path = Path(output_dir) / "link_report.shp"
        try:
            write_shapefile_with_results(report_with_stats_gdf, str(report_shp_path))
            update_progress()
            if status_callback:
                file_size_mb = report_shp_path.stat().st_size / (1024 * 1024)
                status_callback(f"Created link report shapefile ({file_size_mb:.1f}MB)")
        except Exception as e:
            print(f"Warning: Failed to create link report shapefile: {e}")
            if status_callback:
                status_callback(f"Failed to create link report shapefile: {e}")

        if status_callback:
            status_callback(f"📦 Packaging link report shapefile...")
        shapefile_zip_path = create_shapefile_zip_package(str(report_shp_path), output_dir)
        output_files['link_report_zip'] = str(shapefile_zip_path)
        update_progress()
        if status_callback:
            zip_size_mb = Path(shapefile_zip_path).stat().st_size / (1024 * 1024)
            status_callback(f"Packaged link report shapefile ({zip_size_mb:.1f}MB)")

        if not validation_failed_df.empty:
            if status_callback:
                status_callback(f"Creating failed observations shapefile...")

            failed_shp_path = Path(output_dir) / "failed_observations.shp"
            try:
                create_failed_observations_shapefile(
                    validation_failed_df,
                    report_gdf,
                    str(failed_shp_path)
                )
                update_progress()
                if status_callback:
                    file_size_mb = failed_shp_path.stat().st_size / (1024 * 1024)
                    status_callback(f"Created failed observations shapefile ({file_size_mb:.1f}MB)")

                if status_callback:
                    status_callback(f"📦 Packaging failed observations shapefile...")
                failed_shapefile_zip_path = create_shapefile_zip_package(str(failed_shp_path), output_dir)
                output_files['failed_observations_zip'] = str(failed_shapefile_zip_path)
                update_progress()
                if status_callback:
                    zip_size_mb = Path(failed_shapefile_zip_path).stat().st_size / (1024 * 1024)
                    status_callback(f"Packaged failed observations shapefile ({zip_size_mb:.1f}MB)")
            except Exception as e:
                print(f"Warning: Failed to create failed observations shapefile: {e}")
                if status_callback:
                    status_callback(f"Failed to create failed observations shapefile: {e}")

            failed_ref_shp_path = Path(output_dir) / "failed_observations_reference.shp"
            try:
                create_failed_observations_reference_shapefile(
                    validation_failed_df,
                    report_gdf,
                    str(failed_ref_shp_path)
                )
                failed_ref_shapefile_zip_path = create_shapefile_zip_package(str(failed_ref_shp_path), output_dir)
                output_files['failed_observations_reference_zip'] = str(failed_ref_shapefile_zip_path)
                print(f"Created failed observations reference shapefile: {failed_ref_shp_path}")
            except Exception as e:
                print(f"Warning: Failed to create failed observations reference shapefile: {e}")

        if completeness_params and not missing_observations_df.empty:
            missing_shp_path = Path(output_dir) / "missing_observations.shp"
            try:
                create_csv_matching_shapefile(
                    missing_observations_df,
                    report_gdf,
                    str(missing_shp_path),
                    geometry_source='shapefile'
                )
                missing_shapefile_zip_path = create_shapefile_zip_package(str(missing_shp_path), output_dir)
                output_files['missing_observations_zip'] = str(missing_shapefile_zip_path)
            except Exception as e:
                print(f"Warning: Failed to create missing observations shapefile: {e}")

        no_data_shp_path = Path(output_dir) / "no_data_links.shp"
        try:
            if not no_data_links_df.empty:
                create_csv_matching_shapefile(
                    no_data_links_df,
                    report_gdf,
                    str(no_data_shp_path),
                    geometry_source='shapefile'
                )
            else:
                empty_gdf = gpd.GeoDataFrame(columns=['link_id', 'Name', 'is_valid', 'valid_code'], geometry=[])
                empty_gdf.crs = report_gdf.crs
                empty_gdf.to_file(str(no_data_shp_path))
            no_data_shapefile_zip_path = create_shapefile_zip_package(str(no_data_shp_path), output_dir)
            output_files['no_data_links_zip'] = str(no_data_shapefile_zip_path)
        except Exception as e:
            print(f"Warning: Failed to create no-data links shapefile: {e}")

    # Release heavy intermediate DataFrames
    del best_valid_df
    del missing_observations_df
    del no_data_links_df
    del report_with_stats_gdf
    if 'validation_failed_df' in locals():
        del validation_failed_df
    gc.collect()

    return output_files


def detect_date_range_from_csv(csv_file):
    """
    Auto-detect start and end dates from CSV timestamp field.
    Returns (start_date, end_date, total_records) tuple.
    """
    if csv_file is None:
        return None, None, 0

    try:
        # Load CSV with encoding detection
        df_sample = load_csv_with_encoding(csv_file)

        if df_sample is None or df_sample.empty:
            return None, None, 0

        # Find timestamp column
        timestamp_cols = []
        for col in df_sample.columns:
            if col.lower() in ['timestamp', 'datetime', 'date', 'time']:
                timestamp_cols.append(col)

        if not timestamp_cols:
            return None, None, len(df_sample)

        # Use the first timestamp column found
        timestamp_col = timestamp_cols[0]

        # Parse timestamps
        timestamps = _parse_timestamp_series(df_sample[timestamp_col])

        # Remove NaN timestamps
        valid_timestamps = timestamps.dropna()

        if valid_timestamps.empty:
            return None, None, len(df_sample)

        # Get min and max dates
        start_date = valid_timestamps.min().date()
        end_date = valid_timestamps.max().date()

        return start_date, end_date, len(df_sample)

    except Exception as e:
        st.warning(f"Could not auto-detect dates from CSV: {e}")
        return None, None, 0


def load_csv_with_encoding(csv_file):
    """Load CSV with automatic encoding detection and Hebrew support"""
    # Save uploaded file to temporary location for encoding detection
    with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
        temp_file.write(csv_file.getvalue())
        temp_file_path = temp_file.name

    # Detect encoding with fallback approach
    detected_encoding = 'utf-8-sig'  # Default for files with BOM
    raw_data = b''

    try:
        with open(temp_file_path, 'rb') as f:
            raw_data = f.read(10000)  # Read first 10KB

        if raw_data.startswith(b'\xef\xbb\xbf'):
            detected_encoding = 'utf-8-sig'
            st.info("Detected UTF-8 with BOM encoding")
        else:
            detection = chardet.detect(raw_data) if HAS_CHARDET and raw_data else {}
            candidate = detection.get('encoding') if detection else None
            confidence = float(detection.get('confidence') or 0.0) if detection else 0.0
            resolved = resolve_hebrew_encoding(raw_data, candidate)

            if candidate and resolved and resolved.lower() != candidate.lower():
                detected_encoding = resolved
                st.info(f"Detected {candidate} (confidence: {confidence:.2f}) but using {resolved} based on Hebrew text")
            elif candidate and confidence > 0.7:
                detected_encoding = resolved
                st.info(f"Detected encoding: {detected_encoding} (confidence: {confidence:.2f})")
            else:
                detected_encoding = resolved
                st.info("Using default encoding: cp1255 (Hebrew)")
    except Exception:
        detected_encoding = resolve_hebrew_encoding(raw_data, None) if raw_data else 'utf-8-sig'
        st.info("Encoding detection fell back to heuristic defaults")

    # Get file size for chunking decision
    file_size = len(csv_file.getvalue())

    # Read CSV with proper encoding
    try:
        if file_size > 50 * 1024 * 1024:  # 50MB threshold for chunking
            st.info("Large file detected, processing in chunks...")
            chunk_reader = pd.read_csv(temp_file_path, chunksize=10000, encoding=detected_encoding)
            chunks = []
            chunk_count = 0
            progress_bar = st.progress(0)

            for chunk in chunk_reader:
                chunks.append(chunk)
                chunk_count += 1
                progress_bar.progress(min(chunk_count * 10000 / 100000, 1.0))

            progress_bar.empty()
            if chunks:
                csv_df = pd.concat(chunks, ignore_index=True)
                del chunks
            else:
                csv_df = pd.DataFrame()
            st.success(f"Processed {len(csv_df)} rows from {chunk_count} chunks")
        else:
            csv_df = pd.read_csv(temp_file_path, encoding=detected_encoding)

    except UnicodeDecodeError:
        # Try alternative encodings if detection fails
        fallback_encodings = ['utf-8-sig', 'cp1255', 'utf-8', 'latin-1', 'iso-8859-8', 'windows-1255', 'utf-16']
        st.warning("Primary encoding failed, trying alternatives...")

        for fallback_encoding in fallback_encodings:
            try:
                if file_size > 50 * 1024 * 1024:
                    chunk_reader = pd.read_csv(temp_file_path, chunksize=10000, encoding=fallback_encoding)
                    chunks = []
                    chunk_count = 0

                    for chunk in chunk_reader:
                        chunks.append(chunk)
                        chunk_count += 1

                    if chunks:
                        csv_df = pd.concat(chunks, ignore_index=True)
                        del chunks
                    else:
                        csv_df = pd.DataFrame()
                    st.success(f"Successfully read file using {fallback_encoding} encoding ({len(csv_df)} rows from {chunk_count} chunks)")
                else:
                    csv_df = pd.read_csv(temp_file_path, encoding=fallback_encoding)
                    st.success(f"Successfully read file using {fallback_encoding} encoding")
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                st.warning(f"{fallback_encoding} failed: {str(e)[:50]}...")
                continue
        else:
            st.error("Could not read CSV file with any supported encoding. Please check the file format.")
            st.info("Supported encodings: UTF-8, CP1255 (Hebrew), Latin-1, ISO-8859-8, Windows-1255, UTF-16")
            # Clean up temp file
            try:
                os.unlink(temp_file_path)
            except:
                pass
            return None
    finally:
        # Clean up temporary file
        try:
            os.unlink(temp_file_path)
        except:
            pass

    # Normalize column names for validation - just strip whitespace, preserve case
    csv_df.columns = csv_df.columns.str.strip()

    # The validator already handles different column name variations,
    # so we don't need to rename columns here. This preserves the original
    # column names exactly as they appear in the input file.

    return csv_df


def fix_hebrew_columns(csv_df):
    """Fix Hebrew text encoding issues in specific columns"""
    hebrew_columns = ['DayInWeek', 'DayType']
    hebrew_fixes_applied = 0

    for col in hebrew_columns:
        if col not in csv_df.columns:
            continue

        series = csv_df[col]
        non_null = series[series.notna()].astype(str)
        if non_null.empty:
            continue

        cache = {value: fix_hebrew_encoding(value) for value in non_null.unique()}

        def _transform(val):
            if pd.isna(val):
                return val
            val_str = str(val)
            return cache.get(val_str, fix_hebrew_encoding(val_str))

        transformed = series.map(_transform)
        csv_df[col] = transformed

        original_compare = series.fillna('__NA__').astype(str)
        transformed_compare = transformed.fillna('__NA__').astype(str)
        fixes_in_column = (original_compare != transformed_compare).sum()
        hebrew_fixes_applied += fixes_in_column

    if hebrew_fixes_applied > 0:
        st.info(f"Applied Hebrew text corrections to {hebrew_fixes_applied} corrupted entries")

    return csv_df


def fix_hebrew_encoding(text):
    """Fix corrupted Hebrew text encoding"""
    if pd.isna(text):
        return text

    text_str = str(text)

    # Known corrupted patterns and their fixes
    known_fixes = {
        "־¹־µ־½ֲ ־²": "יום ב",
        "־¹־µ־½ֲ ־³": "יום ג",
        "־¹־µ־½ֲ ־´": "יום ד",
        "־¹־µ־½ֲ ־µ": "יום ה",
        "־¹־µ־½ֲ ־¶": "יום ו",
        "־©־±־×": "שבת",
        "־¹־µ־½ֲ ־×": "יום א",
        "־¹־µ־½ ־—־µ־÷": "יום חול",
        "־©־±־×ֲ־×־³": "שבתות"
    }

    # Apply known fixes
    for corrupted, fixed in known_fixes.items():
        if corrupted in text_str:
            return text_str.replace(corrupted, fixed)

    # Try to decode common corrupted patterns
    if "־" in text_str or "ֲ" in text_str:
        # This appears to be corrupted Hebrew text
        # Try different decoding approaches
        try:
            # Attempt to fix encoding issues
            fixed = text_str.encode('latin-1', errors='ignore').decode('windows-1255', errors='ignore')
            if fixed and fixed != text_str:
                return fixed
        except:
            pass

        try:
            # Another approach for corrupted Hebrew
            fixed = text_str.encode('cp1252', errors='ignore').decode('windows-1255', errors='ignore')
            if fixed and fixed != text_str:
                return fixed
        except:
            pass

    return text_str


def save_shapefile_upload(uploaded_file):
    """Save uploaded shapefile to temporary location - handles both .shp and .zip files"""
    temp_dir = tempfile.mkdtemp()
    file_name = uploaded_file.name.lower()

    if file_name.endswith('.zip'):
        # Handle ZIP file containing shapefile components
        zip_path = Path(temp_dir) / uploaded_file.name
        with open(zip_path, 'wb') as f:
            f.write(uploaded_file.getvalue())

        try:
            # Extract ZIP contents
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            # Find the .shp file in the extracted contents
            shp_files = list(Path(temp_dir).glob('**/*.shp'))
            if not shp_files:
                raise ValueError("No .shp file found in the uploaded ZIP")

            # Return path to the first .shp file found
            shp_path = str(shp_files[0])

            # Verify that required components exist
            base_path = Path(shp_path).with_suffix('')
            required_files = ['.shp', '.shx', '.dbf']
            missing_files = []

            for ext in required_files:
                if not (base_path.with_suffix(ext)).exists():
                    missing_files.append(ext)

            if missing_files:
                st.warning(f"Missing shapefile components: {', '.join(missing_files)} - proceeding anyway")

            # Clean up the ZIP file
            zip_path.unlink()
            return shp_path

        except zipfile.BadZipFile:
            raise ValueError("Invalid ZIP file format")
        except Exception as e:
            raise ValueError(f"Error extracting shapefile: {str(e)}")

    elif file_name.endswith('.shp'):
        # Handle single .shp file
        temp_path = Path(temp_dir) / uploaded_file.name
        with open(temp_path, 'wb') as f:
            f.write(uploaded_file.getvalue())

        # Warn user about potential missing companion files
        st.warning("**Single .shp file uploaded**\n\n"
                  "Shapefile companion files (.shx, .dbf, .prj) are missing. "
                  "This may cause issues in GIS applications. "
                  "For best results, upload a ZIP file containing all shapefile components with the same base name.")

        return str(temp_path)

    else:
        raise ValueError("Unsupported file format. Please upload a .shp or .zip file containing shapefile components.")


def load_shapefile_robust(file_path):
    """Load shapefile with robust error handling"""
    try:
        return gpd.read_file(file_path)
    except Exception as e:
        # Try to provide more helpful error messages
        if "Unable to open" in str(e):
            raise Exception(f"Cannot open shapefile. Make sure all required components (.shp, .shx, .dbf) are present. Error: {e}")
        else:
            raise e


def cleanup_temp_shapefile(file_path):
    """Clean up temporary shapefile and related files"""
    # Get the temporary directory containing the shapefile
    temp_dir = Path(file_path).parent

    # Check if this looks like a temp directory from tempfile.mkdtemp()
    temp_root = Path(tempfile.gettempdir())

    # If the parent directory is directly under temp root, remove the whole directory
    if temp_dir.parent == temp_root:
        try:
            shutil.rmtree(temp_dir)
            return
        except OSError:
            pass  # Fall back to individual file cleanup

    # Fallback: remove individual shapefile components
    base_path = Path(file_path).with_suffix('')
    for ext in ['.shp', '.shx', '.dbf', '.prj', '.cpg', '.xml']:
        temp_file = base_path.with_suffix(ext)
        if temp_file.exists():
            try:
                temp_file.unlink()
            except OSError:
                pass

    # Try to remove temp directory if empty
    try:
        temp_dir.rmdir()
    except OSError:
        pass


def _collect_shapefile_components(base_path: Path):
    """Yield existing shapefile component paths for zipping."""
    for ext in ['.shp', '.shx', '.dbf', '.prj', '.cpg', '.xml']:
        component_path = base_path.with_suffix(ext)
        if component_path.exists():
            yield component_path


def create_shapefile_zip_package(shp_path, output_dir, cleanup=True, compresslevel=6):
    """Create a ZIP file containing all shapefile components."""
    base_path = Path(shp_path).with_suffix('')
    zip_path = Path(output_dir) / f"{base_path.stem}_shapefile.zip"

    components = list(_collect_shapefile_components(base_path))

    with zipfile.ZipFile(
        zip_path,
        'w',
        compression=zipfile.ZIP_DEFLATED,
        allowZip64=True,
        compresslevel=compresslevel
    ) as zip_file:
        for component_path in components:
            zip_file.write(component_path, component_path.name)
            if cleanup:
                with suppress(OSError):
                    component_path.unlink()

    if cleanup:
        with suppress(OSError):
            base_path.parent.rmdir()

    return str(zip_path)



_DOWNLOAD_LABELS = {
    'validated_csv': 'Validated Data CSV',
    'validated_csv_zip': 'Validated Data CSV (ZIP)',
    'failed_observations_csv': 'Failed Observations CSV',
    'failed_observations_csv_zip': 'Failed Observations CSV (ZIP)',
    'best_valid_observations_csv': 'Best Valid Observations CSV',
    'best_valid_observations_csv_zip': 'Best Valid Observations CSV (ZIP)',
    'missing_observations_csv': 'Missing Observations CSV',
    'missing_observations_csv_zip': 'Missing Observations CSV (ZIP)',
    'missing_observations_zip': 'Missing Observations Shapefile',
    'link_report_csv': 'Link Report CSV',
    'link_report_zip': 'Link Report Shapefile',
    'failed_observations_zip': 'Failed Observations Shapefile',
    'failed_observations_reference_zip': 'Failed Observations Reference Shapefile',
    'no_data_links_csv': 'No-Data Links CSV',
    'no_data_links_zip': 'No-Data Links Shapefile',
}


def _format_file_size(size_bytes: int) -> str:
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    size = float(size_bytes)
    for unit in units:
        if size < 1024 or unit == 'TB':
            if unit == 'B':
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _build_download_entries(output_files: dict) -> list:
    entries = []
    zip_overrides = {'validated_csv', 'failed_observations_csv', 'best_valid_observations_csv', 'missing_observations_csv'}

    for file_type, file_path_str in output_files.items():
        if file_type in zip_overrides and f"{file_type}_zip" in output_files:
            continue

        path_obj = Path(file_path_str)
        if not path_obj.exists():
            continue

        size_bytes = path_obj.stat().st_size
        suffix = path_obj.suffix.lower()

        if suffix == '.csv':
            mime_type = 'text/csv'
        elif suffix == '.zip':
            mime_type = 'application/zip'
        else:
            mime_type = 'application/octet-stream'

        label = _DOWNLOAD_LABELS.get(file_type)
        if not label:
            base_label = file_type.replace('_', ' ').title()
            label = f"{base_label} (ZIP)" if suffix == '.zip' else base_label

        entries.append({
            'file_type': file_type,
            'path': path_obj,
            'mime': mime_type,
            'label': label,
            'size_bytes': size_bytes,
            'size_label': _format_file_size(size_bytes),
        })

    return entries



def display_control_results():
    """Display control validation results"""
    results = st.session_state.control_results

    if not results['success']:
        st.error(f"Validation failed: {results['error_message']}")
        return

    render_subheader_with_icon('results', 'Validation Results')

    validated_df = results['validated_df']
    report_gdf = results['report_gdf']
    output_files = results['output_files']

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # Show both row count and timestamp count for clarity
        total_rows = len(validated_df)

        # Calculate unique timestamps for timestamp-based counting
        name_col = 'name' if 'name' in validated_df.columns else 'Name'
        timestamp_col = 'timestamp' if 'timestamp' in validated_df.columns else 'Timestamp'

        if name_col in validated_df.columns and timestamp_col in validated_df.columns:
            total_observations = len(validated_df.groupby([name_col, timestamp_col]))
            st.metric("Unique Observations", f"{total_observations:,}", f"{total_rows:,} routes")
        else:
            st.metric("Total Observations", f"{total_rows:,}")

    with col2:
        valid_column = None
        if 'hausdorff_pass' in validated_df.columns:
            valid_column = 'hausdorff_pass'
        elif 'is_valid' in validated_df.columns:
            valid_column = 'is_valid'

        if valid_column:
            valid_series = validated_df[valid_column].fillna(False).astype(bool)
            total_routes = len(valid_series)
            valid_routes = int(valid_series.sum())
            valid_routes_pct = (valid_routes / total_routes * 100) if total_routes > 0 else 0
            st.metric("Valid Routes", f"{valid_routes:,}", f"{valid_routes_pct:.1f}%")

            name_col = 'name' if 'name' in validated_df.columns else 'Name'
            timestamp_col = 'timestamp' if 'timestamp' in validated_df.columns else 'Timestamp'

            if name_col in validated_df.columns and timestamp_col in validated_df.columns:
                observation_groups = valid_series.groupby([validated_df[name_col], validated_df[timestamp_col]]).any()
                total_observations = len(observation_groups)
                valid_observations = int(observation_groups.sum())
                observation_pct = (valid_observations / total_observations * 100) if total_observations > 0 else 0
        else:
            st.metric("Valid Routes", "N/A", "0%")

    with col3:
        unique_links = validated_df['name'].nunique() if 'name' in validated_df.columns else validated_df['Name'].nunique() if 'Name' in validated_df.columns else 0
        st.metric("Links Tested", f"{unique_links:,}")

    with col4:
        report_links = len(report_gdf)
        st.metric("Reference Links", f"{report_links:,}")

    # Validation code distribution
    if 'valid_code' in validated_df.columns:
        render_subheader_with_icon('bar-chart', 'Validation Code Distribution')

        code_counts = validated_df['valid_code'].value_counts().sort_index()

        # Create readable code descriptions for new simplified system
        code_descriptions = {
            1: "No route alternative (geometry-only)",
            2: "Single route alternative",
            3: "Multiple route alternatives",
            90: "Required fields missing",
            91: "Name parse failure",
            92: "Link not in shapefile",
            93: "Polyline decode failure",
            94: "Missing observation (expected timestamp not found)"
        }

        code_display = pd.DataFrame({
            'Valid Code': code_counts.index,
            'Count': code_counts.values,
            'Percentage': (code_counts.values / len(validated_df) * 100) if len(validated_df) > 0 else [0] * len(code_counts),
            'Description': [code_descriptions.get(code, f"Code {code}") for code in code_counts.index]
        })

        st.dataframe(code_display, use_container_width=True)

    # Failed Observations Analysis
    if 'is_valid' in validated_df.columns:
        name_col = 'name' if 'name' in validated_df.columns else 'Name'
        timestamp_col = 'timestamp' if 'timestamp' in validated_df.columns else 'Timestamp'

        if name_col in validated_df.columns and timestamp_col in validated_df.columns:
            # Find failed observations (timestamps where ALL routes failed)
            observation_groups = validated_df.groupby([name_col, timestamp_col])
            failed_observations = observation_groups.filter(lambda x: not x['is_valid'].any())

            if len(failed_observations) > 0:
                st.subheader("Failed Observations Details")

                # Group failed observations by link and timestamp
                failed_groups = failed_observations.groupby([name_col, timestamp_col])
                failed_summary = []

                for (link_name, timestamp), group in failed_groups:
                    failure_reasons = []

                    # Analyze failure reasons from individual test results
                    if 'hausdorff_pass' in group.columns:
                        if not group['hausdorff_pass'].any():
                            avg_distance = group['hausdorff_distance'].mean() if 'hausdorff_distance' in group.columns else 'N/A'
                            failure_reasons.append(f"Hausdorff: {avg_distance:.2f}m" if isinstance(avg_distance, (int, float)) else "Hausdorff failed")

                    if 'length_pass' in group.columns:
                        if not group['length_pass'].any():
                            avg_ratio = group['length_ratio'].mean() if 'length_ratio' in group.columns else 'N/A'
                            failure_reasons.append(f"Length ratio: {avg_ratio:.3f}" if isinstance(avg_ratio, (int, float)) else "Length failed")

                    if 'coverage_pass' in group.columns:
                        if not group['coverage_pass'].any():
                            avg_coverage = group['coverage_percent'].mean() if 'coverage_percent' in group.columns else 'N/A'
                            failure_reasons.append(f"Coverage: {avg_coverage:.1f}%" if isinstance(avg_coverage, (int, float)) else "Coverage failed")

                    failed_summary.append({
                        'Link': link_name,
                        'Timestamp': timestamp,
                        'Routes Tested': len(group),
                        'Failure Reasons': '; '.join(failure_reasons) if failure_reasons else 'Unknown'
                    })

                failed_df = pd.DataFrame(failed_summary)
                st.dataframe(failed_df, use_container_width=True)

                st.info(f"**{len(failed_observations)} routes** across **{len(failed_summary)} observations** failed validation")
            else:
                st.success("All observations have at least one valid route!")

    # Sample validation results
    st.subheader("Sample Validation Results")

    # Show first 10 rows with key columns
    name_col = 'Name' if 'Name' in validated_df.columns else 'name'
    display_cols = [name_col, 'is_valid', 'valid_code']

    polyline_col = 'Polyline' if 'Polyline' in validated_df.columns else 'polyline'
    if polyline_col in validated_df.columns:
        display_cols.append(polyline_col)

    route_alt_col = 'RouteAlternative' if 'RouteAlternative' in validated_df.columns else 'route_alternative'
    if route_alt_col in validated_df.columns:
        display_cols.append(route_alt_col)

    sample_df = validated_df[display_cols].head(10)
    st.dataframe(sample_df, use_container_width=True)

    # Link report preview
    st.subheader("Link Report Preview")

    # Updated columns with new field names and breakdown
    report_display_cols = [
        'From', 'To',
        'perfect_match_percent', 'threshold_pass_percent', 'failed_percent',
        'total_observations', 'successful_observations', 'failed_observations',
        'total_routes', 'single_route_observations', 'multi_route_observations',
        'expected_observations', 'missing_observations', 'data_coverage_percent'
    ]
    available_cols = [col for col in report_display_cols if col in report_gdf.columns]

    if available_cols:
        # Format percentages for better display
        display_df = report_gdf[available_cols].head(10).copy()

        # Format percentage columns to 1 decimal place
        percentage_cols = ['perfect_match_percent', 'threshold_pass_percent', 'failed_percent', 'data_coverage_percent']
        for col in percentage_cols:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "No Data")

        st.dataframe(display_df, use_container_width=True)

        # Add explanation of the breakdown
        st.info("**Breakdown Explanation:**\n"
               "• **Perfect Match**: Hausdorff distance = 0.0m (exact geometry match)\n"
               "• **Threshold Pass**: 0 < Hausdorff ≤ threshold (close enough geometry)\n"
               "• **Failed**: Hausdorff > threshold or other test failures")

    # Download section
    st.subheader("Download Results")

    if output_files:
        download_entries = _build_download_entries(output_files)
        if not download_entries:
            st.info("No downloadable files were generated.")
        else:
            # Separate entries into CSV and Shapefile categories
            csv_entries = []
            shapefile_entries = []

            for entry in download_entries:
                if entry['file_type'].endswith('_zip') and 'csv' not in entry['file_type']:
                    # Shapefile packages (all end with _zip except csv_zip files)
                    shapefile_entries.append(entry)
                else:
                    # CSV files (including compressed CSVs)
                    csv_entries.append(entry)

            # Display CSV downloads
            if csv_entries:
                st.markdown("### CSV Data Files")
                compressed_keys = {'validated_csv_zip', 'failed_observations_csv_zip', 'best_valid_observations_csv_zip', 'missing_observations_csv_zip'}
                if any(entry['file_type'] in compressed_keys for entry in csv_entries):
                    st.info("Large CSV outputs are compressed for safer downloads. The raw CSV files remain in the output directory.")

                csv_cols = st.columns(min(3, len(csv_entries)))
                for i, entry in enumerate(csv_entries):
                    col = csv_cols[i % len(csv_cols)]
                    with col:
                        file_path = entry['path']
                        with file_path.open('rb') as file_handle:
                            st.download_button(
                                label=f"{entry['label']} ({entry['size_label']})",
                                data=file_handle,
                                file_name=file_path.name,
                                mime=entry['mime'],
                                use_container_width=True,
                                key=f"download_{entry['file_type']}"
                            )
                        st.caption(f"Saved to {file_path}")

            # Display Shapefile downloads
            if shapefile_entries:
                st.markdown("### Shapefile Packages")
                st.info("Shapefile packages include all required components (.shp, .shx, .dbf, .prj) in ZIP format.")

                shapefile_cols = st.columns(min(3, len(shapefile_entries)))
                for i, entry in enumerate(shapefile_entries):
                    col = shapefile_cols[i % len(shapefile_cols)]
                    with col:
                        file_path = entry['path']
                        with file_path.open('rb') as file_handle:
                            st.download_button(
                                label=f"{entry['label']} ({entry['size_label']})",
                                data=file_handle,
                                file_name=file_path.name,
                                mime=entry['mime'],
                                use_container_width=True,
                                key=f"download_{entry['file_type']}"
                            )
                        st.caption(f"Saved to {file_path}")

