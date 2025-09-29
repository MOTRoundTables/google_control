"""
Simple map rendering - minimal implementation for production use.
"""

import folium
import geopandas as gpd
import pandas as pd
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


def create_simple_map(data: gpd.GeoDataFrame,
                     value_column: str = 'avg_duration_min',
                     metric_name: str = 'Duration (min)') -> folium.Map:
    """
    Create a simple Folium map with colored network links.

    Args:
        data: GeoDataFrame with network geometry and metrics
        value_column: Column to use for coloring
        metric_name: Display name for the metric

    Returns:
        Folium map object
    """
    if data.empty:
        logger.warning("No data to display")
        # Return empty map centered on Israel
        return folium.Map(location=[31.5, 34.8], zoom_start=10)

    # Convert to WGS84 if needed
    if data.crs and data.crs.to_string() != "EPSG:4326":
        data = data.to_crs("EPSG:4326")

    # Calculate map center from data bounds
    bounds = data.total_bounds  # minx, miny, maxx, maxy
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2

    # Create base map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=10,
        tiles='OpenStreetMap'
    )

    # Get values for coloring
    if value_column in data.columns:
        values = data[value_column].dropna()
        if len(values) > 0:
            vmin = values.quantile(0.05)
            vmax = values.quantile(0.95)
        else:
            vmin, vmax = 0, 1
    else:
        vmin, vmax = 0, 1

    # Add features to map
    for idx, row in data.iterrows():
        # Get color based on value
        if value_column in row and pd.notna(row[value_column]):
            value = row[value_column]
            # Normalize to 0-1 range
            if vmax > vmin:
                normalized = (value - vmin) / (vmax - vmin)
                normalized = max(0, min(1, normalized))  # Clamp to 0-1
            else:
                normalized = 0.5

            # Color from green (low) to red (high)
            if normalized < 0.5:
                # Green to yellow
                r = int(normalized * 2 * 255)
                g = 255
            else:
                # Yellow to red
                r = 255
                g = int((1 - normalized) * 2 * 255)
            color = f'#{r:02x}{g:02x}00'
        else:
            color = '#999999'  # Gray for no data

        # Create simple tooltip
        link_id = row.get('Id', row.get('link_id', 'N/A'))
        value_text = f"{row[value_column]:.1f}" if value_column in row and pd.notna(row[value_column]) else "N/A"
        tooltip = f"Link: {link_id}<br>{metric_name}: {value_text}"

        # Add line to map
        folium.GeoJson(
            row['geometry'],
            style_function=lambda x, color=color: {
                'color': color,
                'weight': 3,
                'opacity': 0.8
            },
            tooltip=tooltip
        ).add_to(m)

    logger.info(f"Rendered {len(data)} features on map")
    return m