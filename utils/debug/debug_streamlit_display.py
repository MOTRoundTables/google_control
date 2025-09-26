"""
Debug the Streamlit display issue by creating a minimal test case.
"""

import streamlit as st
import folium
import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString

def test_basic_folium_display():
    """Test if basic Folium maps display in Streamlit."""
    
    st.title("🗺️ Folium Display Test")
    
    # Create a simple map
    m = folium.Map(location=[31.5, 34.8], zoom_start=10)
    
    # Add a simple marker
    folium.Marker([31.5, 34.8], popup="Test Marker").add_to(m)
    
    st.subheader("Basic Folium Map")
    
    try:
        from streamlit_folium import st_folium
        map_data = st_folium(m, width=700, height=500)
        st.success("✅ Basic Folium map displayed successfully")
        return True
    except Exception as e:
        st.error(f"❌ Error displaying Folium map: {e}")
        return False

def test_geopandas_map():
    """Test displaying a map with GeoDataFrame data."""
    
    st.subheader("GeoDataFrame Map Test")
    
    try:
        # Create sample GeoDataFrame
        gdf = gpd.GeoDataFrame({
            'Id': ['link_1', 'link_2', 'link_3'],
            'From': ['A', 'B', 'C'],
            'To': ['B', 'C', 'D'],
            'avg_duration_sec': [120, 180, 240],
            'avg_speed_kmh': [50, 40, 30],
            'geometry': [
                LineString([(34.0, 29.0), (35.0, 30.0)]),
                LineString([(35.0, 30.0), (36.0, 31.0)]),
                LineString([(36.0, 31.0), (37.0, 32.0)])
            ]
        })
        
        # Create map
        m = folium.Map(location=[31.5, 34.8], zoom_start=8)
        
        # Add GeoDataFrame to map
        for idx, row in gdf.iterrows():
            folium.GeoJson(
                row['geometry'].__geo_interface__,
                style_function=lambda x: {
                    'color': 'red',
                    'weight': 3,
                    'opacity': 0.8
                },
                popup=f"Link {row['Id']}: {row['avg_duration_sec']}s"
            ).add_to(m)
        
        from streamlit_folium import st_folium
        map_data = st_folium(m, width=700, height=500)
        
        st.success("✅ GeoDataFrame map displayed successfully")
        st.write(f"Map data returned: {type(map_data)}")
        
        return True
        
    except Exception as e:
        st.error(f"❌ Error displaying GeoDataFrame map: {e}")
        import traceback
        st.code(traceback.format_exc())
        return False

def test_map_interface_directly():
    """Test the map interface directly."""
    
    st.subheader("Map Interface Test")
    
    try:
        from map_a_hourly import HourlyMapInterface
        from shapely.geometry import LineString
        
        # Create sample data
        gdf = gpd.GeoDataFrame({
            'Id': ['link_1', 'link_2'],
            'From': ['A', 'B'],
            'To': ['B', 'C'],
            'geometry': [
                LineString([(34.0, 29.0), (35.0, 30.0)]),
                LineString([(35.0, 30.0), (36.0, 31.0)])
            ]
        })
        
        # Add results data
        gdf['avg_duration_sec'] = [120, 180]
        gdf['avg_speed_kmh'] = [50, 40]
        gdf['avg_duration_min'] = gdf['avg_duration_sec'] / 60
        gdf['n_valid'] = [10, 15]
        
        # Create interface
        interface = HourlyMapInterface()
        
        # Create control state
        control_state = {
            'filters': {
                'metrics': {
                    'metric_type': 'duration'
                }
            }
        }
        
        # Create map
        map_obj = interface._create_hourly_map(gdf, control_state)
        
        # Display map
        from streamlit_folium import st_folium
        map_data = st_folium(map_obj, width=700, height=500)
        
        st.success("✅ Map interface test successful")
        st.write(f"Features in data: {len(gdf)}")
        st.write(f"Map object type: {type(map_obj)}")
        
        return True
        
    except Exception as e:
        st.error(f"❌ Error in map interface test: {e}")
        import traceback
        st.code(traceback.format_exc())
        return False

def test_session_state_data():
    """Test if session state has the expected data."""
    
    st.subheader("Session State Test")
    
    # Check session state
    st.write("**Session State Variables:**")
    
    session_vars = [
        'maps_shapefile_data',
        'maps_hourly_results',
        'maps_weekly_results'
    ]
    
    for var in session_vars:
        if var in st.session_state:
            data = st.session_state[var]
            if data is not None:
                st.success(f"✅ {var}: {type(data)} with {len(data)} items")
            else:
                st.warning(f"⚠️ {var}: None")
        else:
            st.error(f"❌ {var}: Not in session state")
    
    # If data exists, show sample
    if 'maps_shapefile_data' in st.session_state and st.session_state.maps_shapefile_data is not None:
        gdf = st.session_state.maps_shapefile_data
        st.write("**Shapefile Sample:**")
        st.dataframe(gdf.head().drop(columns=['geometry']))
    
    if 'maps_hourly_results' in st.session_state and st.session_state.maps_hourly_results is not None:
        df = st.session_state.maps_hourly_results
        st.write("**Hourly Results Sample:**")
        st.dataframe(df.head())

def main():
    """Main Streamlit app for debugging display issues."""
    
    st.set_page_config(
        page_title="Map Display Debug",
        page_icon="🗺️",
        layout="wide"
    )
    
    st.title("🔍 Map Display Debugging")
    st.markdown("This app tests various aspects of map display to identify issues.")
    
    # Test basic Folium
    if test_basic_folium_display():
        st.success("Basic Folium display works")
    
    st.markdown("---")
    
    # Test GeoDataFrame map
    if test_geopandas_map():
        st.success("GeoDataFrame map display works")
    
    st.markdown("---")
    
    # Test map interface
    if test_map_interface_directly():
        st.success("Map interface works")
    
    st.markdown("---")
    
    # Test session state
    test_session_state_data()

if __name__ == "__main__":
    main()