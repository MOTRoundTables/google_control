"""
Interactive controls module for map visualization.

This module manages user interface controls and real-time filtering
for the traffic monitoring GUI's map visualization feature.
"""

import streamlit as st
import pandas as pd
import geopandas as gpd
from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Union
import logging
import time

# Import the new KPI calculation engine
from .kpi_engine import KPICalculationEngine

logger = logging.getLogger(__name__)


class FilterControls:
    """Manages filter controls for date, time, and attribute filtering."""
    
    def __init__(self):
        self.filter_operators = ['above', 'below', 'between']
    
    def render_temporal_controls(self, data_bounds: Dict, key_prefix: str = "") -> Dict[str, Any]:
        """
        Render temporal filter controls (date picker, hour selector).
        
        Args:
            data_bounds: Dictionary with data bounds (min/max dates, hours)
            key_prefix: Prefix for Streamlit widget keys
            
        Returns:
            Dictionary with selected temporal filters
        """
        st.subheader("Temporal Filters")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Date range picker
            min_date = data_bounds.get('min_date', date.today() - timedelta(days=30))
            max_date = data_bounds.get('max_date', date.today())
            
            date_range = st.date_input(
                "Select Date Range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                key=f"{key_prefix}_date_range"
            )
            
            # Handle single date selection
            if isinstance(date_range, date):
                date_range = (date_range, date_range)
            elif len(date_range) == 1:
                date_range = (date_range[0], date_range[0])
        
        with col2:
            # Hour range selector
            min_hour = data_bounds.get('min_hour', 0)
            max_hour = data_bounds.get('max_hour', 23)
            
            hour_range = st.slider(
                "Select Hour Range",
                min_value=min_hour,
                max_value=max_hour,
                value=(min_hour, max_hour),
                key=f"{key_prefix}_hour_range"
            )
        
        return {
            'date_range': date_range,
            'hour_range': hour_range
        }
    
    def render_metric_controls(self, key_prefix: str = "") -> Dict[str, Any]:
        """
        Render metric selection controls.
        
        Args:
            key_prefix: Prefix for Streamlit widget keys
            
        Returns:
            Dictionary with selected metric options
        """
        st.subheader("Metric Selection")
        
        col1, col2 = st.columns(2)
        
        with col1:
            metric_type = st.selectbox(
                "Primary Metric",
                options=['duration', 'speed'],
                format_func=lambda x: 'Duration (minutes)' if x == 'duration' else 'Speed (km/h)',
                key=f"{key_prefix}_metric_type"
            )
        
        with col2:
            # Aggregation method (for weekly view)
            aggregation_method = st.selectbox(
                "Aggregation Method",
                options=['median', 'mean'],
                key=f"{key_prefix}_aggregation"
            )
        
        return {
            'metric_type': metric_type,
            'aggregation_method': aggregation_method
        }
    
    def render_attribute_filters(self, data_bounds: Dict, key_prefix: str = "") -> Dict[str, Dict]:
        """
        Render attribute filter controls (length, speed, time) with reactive updates.
        
        Args:
            data_bounds: Dictionary with data bounds for each attribute
            key_prefix: Prefix for Streamlit widget keys
            
        Returns:
            Dictionary with attribute filter configurations
        """
        st.subheader("Attribute Filters")
        
        filters = {}
        
        # Length filter
        if 'length_m' in data_bounds:
            with st.expander("🛣️ Length Filter", expanded=False):
                length_enabled = st.checkbox(
                    "Enable Length Filter", 
                    key=f"{key_prefix}_length_enabled",
                    help="Filter links by their physical length"
                )
                
                if length_enabled:
                    length_operator = st.selectbox(
                        "Length Operator",
                        options=self.filter_operators,
                        key=f"{key_prefix}_length_op",
                        help="Choose how to apply the length filter"
                    )
                    
                    min_length = float(data_bounds['length_m']['min'])
                    max_length = float(data_bounds['length_m']['max'])
                    
                    if length_operator == 'between':
                        length_values = st.slider(
                            "Length Range (m)",
                            min_value=min_length,
                            max_value=max_length,
                            value=(min_length, max_length),
                            step=(max_length - min_length) / 100,
                            key=f"{key_prefix}_length_range",
                            help=f"Select length range between {min_length:.0f}m and {max_length:.0f}m"
                        )
                    else:
                        length_values = st.number_input(
                            f"Length {length_operator} (m)",
                            min_value=min_length,
                            max_value=max_length,
                            value=(min_length + max_length) / 2,
                            step=(max_length - min_length) / 100,
                            key=f"{key_prefix}_length_value",
                            help=f"Set threshold for length {length_operator} filter"
                        )
                    
                    filters['length_m'] = {
                        'operator': length_operator,
                        'value': length_values,
                        'enabled': True
                    }
                    
                    # Show filter summary
                    if length_operator == 'between':
                        st.caption(f"📏 Showing links between {length_values[0]:.0f}m and {length_values[1]:.0f}m")
                    else:
                        st.caption(f"📏 Showing links with length {length_operator} {length_values:.0f}m")
        
        # Speed filter
        if 'avg_speed_kmh' in data_bounds:
            with st.expander("🚗 Speed Filter", expanded=False):
                speed_enabled = st.checkbox(
                    "Enable Speed Filter", 
                    key=f"{key_prefix}_speed_enabled",
                    help="Filter links by their average speed"
                )
                
                if speed_enabled:
                    speed_operator = st.selectbox(
                        "Speed Operator",
                        options=self.filter_operators,
                        key=f"{key_prefix}_speed_op",
                        help="Choose how to apply the speed filter"
                    )
                    
                    min_speed = float(data_bounds['avg_speed_kmh']['min'])
                    max_speed = float(data_bounds['avg_speed_kmh']['max'])
                    
                    if speed_operator == 'between':
                        speed_values = st.slider(
                            "Speed Range (km/h)",
                            min_value=min_speed,
                            max_value=max_speed,
                            value=(min_speed, max_speed),
                            step=(max_speed - min_speed) / 100,
                            key=f"{key_prefix}_speed_range",
                            help=f"Select speed range between {min_speed:.1f} and {max_speed:.1f} km/h"
                        )
                    else:
                        speed_values = st.number_input(
                            f"Speed {speed_operator} (km/h)",
                            min_value=min_speed,
                            max_value=max_speed,
                            value=(min_speed + max_speed) / 2,
                            step=(max_speed - min_speed) / 100,
                            key=f"{key_prefix}_speed_value",
                            help=f"Set threshold for speed {speed_operator} filter"
                        )
                    
                    filters['avg_speed_kmh'] = {
                        'operator': speed_operator,
                        'value': speed_values,
                        'enabled': True
                    }
                    
                    # Show filter summary
                    if speed_operator == 'between':
                        st.caption(f"🚗 Showing links between {speed_values[0]:.1f} and {speed_values[1]:.1f} km/h")
                    else:
                        st.caption(f"🚗 Showing links with speed {speed_operator} {speed_values:.1f} km/h")
        
        # Duration filter
        if 'avg_duration_sec' in data_bounds:
            with st.expander("⏱️ Duration Filter", expanded=False):
                duration_enabled = st.checkbox(
                    "Enable Duration Filter", 
                    key=f"{key_prefix}_duration_enabled",
                    help="Filter links by their average travel time"
                )
                
                if duration_enabled:
                    duration_operator = st.selectbox(
                        "Duration Operator",
                        options=self.filter_operators,
                        key=f"{key_prefix}_duration_op",
                        help="Choose how to apply the duration filter"
                    )
                    
                    min_duration = float(data_bounds['avg_duration_sec']['min']) / 60  # Convert to minutes
                    max_duration = float(data_bounds['avg_duration_sec']['max']) / 60
                    
                    if duration_operator == 'between':
                        duration_values = st.slider(
                            "Duration Range (minutes)",
                            min_value=min_duration,
                            max_value=max_duration,
                            value=(min_duration, max_duration),
                            step=(max_duration - min_duration) / 100,
                            key=f"{key_prefix}_duration_range",
                            help=f"Select duration range between {min_duration:.1f} and {max_duration:.1f} minutes"
                        )
                        duration_values = (duration_values[0] * 60, duration_values[1] * 60)  # Convert back to seconds
                    else:
                        duration_value = st.number_input(
                            f"Duration {duration_operator} (minutes)",
                            min_value=min_duration,
                            max_value=max_duration,
                            value=(min_duration + max_duration) / 2,
                            step=(max_duration - min_duration) / 100,
                            key=f"{key_prefix}_duration_value",
                            help=f"Set threshold for duration {duration_operator} filter"
                        )
                        duration_values = duration_value * 60  # Convert to seconds
                    
                    filters['avg_duration_sec'] = {
                        'operator': duration_operator,
                        'value': duration_values,
                        'enabled': True
                    }
                    
                    # Show filter summary
                    if duration_operator == 'between':
                        duration_min_display = duration_values[0] / 60
                        duration_max_display = duration_values[1] / 60
                        st.caption(f"⏱️ Showing links between {duration_min_display:.1f} and {duration_max_display:.1f} minutes")
                    else:
                        duration_display = duration_values / 60
                        st.caption(f"⏱️ Showing links with duration {duration_operator} {duration_display:.1f} minutes")
        
        # Display active filters summary
        if filters:
            st.info(f"🔍 **{len(filters)} attribute filter(s) active**")
        
        return filters
    
    def render_filter_panel(self, data_bounds: Dict, map_type: str = "hourly", 
                           key_prefix: str = "") -> Dict[str, Any]:
        """
        Render complete filter panel for map controls with reactive updates.
        
        Args:
            data_bounds: Dictionary with data bounds
            map_type: Type of map ('hourly' or 'weekly')
            key_prefix: Prefix for Streamlit widget keys
            
        Returns:
            Dictionary with all filter configurations
        """
        filters = {}
        
        # Check if reactive updates are enabled
        reactive_updates = st.session_state.get('maps_preferences', {}).get('reactive_updates', True)
        
        # Add reactive update indicator
        if reactive_updates:
            st.caption("🔄 Reactive mode: Maps update automatically when filters change")
        else:
            st.caption("⏸️ Manual mode: Click refresh to update maps")
        
        # Temporal controls (date picker only for hourly map)
        if map_type == "hourly":
            filters['temporal'] = self.render_temporal_controls(data_bounds, key_prefix)
        else:  # weekly map
            # Only hour selector for weekly map
            st.subheader("Temporal Filters")
            min_hour = data_bounds.get('min_hour', 0)
            max_hour = data_bounds.get('max_hour', 23)
            
            # Use shared state for consistency between maps
            shared_state = st.session_state.get('maps_shared_state', {})
            current_hour_range = shared_state.get('hour_range', (min_hour, max_hour))
            
            hour_range = st.slider(
                "Select Hour Range",
                min_value=min_hour,
                max_value=max_hour,
                value=current_hour_range,
                key=f"{key_prefix}_hour_range",
                help="Hour range applies to both maps for consistency"
            )
            
            # Update shared state if changed
            if 'maps_shared_state' in st.session_state:
                if st.session_state.maps_shared_state.get('hour_range') != hour_range:
                    st.session_state.maps_shared_state['hour_range'] = hour_range
                    if reactive_updates:
                        self._trigger_filter_update("Hour range changed", key_prefix)
            
            filters['temporal'] = {'hour_range': hour_range}
        
        # Metric controls with shared state
        filters['metrics'] = self.render_metric_controls_reactive(key_prefix)
        
        # Attribute filters with reactive updates
        filters['attributes'] = self.render_attribute_filters_reactive(data_bounds, key_prefix)
        
        # Filter summary and performance info
        self._render_filter_summary(filters, key_prefix)
        
        return filters
    
    def render_metric_controls_reactive(self, key_prefix: str = "") -> Dict[str, Any]:
        """
        Render metric selection controls with reactive updates and shared state.
        
        Args:
            key_prefix: Prefix for Streamlit widget keys
            
        Returns:
            Dictionary with selected metric options
        """
        st.subheader("Metric Selection")
        
        # Get shared state
        shared_state = st.session_state.get('maps_shared_state', {})
        reactive_updates = st.session_state.get('maps_preferences', {}).get('reactive_updates', True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            current_metric = shared_state.get('metric_type', 'duration')
            metric_type = st.selectbox(
                "Primary Metric",
                options=['duration', 'speed'],
                index=0 if current_metric == 'duration' else 1,
                format_func=lambda x: 'Duration (minutes)' if x == 'duration' else 'Speed (km/h)',
                key=f"{key_prefix}_metric_type",
                help="Metric type is shared between both maps"
            )
            
            # Update shared state if changed
            if 'maps_shared_state' in st.session_state:
                if st.session_state.maps_shared_state.get('metric_type') != metric_type:
                    st.session_state.maps_shared_state['metric_type'] = metric_type
                    if reactive_updates:
                        self._trigger_filter_update("Metric type changed", key_prefix)
        
        with col2:
            # Aggregation method (for weekly view)
            current_aggregation = shared_state.get('aggregation_method', 'median')
            aggregation_method = st.selectbox(
                "Aggregation Method",
                options=['median', 'mean'],
                index=0 if current_aggregation == 'median' else 1,
                key=f"{key_prefix}_aggregation",
                help="Aggregation method for weekly view"
            )
            
            # Update shared state if changed
            if 'maps_shared_state' in st.session_state:
                if st.session_state.maps_shared_state.get('aggregation_method') != aggregation_method:
                    st.session_state.maps_shared_state['aggregation_method'] = aggregation_method
                    if reactive_updates:
                        self._trigger_filter_update("Aggregation method changed", key_prefix)
        
        return {
            'metric_type': metric_type,
            'aggregation_method': aggregation_method
        }
    
    def render_attribute_filters_reactive(self, data_bounds: Dict, key_prefix: str = "") -> Dict[str, Dict]:
        """
        Render attribute filter controls with reactive updates and improved UX.
        
        Args:
            data_bounds: Dictionary with data bounds for each attribute
            key_prefix: Prefix for Streamlit widget keys
            
        Returns:
            Dictionary with attribute filter configurations
        """
        st.subheader("Attribute Filters")
        
        filters = {}
        reactive_updates = st.session_state.get('maps_preferences', {}).get('reactive_updates', True)
        
        # Add filter reset button
        col_reset, col_count = st.columns([1, 2])
        with col_reset:
            if st.button("🔄 Reset Filters", key=f"{key_prefix}_reset_filters", 
                        help="Reset all attribute filters to default values"):
                self._reset_attribute_filters(key_prefix)
                if reactive_updates:
                    st.rerun()
        
        with col_count:
            # Show active filter count
            active_count = self._count_active_filters(key_prefix)
            if active_count > 0:
                st.caption(f"🔍 {active_count} active filter(s)")
            else:
                st.caption("🔍 No active filters")
        
        # Length filter with reactive updates
        if 'length_m' in data_bounds:
            with st.expander("🛣️ Length Filter", expanded=False):
                length_enabled = st.checkbox(
                    "Enable Length Filter", 
                    key=f"{key_prefix}_length_enabled",
                    help="Filter links by their physical length"
                )
                
                if length_enabled:
                    length_operator = st.selectbox(
                        "Length Operator",
                        options=self.filter_operators,
                        key=f"{key_prefix}_length_op",
                        help="Choose how to apply the length filter"
                    )
                    
                    min_length = float(data_bounds['length_m']['min'])
                    max_length = float(data_bounds['length_m']['max'])
                    
                    if length_operator == 'between':
                        length_values = st.slider(
                            "Length Range (m)",
                            min_value=min_length,
                            max_value=max_length,
                            value=(min_length, max_length),
                            step=(max_length - min_length) / 100,
                            key=f"{key_prefix}_length_range",
                            help=f"Select length range between {min_length:.0f}m and {max_length:.0f}m",
                            on_change=lambda: self._trigger_filter_update("Length filter changed", key_prefix) if reactive_updates else None
                        )
                    else:
                        length_values = st.number_input(
                            f"Length {length_operator} (m)",
                            min_value=min_length,
                            max_value=max_length,
                            value=(min_length + max_length) / 2,
                            step=(max_length - min_length) / 100,
                            key=f"{key_prefix}_length_value",
                            help=f"Set threshold for length {length_operator} filter",
                            on_change=lambda: self._trigger_filter_update("Length filter changed", key_prefix) if reactive_updates else None
                        )
                    
                    filters['length_m'] = {
                        'operator': length_operator,
                        'value': length_values,
                        'enabled': True
                    }
                    
                    # Show filter summary with real-time feedback
                    if length_operator == 'between':
                        st.caption(f"📏 Showing links between {length_values[0]:.0f}m and {length_values[1]:.0f}m")
                    else:
                        st.caption(f"📏 Showing links with length {length_operator} {length_values:.0f}m")
        
        # Speed filter with reactive updates
        if 'avg_speed_kmh' in data_bounds:
            with st.expander("🚗 Speed Filter", expanded=False):
                speed_enabled = st.checkbox(
                    "Enable Speed Filter", 
                    key=f"{key_prefix}_speed_enabled",
                    help="Filter links by their average speed"
                )
                
                if speed_enabled:
                    speed_operator = st.selectbox(
                        "Speed Operator",
                        options=self.filter_operators,
                        key=f"{key_prefix}_speed_op",
                        help="Choose how to apply the speed filter"
                    )
                    
                    min_speed = float(data_bounds['avg_speed_kmh']['min'])
                    max_speed = float(data_bounds['avg_speed_kmh']['max'])
                    
                    if speed_operator == 'between':
                        speed_values = st.slider(
                            "Speed Range (km/h)",
                            min_value=min_speed,
                            max_value=max_speed,
                            value=(min_speed, max_speed),
                            step=(max_speed - min_speed) / 100,
                            key=f"{key_prefix}_speed_range",
                            help=f"Select speed range between {min_speed:.1f} and {max_speed:.1f} km/h",
                            on_change=lambda: self._trigger_filter_update("Speed filter changed", key_prefix) if reactive_updates else None
                        )
                    else:
                        speed_values = st.number_input(
                            f"Speed {speed_operator} (km/h)",
                            min_value=min_speed,
                            max_value=max_speed,
                            value=(min_speed + max_speed) / 2,
                            step=(max_speed - min_speed) / 100,
                            key=f"{key_prefix}_speed_value",
                            help=f"Set threshold for speed {speed_operator} filter",
                            on_change=lambda: self._trigger_filter_update("Speed filter changed", key_prefix) if reactive_updates else None
                        )
                    
                    filters['avg_speed_kmh'] = {
                        'operator': speed_operator,
                        'value': speed_values,
                        'enabled': True
                    }
                    
                    # Show filter summary with real-time feedback
                    if speed_operator == 'between':
                        st.caption(f"🚗 Showing links between {speed_values[0]:.1f} and {speed_values[1]:.1f} km/h")
                    else:
                        st.caption(f"🚗 Showing links with speed {speed_operator} {speed_values:.1f} km/h")
        
        # Duration filter with reactive updates
        if 'avg_duration_sec' in data_bounds:
            with st.expander("⏱️ Duration Filter", expanded=False):
                duration_enabled = st.checkbox(
                    "Enable Duration Filter", 
                    key=f"{key_prefix}_duration_enabled",
                    help="Filter links by their average travel time"
                )
                
                if duration_enabled:
                    duration_operator = st.selectbox(
                        "Duration Operator",
                        options=self.filter_operators,
                        key=f"{key_prefix}_duration_op",
                        help="Choose how to apply the duration filter"
                    )
                    
                    min_duration = float(data_bounds['avg_duration_sec']['min']) / 60  # Convert to minutes
                    max_duration = float(data_bounds['avg_duration_sec']['max']) / 60
                    
                    if duration_operator == 'between':
                        duration_values = st.slider(
                            "Duration Range (minutes)",
                            min_value=min_duration,
                            max_value=max_duration,
                            value=(min_duration, max_duration),
                            step=(max_duration - min_duration) / 100,
                            key=f"{key_prefix}_duration_range",
                            help=f"Select duration range between {min_duration:.1f} and {max_duration:.1f} minutes",
                            on_change=lambda: self._trigger_filter_update("Duration filter changed", key_prefix) if reactive_updates else None
                        )
                        duration_values = (duration_values[0] * 60, duration_values[1] * 60)  # Convert back to seconds
                    else:
                        duration_value = st.number_input(
                            f"Duration {duration_operator} (minutes)",
                            min_value=min_duration,
                            max_value=max_duration,
                            value=(min_duration + max_duration) / 2,
                            step=(max_duration - min_duration) / 100,
                            key=f"{key_prefix}_duration_value",
                            help=f"Set threshold for duration {duration_operator} filter",
                            on_change=lambda: self._trigger_filter_update("Duration filter changed", key_prefix) if reactive_updates else None
                        )
                        duration_values = duration_value * 60  # Convert to seconds
                    
                    filters['avg_duration_sec'] = {
                        'operator': duration_operator,
                        'value': duration_values,
                        'enabled': True
                    }
                    
                    # Show filter summary with real-time feedback
                    if duration_operator == 'between':
                        duration_min_display = duration_values[0] / 60
                        duration_max_display = duration_values[1] / 60
                        st.caption(f"⏱️ Showing links between {duration_min_display:.1f} and {duration_max_display:.1f} minutes")
                    else:
                        duration_display = duration_values / 60
                        st.caption(f"⏱️ Showing links with duration {duration_operator} {duration_display:.1f} minutes")
        
        return filters
    
    def _trigger_filter_update(self, reason: str, key_prefix: str) -> None:
        """Trigger a reactive filter update."""
        if st.session_state.get('maps_preferences', {}).get('reactive_updates', True):
            # Update loading state
            if 'maps_loading_state' in st.session_state:
                st.session_state.maps_loading_state['loading_message'] = f"Applying filters: {reason}"
                st.session_state.maps_loading_state['is_loading'] = True
            
            # Log the update
            logger.info(f"Filter update triggered: {reason} (prefix: {key_prefix})")
    
    def _reset_attribute_filters(self, key_prefix: str) -> None:
        """Reset all attribute filters to default values."""
        # Reset filter checkboxes
        filter_keys = [
            f"{key_prefix}_length_enabled",
            f"{key_prefix}_speed_enabled", 
            f"{key_prefix}_duration_enabled"
        ]
        
        for key in filter_keys:
            if key in st.session_state:
                st.session_state[key] = False
        
        logger.info(f"Attribute filters reset for prefix: {key_prefix}")
    
    def _count_active_filters(self, key_prefix: str) -> int:
        """Count the number of active attribute filters."""
        count = 0
        filter_keys = [
            f"{key_prefix}_length_enabled",
            f"{key_prefix}_speed_enabled",
            f"{key_prefix}_duration_enabled"
        ]
        
        for key in filter_keys:
            if st.session_state.get(key, False):
                count += 1
        
        return count
    
    def _render_filter_summary(self, filters: Dict, key_prefix: str) -> None:
        """Render a summary of active filters with performance info."""
        active_filters = []
        
        # Count temporal filters
        if 'temporal' in filters:
            temporal = filters['temporal']
            if 'date_range' in temporal:
                active_filters.append("Date range")
            if 'hour_range' in temporal:
                hour_range = temporal['hour_range']
                if hour_range != (0, 23):  # Not full range
                    active_filters.append("Hour range")
        
        # Count attribute filters
        if 'attributes' in filters:
            active_filters.extend([f"{attr.replace('_', ' ').title()}" for attr in filters['attributes'].keys()])
        
        # Display summary
        if active_filters:
            st.info(f"🔍 **Active Filters ({len(active_filters)}):** {', '.join(active_filters)}")
        else:
            st.info("🔍 **No active filters** - showing all data")
        
        # Performance info
        if 'maps_performance' in st.session_state:
            perf = st.session_state.maps_performance
            if perf['render_count'] > 0:
                st.caption(f"⚡ Performance: {perf['render_count']} renders, "
                          f"{perf['cache_hits']} cache hits, "
                          f"{perf['cache_misses']} cache misses")


class SpatialSelection:
    """Handles spatial selection tools (box, lasso, text search)."""
    
    def __init__(self):
        self.selection_types = ['box', 'lasso', 'text_search']
        self.active_selection = None
        self.selection_geometry = None
    
    def render_spatial_controls(self, data: gpd.GeoDataFrame, key_prefix: str = "") -> Dict[str, Any]:
        """
        Render enhanced spatial selection controls with improved functionality.
        
        Args:
            data: GeoDataFrame with network data
            key_prefix: Prefix for Streamlit widget keys
            
        Returns:
            Dictionary with spatial selection configuration
        """
        st.subheader("🗺️ Spatial Selection")
        
        selection_config = {}
        
        # Selection type with enhanced options
        selection_type = st.selectbox(
            "Selection Tool",
            options=['none'] + self.selection_types,
            format_func=lambda x: {
                'none': '🚫 No Selection',
                'box': '📦 Box Selection',
                'lasso': '🎯 Lasso Selection', 
                'text_search': '🔍 Text Search'
            }.get(x, x),
            key=f"{key_prefix}_selection_type",
            help="Choose spatial selection method for filtering network links"
        )
        
        selection_config['type'] = selection_type
        
        if selection_type == 'text_search':
            # Enhanced text search for link_id, From, or To values
            col1, col2 = st.columns([1, 2])
            
            with col1:
                search_field = st.selectbox(
                    "Search Field",
                    options=['link_id', 'From', 'To', 'Id'],
                    key=f"{key_prefix}_search_field",
                    help="Select which field to search in"
                )
            
            with col2:
                search_value = st.text_input(
                    f"Search {search_field}",
                    key=f"{key_prefix}_search_value",
                    placeholder=f"Enter {search_field} value to search...",
                    help=f"Search for links containing this value in {search_field} field"
                )
            
            # Advanced search options
            with st.expander("🔧 Advanced Search Options", expanded=False):
                case_sensitive = st.checkbox(
                    "Case Sensitive",
                    key=f"{key_prefix}_case_sensitive",
                    help="Enable case-sensitive search"
                )
                
                exact_match = st.checkbox(
                    "Exact Match",
                    key=f"{key_prefix}_exact_match", 
                    help="Search for exact matches only"
                )
                
                # Multiple search terms
                multi_search = st.text_area(
                    "Multiple Search Terms (one per line)",
                    key=f"{key_prefix}_multi_search",
                    placeholder="Enter multiple search terms, one per line",
                    help="Search for multiple values at once"
                )
            
            selection_config.update({
                'search_field': search_field,
                'search_value': search_value,
                'case_sensitive': case_sensitive,
                'exact_match': exact_match,
                'multi_search': multi_search
            })
            
            # Apply enhanced text search
            if search_value or multi_search:
                filtered_data = self.apply_enhanced_text_search(
                    data, search_field, search_value, multi_search, 
                    case_sensitive, exact_match
                )
                selection_config['selected_data'] = filtered_data
                
                # Display search results summary
                if len(filtered_data) > 0:
                    st.success(f"✅ Found {len(filtered_data)} matching links")
                    
                    # Show sample results
                    if len(filtered_data) <= 10:
                        st.write("**Matching Links:**")
                        for _, row in filtered_data.iterrows():
                            st.write(f"• {row.get('link_id', 'N/A')} ({row.get('From', 'N/A')} → {row.get('To', 'N/A')})")
                    else:
                        st.write(f"**Sample Results (showing first 5 of {len(filtered_data)}):**")
                        for _, row in filtered_data.head(5).iterrows():
                            st.write(f"• {row.get('link_id', 'N/A')} ({row.get('From', 'N/A')} → {row.get('To', 'N/A')})")
                else:
                    st.warning("⚠️ No matching links found")
        
        elif selection_type == 'box':
            # Box selection controls
            st.info("📦 **Box Selection Mode**")
            st.write("Use the map to draw a rectangular selection box:")
            
            col1, col2 = st.columns(2)
            with col1:
                # Manual coordinate input option
                manual_coords = st.checkbox(
                    "Manual Coordinates",
                    key=f"{key_prefix}_manual_box",
                    help="Enter box coordinates manually"
                )
            
            with col2:
                clear_selection = st.button(
                    "Clear Selection",
                    key=f"{key_prefix}_clear_box",
                    help="Clear current box selection"
                )
            
            if manual_coords:
                # Manual coordinate input
                col_x1, col_y1, col_x2, col_y2 = st.columns(4)
                
                with col_x1:
                    x_min = st.number_input("X Min", key=f"{key_prefix}_x_min")
                with col_y1:
                    y_min = st.number_input("Y Min", key=f"{key_prefix}_y_min")
                with col_x2:
                    x_max = st.number_input("X Max", key=f"{key_prefix}_x_max")
                with col_y2:
                    y_max = st.number_input("Y Max", key=f"{key_prefix}_y_max")
                
                if st.button("Apply Box Selection", key=f"{key_prefix}_apply_box"):
                    try:
                        from shapely.geometry import box
                        selection_box = box(x_min, y_min, x_max, y_max)
                        filtered_data = self.apply_spatial_filter(data, selection_box)
                        selection_config['selected_data'] = filtered_data
                        selection_config['selection_geometry'] = selection_box
                        st.success(f"✅ Box selection applied: {len(filtered_data)} links selected")
                    except Exception as e:
                        st.error(f"❌ Error applying box selection: {str(e)}")
            
            selection_config['manual_coords'] = manual_coords
            selection_config['clear_selection'] = clear_selection
        
        elif selection_type == 'lasso':
            # Lasso selection controls
            st.info("🎯 **Lasso Selection Mode**")
            st.write("Use the map to draw a freehand selection area:")
            
            col1, col2 = st.columns(2)
            with col1:
                # Lasso drawing options
                smooth_lasso = st.checkbox(
                    "Smooth Lasso",
                    value=True,
                    key=f"{key_prefix}_smooth_lasso",
                    help="Apply smoothing to lasso selection"
                )
            
            with col2:
                clear_lasso = st.button(
                    "Clear Lasso",
                    key=f"{key_prefix}_clear_lasso",
                    help="Clear current lasso selection"
                )
            
            # Lasso tolerance setting
            lasso_tolerance = st.slider(
                "Selection Tolerance",
                min_value=0.1,
                max_value=2.0,
                value=0.5,
                step=0.1,
                key=f"{key_prefix}_lasso_tolerance",
                help="Adjust sensitivity of lasso selection"
            )
            
            selection_config.update({
                'smooth_lasso': smooth_lasso,
                'clear_lasso': clear_lasso,
                'lasso_tolerance': lasso_tolerance
            })
        
        # Display current selection summary
        if selection_config.get('selected_data') is not None:
            selected_count = len(selection_config['selected_data'])
            total_count = len(data)
            percentage = (selected_count / total_count * 100) if total_count > 0 else 0
            
            st.info(f"🎯 **Current Selection:** {selected_count:,} of {total_count:,} links ({percentage:.1f}%)")
        
        return selection_config
    
    def apply_enhanced_text_search(self, data: gpd.GeoDataFrame, search_field: str, 
                                 search_value: str, multi_search: str = "",
                                 case_sensitive: bool = False, exact_match: bool = False) -> gpd.GeoDataFrame:
        """
        Apply enhanced text search with multiple options.
        
        Args:
            data: Input GeoDataFrame
            search_field: Field to search in
            search_value: Primary search value
            multi_search: Multiple search terms (newline separated)
            case_sensitive: Whether search is case sensitive
            exact_match: Whether to use exact matching
            
        Returns:
            Filtered GeoDataFrame
        """
        if search_field not in data.columns:
            logger.warning(f"Search field '{search_field}' not found in data")
            return data
        
        # Prepare search terms
        search_terms = []
        if search_value.strip():
            search_terms.append(search_value.strip())
        
        if multi_search.strip():
            search_terms.extend([term.strip() for term in multi_search.split('\n') if term.strip()])
        
        if not search_terms:
            return data
        
        # Apply search
        mask = pd.Series([False] * len(data), index=data.index)
        
        for term in search_terms:
            if exact_match:
                # Exact match
                if case_sensitive:
                    term_mask = data[search_field].astype(str) == term
                else:
                    term_mask = data[search_field].astype(str).str.lower() == term.lower()
            else:
                # Contains match
                term_mask = data[search_field].astype(str).str.contains(
                    term, case=case_sensitive, na=False, regex=False
                )
            
            mask = mask | term_mask
        
        filtered_data = data[mask]
        
        logger.info(f"Enhanced text search in {search_field}: {len(filtered_data)} results from {len(search_terms)} terms")
        return filtered_data
    
    def apply_spatial_filter(self, data: gpd.GeoDataFrame, selection_geometry) -> gpd.GeoDataFrame:
        """
        Apply spatial filter using selection geometry.
        
        Args:
            data: Input GeoDataFrame
            selection_geometry: Shapely geometry for spatial filtering
            
        Returns:
            Filtered GeoDataFrame containing links within selection
        """
        try:
            # Ensure both data and selection geometry are in same CRS
            if hasattr(selection_geometry, 'crs') and data.crs != selection_geometry.crs:
                selection_geometry = selection_geometry.to_crs(data.crs)
            
            # Apply spatial filter - links that intersect with selection
            mask = data.geometry.intersects(selection_geometry)
            filtered_data = data[mask]
            
            logger.info(f"Spatial filter applied: {len(filtered_data)} links selected from {len(data)} total")
            return filtered_data
            
        except Exception as e:
            logger.error(f"Error applying spatial filter: {str(e)}")
            return data
    
    def apply_text_search(self, data: gpd.GeoDataFrame, search_field: str, 
                         search_value: str) -> gpd.GeoDataFrame:
        """
        Apply basic text search to data (maintained for backward compatibility).
        
        Args:
            data: Input GeoDataFrame
            search_field: Field to search in
            search_value: Value to search for
            
        Returns:
            Filtered GeoDataFrame
        """
        return self.apply_enhanced_text_search(data, search_field, search_value)
    
    def handle_spatial_selection(self, selection_type: str, data: gpd.GeoDataFrame, 
                                **kwargs) -> gpd.GeoDataFrame:
        """
        Handle spatial selection based on type and parameters.
        
        Args:
            selection_type: Type of spatial selection
            data: Input GeoDataFrame
            **kwargs: Additional parameters for selection
            
        Returns:
            Filtered GeoDataFrame
        """
        if selection_type == 'text_search':
            return self.apply_enhanced_text_search(
                data, 
                kwargs.get('search_field', 'link_id'),
                kwargs.get('search_value', ''),
                kwargs.get('multi_search', ''),
                kwargs.get('case_sensitive', False),
                kwargs.get('exact_match', False)
            )
        elif selection_type in ['box', 'lasso']:
            selection_geometry = kwargs.get('selection_geometry')
            if selection_geometry:
                return self.apply_spatial_filter(data, selection_geometry)
        
        return data


class PlaybackController:
    """Handles time slider animation and playback controls with throttled rendering."""
    
    def __init__(self):
        self.playback_speeds = [0.25, 0.5, 1.0, 2.0, 4.0, 8.0]  # Seconds per hour
        self.playback_state = {
            'is_playing': False,
            'current_hour': 0,
            'last_update': None,
            'frame_count': 0
        }
        self.throttle_interval = 1.0  # Minimum seconds between updates
    
    def render_playback_controls(self, time_range: Tuple[int, int], key_prefix: str = "") -> Dict[str, Any]:
        """
        Render enhanced playback controls for hourly animation with throttled rendering.
        
        Args:
            time_range: Tuple of (min_hour, max_hour)
            key_prefix: Prefix for Streamlit widget keys
            
        Returns:
            Dictionary with playback configuration
        """
        st.subheader("⏯️ Playback Animation")
        
        # Main playback controls row
        col1, col2, col3, col4 = st.columns([1, 2, 1, 1])
        
        with col1:
            # Play/pause toggle button
            if st.session_state.get(f"{key_prefix}_is_playing", False):
                if st.button("⏸️ Pause", key=f"{key_prefix}_pause"):
                    st.session_state[f"{key_prefix}_is_playing"] = False
                    self.playback_state['is_playing'] = False
            else:
                if st.button("▶️ Play", key=f"{key_prefix}_play"):
                    st.session_state[f"{key_prefix}_is_playing"] = True
                    self.playback_state['is_playing'] = True
        
        with col2:
            # Current hour slider with enhanced formatting
            current_hour = st.slider(
                "Time of Day",
                min_value=time_range[0],
                max_value=time_range[1],
                value=st.session_state.get(f"{key_prefix}_current_hour", time_range[0]),
                key=f"{key_prefix}_current_hour",
                format="%d:00",
                help=f"Select hour from {time_range[0]}:00 to {time_range[1]}:00"
            )
        
        with col3:
            # Playback speed with enhanced options
            playback_speed = st.selectbox(
                "Speed",
                options=self.playback_speeds,
                index=2,  # Default to 1.0x
                format_func=lambda x: f"{x}x",
                key=f"{key_prefix}_speed",
                help="Animation playback speed"
            )
        
        with col4:
            # Reset button
            if st.button("⏮️ Reset", key=f"{key_prefix}_reset"):
                st.session_state[f"{key_prefix}_current_hour"] = time_range[0]
                st.session_state[f"{key_prefix}_is_playing"] = False
                self.playback_state['current_hour'] = time_range[0]
                self.playback_state['is_playing'] = False
        
        # Advanced playback options
        with st.expander("🔧 Playback Options", expanded=False):
            col_opt1, col_opt2 = st.columns(2)
            
            with col_opt1:
                # Loop playback
                loop_playback = st.checkbox(
                    "Loop Playback",
                    value=True,
                    key=f"{key_prefix}_loop",
                    help="Automatically restart from beginning when reaching end"
                )
                
                # Auto-advance
                auto_advance = st.checkbox(
                    "Auto-advance",
                    value=st.session_state.get(f"{key_prefix}_is_playing", False),
                    key=f"{key_prefix}_auto_advance",
                    help="Automatically advance to next hour during playback"
                )
            
            with col_opt2:
                # Frame rate throttling
                throttle_fps = st.slider(
                    "Max FPS",
                    min_value=1,
                    max_value=10,
                    value=2,
                    key=f"{key_prefix}_throttle_fps",
                    help="Maximum frames per second for smooth animation"
                )
                
                # Step size
                step_size = st.selectbox(
                    "Hour Step",
                    options=[1, 2, 3, 4, 6],
                    index=0,
                    key=f"{key_prefix}_step_size",
                    help="Number of hours to advance per step"
                )
        
        # Clock badge display with enhanced formatting
        is_playing = st.session_state.get(f"{key_prefix}_is_playing", False)
        if is_playing:
            # Format hour as HH:MM
            hour_display = f"{current_hour:02d}:00"
            progress = (current_hour - time_range[0]) / (time_range[1] - time_range[0]) * 100
            
            st.info(f"🕐 **Playing:** {hour_display} | Progress: {progress:.0f}% | Speed: {playback_speed}x")
            
            # Progress bar
            st.progress(progress / 100)
        else:
            hour_display = f"{current_hour:02d}:00"
            st.info(f"⏸️ **Paused:** {hour_display}")
        
        # Update playback state
        self.playback_state.update({
            'is_playing': is_playing,
            'current_hour': current_hour,
            'playback_speed': playback_speed,
            'loop_playback': loop_playback,
            'auto_advance': auto_advance,
            'throttle_fps': throttle_fps,
            'step_size': step_size
        })
        
        return {
            'is_playing': is_playing,
            'current_hour': current_hour,
            'playback_speed': playback_speed,
            'time_range': time_range,
            'loop_playback': loop_playback,
            'auto_advance': auto_advance,
            'throttle_fps': throttle_fps,
            'step_size': step_size,
            'hour_display': hour_display,
            'progress_percent': (current_hour - time_range[0]) / (time_range[1] - time_range[0]) * 100 if time_range[1] > time_range[0] else 0
        }
    
    def create_playback_controls(self, time_range: Tuple[int, int]) -> Dict[str, Any]:
        """
        Create enhanced playback controls configuration.
        
        Args:
            time_range: Tuple of (min_hour, max_hour)
            
        Returns:
            Dictionary with playback configuration
        """
        return {
            'enabled': True,
            'time_range': time_range,
            'current_hour': time_range[0],
            'is_playing': False,
            'playback_speed': 1.0,
            'loop_playback': True,
            'auto_advance': False,
            'throttle_fps': 2,
            'step_size': 1
        }
    
    def should_update_frame(self, playback_config: Dict[str, Any]) -> bool:
        """
        Determine if frame should be updated based on throttling settings.
        
        Args:
            playback_config: Playback configuration dictionary
            
        Returns:
            Boolean indicating if frame should be updated
        """
        import time
        
        if not playback_config.get('is_playing', False):
            return False
        
        current_time = time.time()
        throttle_fps = playback_config.get('throttle_fps', 2)
        min_interval = 1.0 / throttle_fps
        
        last_update = self.playback_state.get('last_update')
        if last_update is None or (current_time - last_update) >= min_interval:
            self.playback_state['last_update'] = current_time
            return True
        
        return False
    
    def advance_playback(self, playback_config: Dict[str, Any], key_prefix: str = "") -> Dict[str, Any]:
        """
        Advance playback to next frame with throttling and loop handling.
        
        Args:
            playback_config: Current playback configuration
            key_prefix: Prefix for session state keys
            
        Returns:
            Updated playback configuration
        """
        if not self.should_update_frame(playback_config):
            return playback_config
        
        current_hour = playback_config['current_hour']
        time_range = playback_config['time_range']
        step_size = playback_config.get('step_size', 1)
        loop_playback = playback_config.get('loop_playback', True)
        
        # Calculate next hour
        next_hour = current_hour + step_size
        
        # Handle end of range
        if next_hour > time_range[1]:
            if loop_playback:
                next_hour = time_range[0]  # Loop back to start
            else:
                next_hour = time_range[1]  # Stop at end
                playback_config['is_playing'] = False
                st.session_state[f"{key_prefix}_is_playing"] = False
        
        # Update session state
        st.session_state[f"{key_prefix}_current_hour"] = next_hour
        
        # Update configuration
        playback_config['current_hour'] = next_hour
        self.playback_state['current_hour'] = next_hour
        self.playback_state['frame_count'] += 1
        
        return playback_config
    
    def get_playback_status(self) -> Dict[str, Any]:
        """
        Get current playback status for debugging and monitoring.
        
        Returns:
            Dictionary with playback status information
        """
        return {
            'state': self.playback_state.copy(),
            'throttle_interval': self.throttle_interval,
            'frame_count': self.playback_state.get('frame_count', 0)
        }
    
    def reset_playback_state(self) -> None:
        """Reset playback state to initial values."""
        self.playback_state = {
            'is_playing': False,
            'current_hour': 0,
            'last_update': None,
            'frame_count': 0
        }


class KPIDisplay:
    """Enhanced KPI strip display and calculations using KPICalculationEngine."""
    
    def __init__(self):
        self.kpi_engine = KPICalculationEngine()
        self.previous_kpis = None  # Store for reactive updates
    
    def calculate_kpis(self, data: gpd.GeoDataFrame, total_links: int, 
                      date_context: Optional[Dict] = None,
                      original_results: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Calculate comprehensive KPI metrics for current data with reactive updates.
        
        Args:
            data: Current filtered/displayed data
            total_links: Total number of links in network
            date_context: Optional date context information
            original_results: Original results data for comparison
            
        Returns:
            Dictionary with calculated KPIs
        """
        # Calculate reactive KPIs with change indicators
        kpis = self.kpi_engine.calculate_reactive_kpis(
            current_data=data,
            previous_kpis=self.previous_kpis,
            total_network_links=total_links,
            date_context=date_context,
            original_results=original_results
        )
        
        # Store current KPIs for next reactive update
        self.previous_kpis = kpis.copy()
        
        return kpis
    
    def render_kpi_strip(self, kpis: Dict[str, Any]) -> None:
        """
        Render enhanced KPI strip in Streamlit with change indicators.
        
        Args:
            kpis: Dictionary with KPI values and change indicators
        """
        st.subheader("📊 Key Performance Indicators")
        
        # Main KPI metrics row
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            value, unit, change = self.kpi_engine.format_kpi_for_display(kpis, 'coverage_percent')
            st.metric(
                "Coverage",
                f"{value}{unit}",
                delta=change,
                help="Percentage of network links currently displayed"
            )
        
        with col2:
            value, unit, change = self.kpi_engine.format_kpi_for_display(kpis, 'mean_speed')
            st.metric(
                "Mean Speed",
                f"{value} {unit}",
                delta=change,
                help="Average speed across all displayed links"
            )
        
        with col3:
            value, unit, change = self.kpi_engine.format_kpi_for_display(kpis, 'mean_duration')
            st.metric(
                "Mean Duration",
                f"{value} {unit}",
                delta=change,
                help="Average travel time across all displayed links"
            )
        
        with col4:
            value, unit, change = self.kpi_engine.format_kpi_for_display(kpis, 'n_links_rendered')
            st.metric(
                "Links Rendered",
                f"{value}",
                delta=change,
                help="Number of network links currently displayed"
            )
        
        with col5:
            value, unit, change = self.kpi_engine.format_kpi_for_display(kpis, 'n_days')
            st.metric(
                "Days",
                f"{value}",
                help="Number of days in current analysis period"
            )
        
        # Additional metrics row
        col6, col7, col8, col9 = st.columns(4)
        
        with col6:
            value, unit, change = self.kpi_engine.format_kpi_for_display(kpis, 'total_observations')
            st.metric(
                "Observations",
                f"{value}",
                delta=change,
                help="Total number of traffic observations"
            )
        
        with col7:
            value, unit, change = self.kpi_engine.format_kpi_for_display(kpis, 'network_length_km')
            st.metric(
                "Network Length",
                f"{value} {unit}",
                help="Total length of displayed network"
            )
        
        with col8:
            value, unit, change = self.kpi_engine.format_kpi_for_display(kpis, 'data_quality_score')
            st.metric(
                "Data Quality",
                f"{value}{unit}",
                help="Overall data quality score based on validity checks"
            )
        
        with col9:
            # Display quality assessment as colored indicator
            quality = kpis.get('quality_assessment', 'unknown')
            quality_colors = {
                'excellent': '🟢',
                'good': '🟡', 
                'moderate': '🟠',
                'poor': '🔴',
                'unknown': '⚪'
            }
            quality_icon = quality_colors.get(quality, '⚪')
            st.metric(
                "Quality",
                f"{quality_icon} {quality.title()}",
                help=f"Data quality assessment: {quality}"
            )
        
        # KPI summary text
        summary_text = self.kpi_engine.get_kpi_summary_text(kpis)
        st.info(f"📈 **Summary:** {summary_text}")
    
    def render_detailed_kpis(self, kpis: Dict[str, Any]) -> None:
        """
        Render detailed KPI breakdown in expandable section.
        
        Args:
            kpis: Dictionary with KPI values
        """
        with st.expander("📊 Detailed KPI Breakdown", expanded=False):
            
            # Performance metrics
            col_perf1, col_perf2 = st.columns(2)
            
            with col_perf1:
                st.write("**Speed Metrics:**")
                st.write(f"• Mean: {kpis.get('mean_speed', 0):.1f} km/h")
                st.write(f"• Median: {kpis.get('median_speed', 0):.1f} km/h")
                st.write(f"• Range: {kpis.get('min_speed', 0):.1f} - {kpis.get('max_speed', 0):.1f} km/h")
                if kpis.get('speed_std', 0) > 0:
                    st.write(f"• Std Dev: {kpis.get('speed_std', 0):.1f} km/h")
            
            with col_perf2:
                st.write("**Duration Metrics:**")
                st.write(f"• Mean: {kpis.get('mean_duration', 0):.1f} min")
                st.write(f"• Median: {kpis.get('median_duration', 0):.1f} min")
                st.write(f"• Range: {kpis.get('min_duration', 0):.1f} - {kpis.get('max_duration', 0):.1f} min")
                if kpis.get('duration_std', 0) > 0:
                    st.write(f"• Std Dev: {kpis.get('duration_std', 0):.1f} min")
            
            # Coverage and quality metrics
            col_qual1, col_qual2 = st.columns(2)
            
            with col_qual1:
                st.write("**Coverage Metrics:**")
                st.write(f"• Coverage: {kpis.get('coverage_percent', 0):.1f}%")
                st.write(f"• Quality: {kpis.get('coverage_quality', 'unknown').title()}")
                st.write(f"• Links: {kpis.get('n_links_rendered', 0):,}")
                st.write(f"• Network: {kpis.get('network_length_km', 0):.1f} km")
            
            with col_qual2:
                st.write("**Data Quality:**")
                st.write(f"• Overall Score: {kpis.get('data_quality_score', 0):.0f}/100")
                st.write(f"• Sparse Links: {kpis.get('sparse_links_percent', 0):.1f}%")
                st.write(f"• Invalid Speeds: {kpis.get('invalid_speeds_percent', 0):.1f}%")
                st.write(f"• Invalid Durations: {kpis.get('invalid_durations_percent', 0):.1f}%")
            
            # Temporal and filter metrics
            col_temp1, col_temp2 = st.columns(2)
            
            with col_temp1:
                st.write("**Temporal Coverage:**")
                st.write(f"• Days: {kpis.get('n_days', 0)}")
                st.write(f"• Date Range: {kpis.get('date_range_str', 'Unknown')}")
                st.write(f"• Coverage: {kpis.get('temporal_coverage', 'unknown').title()}")
            
            with col_temp2:
                st.write("**Filter Effectiveness:**")
                st.write(f"• Reduction: {kpis.get('filter_reduction_percent', 0):.1f}%")
                st.write(f"• Effectiveness: {kpis.get('filter_effectiveness', 'unknown').replace('_', ' ').title()}")
                
                # Show observations statistics
                if kpis.get('total_observations', 0) > 0:
                    st.write(f"• Total Observations: {kpis.get('total_observations', 0):,}")
                    st.write(f"• Mean per Link: {kpis.get('mean_observations_per_link', 0):.1f}")
    
    def reset_reactive_state(self) -> None:
        """Reset the reactive state for KPI change tracking."""
        self.previous_kpis = None


class InteractiveControls:
    """Main interface for interactive control operations."""
    
    def __init__(self):
        self.filter_controls = FilterControls()
        self.spatial_selection = SpatialSelection()
        self.playback_controller = PlaybackController()
        self.kpi_display = KPIDisplay()
    
    def render_control_panel(self, data: gpd.GeoDataFrame, data_bounds: Dict,
                           map_type: str = "hourly", key_prefix: str = "") -> Dict[str, Any]:
        """
        Render complete control panel for map interaction.
        
        Args:
            data: GeoDataFrame with network data
            data_bounds: Dictionary with data bounds
            map_type: Type of map ('hourly' or 'weekly')
            key_prefix: Prefix for Streamlit widget keys
            
        Returns:
            Dictionary with all control configurations
        """
        controls = {}
        
        # Filter controls
        controls['filters'] = self.filter_controls.render_filter_panel(
            data_bounds, map_type, key_prefix
        )
        
        # Spatial selection
        controls['spatial'] = self.spatial_selection.render_spatial_controls(
            data, key_prefix
        )
        
        # Playback controls (only for hourly map)
        if map_type == "hourly":
            time_range = (data_bounds.get('min_hour', 0), data_bounds.get('max_hour', 23))
            controls['playback'] = self.playback_controller.render_playback_controls(
                time_range, key_prefix
            )
        
        return controls
    
    def calculate_and_display_kpis(self, current_data: gpd.GeoDataFrame, 
                                  total_links: int, date_context: Optional[Dict] = None,
                                  original_results: Optional[pd.DataFrame] = None,
                                  show_detailed: bool = False) -> Dict[str, Any]:
        """
        Calculate and display comprehensive KPIs for current data state with reactive updates.
        
        Args:
            current_data: Current filtered/displayed data
            total_links: Total number of links in network
            date_context: Optional date context information
            original_results: Original results data for comparison
            show_detailed: Whether to show detailed KPI breakdown
            
        Returns:
            Dictionary with calculated KPIs
        """
        kpis = self.kpi_display.calculate_kpis(
            current_data, total_links, date_context, original_results
        )
        self.kpi_display.render_kpi_strip(kpis)
        
        if show_detailed:
            self.kpi_display.render_detailed_kpis(kpis)
        
        return kpis
    
    def reset_kpi_state(self) -> None:
        """Reset KPI reactive state for fresh calculations."""
        self.kpi_display.reset_reactive_state()