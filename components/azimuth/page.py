# -*- coding: utf-8 -*-
"""
Azimuth Preprocessing Page

Streamlit UI for preprocessing road network shapefiles with directional azimuth coding.
Calculates compass bearings and octant codes for each link.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import re
import tempfile
import os
import subprocess
import sys
from datetime import datetime


def azimuth_page():
    """Main azimuth preprocessing page"""
    st.title("🧭 Azimuth Preprocessing")
    st.markdown("---")
    st.markdown("### Calculate directional azimuths and octant codes for road network shapefiles")
    st.markdown("")

    # Check dependencies
    check_dependencies()

    # Main layout
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("""
        <div style="background-color: #f0f2f6; padding: 1rem; border-radius: 8px; margin-bottom: 1.5rem; border-left: 5px solid #1f77b4;">
            <h2 style="margin: 0; color: #1f77b4;">📁 Input Configuration</h2>
        </div>
        """, unsafe_allow_html=True)

        # File Upload
        st.markdown("#### 📂 Upload Base Map Shapefile")
        uploaded_file = st.file_uploader(
            "Upload shapefile (.shp or .zip)",
            type=['shp', 'zip'],
            help="Upload a shapefile containing the road network geometry. Can be a single .shp file or a complete .zip package."
        )

        # Auto-detect base directory from uploaded file
        auto_base_dir = "runs/1_11_25/input/maps"  # Default fallback

        if uploaded_file:
            st.success(f"✅ File uploaded: {uploaded_file.name} ({uploaded_file.size:,} bytes)")

            # Extract date from filename to determine batch folder
            file_name = uploaded_file.name
            base_name = Path(file_name).stem
            date_match = re.match(r'(\d{1,2}_\d{1,2}_\d{4})_', base_name)

            if date_match:
                full_date = date_match.group(1)  # e.g., 2_11_2025
                # Convert to batch format: DD_MM_YY
                parts = full_date.split('_')
                if len(parts) == 3:
                    day, month, year = parts
                    batch_id = f"{day}_{month}_{year[2:]}"  # e.g., 2_11_25
                    auto_base_dir = f"runs/{batch_id}/input/maps"
                    st.success(f"🔍 **Auto-detected batch:** `{batch_id}` from filename")

        # Base output directory
        st.markdown("#### 📂 Output Configuration")
        base_output_dir = st.text_input(
            "Base output directory",
            value=auto_base_dir,
            help="Base directory for all outputs. Auto-detected from filename, but you can override it here."
        )

        # Extract date and generate paths
        if uploaded_file:
            file_name = uploaded_file.name
            base_name = Path(file_name).stem

            # Extract date from filename (e.g., 1_11_2025_base_map -> 1_11_2025)
            date_match = re.match(r'(\d{1,2}_\d{1,2}_\d{4})_', base_name)

            if date_match:
                date_prefix = date_match.group(1)

                # Generate output paths
                basemap_folder = Path(base_output_dir) / "basemap"
                azimuth_folder = basemap_folder / f"{date_prefix}_azimut_base_map"
                a_b_folder = Path(base_output_dir) / "a_b"

                # Output filenames
                azimut_id_shp = azimuth_folder / f"{date_prefix}_base_map_azimut_id.shp"
                crow_shp = azimuth_folder / f"{date_prefix}_base_map_crow_only.shp"
                crow_csv = azimuth_folder / f"{date_prefix}_base_map_crow_only.csv"
                a_b_xlsx = a_b_folder / f"{date_prefix}_a_b.xlsx"

                st.success(f"📅 **Detected date:** `{date_prefix}`")

                # Show output structure
                with st.expander("📋 Output File Structure", expanded=True):
                    st.markdown("**Output files will be created:**")
                    st.code(f"""
{basemap_folder}/
└── {date_prefix}_azimut_base_map/
    ├── {date_prefix}_base_map_azimut_id.shp
    ├── {date_prefix}_base_map_crow_only.shp
    └── {date_prefix}_base_map_crow_only.csv

{a_b_folder}/
└── {date_prefix}_a_b.xlsx
                    """, language="text")

                # Store paths in session state
                st.session_state.azimuth_config = {
                    'uploaded_file': uploaded_file,
                    'date_prefix': date_prefix,
                    'azimut_id_shp': str(azimut_id_shp),
                    'crow_shp': str(crow_shp),
                    'crow_csv': str(crow_csv),
                    'a_b_xlsx': str(a_b_xlsx)
                }

            else:
                st.warning("⚠️ Could not extract date from filename. Expected format: `DD_MM_YYYY_base_map.shp`")
                st.info("💡 Example: `1_11_2025_base_map.shp`")
                st.session_state.azimuth_config = None

        else:
            st.info("Please upload a shapefile to begin")
            st.info("💡 **Filename format:** The input file should follow the pattern `DD_MM_YYYY_base_map.shp` where the date will be extracted automatically.")

    with col2:
        st.markdown("""
        <div style="background-color: #f0f2f6; padding: 1rem; border-radius: 8px; margin-bottom: 1.5rem; border-left: 5px solid #28a745;">
            <h2 style="margin: 0; color: #28a745;">▶️ Processing</h2>
        </div>
        """, unsafe_allow_html=True)

        # Run button
        can_run = (uploaded_file is not None and
                  'azimuth_config' in st.session_state and
                  st.session_state.azimuth_config is not None)

        if st.button("🚀 Run Azimuth Processing", disabled=not can_run, use_container_width=True, type="primary"):
            if can_run:
                run_azimuth_processing()
            else:
                st.error("Please upload a valid file with proper naming format")

        if not can_run:
            st.warning("⚠️ Please upload a shapefile with date prefix to run processing")

        # Show results if available
        if 'azimuth_results' in st.session_state:
            results = st.session_state.azimuth_results

            if results.get('success', False):
                st.success("🎉 Processing completed successfully!")

                # Summary metrics
                st.subheader("📊 Summary")

                feature_count = results.get('feature_count', 0)
                axis_fix_count = results.get('axis_fix_count', 0)

                st.metric("Features Processed", f"{feature_count:,}")
                st.metric("Axis Corrections", f"{axis_fix_count:,}")

                # Output files
                st.subheader("📥 Output Files")
                output_files = results.get('output_files', {})

                for file_type, file_path in output_files.items():
                    if Path(file_path).exists():
                        file_size = Path(file_path).stat().st_size
                        st.text(f"✅ {file_type}: {Path(file_path).name} ({file_size:,} bytes)")
                    else:
                        st.text(f"⚠️ {file_type}: Not found")

                # Processing log
                if 'log' in results:
                    with st.expander("📋 Processing Log", expanded=False):
                        st.text(results['log'])

                # Clear and run again
                if st.button("🔄 Run New Processing", use_container_width=True):
                    del st.session_state.azimuth_results
                    st.rerun()

            else:
                st.error(f"❌ Processing failed: {results.get('error_message', 'Unknown error')}")

                # Show error details
                with st.expander("Error Details", expanded=True):
                    st.code(results.get('error_message', 'Unknown error'))

                # Try again
                if st.button("🔄 Try Again", use_container_width=True):
                    del st.session_state.azimuth_results
                    st.rerun()


def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = ['geopandas', 'shapely', 'pyproj', 'xlsxwriter']
    missing = []

    for pkg in required_packages:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if missing:
        st.warning(f"⚠️ Missing dependencies: {', '.join(missing)}")

        with st.expander("📦 Install Dependencies", expanded=True):
            st.markdown("**Required packages are missing. You can install them by:**")
            st.markdown("1. **Using pip:**")
            st.code(f"pip install {' '.join(missing)}", language="bash")

            st.markdown("2. **Using the provided installation script:**")
            if st.button("🔧 Install Dependencies Now", type="primary"):
                install_dependencies()
    else:
        st.success("✅ All required dependencies are installed")


def install_dependencies():
    """Install required dependencies using pip"""
    packages = ['geopandas', 'shapely', 'pyproj', 'xlsxwriter']

    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, pkg in enumerate(packages):
        status_text.text(f"Installing {pkg}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            progress_bar.progress((i + 1) / len(packages))
            st.success(f"✅ Installed {pkg}")
        except subprocess.CalledProcessError as e:
            st.error(f"❌ Failed to install {pkg}: {e}")
            return

    status_text.text("✅ All dependencies installed successfully!")
    st.info("Please refresh the page to continue.")


def run_azimuth_processing():
    """Execute the azimuth preprocessing"""
    try:
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Get configuration
        config = st.session_state.azimuth_config

        status_text.text("📁 Saving uploaded file...")
        progress_bar.progress(10)

        # Save uploaded file temporarily
        temp_file_path = save_uploaded_file(config['uploaded_file'])

        status_text.text("🔧 Creating output directories...")
        progress_bar.progress(20)

        # Create output directories
        for path_key in ['azimut_id_shp', 'crow_shp', 'a_b_xlsx']:
            Path(config[path_key]).parent.mkdir(parents=True, exist_ok=True)

        status_text.text("🧭 Running azimuth calculation...")
        progress_bar.progress(30)

        # Import and run the processing function
        from .pre_process_map_with_paths_new import (
            read_vector_any, to_linestring, pick_id_field,
            endpoints_xy, normalize_bearing, octant,
            planar_bearing_from_north, angular_distance
        )
        import geopandas as gpd
        import pandas as pd
        from shapely.geometry import LineString
        from pyproj import Geod
        import math

        # Read input
        gdf = read_vector_any(temp_file_path)
        if gdf.empty:
            raise ValueError("Input layer is empty.")

        crs = gdf.crs
        if crs is None:
            raise ValueError("Input layer has no CRS; bearings require a defined coordinate reference system.")

        progress_bar.progress(40)

        # Process geometry
        gdf = gdf[gdf.geometry.notna()].copy()
        gdf["geometry"] = gdf["geometry"].apply(to_linestring)
        gdf = gdf[gdf.geometry.notna()].copy()

        kid_field = pick_id_field(gdf)

        progress_bar.progress(50)
        status_text.text("🗺️ Calculating geodesic azimuths...")

        # Calculate azimuths
        geod = Geod(ellps="WGS84")
        gdf_ll = gdf.to_crs(4326)

        rows = []
        crow_geoms = []
        axis_fix_count = 0

        total_features = len(gdf)

        for idx, (geom_orig, geom_ll, kid_val) in enumerate(zip(gdf.geometry, gdf_ll.geometry, gdf[kid_field])):
            if idx % 100 == 0:
                progress_bar.progress(50 + int(40 * idx / total_features))
                status_text.text(f"🧭 Processing feature {idx}/{total_features}...")

            ls_orig = to_linestring(geom_orig)
            ls_ll = to_linestring(geom_ll)
            if ls_orig is None or ls_ll is None:
                continue

            # Endpoints
            (x1_ll, y1_ll), (x2_ll, y2_ll) = endpoints_xy(ls_ll)

            # Geodesic azimuths
            fwd_az, back_az, _ = geod.inv(x1_ll, y1_ll, x2_ll, y2_ll)
            fwd_az = normalize_bearing(fwd_az)
            back_az = normalize_bearing(back_az)

            # Axis-order diagnostic
            fwd_az_swap, back_az_swap, _ = geod.inv(y1_ll, x1_ll, y2_ll, x2_ll)
            fwd_az_swap = normalize_bearing(fwd_az_swap)
            back_az_swap = normalize_bearing(back_az_swap)

            # Crow line
            (x1, y1), (x2, y2) = endpoints_xy(ls_orig)
            crow = LineString([(x1, y1), (x2, y2)])

            # Planar bearings
            planar_ab = planar_bearing_from_north(x1, y1, x2, y2)
            planar_ba = planar_bearing_from_north(x2, y2, x1, y1)

            # Determine axis swap
            use_axis_swap = False
            if planar_ab is not None:
                diff_regular = angular_distance(fwd_az, planar_ab)
                diff_swap = angular_distance(fwd_az_swap, planar_ab)
                if diff_swap + 1e-9 < diff_regular and diff_swap <= 45.0:
                    use_axis_swap = True

            if use_axis_swap:
                axis_fix_count += 1
                fwd_use = fwd_az_swap
                back_use = back_az_swap
            else:
                fwd_use = fwd_az
                back_use = back_az

            # Octant codes
            code_a, dir_a = octant(fwd_use)
            code_b, dir_b = octant(back_use)

            # New ID
            kid_str = str(kid_val)
            new_id = f"{kid_str}-{code_b}{code_a}"

            # Coordinates for Excel
            start_coord = f"{y1_ll:.15f},{x1_ll:.15f}"
            end_coord = f"{y2_ll:.15f},{x2_ll:.15f}"

            rows.append({
                "kid": kid_str,
                "Id": new_id,
                "code_a": code_a,
                "dir_a": dir_a,
                "azi_a": fwd_use,
                "code_b": code_b,
                "dir_b": dir_b,
                "azi_b": back_use,
                "code_start": code_b,
                "dir_start": dir_b,
                "code_end": code_a,
                "dir_end": dir_a,
                "start_lat": y1_ll,
                "start_lon": x1_ll,
                "end_lat": y2_ll,
                "end_lon": x2_ll,
                "start_x": x1,
                "start_y": y1,
                "end_x": x2,
                "end_y": y2,
                "start_coord": start_coord,
                "end_coord": end_coord,
                "travel_mode": f"{code_b}-{code_a}",
                "azi_a_raw": fwd_az,
                "azi_b_raw": back_az,
                "azi_a_sw": fwd_az_swap,
                "azi_b_sw": back_az_swap,
                "azi_a_pl": float("nan") if planar_ab is None else planar_ab,
                "azi_b_pl": float("nan") if planar_ba is None else planar_ba,
                "axis_fix": int(use_axis_swap),
            })
            crow_geoms.append(crow)

        progress_bar.progress(90)
        status_text.text("💾 Writing output files...")

        # Build crow GDF
        crow_df = gpd.GeoDataFrame(rows, geometry=crow_geoms, crs=crs)

        # Write output files
        id_map = dict(zip(crow_df["kid"], crow_df["Id"]))
        out_gdf = gdf[["geometry"]].copy()
        if gdf[kid_field].is_unique:
            out_gdf["Id"] = gdf[kid_field].astype(str).map(id_map)
        else:
            out_gdf["Id"] = [rows[i]["Id"] for i in range(len(out_gdf))]

        # 1. Azimuth ID shapefile
        try:
            out_gdf.to_file(config['azimut_id_shp'])
        except PermissionError:
            st.warning(f"⚠️ Could not overwrite {config['azimut_id_shp']} - file may be open")

        # 2. Crow shapefile
        crow_fields = [
            "Id", "kid", "code_start", "dir_start", "code_end", "dir_end",
            "code_a", "dir_a", "azi_a", "code_b", "dir_b", "azi_b",
            "travel_mode", "azi_a_raw", "azi_b_raw", "azi_a_sw", "azi_b_sw",
            "azi_a_pl", "azi_b_pl", "axis_fix"
        ]
        crow_min = crow_df[crow_fields + ["geometry"]].copy()
        try:
            crow_min.to_file(config['crow_shp'])
        except PermissionError:
            st.warning(f"⚠️ Could not overwrite {config['crow_shp']} - file may be open")

        # 3. Excel file
        excel_rows = [
            {
                "שם מקטע": r["Id"],
                "אופן": 0,
                "נקודת התחלה": r["start_coord"],
                "נקודת סיום": r["end_coord"],
            }
            for r in rows
        ]
        xls = pd.DataFrame(excel_rows, columns=["שם מקטע", "אופן", "נקודת התחלה", "נקודת סיום"])
        try:
            xls.to_excel(config['a_b_xlsx'], index=False, sheet_name="links", engine='xlsxwriter')
        except PermissionError:
            st.warning(f"⚠️ Could not overwrite {config['a_b_xlsx']} - file may be open")

        # 4. Crow CSV
        crow_csv_df = crow_df.copy()
        drop_coords = ["start_lat", "start_lon", "end_lat", "end_lon",
                      "start_x", "start_y", "end_x", "end_y",
                      "start_coord", "end_coord"]
        crow_csv_df = crow_csv_df.drop(columns=drop_coords, errors="ignore")
        crow_csv_df["geometry_wkt"] = crow_csv_df.geometry.to_wkt()
        crow_csv_df = crow_csv_df.drop(columns="geometry")
        crow_csv_df.to_csv(config['crow_csv'], index=False, encoding="utf-8-sig")

        # Clean up temp file
        Path(temp_file_path).unlink(missing_ok=True)

        progress_bar.progress(100)
        status_text.text("✅ Processing completed!")

        # Build log
        log = f"""Azimuth Preprocessing Log
========================
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Input file: {config['uploaded_file'].name}
Date prefix: {config['date_prefix']}

Processing Summary:
- Features processed: {len(rows)}
- Axis corrections: {axis_fix_count}
- CRS: {crs}
- ID field: {kid_field}

Output Files:
- Azimuth ID shapefile: {config['azimut_id_shp']}
- Crow shapefile: {config['crow_shp']}
- Crow CSV: {config['crow_csv']}
- Excel file: {config['a_b_xlsx']}
"""

        # Store results
        st.session_state.azimuth_results = {
            'success': True,
            'feature_count': len(rows),
            'axis_fix_count': axis_fix_count,
            'output_files': {
                'Azimuth ID Shapefile': config['azimut_id_shp'],
                'Crow Shapefile': config['crow_shp'],
                'Crow CSV': config['crow_csv'],
                'Excel (A-B)': config['a_b_xlsx']
            },
            'log': log
        }

        st.rerun()

    except Exception as e:
        # Clean up temp file on error
        if 'temp_file_path' in locals():
            Path(temp_file_path).unlink(missing_ok=True)

        st.session_state.azimuth_results = {
            'success': False,
            'error_message': str(e)
        }

        st.error(f"❌ Processing failed: {e}")

        # Show traceback
        import traceback
        with st.expander("Error Traceback", expanded=False):
            st.code(traceback.format_exc())


def save_uploaded_file(uploaded_file) -> str:
    """Save uploaded file to temporary location"""
    import tempfile

    # Determine suffix
    suffix = '.zip' if uploaded_file.name.endswith('.zip') else '.shp'

    # Create temp file
    temp_fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix='azimuth_input_')

    try:
        with os.fdopen(temp_fd, 'wb') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
        return temp_path
    except Exception as e:
        try:
            os.close(temp_fd)
        except:
            pass
        Path(temp_path).unlink(missing_ok=True)
        raise e
