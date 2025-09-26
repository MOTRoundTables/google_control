"""
Map rendering module for interactive map visualization.

This module handles creating interactive maps with symbology, legends, and controls
using Folium integrated with Streamlit.
"""

import folium
import geopandas as gpd
import pandas as pd
import streamlit as st
from typing import Dict, List, Tuple, Optional, Any
import json
import logging

logger = logging.getLogger(__name__)


class MapRenderer:
    """Core map rendering using Folium."""
    
    def __init__(self, target_crs: str = "EPSG:2039"):
        self.target_crs = target_crs
        self.default_zoom = 10
        self.default_center = [31.5, 34.8]  # Approximate center of Israel
    
    def create_base_map(self, bounds: Optional[Tuple] = None, crs: str = "EPSG:2039") -> folium.Map:
        """
        Create base map with EPSG 2039 support.
        
        Args:
            bounds: Optional bounds tuple (minx, miny, maxx, maxy)
            crs: Coordinate reference system
            
        Returns:
            Folium Map object
        """
        # Calculate center and zoom from bounds if provided
        if bounds is not None and len(bounds) == 4:
            minx, miny, maxx, maxy = bounds
            center_lat = (miny + maxy) / 2
            center_lon = (minx + maxx) / 2
            center = [center_lat, center_lon]
        else:
            center = self.default_center
        
        # Create base map
        m = folium.Map(
            location=center,
            zoom_start=self.default_zoom,
            tiles='OpenStreetMap'
        )
        
        logger.debug(f"Created base map centered at {center}")
        return m
    
    def add_network_layer(self, map_obj: folium.Map, data: gpd.GeoDataFrame, 
                         style_config: Dict) -> folium.Map:
        """
        Add network layer to map with dynamic styling.
        
        Args:
            map_obj: Folium Map object
            data: GeoDataFrame with network data
            style_config: Styling configuration
            
        Returns:
            Updated Folium Map object
        """
        if data.empty:
            logger.warning("No data to render")
            return map_obj
        
        # Convert to WGS84 for Folium if needed
        if data.crs and data.crs.to_string() != "EPSG:4326":
            data_wgs84 = data.to_crs("EPSG:4326")
        else:
            data_wgs84 = data
        
        # Add each feature to map
        for idx, row in data_wgs84.iterrows():
            self._add_feature_to_map(map_obj, row, style_config)
        
        logger.info(f"Added {len(data)} features to map")
        return map_obj
    
    def _add_feature_to_map(self, map_obj: folium.Map, feature: pd.Series, 
                           style_config: Dict) -> None:
        """Add individual feature to map with enhanced styling and interactions."""
        # Extract styling properties
        color = style_config.get('color', '#3388ff')
        weight = style_config.get('weight', 3)
        opacity = style_config.get('opacity', 0.8)
        
        # Create enhanced popup content
        popup_content = self._create_enhanced_popup_content(feature)
        
        # Create enhanced tooltip content
        tooltip_content = self._create_enhanced_tooltip_content(feature)
        
        # Add feature to map with enhanced interactions
        folium.GeoJson(
            feature['geometry'].__geo_interface__,
            style_function=lambda x: {
                'color': color,
                'weight': weight,
                'opacity': opacity,
                'fillOpacity': 0.0,
                'dashArray': '0',
                'lineCap': 'round',
                'lineJoin': 'round'
            },
            popup=folium.Popup(popup_content, max_width=400),
            tooltip=folium.Tooltip(tooltip_content, sticky=True, max_width=300)
        ).add_to(map_obj)
    
    def _create_popup_content(self, feature: pd.Series) -> str:
        """Create HTML popup content for feature."""
        content = f"""
        <div style="font-family: Arial, sans-serif;">
            <h4>Link Details</h4>
            <p><strong>ID:</strong> {feature.get('Id', 'N/A')}</p>
            <p><strong>From:</strong> {feature.get('From', 'N/A')}</p>
            <p><strong>To:</strong> {feature.get('To', 'N/A')}</p>
        """
        
        # Add results data if available
        if 'avg_speed_kmh' in feature:
            content += f"<p><strong>Speed:</strong> {feature['avg_speed_kmh']:.1f} km/h</p>"
        if 'avg_duration_sec' in feature:
            duration_min = feature['avg_duration_sec'] / 60
            content += f"<p><strong>Duration:</strong> {duration_min:.1f} minutes</p>"
        if 'n_valid' in feature:
            content += f"<p><strong>Observations:</strong> {feature['n_valid']}</p>"
        
        content += "</div>"
        return content
    
    def _create_tooltip_content(self, feature: pd.Series) -> str:
        """Create tooltip content for feature."""
        tooltip = f"ID: {feature.get('Id', 'N/A')}"
        if 'avg_speed_kmh' in feature:
            tooltip += f" | Speed: {feature['avg_speed_kmh']:.1f} km/h"
        return tooltip
    
    def _create_enhanced_popup_content(self, feature: pd.Series) -> str:
        """Create enhanced HTML popup content with detailed statistics."""
        # Basic link information
        link_id = feature.get('Id', feature.get('link_id', 'N/A'))
        from_node = feature.get('From', 'N/A')
        to_node = feature.get('To', 'N/A')
        
        content = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px; line-height: 1.4;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        color: white; padding: 8px 12px; margin: -8px -12px 12px -12px; 
                        border-radius: 4px 4px 0 0;">
                <h4 style="margin: 0; font-size: 16px; font-weight: 600;">🔗 Link Details</h4>
            </div>
            
            <div style="margin-bottom: 12px;">
                <p style="margin: 4px 0;"><strong>🆔 ID:</strong> {link_id}</p>
                <p style="margin: 4px 0;"><strong>📍 From:</strong> {from_node}</p>
                <p style="margin: 4px 0;"><strong>📍 To:</strong> {to_node}</p>
        """
        
        # Add length if available
        if 'length_m' in feature and pd.notna(feature['length_m']):
            length_km = feature['length_m'] / 1000
            content += f'<p style="margin: 4px 0;"><strong>📏 Length:</strong> {length_km:.2f} km</p>'
        
        content += "</div>"
        
        # Traffic metrics section
        if any(col in feature for col in ['avg_speed_kmh', 'avg_duration_sec', 'n_valid']):
            content += """
            <div style="border-top: 1px solid #e0e0e0; padding-top: 8px; margin-bottom: 12px;">
                <h5 style="margin: 0 0 8px 0; color: #333; font-size: 14px;">📊 Traffic Metrics</h5>
            """
            
            # Speed
            if 'avg_speed_kmh' in feature and pd.notna(feature['avg_speed_kmh']):
                speed = feature['avg_speed_kmh']
                speed_color = '#28a745' if speed > 40 else '#ffc107' if speed > 20 else '#dc3545'
                content += f"""
                <p style="margin: 4px 0;">
                    <strong>🚗 Speed:</strong> 
                    <span style="color: {speed_color}; font-weight: bold;">{speed:.1f} km/h</span>
                </p>
                """
            
            # Duration
            if 'avg_duration_sec' in feature and pd.notna(feature['avg_duration_sec']):
                duration_min = feature['avg_duration_sec'] / 60
                duration_color = '#28a745' if duration_min < 5 else '#ffc107' if duration_min < 15 else '#dc3545'
                content += f"""
                <p style="margin: 4px 0;">
                    <strong>⏱️ Duration:</strong> 
                    <span style="color: {duration_color}; font-weight: bold;">{duration_min:.1f} min</span>
                </p>
                """
            
            # Observations
            if 'n_valid' in feature and pd.notna(feature['n_valid']):
                n_obs = int(feature['n_valid'])
                obs_color = '#28a745' if n_obs > 10 else '#ffc107' if n_obs > 5 else '#dc3545'
                content += f"""
                <p style="margin: 4px 0;">
                    <strong>📈 Observations:</strong> 
                    <span style="color: {obs_color}; font-weight: bold;">{n_obs}</span>
                </p>
                """
            
            content += "</div>"
        
        # Statistical details section
        statistical_fields = ['median_duration_sec', 'p10_duration_sec', 'p90_duration_sec', 
                             'median_speed_kmh', 'p10_speed_kmh', 'p90_speed_kmh']
        
        if any(field in feature for field in statistical_fields):
            content += """
            <div style="border-top: 1px solid #e0e0e0; padding-top: 8px;">
                <h5 style="margin: 0 0 8px 0; color: #333; font-size: 14px;">📈 Statistics</h5>
            """
            
            # Duration statistics
            if 'median_duration_sec' in feature:
                median_dur = feature['median_duration_sec'] / 60
                content += f'<p style="margin: 2px 0; font-size: 12px;"><strong>Median Duration:</strong> {median_dur:.1f} min</p>'
            
            if 'p10_duration_sec' in feature and 'p90_duration_sec' in feature:
                p10_dur = feature['p10_duration_sec'] / 60
                p90_dur = feature['p90_duration_sec'] / 60
                content += f'<p style="margin: 2px 0; font-size: 12px;"><strong>Duration Range (P10-P90):</strong> {p10_dur:.1f} - {p90_dur:.1f} min</p>'
            
            # Speed statistics
            if 'median_speed_kmh' in feature:
                median_speed = feature['median_speed_kmh']
                content += f'<p style="margin: 2px 0; font-size: 12px;"><strong>Median Speed:</strong> {median_speed:.1f} km/h</p>'
            
            if 'p10_speed_kmh' in feature and 'p90_speed_kmh' in feature:
                p10_speed = feature['p10_speed_kmh']
                p90_speed = feature['p90_speed_kmh']
                content += f'<p style="margin: 2px 0; font-size: 12px;"><strong>Speed Range (P10-P90):</strong> {p10_speed:.1f} - {p90_speed:.1f} km/h</p>'
            
            content += "</div>"
        
        # Date/time context if available
        if 'date' in feature or 'hour' in feature:
            content += """
            <div style="border-top: 1px solid #e0e0e0; padding-top: 8px; margin-top: 8px;">
                <h5 style="margin: 0 0 6px 0; color: #666; font-size: 12px;">📅 Context</h5>
            """
            
            if 'date' in feature and pd.notna(feature['date']):
                content += f'<p style="margin: 2px 0; font-size: 11px; color: #666;">Date: {feature["date"]}</p>'
            
            if 'hour' in feature and pd.notna(feature['hour']):
                hour = int(feature['hour'])
                content += f'<p style="margin: 2px 0; font-size: 11px; color: #666;">Hour: {hour:02d}:00</p>'
            
            content += "</div>"
        
        content += "</div>"
        return content
    
    def _create_enhanced_tooltip_content(self, feature: pd.Series) -> str:
        """Create enhanced tooltip content with key metrics."""
        # Basic info
        link_id = feature.get('Id', feature.get('link_id', 'N/A'))
        from_node = feature.get('From', 'N/A')
        to_node = feature.get('To', 'N/A')
        
        tooltip_parts = [f"🔗 {link_id}", f"📍 {from_node} → {to_node}"]
        
        # Add length
        if 'length_m' in feature and pd.notna(feature['length_m']):
            length_km = feature['length_m'] / 1000
            tooltip_parts.append(f"📏 {length_km:.2f} km")
        
        # Add primary metric
        if 'avg_speed_kmh' in feature and pd.notna(feature['avg_speed_kmh']):
            speed = feature['avg_speed_kmh']
            tooltip_parts.append(f"🚗 {speed:.1f} km/h")
        
        if 'avg_duration_sec' in feature and pd.notna(feature['avg_duration_sec']):
            duration_min = feature['avg_duration_sec'] / 60
            tooltip_parts.append(f"⏱️ {duration_min:.1f} min")
        
        # Add observation count
        if 'n_valid' in feature and pd.notna(feature['n_valid']):
            n_obs = int(feature['n_valid'])
            tooltip_parts.append(f"📈 N={n_obs}")
        
        # Add statistical info if available
        if 'median_duration_sec' in feature and pd.notna(feature['median_duration_sec']):
            median_dur = feature['median_duration_sec'] / 60
            tooltip_parts.append(f"📊 Median: {median_dur:.1f} min")
        
        if 'p10_duration_sec' in feature and 'p90_duration_sec' in feature:
            p10_dur = feature['p10_duration_sec'] / 60
            p90_dur = feature['p90_duration_sec'] / 60
            tooltip_parts.append(f"📊 P10-P90: {p10_dur:.1f}-{p90_dur:.1f} min")
        
        return " | ".join(tooltip_parts)
    
    def add_controls(self, map_obj: folium.Map, control_config: Dict) -> folium.Map:
        """
        Add controls to map.
        
        Args:
            map_obj: Folium Map object
            control_config: Control configuration
            
        Returns:
            Updated Folium Map object
        """
        # Add layer control if multiple layers
        if control_config.get('layer_control', False):
            folium.LayerControl().add_to(map_obj)
        
        # Add fullscreen control
        if control_config.get('fullscreen', True):
            from folium.plugins import Fullscreen
            Fullscreen().add_to(map_obj)
        
        # Add measure control
        if control_config.get('measure', False):
            from folium.plugins import MeasureControl
            MeasureControl().add_to(map_obj)
        
        return map_obj
    
    def render_to_streamlit(self, map_obj: folium.Map, height: int = 600) -> None:
        """
        Render Folium map in Streamlit.
        
        Args:
            map_obj: Folium Map object
            height: Map height in pixels
        """
        from streamlit_folium import st_folium
        
        st_folium(map_obj, width=None, height=height, returned_objects=["last_clicked"])


class LegendGenerator:
    """Generates dynamic legends for map visualization."""
    
    def __init__(self):
        self.legend_template = """
        <div style="position: fixed; 
                    bottom: 50px; left: 50px; width: 250px; height: auto; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:12px; padding: 10px; border-radius: 5px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
        <h4 style="margin: 0 0 10px 0; font-size: 14px; color: #333;">{title}</h4>
        {content}
        </div>
        """
    
    def create_legend(self, title: str, class_breaks: List[float], 
                     colors: List[str], active_filters: List[str] = None,
                     outlier_caps: Tuple[float, float] = None,
                     classification_method: str = None) -> str:
        """
        Create HTML legend with class breaks, colors, and metadata.
        
        Args:
            title: Legend title with units (e.g., "Speed km/h", "Duration minutes")
            class_breaks: List of class break values
            colors: List of colors corresponding to classes
            active_filters: List of active filter descriptions
            outlier_caps: Tuple of (min_percentile, max_percentile) if capping is active
            classification_method: Method used for classification (quantiles, equal_interval, etc.)
            
        Returns:
            HTML string for legend
        """
        content = ""
        
        # Add classification method info
        if classification_method:
            content += f'<div style="font-size: 10px; color: #666; margin-bottom: 5px;">Method: {classification_method}</div>'
        
        # Add outlier cap info
        if outlier_caps:
            content += f'<div style="font-size: 10px; color: #666; margin-bottom: 8px;">Capped: {outlier_caps[0]}th - {outlier_caps[1]}th percentile</div>'
        
        # Add class breaks with improved styling
        for i, (break_val, color) in enumerate(zip(class_breaks[:-1], colors)):
            next_break = class_breaks[i + 1]
            content += f"""
            <div style="margin: 3px 0; display: flex; align-items: center;">
                <span style="background-color: {color}; width: 20px; height: 12px; 
                           display: inline-block; margin-right: 8px; border: 1px solid #ccc;"></span>
                <span style="font-size: 11px;">{break_val:.1f} - {next_break:.1f}</span>
            </div>
            """
        
        # Add active filters section
        if active_filters:
            content += '<hr style="margin: 10px 0; border: none; border-top: 1px solid #ddd;">'
            content += '<div style="font-size: 10px;"><strong>Active Filters:</strong></div>'
            for filter_desc in active_filters:
                content += f'<div style="font-size: 10px; color: #666; margin: 2px 0;">• {filter_desc}</div>'
        
        return self.legend_template.format(title=title, content=content)
    
    def create_legend_with_units(self, metric_type: str, class_breaks: List[float], 
                                colors: List[str], **kwargs) -> str:
        """
        Create legend with proper units in title.
        
        Args:
            metric_type: 'duration' or 'speed'
            class_breaks: List of class break values
            colors: List of colors corresponding to classes
            **kwargs: Additional arguments passed to create_legend
            
        Returns:
            HTML string for legend
        """
        if metric_type == 'duration':
            title = "Duration (minutes)"
        elif metric_type == 'speed':
            title = "Speed (km/h)"
        else:
            title = metric_type.title()
        
        return self.create_legend(title, class_breaks, colors, **kwargs)
    
    def add_legend_to_map(self, map_obj: folium.Map, legend_html: str) -> folium.Map:
        """
        Add legend to Folium map.
        
        Args:
            map_obj: Folium Map object
            legend_html: HTML legend content
            
        Returns:
            Updated Folium Map object
        """
        map_obj.get_root().html.add_child(folium.Element(legend_html))
        return map_obj
    
    def format_active_filters(self, filter_state: Dict) -> List[str]:
        """
        Format filter state into human-readable descriptions.
        
        Args:
            filter_state: Dictionary containing filter parameters
            
        Returns:
            List of filter descriptions
        """
        filters = []
        
        # Date range filter
        if filter_state.get('date_range'):
            start_date, end_date = filter_state['date_range']
            if start_date == end_date:
                filters.append(f"Date: {start_date}")
            else:
                filters.append(f"Dates: {start_date} to {end_date}")
        
        # Hour range filter
        if filter_state.get('hour_range'):
            start_hour, end_hour = filter_state['hour_range']
            if start_hour == end_hour:
                filters.append(f"Hour: {start_hour}:00")
            else:
                filters.append(f"Hours: {start_hour}:00-{end_hour}:00")
        
        # Length filter
        if filter_state.get('length_filter'):
            length_min, length_max = filter_state['length_filter']
            filters.append(f"Length: {length_min:.0f}-{length_max:.0f}m")
        
        # Speed filter
        if filter_state.get('speed_filter'):
            speed_min, speed_max = filter_state['speed_filter']
            filters.append(f"Speed: {speed_min:.1f}-{speed_max:.1f} km/h")
        
        # Time filter
        if filter_state.get('time_filter'):
            time_min, time_max = filter_state['time_filter']
            filters.append(f"Duration: {time_min:.1f}-{time_max:.1f} min")
        
        # Text search
        if filter_state.get('text_search'):
            filters.append(f"Search: '{filter_state['text_search']}'")
        
        # Spatial selection
        if filter_state.get('spatial_selection_active'):
            filters.append("Spatial selection active")
        
        return filters


class BasemapManager:
    """Manages basemap tiles and labeling with EPSG 2039 compatibility."""
    
    def __init__(self):
        self.available_basemaps = {
            'OpenStreetMap': {
                'tiles': 'OpenStreetMap',
                'name': 'OpenStreetMap',
                'epsg2039_compatible': False
            },
            'CartoDB Positron': {
                'tiles': 'CartoDB positron',
                'name': 'CartoDB Positron',
                'epsg2039_compatible': False
            },
            'CartoDB Dark': {
                'tiles': 'CartoDB dark_matter',
                'name': 'CartoDB Dark',
                'epsg2039_compatible': False
            },
            'Stamen Terrain': {
                'tiles': 'Stamen Terrain',
                'name': 'Stamen Terrain',
                'epsg2039_compatible': False
            },
            'None': {
                'tiles': None,
                'name': 'No Basemap',
                'epsg2039_compatible': True
            }
        }
        self._tile_cache = {}
    
    def add_basemap_options(self, map_obj: folium.Map, basemap_type: str = 'OpenStreetMap',
                           enable_toggle: bool = True) -> folium.Map:
        """
        Add basemap options to map with EPSG 2039 compatibility handling.
        
        Args:
            map_obj: Folium Map object
            basemap_type: Type of basemap to add
            enable_toggle: Whether to enable basemap toggle
            
        Returns:
            Updated Folium Map object
        """
        if basemap_type == 'None':
            # Remove default tiles for no basemap option
            for key in list(map_obj._children.keys()):
                if 'openstreetmap' in key.lower():
                    del map_obj._children[key]
            return map_obj
        
        if basemap_type in self.available_basemaps:
            basemap_config = self.available_basemaps[basemap_type]
            
            # Add warning for non-EPSG 2039 compatible basemaps
            if not basemap_config['epsg2039_compatible']:
                logger.warning(f"Basemap {basemap_type} may not align perfectly with EPSG 2039 data")
            
            # Add tile layer
            folium.TileLayer(
                tiles=basemap_config['tiles'],
                name=basemap_config['name'],
                overlay=False,
                control=enable_toggle,
                attr='Map data © contributors'
            ).add_to(map_obj)
            
            logger.info(f"Added basemap: {basemap_type}")
        else:
            logger.warning(f"Unknown basemap type: {basemap_type}")
        
        return map_obj
    
    def add_multiple_basemaps(self, map_obj: folium.Map, 
                             basemap_types: List[str] = None) -> folium.Map:
        """
        Add multiple basemap options with layer control.
        
        Args:
            map_obj: Folium Map object
            basemap_types: List of basemap types to add
            
        Returns:
            Updated Folium Map object
        """
        if basemap_types is None:
            basemap_types = ['OpenStreetMap', 'CartoDB Positron', 'CartoDB Dark', 'None']
        
        for basemap_type in basemap_types:
            self.add_basemap_options(map_obj, basemap_type, enable_toggle=True)
        
        # Add layer control
        folium.LayerControl(position='topright').add_to(map_obj)
        
        return map_obj
    
    def add_link_labels(self, map_obj: folium.Map, data: gpd.GeoDataFrame, 
                       label_config: Dict) -> folium.Map:
        """
        Add labels for top K slowest/longest links with improved styling.
        
        Args:
            map_obj: Folium Map object
            data: GeoDataFrame with network data
            label_config: Label configuration with keys:
                - top_k: Number of top links to label
                - metric: Metric to use for ranking ('avg_duration_sec', 'avg_speed_kmh', 'length_m')
                - label_type: 'slowest' or 'longest'
                - show_values: Whether to show metric values in labels
            
        Returns:
            Updated Folium Map object
        """
        if data.empty:
            logger.warning("No data available for labeling")
            return map_obj
        
        k = label_config.get('top_k', 10)
        metric = label_config.get('metric', 'avg_duration_sec')
        label_type = label_config.get('label_type', 'slowest')
        show_values = label_config.get('show_values', True)
        
        if metric not in data.columns:
            logger.warning(f"Metric {metric} not found in data columns: {list(data.columns)}")
            return map_obj
        
        # Get top K links based on metric
        if label_type == 'slowest' and metric in ['avg_speed_kmh']:
            # For speed, slowest means lowest values
            top_links = data.nsmallest(k, metric)
        else:
            # For duration and length, highest values
            top_links = data.nlargest(k, metric)
        
        if top_links.empty:
            logger.warning("No links found for labeling after filtering")
            return map_obj
        
        # Convert to WGS84 for Folium
        if top_links.crs and top_links.crs.to_string() != "EPSG:4326":
            top_links = top_links.to_crs("EPSG:4326")
        
        # Create feature group for labels
        label_group = folium.FeatureGroup(name=f"Top {k} {label_type} links")
        
        # Add labels at link centroids
        for idx, row in top_links.iterrows():
            try:
                centroid = row['geometry'].centroid
                link_id = row.get('Id', row.get('link_id', 'N/A'))
                
                # Format label text
                if show_values:
                    if metric == 'avg_duration_sec':
                        value_text = f"{row[metric]/60:.1f} min"
                    elif metric == 'avg_speed_kmh':
                        value_text = f"{row[metric]:.1f} km/h"
                    elif metric == 'length_m':
                        value_text = f"{row[metric]:.0f} m"
                    else:
                        value_text = f"{row[metric]:.1f}"
                    
                    label_text = f"{link_id}: {value_text}"
                else:
                    label_text = str(link_id)
                
                # Create styled label
                folium.Marker(
                    location=[centroid.y, centroid.x],
                    popup=folium.Popup(
                        f"""
                        <div style="font-family: Arial, sans-serif;">
                            <strong>Link ID:</strong> {link_id}<br>
                            <strong>From:</strong> {row.get('From', 'N/A')}<br>
                            <strong>To:</strong> {row.get('To', 'N/A')}<br>
                            <strong>{metric}:</strong> {row[metric]:.2f}
                        </div>
                        """,
                        max_width=200
                    ),
                    icon=folium.DivIcon(
                        html=f'''
                        <div style="
                            font-size: 10px; 
                            color: #d63031; 
                            font-weight: bold; 
                            background-color: rgba(255,255,255,0.8);
                            padding: 2px 4px;
                            border-radius: 3px;
                            border: 1px solid #d63031;
                            white-space: nowrap;
                        ">{label_text}</div>
                        ''',
                        icon_size=(len(label_text) * 6 + 10, 16),
                        icon_anchor=(len(label_text) * 3 + 5, 8)
                    )
                ).add_to(label_group)
                
            except Exception as e:
                logger.warning(f"Failed to add label for link {idx}: {e}")
                continue
        
        # Add label group to map
        label_group.add_to(map_obj)
        
        logger.info(f"Added labels for top {k} {label_type} links by {metric}")
        return map_obj
    
    def handle_epsg2039_basemap(self, map_obj: folium.Map, 
                               data_bounds: Tuple = None) -> folium.Map:
        """
        Handle basemap compatibility with EPSG 2039 data.
        
        Args:
            map_obj: Folium Map object
            data_bounds: Bounds of the data in EPSG 2039
            
        Returns:
            Updated Folium Map object with appropriate basemap handling
        """
        # Add note about coordinate system compatibility
        note_html = '''
        <div style="position: fixed; top: 10px; right: 10px; 
                    background-color: rgba(255,255,255,0.9); 
                    padding: 5px; font-size: 10px; 
                    border-radius: 3px; border: 1px solid #ccc;
                    z-index: 1000;">
            <strong>Note:</strong> Data in EPSG:2039<br>
            Basemap may not align perfectly
        </div>
        '''
        
        map_obj.get_root().html.add_child(folium.Element(note_html))
        
        return map_obj
    
    def clear_labels(self, map_obj: folium.Map) -> folium.Map:
        """
        Clear existing labels from map.
        
        Args:
            map_obj: Folium Map object
            
        Returns:
            Updated Folium Map object
        """
        # Remove label feature groups
        keys_to_remove = []
        for key, child in map_obj._children.items():
            if hasattr(child, 'layer_name') and 'links' in str(child.layer_name).lower():
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del map_obj._children[key]
        
        return map_obj


class MapVisualizationRenderer:
    """Main interface for map rendering operations."""
    
    def __init__(self):
        self.renderer = MapRenderer()
        self.legend_generator = LegendGenerator()
        self.basemap_manager = BasemapManager()
    
    def create_interactive_map(self, data: gpd.GeoDataFrame, style_config: Dict,
                             legend_config: Dict, control_config: Dict = None) -> folium.Map:
        """
        Create complete interactive map with data, styling, and controls.
        
        Args:
            data: GeoDataFrame with network data
            style_config: Styling configuration
            legend_config: Legend configuration
            control_config: Optional control configuration
            
        Returns:
            Complete Folium Map object
        """
        if control_config is None:
            control_config = {'fullscreen': True, 'layer_control': False}
        
        # Calculate bounds from data
        bounds = None
        if not data.empty:
            bounds = data.total_bounds
        
        # Create base map
        map_obj = self.renderer.create_base_map(bounds)
        
        # Add network layer
        map_obj = self.renderer.add_network_layer(map_obj, data, style_config)
        
        # Add legend
        if legend_config:
            legend_html = self.legend_generator.create_legend(**legend_config)
            map_obj = self.legend_generator.add_legend_to_map(map_obj, legend_html)
        
        # Add controls
        map_obj = self.renderer.add_controls(map_obj, control_config)
        
        return map_obj