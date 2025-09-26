"""
Map A (Hourly View) implementation for interactive map visualization.

This module implements the hourly map interface with date/time controls,
metric toggles, and filtering capabilities.
"""

import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import logging

# Import existing modules
from .controls import InteractiveControls
from .map_renderer import MapVisualizationRenderer
from .map_data import MapDataProcessor
from .symbology import SymbologyEngine
from components.processing.optimizer import PerformanceOptimizer

logger = logging.getLogger(__name__)


class HourlyMapInterface:
    """Main interface for Map A (Hourly View) with controls."""
    
    def __init__(self):
        self.controls = InteractiveControls()
        self.renderer = MapVisualizationRenderer()
        self.data_processor = MapDataProcessor()
        self.symbology = SymbologyEngine()
        self.performance_optimizer = PerformanceOptimizer()
        
    def render_hourly_map_page(self, shapefile_data: gpd.GeoDataFrame, 
                              results_data: pd.DataFrame) -> None:
        """
        Render the complete Map A (Hourly View) page.
        
        Args:
            shapefile_data: GeoDataFrame with network shapefile
            results_data: DataFrame with hourly aggregation results
        """
        st.title("🗺️ Map A: Hourly View")
        st.markdown("Interactive map showing traffic patterns for specific dates and hours")
        
        # Check if data is available
        if shapefile_data.empty or results_data.empty:
            st.warning("⚠️ No data available. Please load shapefile and results data first.")
            return
        
        # Calculate data bounds for controls
        data_bounds = self._calculate_data_bounds(results_data)
        
        # Create two-column layout: controls on left, map on right
        col_controls, col_map = st.columns([1, 2])
        
        with col_controls:
            st.subheader("🎛️ Controls")
            
            # Add reactive update button
            if st.button("🔄 Refresh Map", help="Click to refresh map with current filter settings", key="map_a_refresh"):
                st.rerun()
            
            # Render control panel for hourly map
            control_state = self.controls.render_control_panel(
                data=shapefile_data,
                data_bounds=data_bounds,
                map_type="hourly",
                key_prefix="map_a"
            )
            
            # Apply filters and process data
            filtered_data = self._apply_filters(
                shapefile_data, results_data, control_state
            )
            
            # Show filter summary
            active_filters = self._format_active_filters(control_state)
            if active_filters:
                st.info(f"🔍 **Active Filters:** {len(active_filters)}")
                for filter_desc in active_filters:
                    st.caption(f"• {filter_desc}")
            else:
                st.info("🔍 **No filters active** - showing all data")
            
            # Calculate and display KPIs with performance optimization
            date_context = self._get_date_context(control_state)
            kpis = self.controls.calculate_and_display_kpis(
                filtered_data, len(shapefile_data), date_context, 
                original_results=results_data, show_detailed=True
            )
        
        with col_map:
            st.subheader("🗺️ Interactive Map")
            
            if not filtered_data.empty:
                # Create and render map with click handling
                map_obj = self._create_hourly_map(filtered_data, control_state)
                
                # Render map and capture click events
                from streamlit_folium import st_folium
                map_data = st_folium(map_obj, width=None, height=600, returned_objects=["last_clicked"])
                
                # Handle click interactions
                self._handle_map_clicks(map_data, filtered_data, results_data, control_state)
                
                # Display map statistics
                self._display_map_statistics(filtered_data, control_state)
            else:
                st.warning("⚠️ No data matches current filters. Try adjusting your selection.")
                
                # Show helpful suggestions
                st.info("💡 **Suggestions:**")
                st.info("• Expand date range")
                st.info("• Include more hours")
                st.info("• Relax attribute filters")
    
    def _calculate_data_bounds(self, results_data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate bounds for control widgets from results data."""
        bounds = {}
        
        # Date bounds
        if 'date' in results_data.columns:
            dates = pd.to_datetime(results_data['date'])
            bounds['min_date'] = dates.min().date()
            bounds['max_date'] = dates.max().date()
        
        # Hour bounds
        if 'hour' in results_data.columns:
            bounds['min_hour'] = int(results_data['hour'].min())
            bounds['max_hour'] = int(results_data['hour'].max())
        
        # Numeric attribute bounds
        numeric_columns = ['avg_speed_kmh', 'avg_duration_sec', 'length_m']
        for col in numeric_columns:
            if col in results_data.columns:
                bounds[col] = {
                    'min': float(results_data[col].min()),
                    'max': float(results_data[col].max())
                }
        
        logger.debug(f"Calculated data bounds: {bounds}")
        return bounds
    
    def _apply_filters(self, shapefile_data: gpd.GeoDataFrame, 
                      results_data: pd.DataFrame, 
                      control_state: Dict[str, Any]) -> gpd.GeoDataFrame:
        """Apply all filters and join data for visualization with reactive updates."""
        
        # Extract filter parameters
        temporal_filters = control_state.get('filters', {}).get('temporal', {})
        metric_config = control_state.get('filters', {}).get('metrics', {})
        attribute_filters = control_state.get('filters', {}).get('attributes', {})
        spatial_config = control_state.get('spatial', {})
        
        # Store original data size for comparison
        original_size = len(results_data)
        
        # Apply temporal filters to results data
        filtered_results = self._apply_temporal_filters(results_data, temporal_filters)
        temporal_filtered_size = len(filtered_results)
        
        # Apply attribute filters
        filtered_results = self._apply_attribute_filters(filtered_results, attribute_filters)
        attribute_filtered_size = len(filtered_results)
        
        # Join results to shapefile
        joined_data = self.data_processor.join_results_to_shapefile(
            shapefile_data, filtered_results
        )
        joined_size = len(joined_data)
        
        # Apply spatial selection
        if spatial_config.get('type') == 'text_search' and spatial_config.get('search_value'):
            joined_data = self.controls.spatial_selection.apply_text_search(
                joined_data, 
                spatial_config['search_field'], 
                spatial_config['search_value']
            )
        
        # Convert duration to minutes for display
        if 'avg_duration_sec' in joined_data.columns:
            joined_data['avg_duration_min'] = joined_data['avg_duration_sec'] / 60
        
        # Log filtering progress for debugging
        logger.info(f"Filter progression: {original_size} → {temporal_filtered_size} (temporal) → {attribute_filtered_size} (attributes) → {joined_size} (joined) → {len(joined_data)} (final)")
        
        # Store filter statistics in session state for display
        if 'filter_stats' not in st.session_state:
            st.session_state.filter_stats = {}
        
        st.session_state.filter_stats['map_a'] = {
            'original_records': original_size,
            'temporal_filtered': temporal_filtered_size,
            'attribute_filtered': attribute_filtered_size,
            'joined_features': joined_size,
            'final_features': len(joined_data),
            'temporal_reduction': ((original_size - temporal_filtered_size) / original_size * 100) if original_size > 0 else 0,
            'attribute_reduction': ((temporal_filtered_size - attribute_filtered_size) / temporal_filtered_size * 100) if temporal_filtered_size > 0 else 0
        }
        
        return joined_data
    
    def _apply_temporal_filters(self, results_data: pd.DataFrame, 
                               temporal_filters: Dict[str, Any]) -> pd.DataFrame:
        """Apply date and hour filters to results data."""
        filtered_data = results_data.copy()
        
        # Date range filter
        if 'date_range' in temporal_filters:
            date_range = temporal_filters['date_range']
            if len(date_range) == 2:
                start_date, end_date = date_range
                
                # Convert date column to datetime for comparison
                if 'date' in filtered_data.columns:
                    date_col = pd.to_datetime(filtered_data['date'])
                    mask = (date_col.dt.date >= start_date) & (date_col.dt.date <= end_date)
                    filtered_data = filtered_data[mask]
        
        # Hour range filter
        if 'hour_range' in temporal_filters:
            hour_range = temporal_filters['hour_range']
            if len(hour_range) == 2:
                start_hour, end_hour = hour_range
                
                if 'hour' in filtered_data.columns:
                    mask = (filtered_data['hour'] >= start_hour) & (filtered_data['hour'] <= end_hour)
                    filtered_data = filtered_data[mask]
        
        return filtered_data
    
    def _apply_attribute_filters(self, results_data: pd.DataFrame, 
                                attribute_filters: Dict[str, Dict]) -> pd.DataFrame:
        """Apply length, speed, and duration filters."""
        filtered_data = results_data.copy()
        
        for column, filter_config in attribute_filters.items():
            if column not in filtered_data.columns:
                continue
                
            operator = filter_config['operator']
            value = filter_config['value']
            
            if operator == 'above':
                mask = filtered_data[column] > value
            elif operator == 'below':
                mask = filtered_data[column] < value
            elif operator == 'between':
                if isinstance(value, (list, tuple)) and len(value) == 2:
                    mask = (filtered_data[column] >= value[0]) & (filtered_data[column] <= value[1])
                else:
                    continue
            else:
                continue
            
            filtered_data = filtered_data[mask]
        
        return filtered_data
    
    def _create_hourly_map(self, data: gpd.GeoDataFrame, 
                          control_state: Dict[str, Any]) -> folium.Map:
        """Create the interactive hourly map with styling."""
        
        # Get metric configuration
        metric_config = control_state.get('filters', {}).get('metrics', {})
        metric_type = metric_config.get('metric_type', 'duration')
        
        # Determine value column based on metric type
        if metric_type == 'duration':
            value_column = 'avg_duration_min'
            metric_title = 'Duration (minutes)'
        else:  # speed
            value_column = 'avg_speed_kmh'
            metric_title = 'Speed (km/h)'
        
        if value_column not in data.columns:
            logger.warning(f"Value column {value_column} not found in data")
            # Create empty map
            return self.renderer.renderer.create_base_map()
        
        # Calculate symbology
        values = data[value_column].values
        if len(values) == 0:
            return self.renderer.renderer.create_base_map()
        
        # Classify data and get colors
        class_breaks, colors = self.symbology.classify_and_color_data(
            values, metric_type, method='quantiles', n_classes=5
        )
        
        # Create style configuration
        style_config = {
            'color': colors[0] if colors else '#3388ff',
            'weight': 3,
            'opacity': 0.8
        }
        
        # Create legend configuration
        legend_config = {
            'title': metric_title,
            'class_breaks': class_breaks,
            'colors': colors,
            'active_filters': self._format_active_filters(control_state),
            'classification_method': 'quantiles'
        }
        
        # Create map
        map_obj = self.renderer.create_interactive_map(
            data=data,
            style_config=style_config,
            legend_config=legend_config
        )
        
        return map_obj
    
    def _format_active_filters(self, control_state: Dict[str, Any]) -> List[str]:
        """Format active filters for legend display."""
        filters = []
        
        temporal = control_state.get('filters', {}).get('temporal', {})
        
        # Date range
        if 'date_range' in temporal:
            date_range = temporal['date_range']
            if len(date_range) == 2:
                start_date, end_date = date_range
                if start_date == end_date:
                    filters.append(f"Date: {start_date}")
                else:
                    filters.append(f"Dates: {start_date} to {end_date}")
        
        # Hour range
        if 'hour_range' in temporal:
            hour_range = temporal['hour_range']
            if len(hour_range) == 2:
                start_hour, end_hour = hour_range
                if start_hour == end_hour:
                    filters.append(f"Hour: {start_hour}:00")
                else:
                    filters.append(f"Hours: {start_hour}:00-{end_hour}:00")
        
        # Attribute filters
        attribute_filters = control_state.get('filters', {}).get('attributes', {})
        for column, filter_config in attribute_filters.items():
            operator = filter_config['operator']
            value = filter_config['value']
            
            if column == 'length_m':
                if operator == 'between':
                    filters.append(f"Length: {value[0]:.0f}-{value[1]:.0f}m")
                else:
                    filters.append(f"Length {operator}: {value:.0f}m")
            elif column == 'avg_speed_kmh':
                if operator == 'between':
                    filters.append(f"Speed: {value[0]:.1f}-{value[1]:.1f} km/h")
                else:
                    filters.append(f"Speed {operator}: {value:.1f} km/h")
            elif column == 'avg_duration_sec':
                value_min = value / 60 if not isinstance(value, (list, tuple)) else [v/60 for v in value]
                if operator == 'between':
                    filters.append(f"Duration: {value_min[0]:.1f}-{value_min[1]:.1f} min")
                else:
                    filters.append(f"Duration {operator}: {value_min:.1f} min")
        
        return filters
    
    def _get_date_context(self, control_state: Dict[str, Any]) -> Dict[str, Any]:
        """Get date context for KPI calculations."""
        temporal = control_state.get('filters', {}).get('temporal', {})
        
        context = {'n_days': 1}
        
        if 'date_range' in temporal:
            date_range = temporal['date_range']
            if len(date_range) == 2:
                start_date, end_date = date_range
                n_days = (end_date - start_date).days + 1
                context['n_days'] = n_days
        
        return context
    
    def _display_map_statistics(self, data: gpd.GeoDataFrame, 
                               control_state: Dict[str, Any]) -> None:
        """Display additional map statistics and filter effectiveness below the map."""
        
        if data.empty:
            st.warning("⚠️ No data to display after applying filters")
            return
        
        st.subheader("📊 Map Statistics")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Features Displayed", f"{len(data):,}")
            
            if 'n_valid' in data.columns:
                total_observations = data['n_valid'].sum()
                st.metric("Total Observations", f"{total_observations:,}")
        
        with col2:
            metric_config = control_state.get('filters', {}).get('metrics', {})
            metric_type = metric_config.get('metric_type', 'duration')
            
            if metric_type == 'duration' and 'avg_duration_min' in data.columns:
                avg_duration = data['avg_duration_min'].mean()
                st.metric("Average Duration", f"{avg_duration:.1f} min")
            elif metric_type == 'speed' and 'avg_speed_kmh' in data.columns:
                avg_speed = data['avg_speed_kmh'].mean()
                st.metric("Average Speed", f"{avg_speed:.1f} km/h")
        
        with col3:
            if 'length_m' in data.columns:
                total_length = data['length_m'].sum() / 1000  # Convert to km
                st.metric("Total Network Length", f"{total_length:.1f} km")
        
        # Display filter effectiveness
        if 'filter_stats' in st.session_state and 'map_a' in st.session_state.filter_stats:
            stats = st.session_state.filter_stats['map_a']
            
            with st.expander("🔍 Filter Effectiveness", expanded=False):
                col_stats1, col_stats2 = st.columns(2)
                
                with col_stats1:
                    st.write("**Data Reduction:**")
                    st.write(f"• Original records: {stats['original_records']:,}")
                    st.write(f"• After temporal filters: {stats['temporal_filtered']:,}")
                    st.write(f"• After attribute filters: {stats['attribute_filtered']:,}")
                    st.write(f"• Final features: {stats['final_features']:,}")
                
                with col_stats2:
                    st.write("**Reduction Percentages:**")
                    if stats['temporal_reduction'] > 0:
                        st.write(f"• Temporal filtering: -{stats['temporal_reduction']:.1f}%")
                    if stats['attribute_reduction'] > 0:
                        st.write(f"• Attribute filtering: -{stats['attribute_reduction']:.1f}%")
                    
                    total_reduction = ((stats['original_records'] - stats['final_features']) / stats['original_records'] * 100) if stats['original_records'] > 0 else 0
                    st.write(f"• **Total reduction: -{total_reduction:.1f}%**")
        
        # Display data quality indicators
        if 'n_valid' in data.columns:
            with st.expander("📈 Data Quality", expanded=False):
                col_qual1, col_qual2 = st.columns(2)
                
                with col_qual1:
                    # Observation count statistics
                    obs_stats = data['n_valid'].describe()
                    st.write("**Observations per Link:**")
                    st.write(f"• Mean: {obs_stats['mean']:.1f}")
                    st.write(f"• Median: {obs_stats['50%']:.1f}")
                    st.write(f"• Min: {obs_stats['min']:.0f}")
                    st.write(f"• Max: {obs_stats['max']:.0f}")
                
                with col_qual2:
                    # Data coverage indicators
                    low_obs_threshold = 5  # Links with fewer than 5 observations
                    low_obs_count = (data['n_valid'] < low_obs_threshold).sum()
                    low_obs_percent = (low_obs_count / len(data) * 100) if len(data) > 0 else 0
                    
                    st.write("**Coverage Quality:**")
                    st.write(f"• Links with <{low_obs_threshold} obs: {low_obs_count} ({low_obs_percent:.1f}%)")
                    
                    if low_obs_percent > 20:
                        st.warning(f"⚠️ {low_obs_percent:.1f}% of links have sparse data")
                    elif low_obs_percent > 10:
                        st.info(f"ℹ️ {low_obs_percent:.1f}% of links have limited data")
                    else:
                        st.success(f"✅ Good data coverage ({100-low_obs_percent:.1f}% well-covered)")
    
    def _handle_map_clicks(self, map_data: Dict, filtered_data: gpd.GeoDataFrame,
                          results_data: pd.DataFrame, control_state: Dict[str, Any]) -> None:
        """Handle map click events and display link details."""
        
        # Check if there was a click event
        if map_data['last_clicked'] is not None and 'lat' in map_data['last_clicked']:
            click_lat = map_data['last_clicked']['lat']
            click_lon = map_data['last_clicked']['lon']
            
            # Find the closest link to the click point
            clicked_link = self._find_closest_link(click_lat, click_lon, filtered_data)
            
            if clicked_link is not None:
                # Store selected link in session state
                st.session_state['selected_link_id'] = clicked_link['Id']
                st.session_state['selected_link_data'] = clicked_link
                
                # Display link details panel
                self._display_link_details_panel(clicked_link, results_data, control_state)
        
        # Display details panel if a link is selected
        elif 'selected_link_id' in st.session_state:
            selected_link_id = st.session_state['selected_link_id']
            
            # Find the link in current filtered data
            selected_links = filtered_data[filtered_data['Id'] == selected_link_id]
            
            if not selected_links.empty:
                selected_link = selected_links.iloc[0]
                self._display_link_details_panel(selected_link, results_data, control_state)
            else:
                # Link not in current filter - clear selection
                if st.button("🗑️ Clear Selection", help="Selected link not visible with current filters"):
                    del st.session_state['selected_link_id']
                    if 'selected_link_data' in st.session_state:
                        del st.session_state['selected_link_data']
                    st.rerun()
                
                st.warning(f"⚠️ Selected link {selected_link_id} is not visible with current filters")
    
    def _find_closest_link(self, click_lat: float, click_lon: float, 
                          data: gpd.GeoDataFrame) -> Optional[pd.Series]:
        """Find the link closest to the clicked point."""
        if data.empty:
            return None
        
        try:
            from shapely.geometry import Point
            
            # Create point from click coordinates
            click_point = Point(click_lon, click_lat)
            
            # Convert to same CRS as data if needed
            if data.crs and data.crs.to_string() != "EPSG:4326":
                # Convert click point to data CRS
                import geopandas as gpd
                click_gdf = gpd.GeoDataFrame([1], geometry=[click_point], crs="EPSG:4326")
                click_gdf = click_gdf.to_crs(data.crs)
                click_point = click_gdf.geometry.iloc[0]
            
            # Calculate distances to all links
            distances = data.geometry.distance(click_point)
            
            # Find closest link
            closest_idx = distances.idxmin()
            closest_link = data.loc[closest_idx]
            
            logger.info(f"Found closest link: {closest_link.get('Id', 'N/A')} at distance {distances.loc[closest_idx]}")
            return closest_link
            
        except Exception as e:
            logger.error(f"Error finding closest link: {e}")
            return None
    
    def _display_link_details_panel(self, link_data: pd.Series, 
                                   results_data: pd.DataFrame,
                                   control_state: Dict[str, Any]) -> None:
        """Display detailed information panel for selected link."""
        
        from .link_details_panel import LinkDetailsPanel
        
        # Create expandable details panel
        with st.expander(f"🔗 Link Details: {link_data.get('Id', 'N/A')}", expanded=True):
            
            # Get all hourly data for this link
            link_id = link_data.get('Id', link_data.get('link_id'))
            
            if link_id and 'link_id' in results_data.columns:
                # Create link_id column if it doesn't exist
                if 'link_id' not in results_data.columns:
                    # Try to create from s_From-To pattern
                    if 'From' in link_data and 'To' in link_data:
                        expected_link_id = f"s_{link_data['From']}-{link_data['To']}"
                        link_hourly_data = results_data[results_data.get('link_id', '') == expected_link_id]
                    else:
                        link_hourly_data = pd.DataFrame()
                else:
                    link_hourly_data = results_data[results_data['link_id'] == link_id]
            else:
                link_hourly_data = pd.DataFrame()
            
            # Prepare context information
            context = {
                'filters': control_state.get('filters', {}),
                'date_range': control_state.get('filters', {}).get('temporal', {}).get('date_range'),
                'hour_range': control_state.get('filters', {}).get('temporal', {}).get('hour_range'),
                'metric_type': control_state.get('filters', {}).get('metrics', {}).get('metric_type', 'duration')
            }
            
            # Create and render details panel
            details_panel = LinkDetailsPanel()
            details_panel.render_link_details(
                link_data=link_data,
                hourly_data=link_hourly_data,
                context=context
            )
            
            # Add action buttons
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            
            with col_btn1:
                if st.button("🗑️ Clear Selection", key="clear_link_selection"):
                    if 'selected_link_id' in st.session_state:
                        del st.session_state['selected_link_id']
                    if 'selected_link_data' in st.session_state:
                        del st.session_state['selected_link_data']
                    st.rerun()
            
            with col_btn2:
                if st.button("📊 Focus on Link", key="focus_link"):
                    # Set filters to focus on this specific link
                    st.info("Focus functionality will be implemented")
            
            with col_btn3:
                if st.button("📋 Export Data", key="export_link_data"):
                    # Export link data
                    st.info("Export functionality will be implemented")


def render_map_a_page():
    """
    Main function to render Map A page in Streamlit.
    This function should be called from the main app navigation.
    """
    
    # Initialize the hourly map interface
    hourly_interface = HourlyMapInterface()
    
    # Check if data is loaded in session state
    if 'shapefile_data' not in st.session_state or 'hourly_results' not in st.session_state:
        st.warning("⚠️ Please load shapefile and results data first.")
        
        # Provide file upload interface
        st.subheader("📁 Data Loading")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Shapefile Upload**")
            shapefile = st.file_uploader(
                "Upload shapefile (.shp)",
                type=['shp'],
                help="Upload the network shapefile with Id, From, To fields"
            )
            
            if shapefile:
                # TODO: Implement shapefile loading
                st.info("Shapefile loading will be implemented")
        
        with col2:
            st.markdown("**Results Data Upload**")
            results_file = st.file_uploader(
                "Upload hourly results (.csv)",
                type=['csv'],
                help="Upload the hourly aggregation results CSV"
            )
            
            if results_file:
                # TODO: Implement results loading
                st.info("Results loading will be implemented")
        
        return
    
    # Get data from session state
    shapefile_data = st.session_state.shapefile_data
    hourly_results = st.session_state.hourly_results
    
    # Render the hourly map interface
    hourly_interface.render_hourly_map_page(shapefile_data, hourly_results)


if __name__ == "__main__":
    # For testing purposes
    render_map_a_page()