"""
Google Maps Link Monitoring CSV Processor - Streamlit GUI Application

This module provides the Streamlit-based web interface for configuring
processing parameters, uploading files, and viewing results.
"""

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import json
import tempfile
import os
from datetime import datetime, date
from typing import Dict, List, Optional

# Import processing functions
from components.aggregation.pipeline import run_pipeline, resolve_hebrew_encoding

# Import maps page
from components.maps import render_maps_page

# Import control component
from components.control import control_page

# Import azimuth component
from components.azimuth import azimuth_page

# Try to import streamlit-option-menu for professional icons
try:
    from streamlit_option_menu import option_menu
    HAS_OPTION_MENU = True
except ImportError:
    HAS_OPTION_MENU = False


# Lucide icon functions removed due to HTML rendering issues in Streamlit
# Reverted to emoji icons for better compatibility

# Configure Streamlit page
st.set_page_config(
    page_title="Google Maps Link Monitoring Processor",
    page_icon="🗺️",  # Keep emoji for favicon compatibility
    layout="wide",
    initial_sidebar_state="expanded"
)


def fix_hebrew_encoding(text):
    """Fix corrupted Hebrew text encoding issues"""
    if pd.isna(text) or not isinstance(text, str):
        return text

    try:
        # Handle common Hebrew corruption patterns
        # Method 1: Try to fix UTF-8 bytes misinterpreted as other encodings
        corruption_indicators = ['־', '֞', '֟', '֠', '֡', '֢', '֣', '֤', '֥', '֦', '֧', '֨', '֩', '֪', '֫', '֬', '֭', '֮', 'ι', 'ε', 'ν', 'η', 'μ', 'β']
        if any(char in text for char in corruption_indicators):
            # Text contains Hebrew-like corruption - try to recover

            # Common Hebrew day names mapping for fallback
            hebrew_days = {
                'יום א': 'יום א',  # Sunday
                'יום ב': 'יום ב',  # Monday
                'יום ג': 'יום ג',  # Tuesday
                'יום ד': 'יום ד',  # Wednesday
                'יום ה': 'יום ה',  # Thursday
                'יום ו': 'יום ו',  # Friday
                'שבת': 'שבת'       # Saturday
            }

            hebrew_types = {
                'יום חול': 'יום חול',  # Weekday
                'חג': 'חג',             # Holiday
                'ערב חג': 'ערב חג'       # Holiday eve
            }

            # Try pattern matching for common corrupted patterns based on actual observations
            # Map corrupted text patterns to correct Hebrew
            corruption_map = {
                '־¹־µ־½ֲ ־²': 'יום ג',      # Tuesday
                '־¹־µ־½ ־·־µ־¼': 'יום חול',  # Weekday
                'ιεν� β': 'יום ג',         # Tuesday (alternate corruption)
                'ιεν ηεμ': 'יום חול',      # Weekday (alternate corruption)
            }

            # Check for exact matches first
            if text in corruption_map:
                return corruption_map[text]

            # Check for partial matches for flexibility
            if '־¹־µ־½' in text:
                if '־²' in text or 'β' in text:
                    return 'יום ג'  # Tuesday
                elif '־·־µ־¼' in text or 'ηεμ' in text:
                    return 'יום חול'  # Weekday
                elif '־¤' in text:
                    return 'יום ה'  # Thursday
                elif '־º' in text:
                    return 'יום א'  # Sunday
                elif '־¡' in text:
                    return 'יום ב'  # Monday
                elif '־¥' in text:
                    return 'יום ד'  # Wednesday

        # Try direct UTF-8 decoding repair
        try:
            # Encode as latin-1 then decode as utf-8 (common double-encoding fix)
            if text.encode('latin-1'):
                fixed = text.encode('latin-1').decode('utf-8')
                if any(char in fixed for char in ['י', 'ו', 'ם', 'ח', 'ל', 'ג', 'ד', 'ה', 'ב', 'א']):
                    return fixed
        except:
            pass

        # Return original if no fix worked
        return text

    except Exception:
        # Return original text if any error occurs
        return text


def create_shapefile_zip_package(shp_path: str, output_dir: str) -> str:
    """
    Create a ZIP package containing all shapefile components.

    Args:
        shp_path: Path to the main .shp file
        output_dir: Output directory for the ZIP file

    Returns:
        Path to the created ZIP file
    """
    import zipfile
    from pathlib import Path

    base_path = Path(shp_path).with_suffix('')
    zip_path = Path(output_dir) / f"{base_path.name}_shapefile.zip"

    # List of shapefile extensions to include
    shapefile_extensions = ['.shp', '.shx', '.dbf', '.prj', '.cpg', '.xml']

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for ext in shapefile_extensions:
            component_path = base_path.with_suffix(ext)
            if component_path.exists():
                # Add file to ZIP with just the filename (no path)
                zipf.write(component_path, component_path.name)

    return str(zip_path)


def load_shapefile_robust(shp_path: str):
    """
    Load shapefile with robust error handling for missing companion files.

    Args:
        shp_path: Path to the .shp file

    Returns:
        GeoDataFrame containing the shapefile data

    Raises:
        Exception: If shapefile cannot be loaded or repaired
    """
    import geopandas as gpd
    import os
    from pathlib import Path

    try:
        # First, try loading normally
        return gpd.read_file(shp_path)

    except Exception as e:
        # If loading fails, try to handle missing companion files
        if "shx" in str(e).lower():
            # Missing .shx file - try to recreate it or use alternative approach
            try:
                # Set GDAL/OGR configuration to restore SHX
                os.environ['SHAPE_RESTORE_SHX'] = 'YES'

                # Try loading again
                gdf = gpd.read_file(shp_path)

                import streamlit as st
                st.warning("⚠️ Recreated missing .shx index file. Shapefile loaded successfully.")

                return gdf

            except Exception as e2:
                # If that fails, try creating minimal companion files
                try:
                    return create_minimal_shapefile_companions(shp_path)
                except Exception as e3:
                    raise Exception(f"Could not load shapefile. Original error: {e}. "
                                  f"Recovery attempts failed: {e2}, {e3}. "
                                  f"Please upload a complete shapefile package as a ZIP file.")
        else:
            # Different error - re-raise
            raise e


def create_minimal_shapefile_companions(shp_path: str):
    """
    Create minimal companion files for a standalone .shp file.

    Args:
        shp_path: Path to the .shp file

    Returns:
        GeoDataFrame if successful
    """
    import geopandas as gpd
    from pathlib import Path
    import struct

    base_path = Path(shp_path).with_suffix('')

    # Try to create a minimal .shx file by reading the .shp header
    try:
        with open(shp_path, 'rb') as shp_file:
            # Read SHP header to get basic info
            shp_file.seek(24)  # Skip to file length
            file_length = struct.unpack('>I', shp_file.read(4))[0]

            # Create minimal .shx file
            shx_path = base_path.with_suffix('.shx')
            with open(shx_path, 'wb') as shx_file:
                # Write SHX header (100 bytes)
                shx_header = bytearray(100)

                # File code (9994)
                struct.pack_into('>I', shx_header, 0, 9994)
                # File length (50 + number of records * 4)
                struct.pack_into('>I', shx_header, 24, 50)  # Minimal size
                # Version (1000)
                struct.pack_into('<I', shx_header, 28, 1000)
                # Shape type (from SHP file)
                shp_file.seek(32)
                shape_type = struct.unpack('<I', shp_file.read(4))[0]
                struct.pack_into('<I', shx_header, 32, shape_type)

                shx_file.write(shx_header)

        # Now try to load with the created .shx
        return gpd.read_file(shp_path)

    except Exception:
        # If SHX creation fails, try loading as a different format or with fiona directly
        import fiona
        try:
            # Use fiona directly which might be more tolerant
            with fiona.open(shp_path) as src:
                features = list(src)
                crs = src.crs

            # Convert to GeoDataFrame
            import geopandas as gpd
            gdf = gpd.GeoDataFrame.from_features(features, crs=crs)

            import streamlit as st
            st.warning("⚠️ Loaded shapefile using alternative method. Some features may be missing.")

            return gdf

        except Exception:
            raise Exception("Could not load or repair shapefile. Please upload a complete shapefile package.")


def main():
    """Main Streamlit application entry point"""

    # Initialize current page in session state if not exists
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Dataset Control"

    # Define pages with professional icons using Unicode symbols
    page_configs = [
        ("Azimuth Preprocessing", "🧭", "Azimuth Preprocessing"),
        ("Dataset Control", "🛡️", "Dataset Control"),
        ("Aggregation", "⏰", "Aggregation"),
        ("Aggregated Maps", "🗺️", "Aggregated Maps"),
        ("Azimuth Methodology", "📐", "Azimuth Methodology"),
        ("Control Methodology", "🔬", "Control Methodology"),
        ("Aggregation Methodology", "📚", "Aggregation Methodology")
    ]

    # Try professional option menu first
    if HAS_OPTION_MENU:
        # Use streamlit-option-menu for professional navigation in sidebar
        with st.sidebar:
            st.markdown("### Navigation")

            selected_page = option_menu(
                menu_title=None,
                options=[config[0] for config in page_configs],
                icons=["compass", "shield-check", "clock", "map", "rulers", "tools", "book"],
                menu_icon="cast",
                default_index=0,
                orientation="vertical",
                key="nav_menu",
                styles={
                    "container": {"padding": "0!important", "background-color": "#f0f2f6"},
                    "icon": {"color": "#0068c9", "font-size": "16px"},
                    "nav-link": {
                        "font-size": "14px",
                        "text-align": "left",
                        "margin": "0px",
                        "color": "#262730",
                        "background-color": "#f0f2f6",
                        "--hover-color": "#e8f4f8"
                    },
                    "nav-link-selected": {
                        "background-color": "#e8f4f8",
                        "color": "#000000 !important",
                        "font-weight": "bold"
                    },
                }
            )
    else:
        # Fallback to enhanced radio buttons with Unicode icons
        st.sidebar.markdown("""
        <div style="display: flex; align-items: center; margin-bottom: 1rem;">
            <span style="font-size: 24px; margin-right: 8px;">🧭</span>
            <h3 style="margin: 0;">Navigation</h3>
        </div>
        """, unsafe_allow_html=True)

        # Get current page for radio button selection
        current_page = st.session_state.current_page
        pages = [config[0] for config in page_configs]
        current_index = pages.index(current_page) if current_page in pages else 0

        # Create enhanced radio options with icons
        radio_options = []
        for page_key, icon, display_name in page_configs:
            radio_options.append(f"{icon} {display_name}")

        selected_option = st.sidebar.radio(
            "Choose a page:",
            radio_options,
            index=current_index,
            key="page_radio"
        )

        # Extract page key from selected option
        selected_page = None
        for i, (page_key, icon, display_name) in enumerate(page_configs):
            if selected_option == f"{icon} {display_name}":
                selected_page = page_key
                break
    
    # Update session state only if page actually changed
    if selected_page != st.session_state.current_page:
        st.session_state.current_page = selected_page
        # Clear the "just completed processing" flag when navigating away from results
        if 'just_completed_processing' in st.session_state:
            del st.session_state.just_completed_processing
        st.rerun()
    
    # Use the current page from session state (not the selected page) to avoid conflicts
    page = st.session_state.current_page

    if page == "Aggregation":
        main_processing_page()
    elif page == "Aggregated Maps":
        maps_page()
    elif page == "Dataset Control":
        control_page()
    elif page == "Azimuth Preprocessing":
        azimuth_page()
    elif page == "Aggregation Methodology":
        methodology_page()
    elif page == "Control Methodology":
        control_methodology_page()
    elif page == "Azimuth Methodology":
        azimuth_methodology_page()


def maps_page():
    """Maps visualization page"""
    try:
        render_maps_page()
    except Exception as e:
        st.error(f"❌ Error in main maps page: {e}")
        st.info("🔧 Error details:")
        import traceback
        st.code(traceback.format_exc())
        st.info("💡 Try refreshing the page or check the data files.")


def main_processing_page():
    """Main processing page"""
    st.title("⏰ Data Aggregation")
    st.markdown("---")
    st.markdown("### Process large-scale traffic monitoring datasets with configurable parameters")
    st.markdown("")

    # Sidebar now only contains navigation - methodology moved to dedicated page

    # Main application layout
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("""
        <div style="background-color: #f0f2f6; padding: 1rem; border-radius: 8px; margin-bottom: 1.5rem; border-left: 5px solid #1f77b4;">
            <h2 style="margin: 0; color: #1f77b4;">⚙️ Configuration</h2>
        </div>
        """, unsafe_allow_html=True)

        # File Input Section
        st.markdown("#### 📁 File Input")
        uploaded_file = st.file_uploader(
            "Upload CSV file containing Google Maps link monitoring data",
            type=['csv'],
            help="Select a CSV file with the required columns"
        )

        # Automatic folder detection for control output files
        extracted_folder_info = None
        if uploaded_file is not None:
            file_name = uploaded_file.name
            if any(keyword in file_name.lower() for keyword in ['best_valid', 'failed_observations', 'validated_data']):
                st.info("💡 **Control output file detected!**")

                # Ask for log file to auto-extract timestamp
                st.markdown("**Upload the log file to auto-detect folder timestamp:**")
                log_file = st.file_uploader(
                    "Upload performance_and_parameters_log.txt",
                    type=['txt', 'log'],
                    help="Upload the log file from the same control output folder",
                    key="log_file_uploader"
                )

                if log_file:
                    try:
                        # Read log file content
                        log_content = log_file.read().decode('utf-8')

                        # Extract date and time from log
                        import re
                        date_match = re.search(r'Run Date:\s*(\d{4})-(\d{2})-(\d{2})', log_content)
                        time_match = re.search(r'Start Time:\s*(\d{2}):(\d{2}):(\d{2})', log_content)

                        if date_match and time_match:
                            year, month, day = date_match.groups()
                            hour, minute, second = time_match.groups()

                            # Format as DD_MM_YY_HH_MM
                            timestamp = f"{day}_{month}_{year[2:]}_{hour}_{minute}"
                            extracted_folder_info = timestamp
                            st.success(f"✅ **Auto-detected timestamp from log:** `{timestamp}`")
                            st.success(f"✅ **Output folder:** `from_control_{timestamp}`")
                        else:
                            st.warning("⚠️ Could not extract timestamp from log file. Please enter manually below.")
                    except Exception as e:
                        st.error(f"❌ Error reading log file: {e}")

                # Manual input fallback
                if not extracted_folder_info:
                    st.markdown("**OR enter timestamp manually:**")
                    control_folder = st.text_input(
                        "Control folder timestamp (e.g., 05_10_25_16_36)",
                        help="Enter the timestamp from your control output folder path",
                        placeholder="DD_MM_YY_HH_MM",
                        key="control_folder_input"
                    )

                    if control_folder:
                        import re
                        if re.match(r'\d{2}_\d{2}_\d{2}_\d{2}_\d{2}', control_folder):
                            extracted_folder_info = control_folder
                            st.success(f"✅ **Output folder:** `from_control_{control_folder}`")
                        else:
                            st.error("❌ Invalid format. Use DD_MM_YY_HH_MM (e.g., 05_10_25_16_36)")
                            extracted_folder_info = None
        
        # Output Directory Section
        st.markdown("#### 📂 Output Directory")
        output_dir = st.text_input(
            "Output directory path",
            value="runs/1_10_25/output/aggregation",
            help="Directory where processed files will be saved. Will be created if it doesn't exist."
        )
        
        # Basic Parameters Section
        st.markdown("#### ⚙️ Basic Parameters")
        
        # Chunk size for memory management
        chunk_size = st.number_input(
            "Chunk size for CSV reading",
            min_value=1000,
            max_value=1000000,
            value=50000,
            step=10000,
            help="Number of rows to process at once. Larger values use more memory but may be faster."
        )
        
        # Minimum valid rows per hour
        min_valid_per_hour = st.number_input(
            "Minimum valid rows per hour",
            min_value=1,
            max_value=100,
            value=1,
            help="""
            **Data Quality Threshold:** Minimum number of valid data points required for an hour to be considered reliable.
            
            **How it works:**
            - Each hour is grouped by link and time
            - Only hours with at least this many valid measurements are included in weekly profiles
            - Hours below this threshold are marked as invalid and excluded from analysis
            
            **Examples for different data frequencies:**
            - **15-minute data (4 per hour):** Value = 1-3 (since max possible is 4)
            - **5-minute data (12 per hour):** Value = 3-8 
            - **1-minute data (60 per hour):** Value = 10-30
            
            **For your 15-minute data:**
            - Value = 1: Include hours with at least 1 measurement (very lenient)
            - Value = 2: Include hours with at least 2 measurements (balanced)
            - Value = 3: Include hours with at least 3 measurements (strict, requires 75% coverage)
            - Value = 4: Include hours with all 4 measurements (perfect coverage only)
            
            **Recommendation:** For 15-minute data, use 1-2 for good coverage, 3-4 for high quality only.
            """
        )
        
        # Timestamp and Timezone Configuration
        st.markdown("#### 🕐 Timestamp Configuration")
        
        col_tz, col_fmt = st.columns(2)
        
        with col_tz:
            timezone = st.selectbox(
                "Timezone",
                options=[
                    "Asia/Jerusalem", "UTC", "Europe/London", "Europe/Paris", 
                    "America/New_York", "America/Los_Angeles", "Asia/Tokyo"
                ],
                index=0,  # Default to Asia/Jerusalem
                help="Timezone for timestamp parsing. Naive timestamps will be localized to this timezone."
            )
        
        with col_fmt:
            timestamp_format = st.text_input(
                "Timestamp format",
                value="%Y-%m-%d %H:%M:%S",
                help="Python strptime format for parsing timestamps. The system automatically tries common formats like DD/MM/YYYY HH:MM, YYYY-MM-DD HH:MM:SS, etc. Only specify if you have an unusual format."
            )
        
        # Date Range Configuration
        if 'auto_detected_dates' in st.session_state:
            st.markdown("#### 📅 Date Range Filters ✨ Auto-detected")
        else:
            st.markdown("#### 📅 Date Range Filters")
        
        col_start, col_end = st.columns(2)
        
        # Use detected dates as defaults if available
        default_start = None
        default_end = None
        if 'auto_detected_dates' in st.session_state:
            default_start = st.session_state.auto_detected_dates['start']
            default_end = st.session_state.auto_detected_dates['end']
            
            # Add option to clear auto-detected dates
            col_info, col_reset = st.columns([3, 1])
            with col_info:
                st.caption(f"📅 Using auto-detected range: {default_start} to {default_end}")
            with col_reset:
                if st.button("🗑️ Clear", help="Clear auto-detected dates to set custom range"):
                    del st.session_state.auto_detected_dates
                    st.rerun()
        
        with col_start:
            # Use default_start if available, otherwise use today's date as fallback
            start_value = default_start if default_start is not None else date.today()
            start_date = st.date_input(
                "Start date (inclusive)",
                value=start_value,
                key="start_date_input",
                help="Filter data from this date onwards. Leave empty to include all dates from the beginning."
            )
            # If no auto-detected date and user hasn't changed from today, treat as None
            if default_start is None and start_date == date.today():
                start_date = None
        
        with col_end:
            # Use default_end if available, otherwise use today's date as fallback  
            end_value = default_end if default_end is not None else date.today()
            end_date = st.date_input(
                "End date (inclusive)", 
                value=end_value,
                key="end_date_input",
                help="Filter data up to this date. Leave empty to include all dates to the end."
            )
            # If no auto-detected date and user hasn't changed from today, treat as None
            if default_end is None and end_date == date.today():
                end_date = None
        
        # Validate date range
        if start_date and end_date and start_date > end_date:
            st.error("❌ Start date must be before or equal to end date")
        
        # Time Filters Configuration
        st.markdown("#### ⏰ Time Filters")
        
        # Weekday selection
        weekday_options = [
            ("Monday", 0), ("Tuesday", 1), ("Wednesday", 2), ("Thursday", 3),
            ("Friday", 4), ("Saturday", 5), ("Sunday", 6)
        ]
        
        selected_weekdays = st.multiselect(
            "Include weekdays",
            options=[opt[1] for opt in weekday_options],
            default=[0, 1, 2, 3, 4, 5, 6],  # Default to all days
            format_func=lambda x: next(opt[0] for opt in weekday_options if opt[1] == x),
            help="Select which days of the week to include in processing. Monday=0, Sunday=6."
        )
        
        # Hour selection
        hour_options = list(range(24))
        selected_hours = st.multiselect(
            "Include hours (0-23)",
            options=hour_options,
            default=hour_options,  # Default to all hours
            format_func=lambda x: f"{x:02d}:00",
            help="Select which hours of the day to include in processing. 0=midnight, 23=11PM."
        )
        
        # Advanced Configuration
        st.markdown("#### 🔧 Advanced Configuration")
        
        # Day Type Mapping
        with st.expander("Day Type Mapping", expanded=False):
            st.markdown("Map raw DayType values from CSV to standard categories:")
            
            col_dt1, col_dt2, col_dt3 = st.columns(3)
            
            with col_dt1:
                weekday_mapping = st.text_area(
                    "Weekday values (one per line)",
                    value="יום חול\nחול\nweekday",
                    help="DayType values that should be classified as weekdays"
                )
            
            with col_dt2:
                weekend_mapping = st.text_area(
                    "Weekend values (one per line)",
                    value="סוף שבוע\nשבת\nweekend",
                    help="DayType values that should be classified as weekends"
                )
            
            with col_dt3:
                holiday_mapping = st.text_area(
                    "Holiday values (one per line)",
                    value="חג\nholiday",
                    help="DayType values that should be classified as holidays"
                )
        
        # Holiday Processing
        with st.expander("Holiday Processing", expanded=False):
            use_holidays = st.checkbox(
                "Enable automatic holiday detection",
                value=True,
                help="Use Python holidays library to automatically detect Israeli holidays"
            )
            
            if use_holidays:
                holidays_treatment = st.radio(
                    "Treat holidays as:",
                    options=["weekend", "holiday"],
                    index=1,
                    help="How to categorize automatically detected holidays"
                )
                
                custom_holidays_file = st.file_uploader(
                    "Custom holidays file (optional)",
                    type=['txt', 'ics'],
                    help="Upload a text file with ISO dates (YYYY-MM-DD) or ICS calendar file to override automatic detection"
                )
            else:
                holidays_treatment = "weekend"
                custom_holidays_file = None
        
        # Data Validation Ranges
        with st.expander("Data Validation Ranges", expanded=False):
            st.markdown("Set acceptable ranges for numeric validation:")
            
            col_dur, col_dist, col_speed = st.columns(3)
            
            with col_dur:
                duration_min = st.number_input("Min duration (seconds)", value=0, min_value=0)
                duration_max = st.number_input("Max duration (seconds)", value=7200, min_value=1)
            
            with col_dist:
                distance_min = st.number_input("Min distance (meters)", value=0, min_value=0)
                distance_max = st.number_input("Max distance (meters)", value=50000, min_value=1)
            
            with col_speed:
                speed_min = st.number_input("Min speed (km/h)", value=0, min_value=0)
                speed_max = st.number_input("Max speed (km/h)", value=200, min_value=1)
        
        # Valid Codes and Link Filters
        with st.expander("Data Filtering Options", expanded=False):
            valid_codes = st.text_input(
                "Valid codes (comma-separated)",
                value="OK,VALID,1",
                help="When using valid_code column, only these codes will be considered valid"
            )
            
            col_wl, col_bl = st.columns(2)
            
            with col_wl:
                link_whitelist = st.text_area(
                    "Link whitelist (one per line)",
                    value="",
                    help="If specified, only process these link IDs. Leave empty to process all links."
                )
            
            with col_bl:
                link_blacklist = st.text_area(
                    "Link blacklist (one per line)", 
                    value="",
                    help="Exclude these link IDs from processing. Applied after whitelist."
                )
        
        # Processing Options
        with st.expander("Processing Options", expanded=False):
            col_opt1, col_opt2 = st.columns(2)
            
            with col_opt1:
                weekly_grouping = st.radio(
                    "Weekly profile grouping",
                    options=["daytype", "weekday_index"],
                    index=0,
                    help="Group weekly profiles by daytype categories or individual weekday indices"
                )
                
                recompute_std = st.checkbox(
                    "Recompute standard deviation from raw data",
                    value=False,
                    help="If checked, compute stddur from pooled raw data. Otherwise use mean of hourly std values."
                )
            
            with col_opt2:
                generate_quality_reports = st.checkbox(
                    "Generate quality reports",
                    value=True,
                    help="Create quality_by_link.csv and invalid_reason_counts.csv files"
                )
                
                output_parquet = st.checkbox(
                    "Output Parquet files",
                    value=False,
                    help="Save intermediate results as Parquet files for faster downstream processing"
                )
        
        # Store all configuration in session state
        if 'full_config' not in st.session_state:
            st.session_state.full_config = {}
        
        # Parse text inputs into lists
        weekday_values = [line.strip() for line in weekday_mapping.split('\n') if line.strip()]
        weekend_values = [line.strip() for line in weekend_mapping.split('\n') if line.strip()]
        holiday_values = [line.strip() for line in holiday_mapping.split('\n') if line.strip()]
        valid_codes_list = [code.strip() for code in valid_codes.split(',') if code.strip()]
        whitelist_links = [link.strip() for link in link_whitelist.split('\n') if link.strip()]
        blacklist_links = [link.strip() for link in link_blacklist.split('\n') if link.strip()]
        
        st.session_state.full_config.update({
            'uploaded_file': uploaded_file,
            'extracted_folder_info': extracted_folder_info,
            'output_dir': output_dir,
            'chunk_size': chunk_size,
            'min_valid_per_hour': min_valid_per_hour,
            'timezone': timezone,
            'timestamp_format': timestamp_format,
            'start_date': start_date,
            'end_date': end_date,
            'selected_weekdays': selected_weekdays,
            'selected_hours': selected_hours,
            'daytype_mapping': {
                'weekday': weekday_values,
                'weekend': weekend_values,
                'holiday': holiday_values
            },
            'use_holidays': use_holidays,
            'holidays_treatment': holidays_treatment,
            'custom_holidays_file': custom_holidays_file,
            'duration_range': (duration_min, duration_max),
            'distance_range': (distance_min, distance_max),
            'speed_range': (speed_min, speed_max),
            'valid_codes': valid_codes_list,
            'link_whitelist': whitelist_links,
            'link_blacklist': blacklist_links,
            'weekly_grouping': weekly_grouping,
            'recompute_std': recompute_std,
            'generate_quality_reports': generate_quality_reports,
            'output_parquet': output_parquet
        })
        
        # Show configuration summary
        if len(selected_weekdays) == 0:
            st.warning("⚠️ No weekdays selected - no data will be processed")
        elif len(selected_hours) == 0:
            st.warning("⚠️ No hours selected - no data will be processed")
        else:
            weekday_names = [next(opt[0] for opt in weekday_options if opt[1] == wd) for wd in selected_weekdays]
            st.info(f"📊 Will process {len(selected_weekdays)} weekdays ({', '.join(weekday_names)}) and {len(selected_hours)} hours")
            
            # Debug information
            with st.expander("🔍 Debug Information", expanded=False):
                st.write("**Selected Parameters:**")
                st.write(f"- Weekdays: {selected_weekdays}")
                st.write(f"- Hours: {len(selected_hours)} hours (0-{max(selected_hours) if selected_hours else 'none'})")
                st.write(f"- Min valid per hour: {min_valid_per_hour}")
                st.write(f"- Date range: {start_date} to {end_date}")
                st.write(f"- Timezone: {timezone}")
                st.write(f"- Timestamp format: {timestamp_format}")
        
        # Show file validation status and auto-detect date range
        if uploaded_file is not None:
            st.success(f"✅ File uploaded: {uploaded_file.name} ({uploaded_file.size:,} bytes)")
            
            # Basic file validation and date range detection
            try:
                # Read sample to validate columns and detect date range
                # First detect encoding, then read with proper encoding
                from components.aggregation.pipeline import detect_file_encoding
                
                # Save uploaded file temporarily to detect encoding
                temp_file_path = save_uploaded_file(uploaded_file)
                try:
                    detected_encoding = detect_file_encoding(temp_file_path)
                    sample_df = pd.read_csv(temp_file_path, nrows=1000, encoding=detected_encoding)
                finally:
                    # Clean up temp file
                    Path(temp_file_path).unlink(missing_ok=True)
                    # Reset file pointer for later use
                    uploaded_file.seek(0)
                # Use the proper validation function from processing.py
                from components.aggregation.pipeline import validate_csv_columns
                is_valid, missing_columns = validate_csv_columns(sample_df)
                
                if not is_valid:
                    st.error(f"❌ Missing required columns: {', '.join(missing_columns)}")
                    st.info("💡 **Tip**: The system supports flexible column names. For example:")
                    st.info("• `Duration (seconds)` is accepted for `Duration`")
                    st.info("• `Distance (meters)` is accepted for `Distance`") 
                    st.info("• `Speed (km/h)` is accepted for `Speed`")
                else:
                    st.success("✅ All required columns found")
                    
                    # Auto-detect date range from the file
                    if 'Timestamp' in sample_df.columns:
                        try:
                            # Clean timestamp strings first
                            cleaned_timestamps = sample_df['Timestamp'].astype(str).str.strip()
                            
                            # Try multiple timestamp formats for better compatibility
                            timestamp_formats = [
                                timestamp_format,  # User-specified format
                                '%d/%m/%Y %H:%M',  # European format DD/MM/YYYY HH:MM (common)
                                '%Y-%m-%d %H:%M:%S',  # Default format YYYY-MM-DD HH:MM:SS
                                '%d/%m/%Y %H:%M:%S',  # European format DD/MM/YYYY HH:MM:SS
                                '%m/%d/%Y %H:%M',  # US format MM/DD/YYYY HH:MM
                                '%m/%d/%Y %H:%M:%S',  # US format MM/DD/YYYY HH:MM:SS
                                '%Y-%m-%d %H:%M',  # ISO format without seconds
                                '%Y-%m-%d %H:%M:%S.%f',  # With microseconds
                                '%d-%m-%Y %H:%M:%S',  # European with dashes
                                '%d-%m-%Y %H:%M',  # European with dashes, no seconds
                            ]
                            
                            timestamps = None
                            successful_format = None
                            for fmt in timestamp_formats:
                                try:
                                    timestamps = pd.to_datetime(cleaned_timestamps, format=fmt, errors='coerce')
                                    success_rate = (len(timestamps) - timestamps.isna().sum()) / len(timestamps)
                                    if success_rate > 0.5:  # At least 50% success rate
                                        successful_format = fmt
                                        break
                                except:
                                    continue
                            
                            # Fallback to automatic parsing
                            if timestamps is None or timestamps.isna().all():
                                timestamps = pd.to_datetime(cleaned_timestamps, errors='coerce')
                                successful_format = "automatic"
                            
                            valid_timestamps = timestamps.dropna()
                            
                            # Filter out unrealistic dates (likely test/placeholder data)
                            current_year = pd.Timestamp.now().year
                            realistic_timestamps = valid_timestamps[
                                (valid_timestamps.dt.year >= current_year - 10) & 
                                (valid_timestamps.dt.year <= current_year + 10)
                            ]
                            
                            # Use realistic timestamps if available, otherwise use all valid timestamps
                            timestamps_to_use = realistic_timestamps if not realistic_timestamps.empty else valid_timestamps
                            
                            if not timestamps_to_use.empty:
                                file_start_date = timestamps_to_use.min().date()
                                file_end_date = timestamps_to_use.max().date()
                                
                                                # Always update session state with detected dates (auto-update)
                                new_dates = {
                                    'start': file_start_date,
                                    'end': file_end_date
                                }
                                
                                # Only update and rerun if dates have changed
                                if ('auto_detected_dates' not in st.session_state or 
                                    st.session_state.auto_detected_dates != new_dates):
                                    st.session_state.auto_detected_dates = new_dates
                                    # Clear the date input widget states to force refresh
                                    for key in ['start_date_input', 'end_date_input']:
                                        if key in st.session_state:
                                            del st.session_state[key]
                                    st.rerun()
                                
                                st.success(f"📅 **Auto-detected date range:** {file_start_date} to {file_end_date}")
                                if successful_format and successful_format != timestamp_format:
                                    st.info(f"🔍 **Auto-detected timestamp format:** `{successful_format}` (different from your setting)")
                                    st.caption("The system automatically detected and used the correct format for your data")
                                elif successful_format:
                                    st.caption(f"Date range filters have been automatically set to match your data (format: {successful_format})")
                                else:
                                    st.caption("Date range filters have been automatically set to match your data")
                                
                                # Suggest optimal min_valid_per_hour based on data frequency
                                total_rows = len(sample_df)
                                unique_hours = len(valid_timestamps.dt.floor('H').unique()) if not valid_timestamps.empty else 1
                                avg_rows_per_hour = total_rows / unique_hours if unique_hours > 0 else 1
                                
                                # Determine data frequency and suggest appropriate threshold
                                if avg_rows_per_hour >= 50:
                                    suggested_min = 10
                                    frequency = "1-minute data"
                                elif avg_rows_per_hour >= 10:
                                    suggested_min = 5
                                    frequency = "5-minute data"
                                elif avg_rows_per_hour >= 3:
                                    suggested_min = 2
                                    frequency = "15-minute data"
                                elif avg_rows_per_hour >= 1:
                                    suggested_min = 1
                                    frequency = "hourly or sparse data"
                                else:
                                    suggested_min = 1
                                    frequency = "very sparse data"
                                
                                st.info(f"💡 **Suggested minimum valid rows per hour:** {suggested_min}")
                                st.caption(f"Detected {frequency} (~{avg_rows_per_hour:.1f} rows/hour)")
                                    
                        except Exception as date_error:
                            st.warning(f"⚠️ Could not detect date range: {date_error}")
                            # Clear any previous auto-detected dates on error
                            if 'auto_detected_dates' in st.session_state:
                                del st.session_state.auto_detected_dates
                    
            except Exception as e:
                st.error(f"❌ Error reading file: {str(e)}")
        else:
            st.info("Please upload a CSV file to begin")
            # Clear auto-detected dates when no file is uploaded
            if 'auto_detected_dates' in st.session_state:
                del st.session_state.auto_detected_dates
        
    with col2:
        st.markdown("""
        <div style="background-color: #f0f2f6; padding: 1rem; border-radius: 8px; margin-bottom: 1.5rem; border-left: 5px solid #28a745;">
            <h2 style="margin: 0; color: #28a745;">📊 Results</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Run Processing Button
        can_run = (uploaded_file is not None and 
                  len(selected_weekdays) > 0 and 
                  len(selected_hours) > 0 and
                  (not start_date or not end_date or start_date <= end_date))
        
        if st.button("🚀 Run Processing", disabled=not can_run, use_container_width=True, type="primary"):
            if can_run:
                run_processing()
            else:
                st.error("Please fix configuration issues before running")
        
        if not can_run:
            st.warning("⚠️ Please upload a file and configure valid parameters to run processing")

        # Display results if processing was completed
        if 'processing_results' in st.session_state:
            results = st.session_state.processing_results
            if results.get('success', False):
                st.success("🎉 Processing completed successfully!")

                hourly_df = results.get('hourly_df', pd.DataFrame())
                weekly_df = results.get('weekly_df', pd.DataFrame())
                output_files = results.get('output_files', {})

                # Show summary statistics
                st.subheader("📊 Summary")

                if not hourly_df.empty:
                    st.metric("Hourly Records", f"{len(hourly_df):,}")

                if not weekly_df.empty:
                    st.metric("Weekly Patterns", f"{len(weekly_df):,}")

                if output_files:
                    st.metric("Output Files", len(output_files))

                # Show preview of results
                if not hourly_df.empty:
                    with st.expander("📋 Hourly Data Preview", expanded=False):
                        st.dataframe(hourly_df.head(10), use_container_width=True)

                if not weekly_df.empty:
                    with st.expander("📅 Weekly Profile Preview", expanded=False):
                        st.dataframe(weekly_df.head(10), use_container_width=True)

                # Download section
                if output_files:
                    st.subheader("📥 Downloads")
                    for file_type, file_path in output_files.items():
                        if Path(file_path).exists():
                            with open(file_path, 'rb') as f:
                                file_data = f.read()

                            # Determine file extension and MIME type
                            file_ext = Path(file_path).suffix.lower()
                            if file_ext == '.csv':
                                mime_type = 'text/csv'
                            elif file_ext == '.json':
                                mime_type = 'application/json'
                            else:
                                mime_type = 'application/octet-stream'

                            st.download_button(
                                label=f"📄 {file_type.replace('_', ' ').title()}",
                                data=file_data,
                                file_name=Path(file_path).name,
                                mime=mime_type,
                                use_container_width=True
                            )

                # Option to clear results and run again
                if st.button("🔄 Run New Processing", use_container_width=True):
                    del st.session_state.processing_results
                    st.rerun()

            elif results.get('error_message'):
                st.error(f"❌ Processing failed: {results['error_message']}")
                # Option to clear error and try again
                if st.button("🔄 Try Again", use_container_width=True):
                    del st.session_state.processing_results
                    st.rerun()


# Sidebar methodology content removed - now available on dedicated Methodology page


def run_processing():
    """Execute the processing pipeline with configured parameters"""
    try:
        # Show processing status with progress information
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Get configuration from session state
            config = st.session_state.full_config
            
            status_text.text("🔧 Preparing processing parameters...")
            progress_bar.progress(10)
            
            # Prepare parameters for processing pipeline
            params = prepare_processing_parameters(config)
            
            status_text.text("💾 Saving uploaded file...")
            progress_bar.progress(20)
            
            # Save uploaded file temporarily
            temp_file_path = save_uploaded_file(config['uploaded_file'])
            params['input_file_path'] = temp_file_path
            
            status_text.text("📊 Getting input data preview...")
            progress_bar.progress(30)
            
            # Get a sample of parsed input for preview
            parsed_input_sample = get_parsed_input_sample(config['uploaded_file'], params)
            
            status_text.text("🚀 Running processing pipeline... This may take a few minutes for large files.")
            progress_bar.progress(40)
            
            # Run the processing pipeline
            hourly_df, weekly_df, output_files = run_pipeline(params)
            
            status_text.text("✅ Processing completed successfully!")
            progress_bar.progress(100)
            
            # Store results in session state
            st.session_state.processing_results = {
                'hourly_df': hourly_df,
                'weekly_df': weekly_df,
                'output_files': output_files,
                'parsed_input_sample': parsed_input_sample,
                'params': params,
                'success': True,
                'error_message': None
            }

            # Clean up temporary file
            Path(temp_file_path).unlink(missing_ok=True)
            
        except Exception as e:
            # Clean up temporary file on error
            if 'temp_file_path' in locals():
                Path(temp_file_path).unlink(missing_ok=True)
            raise e
            
        st.success("✅ Processing completed successfully!")
        st.rerun()
        
    except Exception as e:
        # Store error in session state
        st.session_state.processing_results = {
            'hourly_df': pd.DataFrame(),
            'weekly_df': pd.DataFrame(),
            'output_files': {},
            'params': {},
            'success': False,
            'error_message': str(e)
        }
        
        st.error(f"❌ Processing failed: {str(e)}")
        
        # Show detailed error information in expander
        with st.expander("Error Details", expanded=False):
            st.code(str(e))
            st.markdown("**Troubleshooting Tips:**")
            
            # Provide specific guidance based on error type
            error_str = str(e).lower()
            if "column" in error_str or "missing" in error_str:
                st.markdown("🔍 **Column Issues:**")
                st.markdown("- Verify your CSV has all required columns: DataID, Name, SegmentID, RouteAlternative, RequestedTime, Timestamp, DayInWeek, DayType, Duration, Distance, Speed, Url, Polyline")
                st.markdown("- Check for extra spaces or different column names")
                st.markdown("- Ensure column headers are in the first row")
            
            elif "timestamp" in error_str or "datetime" in error_str:
                st.markdown("📅 **Timestamp Issues:**")
                st.markdown("- Verify timestamp format matches your data (default: %Y-%m-%d %H:%M:%S)")
                st.markdown("- Check for missing or malformed timestamp values")
                st.markdown("- Ensure timezone setting is appropriate for your data")
            
            elif "memory" in error_str or "size" in error_str:
                st.markdown("💾 **Memory Issues:**")
                st.markdown("- Try reducing chunk size (current: {})".format(st.session_state.full_config.get('chunk_size', 50000)))
                st.markdown("- Close other applications to free up memory")
                st.markdown("- Consider processing smaller date ranges")
            
            elif "file" in error_str or "path" in error_str:
                st.markdown("📁 **File Issues:**")
                st.markdown("- Ensure the uploaded file is a valid CSV")
                st.markdown("- Check that the output directory is writable")
                st.markdown("- Verify file is not corrupted or empty")
            
            else:
                st.markdown("🔧 **General Troubleshooting:**")
                st.markdown("- Check that your CSV file has all required columns")
                st.markdown("- Verify timestamp format matches your data")
                st.markdown("- Ensure date ranges are valid")
                st.markdown("- Try reducing chunk size if memory issues occur")
                st.markdown("- Check the processing log for more details")


def prepare_processing_parameters(config: dict) -> dict:
    """Convert GUI configuration to processing pipeline parameters"""

    # Create subdirectory based on input file name
    uploaded_file = config['uploaded_file']
    base_output_dir = config['output_dir']

    if uploaded_file is not None:
        # Get the filename without extension
        file_name = uploaded_file.name
        if file_name.endswith('.csv.zip'):
            base_name = file_name[:-8]  # Remove .csv.zip
        elif file_name.endswith('.csv'):
            base_name = file_name[:-4]  # Remove .csv
        else:
            base_name = Path(file_name).stem

        # If it's from control output, use automatic detection
        if 'best_valid_observations' in base_name or 'failed_observations' in base_name or 'validated_data' in base_name:
            # Check if we have extracted folder info from the UI
            extracted_folder_info = config.get('extracted_folder_info')
            if extracted_folder_info:
                extracted_folder_info = extracted_folder_info.strip()

            if extracted_folder_info:
                # Use the automatically detected folder
                subfolder = f"from_control_{extracted_folder_info}"
            else:
                # Fallback detection methods (same as in UI but server-side)
                extracted_folder = None

                try:
                    # Method 1: Check session state for recent control results
                    if 'control_results' in st.session_state and st.session_state.control_results.get('success'):
                        control_output_files = st.session_state.control_results.get('output_files', {})
                        if control_output_files:
                            sample_path = next(iter(control_output_files.values()))
                            extracted_folder = Path(sample_path).parent.name

                    # Method 2: Look for pattern in filename itself
                    if not extracted_folder:
                        import re
                        timestamp_pattern = r'(\d{2}_\d{2}_\d{2}_\d{2}_\d{2})'
                        match = re.search(timestamp_pattern, file_name)
                        if match:
                            extracted_folder = match.group(1)

                    # Method 3: Check recent control output directories
                    if not extracted_folder:
                        control_output_base = Path('./output/control')
                        if control_output_base.exists():
                            subdirs = [d for d in control_output_base.iterdir() if d.is_dir()]
                            if subdirs:
                                most_recent = max(subdirs, key=lambda x: x.stat().st_mtime)
                                extracted_folder = most_recent.name

                    # Use extracted folder or fallback
                    if extracted_folder:
                        subfolder = f"from_control_{extracted_folder}"
                    else:
                        # Final fallback: create timestamp-based folder
                        from datetime import datetime
                        timestamp = datetime.now().strftime("%d_%m_%y_%H_%M")
                        subfolder = f"from_control_{timestamp}_auto_fallback"

                except Exception:
                    # Exception fallback
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%d_%m_%y_%H_%M")
                    subfolder = f"from_control_{timestamp}_exception"
        else:
            # Use the file name as subfolder, cleaning it for filesystem safety
            subfolder = base_name.replace(' ', '_').replace('(', '').replace(')', '').replace('.', '_')

        # Create timestamped output directory
        output_dir = str(Path(base_output_dir) / subfolder)
    else:
        output_dir = base_output_dir

    params = {
        'output_dir': output_dir,
        'chunk_size': config['chunk_size'],
        'min_valid_per_hour': config['min_valid_per_hour'],
        'timezone': config['timezone'],
        'timestamp_format': config['timestamp_format'],
        'start_date': config['start_date'],
        'end_date': config['end_date'],
        'weekday_include': config['selected_weekdays'],
        'hours_include': config['selected_hours'],
        'daytype_mapping': config['daytype_mapping'],
        'use_holidays': config['use_holidays'],
        'holidays_treatment': config['holidays_treatment'],
        'duration_range_sec': config['duration_range'],
        'distance_range_m': config['distance_range'],
        'speed_range_kmh': config['speed_range'],
        'valid_codes_ok': config['valid_codes'],
        'whitelist_links': config['link_whitelist'] if config['link_whitelist'] else None,
        'blacklist_links': config['link_blacklist'] if config['link_blacklist'] else None,
        'weekly_grouping': config['weekly_grouping'],
        'recompute_std_from_raw': config['recompute_std'],
        'generate_quality_reports': config['generate_quality_reports'],
        'output_parquet': config['output_parquet']
    }
    
    # Handle custom holidays file if provided
    if config['custom_holidays_file'] is not None:
        # Save custom holidays file temporarily
        custom_holidays_path = Path(config['output_dir']) / 'custom_holidays.txt'
        Path(config['output_dir']).mkdir(parents=True, exist_ok=True)
        
        with open(custom_holidays_path, 'wb') as f:
            f.write(config['custom_holidays_file'].getvalue())
        
        params['custom_holidays_file'] = str(custom_holidays_path)
    else:
        params['custom_holidays_file'] = None
    
    return params


def get_parsed_input_sample(uploaded_file, params: dict) -> pd.DataFrame:
    """Get a sample of parsed input data for preview"""
    try:
        # Reset file pointer
        uploaded_file.seek(0)
        
        # Read a small sample (first 100 rows) for preview
        # Save uploaded file temporarily to detect encoding
        temp_file_path = save_uploaded_file(uploaded_file)
        try:
            from components.aggregation.pipeline import detect_file_encoding
            detected_encoding = detect_file_encoding(temp_file_path)
            sample_df = pd.read_csv(temp_file_path, nrows=100, encoding=detected_encoding)
        finally:
            # Clean up temp file
            Path(temp_file_path).unlink(missing_ok=True)
        
        # Apply basic column normalization like the processing pipeline does
        from components.aggregation.pipeline import normalize_column_names, validate_csv_columns
        
        # Validate columns
        is_valid, missing_cols = validate_csv_columns(sample_df)
        if not is_valid:
            return pd.DataFrame()  # Return empty if validation fails
        
        # Normalize column names
        sample_df = normalize_column_names(sample_df)
        
        # Reset file pointer for later use
        uploaded_file.seek(0)
        
        return sample_df
        
    except Exception as e:
        # Return empty DataFrame on error
        return pd.DataFrame()


def save_uploaded_file(uploaded_file) -> str:
    """Save uploaded file to temporary location and return path"""
    import tempfile
    import os
    
    # Create temporary file
    temp_fd, temp_path = tempfile.mkstemp(suffix='.csv', prefix='maps_data_')
    
    try:
        # Write uploaded file content to temporary file as binary to preserve encoding
        with os.fdopen(temp_fd, 'wb') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
        
        return temp_path
    except Exception as e:
        # Clean up on error
        try:
            os.close(temp_fd)
        except:
            pass
        Path(temp_path).unlink(missing_ok=True)
        raise e


def display_processing_results():
    """Display processing results with preview tables and download links"""
    results = st.session_state.processing_results
    
    if not results['success']:
        st.error(f"❌ Processing failed: {results['error_message']}")
        return
    
    hourly_df = results['hourly_df']
    weekly_df = results['weekly_df']
    output_files = results['output_files']
    
    # Show summary statistics
    st.subheader("📊 Processing Summary")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Hourly Records", f"{len(hourly_df):,}")
    
    with col2:
        st.metric("Weekly Patterns", f"{len(weekly_df):,}")
    
    with col3:
        st.metric("Output Files", len(output_files))
    
    # Display preview tables
    st.subheader("📋 Data Previews")
    
    # Show parsed input preview if available
    if 'parsed_input_sample' in results:
        parsed_sample = results['parsed_input_sample']
        if not parsed_sample.empty:
            with st.expander("Parsed Input Preview", expanded=False):
                st.markdown(f"**Shape:** Sample of parsed input data")
                st.dataframe(parsed_sample.head(10), use_container_width=True)
    
    # Hourly aggregation preview
    if not hourly_df.empty:
        with st.expander("Hourly Aggregation Preview", expanded=True):
            st.markdown(f"**Shape:** {hourly_df.shape[0]:,} rows × {hourly_df.shape[1]} columns")
            
            # Show data types and basic info
            col_info, col_preview = st.columns([1, 2])
            
            with col_info:
                st.markdown("**Column Info:**")
                info_df = pd.DataFrame({
                    'Column': hourly_df.columns,
                    'Type': [str(dtype) for dtype in hourly_df.dtypes],
                    'Non-Null': [f"{hourly_df[col].notna().sum():,}" for col in hourly_df.columns]
                })
                st.dataframe(info_df, use_container_width=True, hide_index=True)
            
            with col_preview:
                st.markdown("**Sample Data:**")
                # Sort hourly data for preview
                hourly_preview = hourly_df.copy()
                
                # Ensure proper data types for sorting
                if 'date' in hourly_preview.columns and hourly_preview['date'].dtype == 'object':
                    try:
                        hourly_preview['date'] = pd.to_datetime(hourly_preview['date'])
                    except:
                        pass
                if 'hour_of_day' in hourly_preview.columns:
                    hourly_preview['hour_of_day'] = pd.to_numeric(hourly_preview['hour_of_day'], errors='coerce')
                
                sort_columns = []
                if 'link_id' in hourly_preview.columns:
                    sort_columns.append('link_id')
                if 'date' in hourly_preview.columns:
                    sort_columns.append('date')
                if 'hour_of_day' in hourly_preview.columns:
                    sort_columns.append('hour_of_day')
                
                if sort_columns:
                    hourly_preview = hourly_preview.sort_values(sort_columns, na_position='last')
                    hourly_preview = hourly_preview.reset_index(drop=True)
                
                st.dataframe(hourly_preview.head(25), use_container_width=True, height=300)
    
    # Weekly profile preview
    if not weekly_df.empty:
        with st.expander("Weekly Profile Preview", expanded=True):
            st.markdown(f"**Shape:** {weekly_df.shape[0]:,} rows × {weekly_df.shape[1]} columns")
            
            # Show data types and basic info
            col_info, col_preview = st.columns([1, 2])
            
            with col_info:
                st.markdown("**Column Info:**")
                info_df = pd.DataFrame({
                    'Column': weekly_df.columns,
                    'Type': [str(dtype) for dtype in weekly_df.dtypes],
                    'Non-Null': [f"{weekly_df[col].notna().sum():,}" for col in weekly_df.columns]
                })
                st.dataframe(info_df, use_container_width=True, hide_index=True)
            
            with col_preview:
                st.markdown("**Sample Data:**")
                # Sort weekly data for preview
                weekly_preview = weekly_df.copy()
                
                # Ensure proper data types for sorting
                if 'hour_of_day' in weekly_preview.columns:
                    weekly_preview['hour_of_day'] = pd.to_numeric(weekly_preview['hour_of_day'], errors='coerce')
                
                sort_columns = []
                if 'link_id' in weekly_preview.columns:
                    sort_columns.append('link_id')
                if 'daytype' in weekly_preview.columns:
                    sort_columns.append('daytype')
                if 'hour_of_day' in weekly_preview.columns:
                    sort_columns.append('hour_of_day')
                
                if sort_columns:
                    weekly_preview = weekly_preview.sort_values(sort_columns, na_position='last')
                    weekly_preview = weekly_preview.reset_index(drop=True)
                
                st.dataframe(weekly_preview.head(25), use_container_width=True, height=300)
    
    # Download section
    st.subheader("📥 Download Results")
    
    if output_files:
        # Create download buttons for each output file
        download_cols = st.columns(min(3, len(output_files)))
        
        for i, (file_type, file_path) in enumerate(output_files.items()):
            col_idx = i % 3
            
            with download_cols[col_idx]:
                if Path(file_path).exists():
                    with open(file_path, 'rb') as f:
                        file_data = f.read()
                    
                    # Determine file extension and MIME type
                    file_ext = Path(file_path).suffix.lower()
                    if file_ext == '.csv':
                        mime_type = 'text/csv'
                    elif file_ext == '.json':
                        mime_type = 'application/json'
                    elif file_ext == '.txt':
                        mime_type = 'text/plain'
                    elif file_ext == '.parquet':
                        mime_type = 'application/octet-stream'
                    else:
                        mime_type = 'application/octet-stream'
                    
                    # Create download button
                    st.download_button(
                        label=f"📄 {file_type.replace('_', ' ').title()}",
                        data=file_data,
                        file_name=Path(file_path).name,
                        mime=mime_type,
                        use_container_width=True
                    )
                else:
                    st.error(f"❌ File not found: {file_type}")
    
    # Show processing log if available
    if 'processing_log' in output_files:
        log_path = output_files['processing_log']
        if Path(log_path).exists():
            with st.expander("Processing Log", expanded=False):
                with open(log_path, 'r') as f:
                    log_content = f.read()
                st.text(log_content)
    
    # Quality metrics if available
    if not hourly_df.empty:
        st.subheader("📈 Data Quality Metrics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Valid hours distribution
            if 'valid_hour' in hourly_df.columns:
                valid_hours_count = hourly_df['valid_hour'].sum()
                total_hours = len(hourly_df)
                valid_percentage = (valid_hours_count / total_hours * 100) if total_hours > 0 else 0
                
                st.metric(
                    "Valid Hours", 
                    f"{valid_hours_count:,} / {total_hours:,}",
                    f"{valid_percentage:.1f}%"
                )
        
        with col2:
            # Links processed
            if 'link_id' in hourly_df.columns:
                unique_links = hourly_df['link_id'].nunique()
                st.metric("Unique Links", f"{unique_links:,}")
    
    # Success message with next steps
    st.success("✅ Processing completed successfully! You can download the results above.")
    
    # Option to run again
    if st.button("🔄 Run Again", use_container_width=True):
        # Clear results to allow new processing
        if 'processing_results' in st.session_state:
            del st.session_state.processing_results
        st.rerun()


def configure_parameters():
    """Render parameter configuration widgets with tooltips"""
    # This function is already implemented inline in main()
    pass


def display_results(hourly_df: pd.DataFrame, weekly_df: pd.DataFrame, file_paths: dict):
    """Show preview tables, charts, and download links"""
    # This functionality is now implemented in display_processing_results()
    pass


def create_visualizations(hourly_df: pd.DataFrame):
    """Generate heatmaps and histograms for data quality assessment"""
    # Placeholder - will be implemented in task 10
    pass


# Results page removed - now integrated into main processing page


# Control page functions moved to components/control/page.py


def methodology_page():
    """Methodology documentation page for hourly aggregation"""
    st.title("📚 Data Aggregation Methodology")
    st.markdown("---")
    st.markdown("")

    # Read and display the methodology from the processing component
    from pathlib import Path
    methodology_path = Path("components/aggregation/methodology.md")
    if methodology_path.exists():
        with open(methodology_path, "r", encoding="utf-8") as f:
            st.markdown(f.read())
    else:
        # Fallback content if file not found
        st.error("Methodology documentation file not found at components/aggregation/methodology.md")
        st.info("Please ensure the methodology.md file exists in the components/aggregation/ directory.")


def control_methodology_page():
    """Control methodology page - redirects to methodology.md"""
    st.title("🔬 Dataset Control Methodology")
    st.markdown("---")
    st.markdown("")

    # Read and display the methodology from the control component
    from pathlib import Path
    methodology_path = Path("components/control/methodology.md")
    if methodology_path.exists():
        with open(methodology_path, "r", encoding="utf-8") as f:
            st.markdown(f.read())
    else:
        st.error("Methodology documentation not found")


def azimuth_methodology_page():
    """Azimuth methodology page - redirects to methodology.md"""
    st.title("📐 Azimuth Preprocessing Methodology")
    st.markdown("---")
    st.markdown("")

    # Read and display the methodology from the azimuth component
    from pathlib import Path
    methodology_path = Path("components/azimuth/methodology.md")
    if methodology_path.exists():
        with open(methodology_path, "r", encoding="utf-8") as f:
            st.markdown(f.read())
    else:
        st.error("Methodology documentation not found")



# Schema documentation page removed - content integrated into Hour Aggregation Methodology


if __name__ == "__main__":
    main()
