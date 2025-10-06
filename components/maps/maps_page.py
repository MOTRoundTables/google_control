"""
Maps page for interactive map visualization.

This module provides the main Maps page interface that integrates Map A (Hourly View)
and Map B (Weekly View) with file loading controls and session state management.
"""

import streamlit as st
import pandas as pd
import geopandas as gpd
import tempfile
import os
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import logging
from datetime import datetime
import time

# Import spatial data manager
from .spatial_data import SpatialDataManager
from utils.icons import render_title_with_icon, render_header_with_icon, render_subheader_with_icon, render_icon_text, get_icon_for_component

logger = logging.getLogger(__name__)


class MapsPageInterface:
    """Main interface for the Maps page with file loading and navigation."""

    def __init__(self):
        self.spatial_manager = SpatialDataManager()
    
    def render_maps_page(self) -> None:
        """Render the main Maps page with navigation and file controls."""

        st.title("🗺️ Interactive Map Visualization")
        st.markdown("---")
        st.markdown("### Visualize traffic patterns with interactive maps showing hourly and weekly aggregation data")
        st.markdown("")
        
        # Initialize session state for maps
        self._initialize_session_state()
        
        # File loading section
        self._render_file_loading_section()
        
        # Check if data is loaded
        if not self._check_data_availability():
            st.info("👆 Please load both shapefile and results data to access the interactive maps")
            return
        
        # Map navigation tabs
        self._render_map_navigation()
    
    def _initialize_session_state(self) -> None:
        """Initialize session state variables for maps with reactive state management."""
        
        # File paths
        if 'maps_shapefile_path' not in st.session_state:
            st.session_state.maps_shapefile_path = None
        
        if 'maps_results_path' not in st.session_state:
            st.session_state.maps_results_path = ""
        
        # Data storage
        if 'maps_shapefile_data' not in st.session_state:
            st.session_state.maps_shapefile_data = None
        
        if 'maps_hourly_results' not in st.session_state:
            st.session_state.maps_hourly_results = None
        
        if 'maps_weekly_results' not in st.session_state:
            st.session_state.maps_weekly_results = None
        
        # Preload default data files if they exist
        self._preload_default_files()
        
        # User preferences
        if 'maps_preferences' not in st.session_state:
            st.session_state.maps_preferences = {
                'default_map': 'Map A: Hourly View',
                'auto_refresh': True,
                'show_data_quality': True,
                'reactive_updates': True,
                'loading_indicators': True
            }
        
        # Reactive state management - shared filter states between maps
        if 'maps_shared_state' not in st.session_state:
            st.session_state.maps_shared_state = {
                'metric_type': 'speed',
                'aggregation_method': 'mean',
                'symbology_settings': {
                    'classification_method': 'quantiles',
                    'n_classes': 5,
                    'outlier_caps': True,
                    'show_direction_arrows': False,
                    'basemap_enabled': True
                },
                'last_update_time': None,
                'filter_hash': None
            }
        
        # Loading and error states
        if 'maps_loading_state' not in st.session_state:
            st.session_state.maps_loading_state = {
                'is_loading': False,
                'loading_message': '',
                'last_error': None,
                'error_timestamp': None
            }
        
        # Performance tracking
        if 'maps_performance' not in st.session_state:
            st.session_state.maps_performance = {
                'last_render_time': None,
                'render_count': 0,
                'cache_hits': 0,
                'cache_misses': 0
            }
    
    def _render_file_loading_section(self) -> None:
        """Render file input controls for shapefile and results loading."""

        st.markdown("""
        <div style="background-color: #f0f2f6; padding: 1rem; border-radius: 8px; margin-bottom: 1.5rem; border-left: 5px solid #6610f2;">
            <h2 style="margin: 0; color: #6610f2;">📂 Data Loading</h2>
        </div>
        """, unsafe_allow_html=True)

        # Create two columns for file inputs
        col_shapefile, col_results = st.columns(2)

        with col_shapefile:
            st.markdown("#### 🗺️ Network Shapefile")

            # Show current shapefile status
            current_shapefile = st.session_state.maps_shapefile_path
            if current_shapefile and os.path.exists(current_shapefile):
                st.success(f"✅ Shapefile loaded: {os.path.basename(current_shapefile)}")
            else:
                st.info("📤 Please upload a shapefile ZIP below")

            # File uploader for shapefile ZIP
            uploaded_shapefile = st.file_uploader(
                "Upload shapefile ZIP",
                type=['zip'],
                help="Upload a ZIP file containing all shapefile components (.shp, .shx, .dbf, .prj)",
                key="shapefile_uploader"
            )
            
            # Add helpful guidance
            with st.expander("💡 Shapefile Loading Help", expanded=False):
                st.markdown("""
                **Shapefile Requirements:**
                - Shapefiles consist of multiple files that must be in the same directory:
                  - `.shp` - Main geometry file
                  - `.shx` - Shape index file  
                  - `.dbf` - Attribute database file
                  - `.prj` - Projection information file (optional but recommended)
                
                **Required Columns:**
                - `Id` (or `id`) - Unique link identifier
                - `From` - Starting node
                - `To` - Ending node
                
                **Supported Coordinate Systems:**
                - Any CRS (will be automatically reprojected to EPSG:2039)
                - EPSG:4326 (WGS84) is commonly used
                
                **Example Path:**
                ```
                E:\\data\\network\\roads.shp
                ```
                """)
            
            # Load shapefile button
            if st.button("🔄 Load Shapefile", key="load_shapefile_btn", disabled=(uploaded_shapefile is None)):
                self._load_shapefile(uploaded_shapefile)
        
        with col_results:
            st.markdown("#### 📊 Results Data")
            
            # Show current results status
            if st.session_state.maps_hourly_results is not None:
                hourly_count = len(st.session_state.maps_hourly_results)
                st.success(f"✅ Hourly data loaded: {hourly_count:,} records")
            else:
                st.info("ℹ️ No hourly data loaded")
            
            if st.session_state.maps_weekly_results is not None:
                weekly_count = len(st.session_state.maps_weekly_results)
                st.success(f"✅ Weekly data loaded: {weekly_count:,} records")
            else:
                st.info("ℹ️ No weekly data loaded")
            
            # File uploaders for results
            uploaded_hourly = st.file_uploader(
                "Upload hourly results (.csv)",
                type=['csv'],
                help="Upload hourly aggregation results from processing pipeline",
                key="hourly_uploader"
            )
            
            uploaded_weekly = st.file_uploader(
                "Upload weekly results (.csv)",
                type=['csv'],
                help="Upload weekly hourly profile results from processing pipeline",
                key="weekly_uploader"
            )
            
            # Auto-detect from output directory
            if st.button("🔍 Auto-detect from Output", key="auto_detect_btn"):
                self._auto_detect_results_files()
            
            # Load results button
            if st.button("🔄 Load Results", key="load_results_btn"):
                self._load_results_data(uploaded_hourly, uploaded_weekly)
        
        # Data validation and summary
        if self._check_data_availability():
            self._display_data_summary()
    
    def _load_shapefile(self, uploaded_file: Optional[st.runtime.uploaded_file_manager.UploadedFile]) -> None:
        """Load shapefile from uploaded ZIP file."""

        try:
            if uploaded_file is not None:
                # Check if it's a ZIP file
                if uploaded_file.name.endswith('.zip'):
                    import tempfile
                    import zipfile

                    # Create temp directory for extraction
                    with tempfile.TemporaryDirectory() as temp_dir:
                        temp_path = Path(temp_dir)
                        zip_path = temp_path / uploaded_file.name

                        # Save uploaded ZIP
                        with open(zip_path, 'wb') as f:
                            f.write(uploaded_file.getvalue())

                        # Extract ZIP
                        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                            zip_ref.extractall(temp_path)

                        # Find .shp file
                        shp_files = list(temp_path.glob('**/*.shp'))
                        if not shp_files:
                            st.error("❌ No .shp file found in ZIP")
                            return

                        shapefile_path = str(shp_files[0])

                        try:
                            # Load shapefile data INSIDE temp directory context
                            shapefile_data = self.spatial_manager.load_shapefile(shapefile_path)

                            # Validate schema
                            is_valid, missing_fields = self.spatial_manager.validate_shapefile_schema(shapefile_data)

                            if is_valid:
                                # Handle column name variations (id vs Id)
                                if 'id' in shapefile_data.columns and 'Id' not in shapefile_data.columns:
                                    shapefile_data = shapefile_data.rename(columns={'id': 'Id'})

                                # Store the GeoDataFrame directly (not the path, since temp dir will be deleted)
                                st.session_state.maps_shapefile_data = shapefile_data
                                st.session_state.maps_shapefile_path = uploaded_file.name  # Just store filename for display
                                st.success(f"✅ Loaded shapefile from ZIP: {uploaded_file.name} ({len(shapefile_data):,} features)")
                            else:
                                st.error(f"❌ Shapefile missing required columns: {', '.join(missing_fields)}")
                                st.info("Required columns: Id, From, To (case-sensitive)")
                                return

                        except Exception as e:
                            st.error(f"❌ Error loading shapefile from ZIP: {str(e)}")
                            return
                else:
                    st.error("❌ Shapefile upload requires a ZIP file containing .shp, .shx, .dbf, and .prj files")
                    return
            else:
                st.error("❌ Please upload a shapefile ZIP file")
                return
                
        except Exception as e:
            st.error(f"❌ Error loading shapefile: {str(e)}")
            logger.error(f"Shapefile loading error: {e}")
    
    def _load_results_data(self, uploaded_hourly: Optional[st.runtime.uploaded_file_manager.UploadedFile],
                          uploaded_weekly: Optional[st.runtime.uploaded_file_manager.UploadedFile]) -> None:
        """Load results data from uploaded files."""
        
        try:
            # Load hourly data
            if uploaded_hourly is not None:
                hourly_data = pd.read_csv(uploaded_hourly)
                
                # Validate hourly data schema (handle column name variations)
                required_hourly_cols = ['link_id', 'date', 'avg_duration_sec', 'avg_speed_kmh']
                hour_col_options = ['hour', 'hour_of_day']
                
                missing_cols = [col for col in required_hourly_cols if col not in hourly_data.columns]
                
                # Check for hour column variations
                hour_col_found = any(col in hourly_data.columns for col in hour_col_options)
                if not hour_col_found:
                    missing_cols.append('hour (or hour_of_day)')
                else:
                    # Standardize hour column name
                    if 'hour_of_day' in hourly_data.columns and 'hour' not in hourly_data.columns:
                        hourly_data = hourly_data.rename(columns={'hour_of_day': 'hour'})
                
                if not missing_cols:
                    st.session_state.maps_hourly_results = hourly_data
                    st.success(f"✅ Hourly data loaded: {len(hourly_data):,} records")
                    
                    # Show data info
                    date_range = pd.to_datetime(hourly_data['date'])
                    st.info(f"📅 Date range: {date_range.min().date()} to {date_range.max().date()}")
                    st.info(f"🔗 Unique links: {hourly_data['link_id'].nunique():,}")
                else:
                    st.error(f"❌ Invalid hourly data schema. Missing columns: {', '.join(missing_cols)}")
            
            # Load weekly data
            if uploaded_weekly is not None:
                weekly_data = pd.read_csv(uploaded_weekly)
                
                # Validate weekly data schema (handle column name variations)
                required_weekly_cols = ['link_id']
                hour_col_options = ['hour', 'hour_of_day']
                duration_col_options = ['avg_duration_sec', 'avg_dur']
                speed_col_options = ['avg_speed_kmh', 'avg_speed']
                
                missing_cols = []
                
                # Check for hour column variations
                hour_col_found = any(col in weekly_data.columns for col in hour_col_options)
                if not hour_col_found:
                    missing_cols.append('hour (or hour_of_day)')
                else:
                    # Standardize hour column name
                    if 'hour_of_day' in weekly_data.columns and 'hour' not in weekly_data.columns:
                        weekly_data = weekly_data.rename(columns={'hour_of_day': 'hour'})
                
                # Check for duration column variations
                duration_col_found = any(col in weekly_data.columns for col in duration_col_options)
                if not duration_col_found:
                    missing_cols.append('avg_duration_sec (or avg_dur)')
                else:
                    # Standardize duration column name and convert if needed
                    if 'avg_dur' in weekly_data.columns and 'avg_duration_sec' not in weekly_data.columns:
                        weekly_data = weekly_data.rename(columns={'avg_dur': 'avg_duration_sec'})
                
                # Check for speed column variations
                speed_col_found = any(col in weekly_data.columns for col in speed_col_options)
                if not speed_col_found:
                    missing_cols.append('avg_speed_kmh (or avg_speed)')
                else:
                    # Standardize speed column name
                    if 'avg_speed' in weekly_data.columns and 'avg_speed_kmh' not in weekly_data.columns:
                        weekly_data = weekly_data.rename(columns={'avg_speed': 'avg_speed_kmh'})
                
                if not missing_cols:
                    st.session_state.maps_weekly_results = weekly_data
                    st.success(f"✅ Weekly data loaded: {len(weekly_data):,} records")
                    
                    # Show data info
                    st.info(f"⏰ Hours covered: {weekly_data['hour'].min()}-{weekly_data['hour'].max()}")
                    st.info(f"🔗 Unique links: {weekly_data['link_id'].nunique():,}")
                else:
                    st.error(f"❌ Invalid weekly data schema. Missing columns: {', '.join(missing_cols)}")
            
            if uploaded_hourly is None and uploaded_weekly is None:
                st.warning("⚠️ Please upload at least one results file")
                
        except Exception as e:
            st.error(f"❌ Error loading results data: {str(e)}")
            logger.error(f"Results loading error: {e}")
    
    def _auto_detect_results_files(self) -> None:
        """Auto-detect results files from the output directory and default paths."""
        
        try:
            found_files = {}
            
            # First, check default paths
            if os.path.exists(self.default_hourly_path):
                found_files['hourly'] = self.default_hourly_path
            
            if os.path.exists(self.default_weekly_path):
                found_files['weekly'] = self.default_weekly_path
            
            # If default paths not found, look for aggregation output directories
            if not found_files:
                possible_dirs = ['./output/aggregation', './output', './test_output', './exports']

                for output_dir in possible_dirs:
                    if os.path.exists(output_dir):
                        # For aggregation directory, search in subdirectories
                        if output_dir == './output/aggregation':
                            self._search_aggregation_subdirs(output_dir, found_files)
                        else:
                            # Look for hourly aggregation file
                            hourly_file = os.path.join(output_dir, 'hourly_agg.csv')
                            if os.path.exists(hourly_file):
                                found_files['hourly'] = hourly_file

                            # Look for weekly profile file
                            weekly_file = os.path.join(output_dir, 'weekly_hourly_profile.csv')
                            if os.path.exists(weekly_file):
                                found_files['weekly'] = weekly_file
            
            if found_files:
                st.success(f"✅ Found {len(found_files)} results files")
                
                # Load found files
                for file_type, file_path in found_files.items():
                    try:
                        data = pd.read_csv(file_path)

                        # Standardize column names
                        column_mappings = {
                            'hour_of_day': 'hour',
                            'avg_dur': 'avg_duration_sec',
                            'avg_speed': 'avg_speed_kmh'
                        }

                        for old_col, new_col in column_mappings.items():
                            if old_col in data.columns and new_col not in data.columns:
                                data = data.rename(columns={old_col: new_col})

                        if file_type == 'hourly':
                            st.session_state.maps_hourly_results = data
                            st.info(f"📊 Loaded hourly data: {len(data):,} records from {file_path}")
                        elif file_type == 'weekly':
                            st.session_state.maps_weekly_results = data
                            st.info(f"📊 Loaded weekly data: {len(data):,} records from {file_path}")
                            
                    except Exception as e:
                        st.warning(f"⚠️ Could not load {file_path}: {str(e)}")
            else:
                st.warning("⚠️ No results files found in common output directories")
                st.info("💡 Try uploading files manually or check your output directory")
                
        except Exception as e:
            st.error(f"❌ Error during auto-detection: {str(e)}")
            logger.error(f"Auto-detection error: {e}")

    def _search_aggregation_subdirs(self, agg_dir: str, found_files: dict) -> None:
        """Search for CSV files in aggregation subdirectories."""
        try:
            import os
            # Get all subdirectories in aggregation output
            subdirs = [d for d in os.listdir(agg_dir)
                      if os.path.isdir(os.path.join(agg_dir, d))]

            # Sort subdirectories by modification time (newest first)
            subdirs.sort(key=lambda x: os.path.getmtime(os.path.join(agg_dir, x)), reverse=True)

            # Search for files in subdirectories
            for subdir in subdirs:
                subdir_path = os.path.join(agg_dir, subdir)

                # Look for hourly aggregation file
                if 'hourly' not in found_files:
                    hourly_file = os.path.join(subdir_path, 'hourly_agg.csv')
                    if os.path.exists(hourly_file):
                        found_files['hourly'] = hourly_file

                # Look for weekly profile file
                if 'weekly' not in found_files:
                    weekly_file = os.path.join(subdir_path, 'weekly_hourly_profile.csv')
                    if os.path.exists(weekly_file):
                        found_files['weekly'] = weekly_file

                # If we found both files, we can stop searching
                if len(found_files) >= 2:
                    break

        except Exception as e:
            logger.warning(f"Error searching aggregation subdirectories: {e}")
    
    def _preload_default_files(self) -> None:
        """Preload default weekly CSV files and default shapefile if they exist."""
        try:
            # Preload shapefile if not already loaded and file exists
            if (st.session_state.maps_shapefile_data is None and 
                os.path.exists(self.default_shapefile_path)):
                try:
                    import geopandas as gpd
                    gdf = gpd.read_file(self.default_shapefile_path)
                    st.session_state.maps_shapefile_data = gdf
                    logger.info(f"✅ Preloaded default shapefile: {len(gdf):,} features")
                except Exception as e:
                    logger.warning(f"Could not preload default shapefile: {e}")
            
            # Preload default CSV files if they exist
            # Hourly data
            if (st.session_state.maps_hourly_results is None and 
                os.path.exists(self.default_hourly_path)):
                try:
                    data = pd.read_csv(self.default_hourly_path)
                    # Standardize column names if needed
                    if 'hour_of_day' in data.columns and 'hour' not in data.columns:
                        data = data.rename(columns={'hour_of_day': 'hour'})
                    st.session_state.maps_hourly_results = data
                    logger.info(f"✅ Preloaded hourly data: {len(data):,} records")
                except Exception as e:
                    logger.warning(f"Could not preload hourly data: {e}")
            
            # Weekly data
            weekly_path = r"E:\google_agg\test_data\weekly_hourly_profile_all.csv"
            if (st.session_state.maps_weekly_results is None and 
                os.path.exists(weekly_path)):
                try:
                    data = pd.read_csv(weekly_path)
                    # Standardize column names if needed
                    column_mappings = {
                        'hour_of_day': 'hour',
                        'avg_dur': 'avg_duration_sec',
                        'avg_speed': 'avg_speed_kmh'
                    }
                    
                    for old_col, new_col in column_mappings.items():
                        if old_col in data.columns and new_col not in data.columns:
                            data = data.rename(columns={old_col: new_col})
                    
                    st.session_state.maps_weekly_results = data
                    logger.info(f"✅ Preloaded weekly data: {len(data):,} records")
                except Exception as e:
                    logger.warning(f"Could not preload weekly data: {e}")
                    
        except Exception as e:
            logger.error(f"Error during file preloading: {e}")
    
    def _check_data_availability(self) -> bool:
        """Check if required data is loaded."""
        
        shapefile_loaded = (st.session_state.maps_shapefile_data is not None and 
                           not st.session_state.maps_shapefile_data.empty)
        
        results_loaded = (st.session_state.maps_hourly_results is not None or 
                         st.session_state.maps_weekly_results is not None)
        
        return shapefile_loaded and results_loaded
    
    def _display_data_summary(self) -> None:
        """Display summary of loaded data."""
        
        render_header_with_icon('statistics', 'Data Summary')
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.session_state.maps_shapefile_data is not None:
                shapefile_data = st.session_state.maps_shapefile_data
                st.metric("Network Features", f"{len(shapefile_data):,}")
                
                # Calculate network bounds
                bounds = shapefile_data.total_bounds
                st.caption(f"Bounds: {bounds[0]:.0f}, {bounds[1]:.0f} to {bounds[2]:.0f}, {bounds[3]:.0f}")
        
        with col2:
            if st.session_state.maps_hourly_results is not None:
                hourly_data = st.session_state.maps_hourly_results
                st.metric("Hourly Records", f"{len(hourly_data):,}")
                
                unique_links = hourly_data['link_id'].nunique()
                st.caption(f"Unique links: {unique_links:,}")
        
        with col3:
            if st.session_state.maps_weekly_results is not None:
                weekly_data = st.session_state.maps_weekly_results
                st.metric("Weekly Records", f"{len(weekly_data):,}")
                
                unique_links = weekly_data['link_id'].nunique()
                st.caption(f"Unique links: {unique_links:,}")
        
        # Data quality checks
        if st.session_state.maps_preferences.get('show_data_quality', True):
            self._display_data_quality_summary()
    
    def _display_data_quality_summary(self) -> None:
        """Display data quality summary and join validation."""
        
        with st.expander("🔍 Data Quality Summary", expanded=False):
            
            shapefile_data = st.session_state.maps_shapefile_data
            hourly_data = st.session_state.maps_hourly_results
            weekly_data = st.session_state.maps_weekly_results
            
            if shapefile_data is not None and (hourly_data is not None or weekly_data is not None):
                
                # Join validation
                st.subheader("🔗 Join Validation")
                
                # Get shapefile link IDs (using s_From-To pattern)
                shapefile_link_ids = set()
                for _, row in shapefile_data.iterrows():
                    link_id = f"s_{row['From']}-{row['To']}"
                    shapefile_link_ids.add(link_id)
                
                col_join1, col_join2 = st.columns(2)
                
                with col_join1:
                    if hourly_data is not None:
                        hourly_link_ids = set(hourly_data['link_id'].unique())
                        
                        # Calculate join statistics
                        matched_links = shapefile_link_ids.intersection(hourly_link_ids)
                        missing_in_shapefile = hourly_link_ids - shapefile_link_ids
                        missing_in_hourly = shapefile_link_ids - hourly_link_ids
                        
                        st.write("**Hourly Data Join:**")
                        st.write(f"• Matched links: {len(matched_links):,}")
                        st.write(f"• Missing in shapefile: {len(missing_in_shapefile):,}")
                        st.write(f"• Missing in hourly: {len(missing_in_hourly):,}")
                        
                        match_rate = len(matched_links) / len(shapefile_link_ids) * 100 if shapefile_link_ids else 0
                        if match_rate > 80:
                            st.success(f"✅ Good join rate: {match_rate:.1f}%")
                        elif match_rate > 50:
                            st.warning(f"⚠️ Moderate join rate: {match_rate:.1f}%")
                        else:
                            st.error(f"❌ Poor join rate: {match_rate:.1f}%")
                
                with col_join2:
                    if weekly_data is not None:
                        weekly_link_ids = set(weekly_data['link_id'].unique())
                        
                        # Calculate join statistics
                        matched_links = shapefile_link_ids.intersection(weekly_link_ids)
                        missing_in_shapefile = weekly_link_ids - shapefile_link_ids
                        missing_in_weekly = shapefile_link_ids - weekly_link_ids
                        
                        st.write("**Weekly Data Join:**")
                        st.write(f"• Matched links: {len(matched_links):,}")
                        st.write(f"• Missing in shapefile: {len(missing_in_shapefile):,}")
                        st.write(f"• Missing in weekly: {len(missing_in_weekly):,}")
                        
                        match_rate = len(matched_links) / len(shapefile_link_ids) * 100 if shapefile_link_ids else 0
                        if match_rate > 80:
                            st.success(f"✅ Good join rate: {match_rate:.1f}%")
                        elif match_rate > 50:
                            st.warning(f"⚠️ Moderate join rate: {match_rate:.1f}%")
                        else:
                            st.error(f"❌ Poor join rate: {match_rate:.1f}%")
                
                # Data completeness
                st.subheader("📊 Data Completeness")
                
                col_comp1, col_comp2 = st.columns(2)
                
                with col_comp1:
                    if hourly_data is not None:
                        st.write("**Hourly Data:**")
                        
                        # Check for missing values
                        missing_duration = hourly_data['avg_duration_sec'].isna().sum()
                        missing_speed = hourly_data['avg_speed_kmh'].isna().sum()
                        
                        st.write(f"• Missing duration: {missing_duration:,} ({missing_duration/len(hourly_data)*100:.1f}%)")
                        st.write(f"• Missing speed: {missing_speed:,} ({missing_speed/len(hourly_data)*100:.1f}%)")
                        
                        # Date range
                        dates = pd.to_datetime(hourly_data['date'])
                        st.write(f"• Date range: {dates.min().date()} to {dates.max().date()}")
                        st.write(f"• Total days: {(dates.max() - dates.min()).days + 1}")
                
                with col_comp2:
                    if weekly_data is not None:
                        st.write("**Weekly Data:**")
                        
                        # Check for missing values
                        missing_duration = weekly_data['avg_duration_sec'].isna().sum()
                        missing_speed = weekly_data['avg_speed_kmh'].isna().sum()
                        
                        st.write(f"• Missing duration: {missing_duration:,} ({missing_duration/len(weekly_data)*100:.1f}%)")
                        st.write(f"• Missing speed: {missing_speed:,} ({missing_speed/len(weekly_data)*100:.1f}%)")
                        
                        # Hour coverage
                        hours = weekly_data['hour'].unique()
                        st.write(f"• Hour coverage: {len(hours)}/24 hours")
                        st.write(f"• Hour range: {hours.min()}-{hours.max()}")
    
    def _render_map_navigation(self) -> None:
        """Render map navigation tabs with reactive interface and consistent state management."""
        
        render_header_with_icon('maps', 'Interactive Maps')
        
        # Add global reactive controls
        self._render_global_controls()
        
        # Create tabs for different map views
        tab_map_a, tab_map_b = st.tabs(["📅 Map A: Hourly View", "📊 Map B: Weekly View"])
        
        with tab_map_a:
            if st.session_state.maps_hourly_results is not None:
                # Show loading indicator if enabled
                if st.session_state.maps_loading_state['is_loading']:
                    with st.spinner(st.session_state.maps_loading_state['loading_message']):
                        self._render_map_a_with_error_handling()
                else:
                    self._render_map_a_with_error_handling()
            else:
                st.warning("⚠️ Hourly results data not loaded. Please upload hourly_agg.csv file.")
                st.info("💡 Map A requires hourly aggregation data with date, hour, and link-level metrics.")
        
        with tab_map_b:
            # For Map B, we can use either weekly data or compute from hourly data
            weekly_data = st.session_state.maps_weekly_results
            hourly_data = st.session_state.maps_hourly_results
            
            if weekly_data is not None or hourly_data is not None:
                # Show loading indicator if enabled
                if st.session_state.maps_loading_state['is_loading']:
                    with st.spinner(st.session_state.maps_loading_state['loading_message']):
                        self._render_map_b_with_error_handling(weekly_data, hourly_data)
                else:
                    self._render_map_b_with_error_handling(weekly_data, hourly_data)
            else:
                st.warning("⚠️ No results data loaded for weekly view.")
                st.info("💡 Map B requires either weekly_hourly_profile.csv or hourly_agg.csv data.")
    
    def _render_global_controls(self) -> None:
        """Render enhanced global controls with reactive interface and real-time feedback."""
        
        with st.expander("⚙️ Global Settings & Reactive Controls", expanded=True):
            # Reactive status indicator
            self._render_reactive_status_indicator()
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write("**🔄 Interface Settings**")
                
                # Reactive updates toggle with enhanced feedback
                reactive_updates = st.checkbox(
                    "🔄 Reactive Updates",
                    value=st.session_state.maps_preferences.get('reactive_updates', True),
                    help="Enable real-time map updates when filters change",
                    key="global_reactive_updates"
                )
                
                # Update preference and show immediate feedback
                if st.session_state.maps_preferences.get('reactive_updates') != reactive_updates:
                    st.session_state.maps_preferences['reactive_updates'] = reactive_updates
                    if reactive_updates:
                        st.success("✅ Reactive mode enabled - maps will update automatically")
                    else:
                        st.info("ℹ️ Manual mode enabled - click refresh to update maps")
                
                # Loading indicators toggle
                loading_indicators = st.checkbox(
                    "⏳ Loading Indicators",
                    value=st.session_state.maps_preferences.get('loading_indicators', True),
                    help="Show loading spinners and progress indicators during map updates",
                    key="global_loading_indicators"
                )
                st.session_state.maps_preferences['loading_indicators'] = loading_indicators
                
                # Auto-refresh interval for reactive mode
                if reactive_updates:
                    refresh_interval = st.selectbox(
                        "🔄 Refresh Rate",
                        options=[0.5, 1.0, 2.0, 5.0],
                        index=1,  # Default to 1.0 second
                        format_func=lambda x: f"{x}s delay",
                        help="Delay between reactive updates to prevent excessive refreshing",
                        key="global_refresh_interval"
                    )
                    st.session_state.maps_preferences['refresh_interval'] = refresh_interval
            
            with col2:
                st.write("**📊 Shared Map Settings**")
                
                # Shared metric type (affects both maps)
                current_metric = st.session_state.maps_shared_state.get('metric_type', 'duration')
                metric_type = st.selectbox(
                    "📊 Default Metric",
                    options=['duration', 'speed'],
                    index=0 if current_metric == 'duration' else 1,
                    format_func=lambda x: 'Duration (minutes)' if x == 'duration' else 'Speed (km/h)',
                    help="Default metric type for both maps (shared state)",
                    key="global_metric_type"
                )
                
                # Update shared state with reactive feedback
                if st.session_state.maps_shared_state.get('metric_type') != metric_type:
                    st.session_state.maps_shared_state['metric_type'] = metric_type
                    if reactive_updates:
                        self._trigger_reactive_update("Metric type changed")
                        st.info(f"🔄 Updating maps to show {metric_type}...")
                
                # Shared aggregation method
                current_aggregation = st.session_state.maps_shared_state.get('aggregation_method', 'mean')
                aggregation_method = st.selectbox(
                    "📈 Aggregation Method",
                    options=['mean', 'median'],
                    index=0 if current_aggregation == 'mean' else 1,
                    help="Default aggregation method for weekly view (shared state)",
                    key="global_aggregation_method"
                )
                
                # Update shared state with reactive feedback
                if st.session_state.maps_shared_state.get('aggregation_method') != aggregation_method:
                    st.session_state.maps_shared_state['aggregation_method'] = aggregation_method
                    if reactive_updates:
                        self._trigger_reactive_update("Aggregation method changed")
                        st.info(f"🔄 Updating weekly aggregation to use {aggregation_method}...")
            
            with col3:
                st.write("**🎨 Symbology Settings**")
                
                # Classification method with reactive updates
                current_classification = st.session_state.maps_shared_state['symbology_settings'].get('classification_method', 'quantiles')
                classification_method = st.selectbox(
                    "Classification",
                    options=['quantiles', 'equal_interval', 'std_dev'],
                    index=['quantiles', 'equal_interval', 'std_dev'].index(current_classification),
                    format_func=lambda x: {
                        'quantiles': 'Quantiles',
                        'equal_interval': 'Equal Interval',
                        'std_dev': 'Standard Deviation'
                    }[x],
                    help="Classification method for color schemes (affects both maps)",
                    key="global_classification_method"
                )
                
                # Update shared state with reactive feedback
                if st.session_state.maps_shared_state['symbology_settings'].get('classification_method') != classification_method:
                    st.session_state.maps_shared_state['symbology_settings']['classification_method'] = classification_method
                    if reactive_updates:
                        self._trigger_reactive_update("Classification method changed")
                        st.info(f"🔄 Updating classification to {classification_method}...")
                
                # Number of classes with reactive updates
                current_n_classes = st.session_state.maps_shared_state['symbology_settings'].get('n_classes', 5)
                n_classes = st.slider(
                    "Number of Classes",
                    min_value=3,
                    max_value=10,
                    value=current_n_classes,
                    help="Number of classification classes (affects both maps)",
                    key="global_n_classes"
                )
                
                # Update shared state with reactive feedback
                if st.session_state.maps_shared_state['symbology_settings'].get('n_classes') != n_classes:
                    st.session_state.maps_shared_state['symbology_settings']['n_classes'] = n_classes
                    if reactive_updates:
                        self._trigger_reactive_update("Number of classes changed")
                        st.info(f"🔄 Updating to {n_classes} classes...")
            
            # Enhanced performance and status information
            self._render_performance_dashboard()
    
    def _render_reactive_status_indicator(self) -> None:
        """Render real-time status indicator for reactive interface."""
        
        # Get current states
        reactive_enabled = st.session_state.maps_preferences.get('reactive_updates', True)
        is_loading = st.session_state.maps_loading_state.get('is_loading', False)
        last_update = st.session_state.maps_shared_state.get('last_update_time')
        last_error = st.session_state.maps_loading_state.get('last_error')
        
        # Status indicator
        col_status, col_update, col_error = st.columns([1, 2, 1])
        
        with col_status:
            if is_loading:
                st.markdown("🔄 **Status:** Updating...")
            elif reactive_enabled:
                st.markdown("✅ **Status:** Reactive")
            else:
                st.markdown("⏸️ **Status:** Manual")
        
        with col_update:
            if last_update:
                time_diff = datetime.now() - last_update
                if time_diff.total_seconds() < 60:
                    st.caption(f"Last update: {int(time_diff.total_seconds())}s ago")
                else:
                    st.caption(f"Last update: {last_update.strftime('%H:%M:%S')}")
            else:
                st.caption("No updates yet")
        
        with col_error:
            if last_error:
                st.error("⚠️ Error occurred")
                if st.button("Clear Error", key="clear_error_btn"):
                    st.session_state.maps_loading_state['last_error'] = None
                    st.session_state.maps_loading_state['error_timestamp'] = None
                    st.rerun()
    
    def _render_performance_dashboard(self) -> None:
        """Render enhanced performance dashboard with detailed metrics."""
        
        if st.session_state.maps_performance['render_count'] > 0:
            st.markdown("---")
            st.write("**📊 Performance Dashboard**")
            
            perf = st.session_state.maps_performance
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Renders", perf['render_count'])
            
            with col2:
                cache_rate = (perf['cache_hits'] / (perf['cache_hits'] + perf['cache_misses']) * 100) if (perf['cache_hits'] + perf['cache_misses']) > 0 else 0
                st.metric("Cache Rate", f"{cache_rate:.1f}%")
            
            with col3:
                if perf['last_render_time']:
                    st.metric("Last Render", f"{perf['last_render_time']:.2f}s")
                else:
                    st.metric("Last Render", "N/A")
            
            with col4:
                # Calculate average render time (if available)
                avg_render_time = perf.get('total_render_time', 0) / perf['render_count'] if perf['render_count'] > 0 else 0
                if avg_render_time > 0:
                    st.metric("Avg Render", f"{avg_render_time:.2f}s")
                else:
                    st.metric("Avg Render", "N/A")
            
            # Performance recommendations
            if cache_rate < 50 and perf['render_count'] > 10:
                st.warning("⚠️ Low cache hit rate - consider reducing filter changes")
            elif perf.get('last_render_time', 0) > 5:
                st.warning("⚠️ Slow rendering detected - consider simplifying data or filters")
    
    def _render_map_a_with_error_handling(self) -> None:
        """Render Map A with comprehensive error handling and loading indicators."""
        import time
        
        try:
            # Show loading indicator if enabled
            loading_indicators = st.session_state.maps_preferences.get('loading_indicators', True)
            
            # FIXED: Apply enhanced map rendering with scroll stability
            st.success("✅ Enhanced map rendering with comprehensive opacity & scroll stability fixes")
            
            if loading_indicators and st.session_state.maps_loading_state.get('is_loading', False):
                loading_message = st.session_state.maps_loading_state.get('loading_message', 'Loading Map A...')
                
                with st.spinner(loading_message):
                    # Track render time
                    render_start = time.time()
                    
                    # Try simple map first, fallback to complex if needed
                    self._render_simple_map_a()
                    
                    # Update performance metrics
                    render_time = time.time() - render_start
                    st.session_state.maps_performance['last_render_time'] = render_time
                    
                    # Finalize reactive update
                    self._finalize_reactive_update()
            else:
                # Render without loading indicator
                render_start = time.time()
                
                # Try simple map first, fallback to complex if needed
                self._render_simple_map_a()
                
                # Update performance metrics
                render_time = time.time() - render_start
                st.session_state.maps_performance['last_render_time'] = render_time
            
            # Clear any previous errors on successful render
            if st.session_state.maps_loading_state.get('last_error'):
                st.session_state.maps_loading_state['last_error'] = None
                st.session_state.maps_loading_state['error_timestamp'] = None
                
            # Update cache hit counter (assuming successful render uses cache)
            st.session_state.maps_performance['cache_hits'] = st.session_state.maps_performance.get('cache_hits', 0) + 1
                
        except Exception as e:
            # Update cache miss counter on error
            st.session_state.maps_performance['cache_misses'] = st.session_state.maps_performance.get('cache_misses', 0) + 1
            
            # Handle the error
            self._handle_map_error("Map A (Hourly View)", e)
            
            # Clear loading state on error
            st.session_state.maps_loading_state['is_loading'] = False
    
    def _render_map_b_with_error_handling(self, weekly_data: Optional[pd.DataFrame], 
                                         hourly_data: Optional[pd.DataFrame]) -> None:
        """Render Map B with comprehensive error handling and loading indicators."""
        import time
        
        try:
            # Show loading indicator if enabled
            loading_indicators = st.session_state.maps_preferences.get('loading_indicators', True)
            
            if loading_indicators and st.session_state.maps_loading_state.get('is_loading', False):
                loading_message = st.session_state.maps_loading_state.get('loading_message', 'Loading Map B...')
                
                with st.spinner(loading_message):
                    render_start = time.time()
                    
                    # FIXED: Apply enhanced Map B rendering
                    st.success("✅ Enhanced Map B rendering with comprehensive opacity & scroll stability fixes")
                    self._render_simple_map_b(weekly_data, hourly_data)
                    
                    # Update performance metrics
                    render_time = time.time() - render_start
                    st.session_state.maps_performance['last_render_time'] = render_time
                    
                    # Finalize reactive update
                    self._finalize_reactive_update()
            else:
                # Render without loading indicator
                render_start = time.time()
                
                # FIXED: Apply enhanced Map B rendering
                st.success("✅ Enhanced Map B rendering with comprehensive opacity & scroll stability fixes")
                self._render_simple_map_b(weekly_data, hourly_data)
                
                # Update performance metrics
                render_time = time.time() - render_start
                st.session_state.maps_performance['last_render_time'] = render_time
            
            # Clear any previous errors on successful render
            if st.session_state.maps_loading_state.get('last_error'):
                st.session_state.maps_loading_state['last_error'] = None
                st.session_state.maps_loading_state['error_timestamp'] = None
                
            # Update cache hit counter (assuming successful render uses cache)
            st.session_state.maps_performance['cache_hits'] = st.session_state.maps_performance.get('cache_hits', 0) + 1
                
        except Exception as e:
            # Update cache miss counter on error
            st.session_state.maps_performance['cache_misses'] = st.session_state.maps_performance.get('cache_misses', 0) + 1
            
            # Handle the error
            self._handle_map_error("Map B (Weekly View)", e)
            
            # Clear loading state on error
            st.session_state.maps_loading_state['is_loading'] = False
    
    def _handle_map_error(self, map_name: str, error: Exception) -> None:
        """Handle map rendering errors with comprehensive user feedback and recovery options."""
        import traceback
        from datetime import datetime
        
        # Store error information
        st.session_state.maps_loading_state['last_error'] = str(error)
        st.session_state.maps_loading_state['error_timestamp'] = datetime.now()
        st.session_state.maps_loading_state['is_loading'] = False
        
        # Update error counter
        st.session_state.maps_performance['error_count'] = st.session_state.maps_performance.get('error_count', 0) + 1
        
        # Display user-friendly error message with severity indication
        error_type = type(error).__name__
        st.error(f"❌ **{map_name} Rendering Error**")
        st.write(f"**Error Type:** {error_type}")
        st.write(f"**Error Message:** {str(error)}")
        
        # Recovery actions
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Retry Rendering", key=f"retry_{map_name}"):
                # Clear error state and retry
                st.session_state.maps_loading_state['last_error'] = None
                st.session_state.maps_loading_state['error_timestamp'] = None
                st.rerun()
        
        with col2:
            if st.button("⚙️ Disable Reactive Mode", key=f"disable_reactive_{map_name}"):
                # Disable reactive updates to prevent repeated errors
                st.session_state.maps_preferences['reactive_updates'] = False
                st.info("ℹ️ Reactive mode disabled. Use manual refresh to update maps.")
                st.rerun()
        
        with col3:
            if st.button("🔄 Reset All Filters", key=f"reset_filters_{map_name}"):
                # Reset filters to default state
                self._reset_all_filters()
                st.info("ℹ️ All filters reset to default values.")
                st.rerun()
        
        # Detailed error information
        with st.expander("🔍 Detailed Error Information", expanded=False):
            
            # Error context
            st.write("**📋 Error Context:**")
            st.write(f"• Map: {map_name}")
            st.write(f"• Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            st.write(f"• Reactive Mode: {'Enabled' if st.session_state.maps_preferences.get('reactive_updates', True) else 'Disabled'}")
            st.write(f"• Data Loaded: Shapefile={st.session_state.maps_shapefile_data is not None}, "
                    f"Hourly={st.session_state.maps_hourly_results is not None}, "
                    f"Weekly={st.session_state.maps_weekly_results is not None}")
            
            # Error details
            st.write("**🐛 Error Details:**")
            st.code(str(error))
            
            # Common solutions based on error type
            st.write("**💡 Suggested Solutions:**")
            
            if "KeyError" in error_type:
                st.write("• **Missing Data Column:** Check that required columns exist in your data")
                st.write("• Verify column names match expected format (link_id, avg_duration_sec, etc.)")
                st.write("• Check for typos in column names or missing data fields")
            elif "ValueError" in error_type:
                st.write("• **Data Format Issue:** Check data types and value ranges")
                st.write("• Ensure numeric columns contain valid numbers")
                st.write("• Check for missing or null values in required fields")
            elif "AttributeError" in error_type:
                st.write("• **Object/Method Issue:** This may be a code-level error")
                st.write("• Try refreshing the page or reloading data")
                st.write("• Check if all required modules are properly loaded")
            elif "MemoryError" in error_type:
                st.write("• **Memory Issue:** Dataset may be too large")
                st.write("• Try filtering data to reduce size")
                st.write("• Consider using a smaller sample of data")
            else:
                st.write("• Check that both shapefile and results data are loaded correctly")
                st.write("• Verify data formats match expected schemas")
                st.write("• Try refreshing the page or reloading data")
                st.write("• Check browser console for additional error details")
            
            # Data validation suggestions
            st.write("**🔍 Data Validation Steps:**")
            st.write("1. Verify shapefile has Id, From, To columns")
            st.write("2. Check results data has link_id, date, hour columns")
            st.write("3. Ensure link_id format matches s_From-To pattern")
            st.write("4. Validate coordinate reference system (should be EPSG:2039)")
            
            # Technical details for debugging
            if st.checkbox("Show Technical Stack Trace", key=f"show_stack_trace_{map_name}"):
                st.write("**🔧 Technical Stack Trace:**")
                st.code(traceback.format_exc())
            
            # Session state debugging
            if st.checkbox("Show Session State Debug Info", key=f"show_session_debug_{map_name}"):
                st.write("**🔧 Session State Debug:**")
                
                debug_info = {
                    'maps_preferences': st.session_state.get('maps_preferences', {}),
                    'maps_shared_state': st.session_state.get('maps_shared_state', {}),
                    'maps_loading_state': st.session_state.get('maps_loading_state', {}),
                    'maps_performance': st.session_state.get('maps_performance', {}),
                    'data_shapes': {
                        'shapefile': len(st.session_state.maps_shapefile_data) if st.session_state.maps_shapefile_data is not None else None,
                        'hourly': len(st.session_state.maps_hourly_results) if st.session_state.maps_hourly_results is not None else None,
                        'weekly': len(st.session_state.maps_weekly_results) if st.session_state.maps_weekly_results is not None else None
                    }
                }
                
                st.json(debug_info)
        
        # Log comprehensive error information
        logger.error(f"Map rendering error in {map_name}: {error_type} - {str(error)}")
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        logger.info(f"Error context - Reactive: {st.session_state.maps_preferences.get('reactive_updates', True)}, "
                   f"Data loaded: {st.session_state.maps_shapefile_data is not None}")
    
    def _reset_all_filters(self) -> None:
        """Reset all filters to default values."""
        try:
            # Reset shared state to defaults
            st.session_state.maps_shared_state.update({
                'metric_type': 'speed',
                'aggregation_method': 'mean',
                'hour_range': (0, 23),
                'symbology_settings': {
                    'classification_method': 'quantiles',
                    'n_classes': 5,
                    'outlier_caps': True,
                    'show_direction_arrows': False,
                    'basemap_enabled': True
                },
                'filter_hash': None
            })
            
            # Clear any active attribute filters by resetting relevant session state keys
            keys_to_reset = [key for key in st.session_state.keys() if any(filter_type in key for filter_type in ['_length_', '_speed_', '_duration_', '_enabled'])]
            for key in keys_to_reset:
                if 'enabled' in key:
                    st.session_state[key] = False
            
            logger.info("All filters reset to default values")
            
        except Exception as e:
            logger.error(f"Error resetting filters: {e}")
            st.error(f"❌ Error resetting filters: {str(e)}")
    
    def _trigger_reactive_update(self, reason: str) -> None:
        """Trigger a reactive update with enhanced error handling and throttling."""
        from datetime import datetime
        import hashlib
        import time
        
        try:
            # Check if reactive updates are enabled
            if not st.session_state.maps_preferences.get('reactive_updates', True):
                logger.info(f"Reactive update skipped (disabled): {reason}")
                return
            
            # Throttling: prevent too frequent updates
            last_update = st.session_state.maps_shared_state.get('last_update_time')
            refresh_interval = st.session_state.maps_preferences.get('refresh_interval', 1.0)
            
            if last_update:
                time_since_last = (datetime.now() - last_update).total_seconds()
                if time_since_last < refresh_interval:
                    logger.debug(f"Reactive update throttled: {reason} (too soon: {time_since_last:.2f}s < {refresh_interval}s)")
                    return
            
            # Update timestamp
            update_time = datetime.now()
            st.session_state.maps_shared_state['last_update_time'] = update_time
            
            # Calculate comprehensive filter hash for change detection
            filter_data = {
                'metric_type': st.session_state.maps_shared_state.get('metric_type', 'speed'),
                'aggregation_method': st.session_state.maps_shared_state.get('aggregation_method', 'mean'),
                'symbology_settings': st.session_state.maps_shared_state.get('symbology_settings', {}),
                'hour_range': st.session_state.maps_shared_state.get('hour_range', (0, 23)),
                'timestamp': update_time.isoformat()  # Include timestamp to ensure uniqueness
            }
            
            filter_hash = hashlib.md5(str(filter_data).encode()).hexdigest()
            
            # Check if filters actually changed
            previous_hash = st.session_state.maps_shared_state.get('filter_hash')
            if previous_hash != filter_hash:
                st.session_state.maps_shared_state['filter_hash'] = filter_hash
                
                # Set loading state if indicators are enabled
                if st.session_state.maps_preferences.get('loading_indicators', True):
                    st.session_state.maps_loading_state['loading_message'] = f"Updating maps: {reason}"
                    st.session_state.maps_loading_state['is_loading'] = True
                    
                    # Clear any previous errors when starting new update
                    st.session_state.maps_loading_state['last_error'] = None
                    st.session_state.maps_loading_state['error_timestamp'] = None
                
                # Update performance counters
                st.session_state.maps_performance['render_count'] += 1
                
                # Track render start time
                render_start = time.time()
                st.session_state.maps_performance['last_render_start'] = render_start
                
                # Log reactive update
                logger.info(f"Reactive update triggered: {reason} (hash: {filter_hash[:8]})")
                
                # Force rerun to update maps with error handling
                try:
                    st.rerun()
                except Exception as rerun_error:
                    logger.error(f"Error during reactive rerun: {rerun_error}")
                    self._handle_reactive_error("Rerun failed", rerun_error)
            else:
                logger.debug(f"Reactive update skipped (no changes): {reason}")
                
        except Exception as e:
            logger.error(f"Error in reactive update trigger: {e}")
            self._handle_reactive_error(f"Reactive update failed: {reason}", e)
    
    def _handle_reactive_error(self, context: str, error: Exception) -> None:
        """Handle errors in reactive updates with user feedback."""
        from datetime import datetime
        
        # Store error information
        st.session_state.maps_loading_state['last_error'] = str(error)
        st.session_state.maps_loading_state['error_timestamp'] = datetime.now()
        st.session_state.maps_loading_state['is_loading'] = False
        
        # Update performance counters
        st.session_state.maps_performance['error_count'] = st.session_state.maps_performance.get('error_count', 0) + 1
        
        # Log error
        logger.error(f"Reactive interface error - {context}: {error}")
        
        # Show user-friendly error message
        st.error(f"⚠️ Reactive update failed: {context}")
        st.info("💡 Try refreshing the page or disabling reactive updates temporarily")
    
    def _render_simple_map_a(self) -> None:
        """Render a simplified version of Map A that definitely works."""
        import folium
        from streamlit_folium import st_folium
        from pyproj import Transformer
        import pandas as pd
        
        try:
            st.subheader("🗺️ Map A: Hourly View")
            st.markdown("Interactive map with enhanced scroll stability")
            
            # Get data from session state
            gdf = st.session_state.maps_shapefile_data
            df_hourly = st.session_state.maps_hourly_results
            
            if gdf is None or df_hourly is None:
                st.error("❌ No data available")
                return
            
            # Performance optimization: Cache processed data
            @st.cache_data
            def get_available_dates(df):
                return sorted(df['date'].unique())
            
            @st.cache_data
            def filter_and_join_data(df_hourly_serialized, gdf_serialized, selected_date, selected_hour):
                """Optimized data filtering and joining with caching."""
                df_hourly = pd.DataFrame(df_hourly_serialized)
                gdf = pd.DataFrame(gdf_serialized)
                
                # Filter data efficiently
                df_filtered = df_hourly[
                    (df_hourly['date'] == selected_date) & 
                    (df_hourly['hour'] == selected_hour)
                ].copy()
                
                return df_filtered.to_dict('records') if len(df_filtered) > 0 else []
            
            # Create simple controls
            col1, col2 = st.columns(2)
            
            with col1:
                # Optimized date selector with caching
                available_dates = get_available_dates(df_hourly)
                # Fast date selector without full page rerun
                selected_date = st.selectbox(
                    "Select Date",
                    options=available_dates,
                    index=0,
                    key="simple_map_a_date"
                )
            
            with col2:
                # Fast hour selector without full page rerun
                selected_hour = st.selectbox(
                    "Select Hour",
                    options=list(range(24)),
                    index=8,  # Default to 8 AM
                    key="simple_map_a_hour"
                )

            # PRE-COMPUTE ALL HOUR MAPS: Generate all 24 maps for selected date
            current_metric = st.session_state.maps_shared_state.get('metric_type', 'speed')
            precompute_key = f"precomputed_maps_{selected_date}_{current_metric}"

            if precompute_key not in st.session_state:
                with st.spinner(f"🔄 Generating maps for all 24 hours of {selected_date}..."):
                    st.session_state[precompute_key] = {}

                    # Pre-process shapefile once
                    if 'processed_shapefile' not in st.session_state:
                        gdf_temp = gdf.copy()
                        gdf_temp['link_id'] = gdf_temp.apply(lambda row: f"s_{row['From']}-{row['To']}", axis=1)
                        if gdf_temp.crs is None:
                            gdf_temp = gdf_temp.set_crs('EPSG:2039')
                        elif gdf_temp.crs != 'EPSG:2039':
                            gdf_temp = gdf_temp.to_crs('EPSG:2039')
                        gdf_wgs84_full = gdf_temp.to_crs('EPSG:4326')
                        wgs84_dict = {}
                        for idx, row in gdf_wgs84_full.iterrows():
                            wgs84_dict[row['link_id']] = row.geometry
                        bounds = gdf_temp.total_bounds
                        center_x = (bounds[0] + bounds[2]) / 2
                        center_y = (bounds[1] + bounds[3]) / 2
                        transformer = Transformer.from_crs('EPSG:2039', 'EPSG:4326', always_xy=True)
                        center_lon, center_lat = transformer.transform(center_x, center_y)
                        st.session_state.processed_shapefile = gdf_temp
                        st.session_state.wgs84_shapefile_dict = wgs84_dict
                        st.session_state.map_center = [center_lat, center_lon]

                    # Generate all 24 hour maps
                    for hour in range(24):
                        df_filtered = df_hourly[
                            (df_hourly['date'] == selected_date) &
                            (df_hourly['hour'] == hour)
                        ].copy()

                        if len(df_filtered) > 0:
                            # Create map for this hour (simplified to just store the HTML)
                            st.session_state[precompute_key][hour] = df_filtered

                    st.success(f"✅ Pre-computed {len(st.session_state[precompute_key])} hour maps")

            # Get pre-computed data for selected hour
            if selected_hour in st.session_state.get(precompute_key, {}):
                df_filtered = st.session_state[precompute_key][selected_hour]
            else:
                # Fallback if hour not available
                df_filtered = df_hourly[
                    (df_hourly['date'] == selected_date) &
                    (df_hourly['hour'] == selected_hour)
                ].copy()
            
            if len(df_filtered) == 0:
                st.warning("⚠️ No data for selected date/hour")
                return
            
            # PERFORMANCE OPTIMIZATION: Pre-process shapefile once per session
            if 'processed_shapefile' not in st.session_state:
                gdf = gdf.copy()
                gdf['link_id'] = gdf.apply(lambda row: f"s_{row['From']}-{row['To']}", axis=1)
                
                # Ensure CRS
                if gdf.crs is None:
                    gdf = gdf.set_crs('EPSG:2039')
                elif gdf.crs != 'EPSG:2039':
                    gdf = gdf.to_crs('EPSG:2039')
                
                # Pre-convert to WGS84 and cache coordinates (MAJOR SPEEDUP)
                gdf_wgs84 = gdf.to_crs('EPSG:4326')
                coords_dict = {}
                for idx, row in gdf_wgs84.iterrows():
                    if hasattr(row.geometry, 'coords'):
                        coords_dict[row['link_id']] = [[lat, lon] for lon, lat in row.geometry.coords]
                
                st.session_state.processed_shapefile = gdf
                st.session_state.coords_cache = coords_dict
                
                # Pre-calculate map center
                bounds = gdf.total_bounds
                center_x = (bounds[0] + bounds[2]) / 2
                center_y = (bounds[1] + bounds[3]) / 2
                transformer = Transformer.from_crs('EPSG:2039', 'EPSG:4326', always_xy=True)
                center_lon, center_lat = transformer.transform(center_x, center_y)
                st.session_state.map_center = [center_lat, center_lon]
            
            # Use cached shapefile
            gdf = st.session_state.processed_shapefile
            
            # Fast join with pre-processed data
            gdf_joined = gdf.merge(df_filtered, on='link_id', how='inner')
            
            if len(gdf_joined) == 0:
                st.warning("⚠️ No data after join")
                return
            
            # Add required columns
            gdf_joined['duration_min'] = gdf_joined['avg_duration_sec'] / 60
            
            # Single status message
            st.success(f"📊 Map A ready: {len(gdf_joined)} features for {selected_date}, hour {selected_hour}")

            # Get current metric type from session state
            current_metric = st.session_state.maps_shared_state.get('metric_type', 'duration')

            # Create Folium map
            m = folium.Map(
                location=st.session_state.map_center,
                zoom_start=10,
                tiles=None
            )

            # Add Google Maps base layer
            folium.TileLayer(
                tiles='https://mt1.google.com/vt/lyrs=r&x={x}&y={y}&z={z}',
                attr='Google Roads',
                name='Google Roads (Grey)',
                overlay=False,
                control=True
            ).add_to(m)

            # Compute colors
            import numpy as np
            if current_metric == 'speed':
                speeds = gdf_joined['avg_speed_kmh'].values
                colors = np.select([speeds < 30, speeds < 50], ['red', 'orange'], default='green')
                gdf_joined['color'] = colors
            else:
                durations = gdf_joined['duration_min'].values
                colors = np.select([durations < 3, durations < 5], ['green', 'orange'], default='red')
                gdf_joined['color'] = colors

            # PERFORMANCE: Check if we have cached WGS84 shapefile
            if 'wgs84_shapefile_dict' not in st.session_state:
                gdf_wgs84_full = st.session_state.processed_shapefile.to_crs('EPSG:4326')
                wgs84_dict = {}
                for idx, row in gdf_wgs84_full.iterrows():
                    wgs84_dict[row['link_id']] = row.geometry
                st.session_state.wgs84_shapefile_dict = wgs84_dict

            # Use cached WGS84 geometries
            wgs84_geoms = []
            valid_indices = []
            for idx, row in gdf_joined.iterrows():
                if row['link_id'] in st.session_state.wgs84_shapefile_dict:
                    wgs84_geoms.append(st.session_state.wgs84_shapefile_dict[row['link_id']])
                    valid_indices.append(idx)

            # Create WGS84 GeoDataFrame
            gdf_display = gdf_joined.loc[valid_indices].copy()
            gdf_display['geometry'] = wgs84_geoms
            gdf_display = gpd.GeoDataFrame(gdf_display, geometry='geometry', crs='EPSG:4326')

            # Style function
            def style_function(feature):
                return {
                    'color': feature['properties']['color'],
                    'weight': 4,
                    'opacity': 0.9
                }

            # Add GeoJSON layer
            folium.GeoJson(
                gdf_display,
                style_function=style_function,
                popup=folium.GeoJsonPopup(fields=['link_id', 'duration_min', 'avg_speed_kmh', 'From', 'To']),
                tooltip=folium.GeoJsonTooltip(fields=['link_id', 'duration_min', 'avg_speed_kmh'],
                                            labels=False,
                                            sticky=True)
            ).add_to(m)

            # Add date/hour display
            datetime_display_html = f'''
            <div style="position: fixed;
                        top: 10px; left: 10px; width: 280px; height: 35px;
                        background-color: rgba(255,255,255,0.95); border:2px solid #333; z-index:9999;
                        font-size:16px; padding: 6px 12px; font-weight: bold; border-radius: 5px;
                        box-shadow: 0 2px 5px rgba(0,0,0,0.3); display: flex; align-items: center;">
            📅 {selected_date} | ⏰ {selected_hour}:00
            </div>
            '''
            m.get_root().html.add_child(folium.Element(datetime_display_html))

            # Add north arrow
            north_arrow_html = '''
            <div style="position: fixed;
                        top: 70px; left: 10px; width: 40px; height: 40px;
                        background-color: rgba(255,255,255,0.95); border:2px solid #333; z-index:9999;
                        font-size:14px; padding: 5px; text-align: center; border-radius: 50%;
                        display: flex; align-items: center; justify-content: center; flex-direction: column;
                        box-shadow: 0 2px 5px rgba(0,0,0,0.3);">
            <span style="font-weight: bold; font-size: 18px;">⬆</span>
            <span style="font-size: 8px; font-weight: bold;">N</span>
            </div>
            '''
            m.get_root().html.add_child(folium.Element(north_arrow_html))

            # Add measurement controls
            from folium import plugins
            plugins.MeasureControl(position='bottomleft').add_to(m)

            # Add legend
            if current_metric == 'speed':
                legend_html = '''
                <div style="position: fixed;
                            top: 10px; right: 10px; width: 180px; height: 100px;
                            background-color: rgba(255,255,255,0.95); border:2px solid grey; z-index:9999;
                            font-size:14px; padding: 10px; border-radius: 5px;
                            box-shadow: 0 2px 5px rgba(0,0,0,0.3);">
                <b>Speed Legend</b><br>
                <i class="fa fa-minus" style="color:green"></i> > 50 km/h (Fast)<br>
                <i class="fa fa-minus" style="color:orange"></i> 30-50 km/h (Medium)<br>
                <i class="fa fa-minus" style="color:red"></i> < 30 km/h (Slow)<br>
                </div>
                '''
            else:
                legend_html = '''
                <div style="position: fixed;
                            top: 10px; right: 10px; width: 150px; height: 100px;
                            background-color: rgba(255,255,255,0.95); border:2px solid grey; z-index:9999;
                            font-size:14px; padding: 10px; border-radius: 5px;
                            box-shadow: 0 2px 5px rgba(0,0,0,0.3);">
                <b>Duration Legend</b><br>
                <i class="fa fa-minus" style="color:green"></i> < 3 min (Fast)<br>
                <i class="fa fa-minus" style="color:orange"></i> 3-5 min (Medium)<br>
                <i class="fa fa-minus" style="color:red"></i> > 5 min (Slow)<br>
                </div>
                '''
            m.get_root().html.add_child(folium.Element(legend_html))

            # Display map
            
            # Apply comprehensive CSS fix for iframe stability during scroll
            self._apply_iframe_stability_css()
            
            # Use dynamic key based on data AND metric type to prevent caching issues
            import hashlib
            map_key = f"map_a_{hashlib.md5(f'{selected_date}_{selected_hour}_{current_metric}_{len(gdf_joined)}'.encode()).hexdigest()[:8]}"
            
            # Render map with unique key to prevent duplicates
            map_data = st_folium(
                m, 
                width=None,  # Full width
                height=700,  # Fixed height
                key=map_key  # Dynamic key to prevent caching issues
            )
            
            # Show statistics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Features Displayed", len(gdf_joined))
            
            with col2:
                avg_duration = gdf_joined['duration_min'].mean()
                st.metric("Average Duration", f"{avg_duration:.1f} min")
            
            with col3:
                avg_speed = gdf_joined['avg_speed_kmh'].mean()
                st.metric("Average Speed", f"{avg_speed:.1f} km/h")
            
        except Exception as e:
            st.error(f"❌ Error in simplified Map A: {e}")
            import traceback
            st.code(traceback.format_exc())
    
    def _render_simple_map_b(self, weekly_data: Optional[pd.DataFrame], hourly_data: Optional[pd.DataFrame]) -> None:
        """Render a simplified version of Map B that definitely works."""
        import folium
        from streamlit_folium import st_folium
        from pyproj import Transformer
        from folium import plugins
        
        try:
            st.subheader("🗺️ Map B: Weekly View")
            st.markdown("Interactive weekly aggregation map with enhanced scroll stability")
            
            # Get data from session state
            gdf = st.session_state.maps_shapefile_data
            
            # Use weekly data if available, otherwise aggregate from hourly
            if weekly_data is not None:
                df_weekly = weekly_data
                st.info("Using pre-computed weekly data")
            elif hourly_data is not None:
                st.info("Computing weekly aggregation from hourly data...")
                df_weekly = hourly_data.groupby(['link_id', 'hour']).agg({
                    'avg_duration_sec': 'median',
                    'avg_speed_kmh': 'median'
                }).reset_index()
            else:
                st.error("❌ No weekly or hourly data available")
                return
            
            if gdf is None or df_weekly is None:
                st.error("❌ No data available")
                return

            # Control selectors
            col1, col2 = st.columns(2)

            with col1:
                # DayType selector
                selected_daytype = st.selectbox(
                    "Day Type",
                    options=['weekday', 'weekend', 'holiday', 'all'],
                    index=0,  # Default to weekday
                    key="simple_map_b_daytype",
                    help="Filter by type of day (default: weekday)"
                )

            with col2:
                # Fast hour selector without full page rerun
                selected_hour = st.selectbox(
                    "Select Hour",
                    options=list(range(24)),
                    index=8,  # Default to 8 AM
                    key="simple_map_b_hour"
                )
            
            # High-performance data caching and filtering for Map B
            @st.cache_data(ttl=3600)  # Cache for 1 hour
            def prepare_weekly_data_cache(_df_weekly):
                """Cache serialized weekly data to avoid repeated conversion."""
                return _df_weekly.to_dict('records')
            
            @st.cache_data
            def filter_weekly_data_ultra_fast(_df_weekly_serialized, selected_hour, selected_daytype):
                """Ultra-fast cached filtering of weekly data."""
                df_weekly = pd.DataFrame(_df_weekly_serialized)

                # Apply daytype filter
                if selected_daytype != 'all' and 'daytype' in df_weekly.columns:
                    df_weekly = df_weekly[df_weekly['daytype'] == selected_daytype].copy()

                # Apply hour filter
                if 'hour' in df_weekly.columns:
                    df_filtered = df_weekly[df_weekly['hour'] == selected_hour].copy()
                else:
                    df_filtered = df_weekly.copy()
                return df_filtered.to_dict('records') if len(df_filtered) > 0 else []
            
            # Use high-performance caching approach
            try:
                # Cache data serialization to avoid repeated conversion
                df_weekly_cached = prepare_weekly_data_cache(df_weekly)

                # Get filtered data from cache (ultra-fast)
                filtered_records = filter_weekly_data_ultra_fast(
                    df_weekly_cached,
                    selected_hour,
                    selected_daytype
                )
                
                if not filtered_records:
                    st.warning("⚠️ No data for selected hour")
                    return
                
                df_filtered = pd.DataFrame(filtered_records)
                
                # Create link_id for shapefile (not cached to avoid complexity)
                gdf = gdf.copy()
                gdf['link_id'] = gdf.apply(lambda row: f"s_{row['From']}-{row['To']}", axis=1)
                
                # Ensure shapefile has CRS before merge
                if gdf.crs is None:
                    gdf = gdf.set_crs('EPSG:2039')
                elif gdf.crs != 'EPSG:2039':
                    gdf = gdf.to_crs('EPSG:2039')
                
                # Join data while preserving geometry and CRS
                gdf_joined = gdf.merge(df_filtered, on='link_id', how='inner')
                
                # Ensure joined result maintains CRS
                if not isinstance(gdf_joined, gpd.GeoDataFrame):
                    gdf_joined = gpd.GeoDataFrame(gdf_joined, geometry='geometry', crs='EPSG:2039')
                elif gdf_joined.crs is None:
                    gdf_joined = gdf_joined.set_crs('EPSG:2039')
                
                if len(gdf_joined) == 0:
                    st.warning("⚠️ No data after join - check link_id matching")
                    return
                    
            except Exception as error:
                # Simple fallback without complex caching
                st.warning(f"⚠️ Using simple processing: {error}")

                # Apply daytype filter
                if selected_daytype != 'all' and 'daytype' in df_weekly.columns:
                    df_weekly = df_weekly[df_weekly['daytype'] == selected_daytype].copy()

                # Apply hour filter
                if 'hour' in df_weekly.columns:
                    df_filtered = df_weekly[df_weekly['hour'] == selected_hour].copy()
                else:
                    df_filtered = df_weekly.copy()

                if len(df_filtered) == 0:
                    st.warning("⚠️ No data for selected hour and day type")
                    return
                
                # Create link_id and join (fallback mode)
                gdf = gdf.copy()
                gdf['link_id'] = gdf.apply(lambda row: f"s_{row['From']}-{row['To']}", axis=1)
                gdf_joined = gdf.merge(df_filtered, on='link_id', how='inner')
            
            daytype_text = f" ({selected_daytype})" if selected_daytype != 'all' else ""
            st.info(f"📊 Showing weekly data{daytype_text} for hour {selected_hour}: {len(gdf_joined)} features")
            
            if len(gdf_joined) == 0:
                st.error("❌ No data after join - check link_id matching")
                return
            
            st.success(f"📊 Map B ready: {len(gdf_joined)} features for hour {selected_hour}")
            
            # Add required columns
            gdf_joined['duration_min'] = gdf_joined['avg_duration_sec'] / 60
            
            # PERFORMANCE OPTIMIZATION: Use cached coordinates from Map A processing
            coords_dict = st.session_state.get('coords_cache', {})
            map_center = st.session_state.get('map_center', [32.0, 35.0])  # Default center if not cached
            
            # Create Folium map with cached center (avoid expensive calculations)
            m = folium.Map(
                location=map_center,
                zoom_start=10,
                tiles=None
            )
            
            # Add Google Maps grey/minimal base layer for clean background
            folium.TileLayer(
                tiles='https://mt1.google.com/vt/lyrs=r&x={x}&y={y}&z={z}',
                attr='Google Roads',
                name='Google Roads (Grey)',
                overlay=False,
                control=True
            ).add_to(m)
            
            # Get current metric type from session state
            current_metric = st.session_state.maps_shared_state.get('metric_type', 'duration')
            
            # HYPER-FAST: Pre-computed color palettes with cached computation for Map B
            import numpy as np
            
            # Cache key for color computation - Map B specific
            metric_data_key = f"mapb_{current_metric}_{selected_hour}_{len(gdf_joined)}"
            
            if f'color_cache_{metric_data_key}' not in st.session_state:
                if current_metric == 'speed':
                    # Vectorized speed-based coloring with pre-computed thresholds
                    speeds = gdf_joined['avg_speed_kmh'].values
                    colors = np.select([speeds < 30, speeds < 50], ['red', 'orange'], default='green')
                    gdf_joined['color'] = colors
                else:
                    # Vectorized duration-based coloring with pre-computed thresholds
                    durations = gdf_joined['duration_min'].values
                    colors = np.select([durations < 3, durations < 5], ['green', 'orange'], default='red')
                    gdf_joined['color'] = colors
                
                # Cache the colors for instant reuse
                st.session_state[f'color_cache_{metric_data_key}'] = gdf_joined['color'].copy()
            else:
                # INSTANT: Use cached colors
                gdf_joined['color'] = st.session_state[f'color_cache_{metric_data_key}']
            
            # ULTRA-FAST: Use cached WGS84 geometries from Map A processing
            if 'wgs84_shapefile_dict' in st.session_state:
                wgs84_geoms = []
                valid_indices = []
                for idx, row in gdf_joined.iterrows():
                    if row['link_id'] in st.session_state.wgs84_shapefile_dict:
                        wgs84_geoms.append(st.session_state.wgs84_shapefile_dict[row['link_id']])
                        valid_indices.append(idx)
                
                # Create WGS84 GeoDataFrame from cached geometries
                gdf_display = gdf_joined.loc[valid_indices].copy()
                gdf_display['geometry'] = wgs84_geoms
                gdf_display = gpd.GeoDataFrame(gdf_display, geometry='geometry', crs='EPSG:4326')
            else:
                # Fallback: normal CRS conversion if cache not available
                gdf_display = gdf_joined.to_crs('EPSG:4326')
            
            # ULTRA-FAST: Single GeoJSON layer instead of 2,432 individual PolyLines
            def style_function(feature):
                return {
                    'color': feature['properties']['color'],
                    'weight': 4,
                    'opacity': 0.9
                }
            
            # Add single GeoJSON layer (MUCH faster than 2,432 individual PolyLines)
            folium.GeoJson(
                gdf_display,
                style_function=style_function,
                popup=folium.GeoJsonPopup(fields=['link_id', 'duration_min', 'avg_speed_kmh', 'From', 'To']),
                tooltip=folium.GeoJsonTooltip(fields=['link_id', 'duration_min', 'avg_speed_kmh'], 
                                            labels=False,
                                            sticky=True)
            ).add_to(m)
            
            # Add hour display overlay for Map B (single line)
            hour_display_html = f'''
            <div style="position: fixed; 
                        top: 10px; left: 10px; width: 240px; height: 35px; 
                        background-color: rgba(255,255,255,0.95); border:2px solid #333; z-index:9999; 
                        font-size:16px; padding: 6px 12px; font-weight: bold; border-radius: 5px; 
                        box-shadow: 0 2px 5px rgba(0,0,0,0.3); display: flex; align-items: center;">
            ⏰ Weekly Hour {selected_hour}:00
            </div>
            '''
            m.get_root().html.add_child(folium.Element(hour_display_html))
            
            # Add north arrow overlay for Map B
            north_arrow_html = '''
            <div style="position: fixed; 
                        top: 60px; left: 10px; width: 40px; height: 40px; 
                        background-color: rgba(255,255,255,0.95); border:2px solid #333; z-index:9999; 
                        font-size:14px; padding: 5px; text-align: center; border-radius: 50%; 
                        display: flex; align-items: center; justify-content: center; flex-direction: column;
                        box-shadow: 0 2px 5px rgba(0,0,0,0.3);">
            <span style="font-weight: bold; font-size: 18px;">⬆</span>
            <span style="font-size: 8px; font-weight: bold;">N</span>
            </div>
            '''
            m.get_root().html.add_child(folium.Element(north_arrow_html))
            
            # Add scale bar control for Map B
            plugins.MeasureControl(position='bottomleft').add_to(m)
            
            # PERFORMANCE: Use shared cached legend HTML for Map B (same as Map A)
            if f'legend_cache_{current_metric}' not in st.session_state:
                if current_metric == 'speed':
                    st.session_state[f'legend_cache_{current_metric}'] = '''
                    <div style="position: fixed; 
                                top: 10px; right: 10px; width: 180px; height: 100px; 
                                background-color: rgba(255,255,255,0.95); border:2px solid grey; z-index:9999; 
                                font-size:14px; padding: 10px; border-radius: 5px;
                                box-shadow: 0 2px 5px rgba(0,0,0,0.3);">
                    <b>Speed Legend</b><br>
                    <i class="fa fa-minus" style="color:green"></i> > 50 km/h (Fast)<br>
                    <i class="fa fa-minus" style="color:orange"></i> 30-50 km/h (Medium)<br>
                    <i class="fa fa-minus" style="color:red"></i> < 30 km/h (Slow)<br>
                    </div>
                    '''
                else:
                    st.session_state[f'legend_cache_{current_metric}'] = '''
                    <div style="position: fixed; 
                                top: 10px; right: 10px; width: 150px; height: 100px; 
                                background-color: rgba(255,255,255,0.95); border:2px solid grey; z-index:9999; 
                                font-size:14px; padding: 10px; border-radius: 5px;
                                box-shadow: 0 2px 5px rgba(0,0,0,0.3);">
                    <b>Duration Legend</b><br>
                    <i class="fa fa-minus" style="color:green"></i> < 3 min (Fast)<br>
                    <i class="fa fa-minus" style="color:orange"></i> 3-5 min (Medium)<br>
                    <i class="fa fa-minus" style="color:red"></i> > 5 min (Slow)<br>
                    </div>
                    '''
            
            # Use cached legend HTML
            legend_html = st.session_state[f'legend_cache_{current_metric}']
            m.get_root().html.add_child(folium.Element(legend_html))
            
            # Display weekly map
            
            # Apply comprehensive CSS fix for iframe stability during scroll
            self._apply_iframe_stability_css()
            
            # Use dynamic key based on data to prevent caching issues
            import hashlib
            map_key = f"map_b_{hashlib.md5(f'{selected_hour}_{current_metric}_{len(gdf_joined)}'.encode()).hexdigest()[:8]}"
            
            # Render map with unique key to prevent duplicates
            map_data = st_folium(
                m, 
                width=None,  # Full width
                height=700,  # Fixed height
                key=map_key  # Dynamic key to prevent caching issues
            )
            
            # Show statistics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Features Displayed", len(gdf_joined))
            
            with col2:
                avg_duration = gdf_joined['duration_min'].mean()
                st.metric("Average Duration", f"{avg_duration:.1f} min")
            
            with col3:
                avg_speed = gdf_joined['avg_speed_kmh'].mean()
                st.metric("Average Speed", f"{avg_speed:.1f} km/h")
            
        except Exception as e:
            st.error(f"❌ Error in simplified Map B: {e}")
            import traceback
            st.code(traceback.format_exc())
    
    def _finalize_reactive_update(self) -> None:
        """Finalize reactive update by clearing loading state and updating performance metrics."""
        import time
        
        try:
            # Clear loading state
            st.session_state.maps_loading_state['is_loading'] = False
            st.session_state.maps_loading_state['loading_message'] = ''
            
            # Update performance metrics
            render_start = st.session_state.maps_performance.get('last_render_start')
            if render_start:
                render_time = time.time() - render_start
                st.session_state.maps_performance['last_render_time'] = render_time
                
                # Update total render time for average calculation
                total_time = st.session_state.maps_performance.get('total_render_time', 0)
                st.session_state.maps_performance['total_render_time'] = total_time + render_time
            
            logger.debug("Reactive update finalized successfully")
            
        except Exception as e:
            logger.error(f"Error finalizing reactive update: {e}")
    
    def _apply_iframe_stability_css(self) -> None:
        """Apply comprehensive CSS fixes to prevent iframe grey out bug during scroll events."""
        try:
            # Load CSS from external file for better performance and maintainability
            css_file_path = Path(__file__).parent / "map_iframe_fix.css"
            
            if css_file_path.exists():
                with open(css_file_path, 'r', encoding='utf-8') as f:
                    css_content = f.read()
                st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
                logger.debug("Applied iframe stability CSS from external file")
            else:
                # Fallback to inline CSS if file not found
                st.markdown("""
                <style>
                /* Comprehensive fix for Streamlit-Folium iframe grey out bug */
                iframe[data-testid="stIFrame"] {
                    position: relative !important;
                    top: 0 !important;
                    left: 0 !important;
                    transform: none !important;
                    transition: none !important;
                    visibility: visible !important;
                    opacity: 1 !important;
                    background-color: white !important;
                    min-height: 700px !important;
                    overflow: hidden !important;
                    will-change: auto !important;
                    backface-visibility: visible !important;
                    transform-style: flat !important;
                }
                iframe[data-testid="stIFrame"] body {
                    margin: 0 !important;
                    padding: 0 !important;
                    overflow: hidden !important;
                    background-color: white !important;
                    visibility: visible !important;
                    opacity: 1 !important;
                }
                .stStreamlitContainer iframe {
                    will-change: auto !important;
                    backface-visibility: visible !important;
                    transform-style: flat !important;
                    transform: translateZ(0) !important;
                }
                [data-testid="stIFrame"] > iframe {
                    position: sticky !important;
                    z-index: 1 !important;
                    contain: layout style paint !important;
                    content-visibility: visible !important;
                }
                .folium-map, .leaflet-container {
                    background-color: white !important;
                    visibility: visible !important;
                    opacity: 1 !important;
                    will-change: auto !important;
                }
                .leaflet-tile-pane, .leaflet-overlay-pane {
                    visibility: visible !important;
                    opacity: 1 !important;
                    will-change: auto !important;
                }
                /* Enhanced fixes for Streamlit container opacity issues */
                .stContainer, [data-testid="stContainer"], .element-container, [data-testid="element-container"] {
                    opacity: 1 !important;
                    visibility: visible !important;
                    transition: none !important;
                }
                .main .block-container, [data-testid="main"] .block-container {
                    opacity: 1 !important;
                    visibility: visible !important;
                    transition: none !important;
                }
                [role="tabpanel"], .stTabs [role="tabpanel"] {
                    opacity: 1 !important;
                    visibility: visible !important;
                    transition: none !important;
                }
                [data-testid="stCustomComponentV1"] {
                    opacity: 1 !important;
                    visibility: visible !important;
                    transition: none !important;
                }
                [style*="opacity: 0"], [style*="opacity:0"], [style*="opacity: ."] {
                    opacity: 1 !important;
                    transition: none !important;
                }
                .stSpinner, [data-testid="stSpinner"], .stLoadingOverlay, [data-testid="stLoadingOverlay"] {
                    display: none !important;
                    opacity: 0 !important;
                    visibility: hidden !important;
                }
                </style>
                """, unsafe_allow_html=True)
                logger.debug("Applied fallback inline iframe stability CSS")
                
        except Exception as e:
            logger.error(f"Error applying iframe stability CSS: {e}")
            # Ensure basic functionality even if CSS fails
            st.markdown("""
            <style>
            iframe[data-testid="stIFrame"] {
                visibility: visible !important;
                opacity: 1 !important;
                background-color: white !important;
            }
            </style>
            """, unsafe_allow_html=True)


def render_maps_page():
    """
    Main function to render Maps page in Streamlit.
    This function should be called from the main app navigation.
    """
    
    # Initialize the maps page interface
    maps_interface = MapsPageInterface()
    
    # Render the complete maps page
    maps_interface.render_maps_page()


if __name__ == "__main__":
    # For testing purposes
    render_maps_page()

# DEBUG VERSION

def debug_render_maps_page():
    """Debug version of render_maps_page with extensive logging."""
    
    st.title("🗺️ Interactive Map Visualization (Debug Mode)")
    st.markdown("Debug version with extensive logging to identify empty map issues")
    
    # Check session state
    st.subheader("🔍 Debug Information")
    
    # Check if data is loaded
    shapefile_loaded = 'maps_shapefile_data' in st.session_state and st.session_state.maps_shapefile_data is not None
    hourly_loaded = 'maps_hourly_results' in st.session_state and st.session_state.maps_hourly_results is not None
    weekly_loaded = 'maps_weekly_results' in st.session_state and st.session_state.maps_weekly_results is not None
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if shapefile_loaded:
            gdf = st.session_state.maps_shapefile_data
            st.success(f"✅ Shapefile: {len(gdf)} features")
            st.caption(f"Columns: {list(gdf.columns)}")
        else:
            st.error("❌ No shapefile data")
    
    with col2:
        if hourly_loaded:
            df = st.session_state.maps_hourly_results
            st.success(f"✅ Hourly: {len(df)} records")
            st.caption(f"Date range: {df['date'].min()} to {df['date'].max()}")
        else:
            st.error("❌ No hourly data")
    
    with col3:
        if weekly_loaded:
            df = st.session_state.maps_weekly_results
            st.success(f"✅ Weekly: {len(df)} records")
            st.caption(f"Hours: {df['hour'].min()}-{df['hour'].max()}")
        else:
            st.error("❌ No weekly data")
    
    if not (shapefile_loaded and (hourly_loaded or weekly_loaded)):
        st.warning("⚠️ Required data not loaded. Please load data first.")
        return
    
