"""
Map B (Weekly View) implementation for interactive map visualization.

This module implements the weekly hourly aggregation map interface without date selection,
showing typical traffic patterns across all available data with mean/median aggregation.
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


class WeeklyMapInterface:
    """Main interface for Map B (Weekly View) with aggregation controls."""
    
    def __init__(self):
        self.controls = InteractiveControls()
        self.renderer = MapVisualizationRenderer()
        self.data_processor = MapDataProcessor()
        self.symbology = SymbologyEngine()
        self.performance_optimizer = PerformanceOptimizer()
        
    def render_weekly_map_page(self, shapefile_data: gpd.GeoDataFrame, 
                              results_data: pd.DataFrame) -> None:
        """
        Render the complete Map B (Weekly View) page.
        
        Args:
            shapefile_data: GeoDataFrame with network shapefile
            results_data: DataFrame with hourly aggregation results
        """
        st.title("🗺️ Map B: Weekly View")
        st.markdown("Interactive map showing weekly hourly aggregation patterns across all available data")
        
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
            if st.button("🔄 Refresh Map", help="Click to refresh map with current filter settings", key="map_b_refresh"):
                st.rerun()
            
            # Render control panel for weekly map (no date picker)
            control_state = self.controls.render_control_panel(
                data=shapefile_data,
                data_bounds=data_bounds,
                map_type="weekly",  # This will exclude date picker
                key_prefix="map_b"
            )
            
            # Apply filters and process data with weekly aggregation
            filtered_data, date_context = self._apply_filters_and_aggregate(
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
            
            # Display context text showing averaged date span and N days
            self._display_date_context(date_context, control_state)
            
            # Calculate and display KPIs
            kpis = self.controls.calculate_and_display_kpis(
                filtered_data, len(shapefile_data), date_context
            )
        
        with col_map:
            st.subheader("🗺️ Interactive Map")
            
            if not filtered_data.empty:
                # Create and render map with click handling
                map_obj = self._create_weekly_map(filtered_data, control_state)
                
                # Render map and capture click events
                from streamlit_folium import st_folium
                map_data = st_folium(map_obj, width=None, height=600, returned_objects=["last_clicked"])
                
                # Handle click interactions
                self._handle_map_clicks(map_data, filtered_data, results_data, control_state)
                
                # Display map statistics
                self._display_map_statistics(filtered_data, control_state, date_context)
            else:
                st.warning("⚠️ No data matches current filters. Try adjusting your selection.")
                
                # Show helpful suggestions
                st.info("💡 **Suggestions:**")
                st.info("• Include more hours")
                st.info("• Relax attribute filters")
                st.info("• Check aggregation method")
    
    def _calculate_data_bounds(self, results_data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate bounds for control widgets from results data."""
        bounds = {}
        
        # Hour bounds (no date bounds for weekly view)
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
        
        logger.debug(f"Calculated data bounds for weekly view: {bounds}")
        return bounds
    
    def _apply_filters_and_aggregate(self, shapefile_data: gpd.GeoDataFrame, 
                                   results_data: pd.DataFrame, 
                                   control_state: Dict[str, Any]) -> Tuple[gpd.GeoDataFrame, Dict[str, Any]]:
        """Apply filters and perform weekly aggregation."""
        
        # Extract filter parameters
        temporal_filters = control_state.get('filters', {}).get('temporal', {})
        metric_config = control_state.get('filters', {}).get('metrics', {})
        attribute_filters = control_state.get('filters', {}).get('attributes', {})
        spatial_config = control_state.get('spatial', {})
        
        # Get aggregation method (median as default)
        aggregation_method = metric_config.get('aggregation_method', 'median')
        
        # Store original data size for comparison
        original_size = len(results_data)
        
        # Apply hour filters to results data (no date filters for weekly view)
        filtered_results = self._apply_hour_filters(results_data, temporal_filters)
        hour_filtered_size = len(filtered_results)
        
        # Calculate date context before aggregation
        date_context = self.data_processor.aggregation_engine.calculate_date_span_context(filtered_results)
        date_context['aggregation_method'] = aggregation_method
        
        # Perform weekly hourly aggregation across all available dates
        weekly_aggregated = self.data_processor.aggregation_engine.compute_weekly_aggregation(
            filtered_results, method=aggregation_method
        )
        aggregated_size = len(weekly_aggregated)
        
        # Apply attribute filters to aggregated data
        weekly_aggregated = self._apply_attribute_filters(weekly_aggregated, attribute_filters)
        attribute_filtered_size = len(weekly_aggregated)
        
        # Join aggregated results to shapefile
        joined_data = self.data_processor.join_results_to_shapefile(
            shapefile_data, weekly_aggregated
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
        
        # Log filtering and aggregation progress
        logger.info(f"Weekly aggregation progression: {original_size} → {hour_filtered_size} (hour filter) → {aggregated_size} (aggregated) → {attribute_filtered_size} (attributes) → {joined_size} (joined) → {len(joined_data)} (final)")
        
        # Store filter statistics in session state for display
        if 'filter_stats' not in st.session_state:
            st.session_state.filter_stats = {}
        
        st.session_state.filter_stats['map_b'] = {
            'original_records': original_size,
            'hour_filtered': hour_filtered_size,
            'aggregated_records': aggregated_size,
            'attribute_filtered': attribute_filtered_size,
            'joined_features': joined_size,
            'final_features': len(joined_data),
            'aggregation_method': aggregation_method,
            'hour_reduction': ((original_size - hour_filtered_size) / original_size * 100) if original_size > 0 else 0,
            'attribute_reduction': ((aggregated_size - attribute_filtered_size) / aggregated_size * 100) if aggregated_size > 0 else 0
        }
        
        return joined_data, date_context
    
    def _apply_hour_filters(self, results_data: pd.DataFrame, 
                           temporal_filters: Dict[str, Any]) -> pd.DataFrame:
        """Apply hour filters to results data (no date filters for weekly view)."""
        filtered_data = results_data.copy()
        
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
        """Apply length, speed, and duration filters to aggregated data."""
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
    
    def _display_date_context(self, date_context: Dict[str, Any], 
                             control_state: Dict[str, Any]) -> None:
        """Display context text showing averaged date span and N days."""
        
        aggregation_method = date_context.get('aggregation_method', 'median')
        method_display = aggregation_method.title()
        
        # Create context message
        context_message = f"**{method_display} aggregation** over {date_context['date_range_str']}, N = {date_context['n_days']} days"
        
        # Display in an info box
        st.info(f"📅 {context_message}")
        
        # Add additional context details in expander
        with st.expander("📊 Aggregation Details", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Date Range:**")
                st.write(f"• Start: {date_context['start_date']}")
                st.write(f"• End: {date_context['end_date']}")
                st.write(f"• Days: {date_context['n_days']}")
            
            with col2:
                st.write("**Aggregation:**")
                st.write(f"• Method: {method_display}")
                st.write(f"• Type: Weekly hourly")
                
                # Show hour range if filtered
                temporal_filters = control_state.get('filters', {}).get('temporal', {})
                if 'hour_range' in temporal_filters:
                    hour_range = temporal_filters['hour_range']
                    if hour_range[0] != 0 or hour_range[1] != 23:
                        st.write(f"• Hours: {hour_range[0]}:00-{hour_range[1]}:00")
    
    def _create_weekly_map(self, data: gpd.GeoDataFrame, 
                          control_state: Dict[str, Any]) -> folium.Map:
        """Create the interactive weekly map with styling."""
        
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
            'title': f"{metric_title} (Weekly Aggregation)",
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
        
        # Hour range (no date range for weekly view)
        if 'hour_range' in temporal:
            hour_range = temporal['hour_range']
            if len(hour_range) == 2:
                start_hour, end_hour = hour_range
                if start_hour == end_hour:
                    filters.append(f"Hour: {start_hour}:00")
                else:
                    filters.append(f"Hours: {start_hour}:00-{end_hour}:00")
        
        # Aggregation method
        metric_config = control_state.get('filters', {}).get('metrics', {})
        aggregation_method = metric_config.get('aggregation_method', 'median')
        filters.append(f"Aggregation: {aggregation_method.title()}")
        
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
    
    def _display_map_statistics(self, data: gpd.GeoDataFrame, 
                               control_state: Dict[str, Any],
                               date_context: Dict[str, Any]) -> None:
        """Display map statistics and aggregation effectiveness."""
        
        if data.empty:
            st.warning("⚠️ No data to display after applying filters and aggregation")
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
            aggregation_method = metric_config.get('aggregation_method', 'median')
            
            if metric_type == 'duration' and 'avg_duration_min' in data.columns:
                avg_duration = data['avg_duration_min'].mean()
                st.metric(f"Average Duration ({aggregation_method.title()})", f"{avg_duration:.1f} min")
            elif metric_type == 'speed' and 'avg_speed_kmh' in data.columns:
                avg_speed = data['avg_speed_kmh'].mean()
                st.metric(f"Average Speed ({aggregation_method.title()})", f"{avg_speed:.1f} km/h")
        
        with col3:
            if 'length_m' in data.columns:
                total_length = data['length_m'].sum() / 1000  # Convert to km
                st.metric("Total Network Length", f"{total_length:.1f} km")
        
        # Display aggregation effectiveness
        if 'filter_stats' in st.session_state and 'map_b' in st.session_state.filter_stats:
            stats = st.session_state.filter_stats['map_b']
            
            with st.expander("🔍 Aggregation & Filter Effectiveness", expanded=False):
                col_stats1, col_stats2 = st.columns(2)
                
                with col_stats1:
                    st.write("**Data Processing:**")
                    st.write(f"• Original records: {stats['original_records']:,}")
                    st.write(f"• After hour filters: {stats['hour_filtered']:,}")
                    st.write(f"• After aggregation: {stats['aggregated_records']:,}")
                    st.write(f"• After attribute filters: {stats['attribute_filtered']:,}")
                    st.write(f"• Final features: {stats['final_features']:,}")
                
                with col_stats2:
                    st.write("**Processing Impact:**")
                    st.write(f"• Aggregation method: {stats['aggregation_method'].title()}")
                    if stats['hour_reduction'] > 0:
                        st.write(f"• Hour filtering: -{stats['hour_reduction']:.1f}%")
                    if stats['attribute_reduction'] > 0:
                        st.write(f"• Attribute filtering: -{stats['attribute_reduction']:.1f}%")
                    
                    # Calculate aggregation ratio
                    if stats['hour_filtered'] > 0:
                        aggregation_ratio = stats['aggregated_records'] / stats['hour_filtered']
                        st.write(f"• Aggregation ratio: {aggregation_ratio:.3f}")
        
        # Display data quality indicators for aggregated data
        if 'n_valid' in data.columns:
            with st.expander("📈 Aggregated Data Quality", expanded=False):
                col_qual1, col_qual2 = st.columns(2)
                
                with col_qual1:
                    # Observation count statistics (these are now summed across dates)
                    obs_stats = data['n_valid'].describe()
                    st.write("**Observations per Link (Aggregated):**")
                    st.write(f"• Mean: {obs_stats['mean']:.1f}")
                    st.write(f"• Median: {obs_stats['50%']:.1f}")
                    st.write(f"• Min: {obs_stats['min']:.0f}")
                    st.write(f"• Max: {obs_stats['max']:.0f}")
                
                with col_qual2:
                    # Data coverage indicators for aggregated data
                    low_obs_threshold = 10  # Higher threshold for aggregated data
                    low_obs_count = (data['n_valid'] < low_obs_threshold).sum()
                    low_obs_percent = (low_obs_count / len(data) * 100) if len(data) > 0 else 0
                    
                    st.write("**Aggregated Coverage Quality:**")
                    st.write(f"• Links with <{low_obs_threshold} obs: {low_obs_count} ({low_obs_percent:.1f}%)")
                    st.write(f"• Aggregated over {date_context['n_days']} days")
                    
                    if low_obs_percent > 20:
                        st.warning(f"⚠️ {low_obs_percent:.1f}% of links have sparse aggregated data")
                    elif low_obs_percent > 10:
                        st.info(f"ℹ️ {low_obs_percent:.1f}% of links have limited aggregated data")
                    else:
                        st.success(f"✅ Good aggregated data coverage ({100-low_obs_percent:.1f}% well-covered)")
    
    def _handle_map_clicks(self, map_data: Dict, filtered_data: gpd.GeoDataFrame,
                          results_data: pd.DataFrame, control_state: Dict[str, Any]) -> None:
        """Handle map click events and display link details for weekly aggregated data."""
        
        # Check if there was a click event
        if map_data['last_clicked'] is not None and 'lat' in map_data['last_clicked']:
            click_lat = map_data['last_clicked']['lat']
            click_lon = map_data['last_clicked']['lon']
            
            # Find the closest link to the click point
            clicked_link = self._find_closest_link(click_lat, click_lon, filtered_data)
            
            if clicked_link is not None:
                # Store selected link in session state
                st.session_state['selected_link_id_weekly'] = clicked_link['Id']
                st.session_state['selected_link_data_weekly'] = clicked_link
                
                # Display link details panel for weekly data
                self._display_weekly_link_details_panel(clicked_link, results_data, control_state)
        
        # Display details panel if a link is selected
        elif 'selected_link_id_weekly' in st.session_state:
            selected_link_id = st.session_state['selected_link_id_weekly']
            
            # Find the link in current filtered data
            selected_links = filtered_data[filtered_data['Id'] == selected_link_id]
            
            if not selected_links.empty:
                selected_link = selected_links.iloc[0]
                self._display_weekly_link_details_panel(selected_link, results_data, control_state)
            else:
                # Link not in current filter - clear selection
                if st.button("🗑️ Clear Selection", help="Selected link not visible with current filters", key="clear_weekly_selection"):
                    del st.session_state['selected_link_id_weekly']
                    if 'selected_link_data_weekly' in st.session_state:
                        del st.session_state['selected_link_data_weekly']
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
            
            logger.info(f"Found closest link for weekly view: {closest_link.get('Id', 'N/A')} at distance {distances.loc[closest_idx]}")
            return closest_link
            
        except Exception as e:
            logger.error(f"Error finding closest link in weekly view: {e}")
            return None
    
    def _display_weekly_link_details_panel(self, link_data: pd.Series, 
                                          results_data: pd.DataFrame,
                                          control_state: Dict[str, Any]) -> None:
        """Display detailed information panel for selected link with weekly aggregated data."""
        
        from .link_details_panel import LinkDetailsPanel
        
        # Create expandable details panel
        with st.expander(f"🔗 Weekly Link Details: {link_data.get('Id', 'N/A')}", expanded=True):
            
            # Get all hourly data for this link (for weekly pattern analysis)
            link_id = link_data.get('Id', link_data.get('link_id'))
            
            if link_id and 'link_id' in results_data.columns:
                link_hourly_data = results_data[results_data['link_id'] == link_id]
            else:
                # Try to create from s_From-To pattern
                if 'From' in link_data and 'To' in link_data:
                    expected_link_id = f"s_{link_data['From']}-{link_data['To']}"
                    link_hourly_data = results_data[results_data.get('link_id', '') == expected_link_id]
                else:
                    link_hourly_data = pd.DataFrame()
            
            # Compute aggregation statistics for this link
            aggregation_method = control_state.get('filters', {}).get('metrics', {}).get('aggregation_method', 'median')
            
            if not link_hourly_data.empty:
                aggregation_stats = self.data_processor.aggregation_engine.compute_aggregation_statistics(
                    link_hourly_data, link_id, method=aggregation_method
                )
            else:
                aggregation_stats = {}
            
            # Prepare context information for weekly view
            context = {
                'filters': control_state.get('filters', {}),
                'hour_range': control_state.get('filters', {}).get('temporal', {}).get('hour_range'),
                'metric_type': control_state.get('filters', {}).get('metrics', {}).get('metric_type', 'duration'),
                'aggregation_method': aggregation_method,
                'view_type': 'weekly',  # Indicate this is weekly view
                'aggregation_stats': aggregation_stats  # Add aggregation statistics
            }
            
            # Display aggregation-specific information first
            self._display_aggregation_summary(aggregation_stats, aggregation_method)
            
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
                if st.button("🗑️ Clear Selection", key="clear_weekly_link_selection"):
                    if 'selected_link_id_weekly' in st.session_state:
                        del st.session_state['selected_link_id_weekly']
                    if 'selected_link_data_weekly' in st.session_state:
                        del st.session_state['selected_link_data_weekly']
                    st.rerun()
            
            with col_btn2:
                if st.button("📊 Focus on Link", key="focus_weekly_link"):
                    # Set filters to focus on this specific link
                    st.info("Focus functionality will be implemented")
            
            with col_btn3:
                if st.button("📋 Export Data", key="export_weekly_link_data"):
                    # Export link data
                    st.info("Export functionality will be implemented")
    
    def _display_aggregation_summary(self, aggregation_stats: Dict[str, Any], 
                                   aggregation_method: str) -> None:
        """Display aggregation summary information for the selected link."""
        
        if not aggregation_stats:
            st.warning("⚠️ No aggregation statistics available for this link")
            return
        
        st.subheader(f"📊 {aggregation_method.title()} Aggregation Summary")
        
        # Basic aggregation metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Observations",
                f"{aggregation_stats.get('total_observations', 0):,}"
            )
        
        with col2:
            st.metric(
                "Unique Dates",
                f"{aggregation_stats.get('unique_dates', 0)}"
            )
        
        with col3:
            st.metric(
                "Unique Hours",
                f"{aggregation_stats.get('unique_hours', 0)}"
            )
        
        with col4:
            data_quality = aggregation_stats.get('data_quality', 'unknown')
            quality_color = {
                'good': '🟢',
                'moderate': '🟡', 
                'limited': '🟠',
                'sparse': '🔴',
                'no_data': '⚫'
            }.get(data_quality, '⚪')
            
            st.metric(
                "Data Quality",
                f"{quality_color} {data_quality.title()}"
            )
        
        # Weekly patterns summary
        weekly_patterns = aggregation_stats.get('weekly_patterns', {})
        
        if weekly_patterns:
            with st.expander("📈 Weekly Pattern Analysis", expanded=False):
                
                for metric_name, pattern_data in weekly_patterns.items():
                    if not pattern_data:
                        continue
                    
                    st.write(f"**{metric_name.title()} Pattern:**")
                    
                    col_pattern1, col_pattern2 = st.columns(2)
                    
                    with col_pattern1:
                        st.write(f"• Peak hour: {pattern_data.get('peak_hour', 'N/A')}:00")
                        st.write(f"• Off-peak hour: {pattern_data.get('off_peak_hour', 'N/A')}:00")
                        
                        min_val = pattern_data.get('min_value', 0)
                        max_val = pattern_data.get('max_value', 0)
                        
                        if metric_name == 'duration':
                            st.write(f"• Range: {min_val/60:.1f} - {max_val/60:.1f} min")
                        else:  # speed
                            st.write(f"• Range: {min_val:.1f} - {max_val:.1f} km/h")
                    
                    with col_pattern2:
                        mean_val = pattern_data.get('mean_value', 0)
                        std_val = pattern_data.get('std_value', 0)
                        variation_coeff = pattern_data.get('variation_coefficient', 0)
                        
                        if metric_name == 'duration':
                            st.write(f"• Mean: {mean_val/60:.1f} min")
                            st.write(f"• Std Dev: {std_val/60:.1f} min")
                        else:  # speed
                            st.write(f"• Mean: {mean_val:.1f} km/h")
                            st.write(f"• Std Dev: {std_val:.1f} km/h")
                        
                        st.write(f"• Variation: {variation_coeff:.2f}")
                    
                    # Create simple hourly pattern chart
                    hourly_values = pattern_data.get('hourly_values', {})
                    if hourly_values:
                        hours = list(hourly_values.keys())
                        values = list(hourly_values.values())
                        
                        # Create a simple line chart
                        chart_data = pd.DataFrame({
                            'Hour': hours,
                            metric_name.title(): values
                        })
                        
                        st.line_chart(chart_data.set_index('Hour'))
        
        # Coverage information
        date_coverage = aggregation_stats.get('date_coverage', [])
        hour_coverage = aggregation_stats.get('hour_coverage', [])
        
        if date_coverage or hour_coverage:
            with st.expander("📅 Data Coverage Details", expanded=False):
                
                col_cov1, col_cov2 = st.columns(2)
                
                with col_cov1:
                    if date_coverage:
                        st.write("**Date Coverage:**")
                        if len(date_coverage) <= 10:
                            for date in date_coverage:
                                st.write(f"• {date}")
                        else:
                            st.write(f"• First: {date_coverage[0]}")
                            st.write(f"• Last: {date_coverage[-1]}")
                            st.write(f"• Total: {len(date_coverage)} dates")
                
                with col_cov2:
                    if hour_coverage:
                        st.write("**Hour Coverage:**")
                        if len(hour_coverage) <= 24:
                            hour_ranges = []
                            start = hour_coverage[0]
                            end = start
                            
                            for i in range(1, len(hour_coverage)):
                                if hour_coverage[i] == end + 1:
                                    end = hour_coverage[i]
                                else:
                                    if start == end:
                                        hour_ranges.append(f"{start}:00")
                                    else:
                                        hour_ranges.append(f"{start}:00-{end}:00")
                                    start = hour_coverage[i]
                                    end = start
                            
                            # Add the last range
                            if start == end:
                                hour_ranges.append(f"{start}:00")
                            else:
                                hour_ranges.append(f"{start}:00-{end}:00")
                            
                            for hour_range in hour_ranges:
                                st.write(f"• {hour_range}")


def render_map_b_page():
    """
    Main function to render Map B page in Streamlit.
    This function should be called from the main app navigation.
    """
    
    # Initialize the weekly map interface
    weekly_interface = WeeklyMapInterface()
    
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
    
    # Render the weekly map interface
    weekly_interface.render_weekly_map_page(shapefile_data, hourly_results)


if __name__ == "__main__":
    # For testing purposes
    render_map_b_page()