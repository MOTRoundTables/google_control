"""
Simple fix for empty maps by adding debugging and fallback logic.
"""

def create_debug_maps_page():
    """Create a debug version of the maps page with better error handling."""
    
    debug_content = '''
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
    
    # Create simple maps without complex controls
    st.subheader("🗺️ Simple Maps (No Filters)")
    
    tab1, tab2 = st.tabs(["📅 Map A: Hourly (Simple)", "📊 Map B: Weekly (Simple)"])
    
    with tab1:
        if shapefile_loaded and hourly_loaded:
            try:
                # Create simple hourly map
                gdf = st.session_state.maps_shapefile_data
                df = st.session_state.maps_hourly_results
                
                # Simple join without filters
                from map_data import MapDataProcessor
                processor = MapDataProcessor()
                joined_data = processor.join_results_to_shapefile(gdf, df)
                
                st.info(f"📊 Joined data: {len(joined_data)} features")
                
                if not joined_data.empty:
                    # Add required columns
                    if 'avg_duration_min' not in joined_data.columns and 'avg_duration_sec' in joined_data.columns:
                        joined_data['avg_duration_min'] = joined_data['avg_duration_sec'] / 60
                    
                    # Create simple map
                    from map_a_hourly import HourlyMapInterface
                    interface = HourlyMapInterface()
                    
                    control_state = {
                        'filters': {
                            'metrics': {
                                'metric_type': 'duration'
                            }
                        }
                    }
                    
                    map_obj = interface._create_hourly_map(joined_data, control_state)
                    
                    from streamlit_folium import st_folium
                    st_folium(map_obj, width=700, height=500)
                    
                    st.success(f"✅ Map A displayed with {len(joined_data)} features")
                else:
                    st.error("❌ No data after join")
                    
            except Exception as e:
                st.error(f"❌ Error creating Map A: {e}")
                import traceback
                st.code(traceback.format_exc())
        else:
            st.warning("⚠️ Required data not available for Map A")
    
    with tab2:
        if shapefile_loaded and (hourly_loaded or weekly_loaded):
            try:
                # Create simple weekly map
                gdf = st.session_state.maps_shapefile_data
                
                # Use weekly data if available, otherwise hourly
                if weekly_loaded:
                    df = st.session_state.maps_weekly_results
                    st.info("Using weekly data")
                else:
                    df = st.session_state.maps_hourly_results
                    st.info("Using hourly data for weekly aggregation")
                
                # Simple join without filters
                from map_data import MapDataProcessor
                processor = MapDataProcessor()
                joined_data = processor.join_results_to_shapefile(gdf, df)
                
                st.info(f"📊 Joined data: {len(joined_data)} features")
                
                if not joined_data.empty:
                    # Add required columns
                    if 'avg_duration_min' not in joined_data.columns and 'avg_duration_sec' in joined_data.columns:
                        joined_data['avg_duration_min'] = joined_data['avg_duration_sec'] / 60
                    
                    # Create simple map
                    from map_b_weekly import WeeklyMapInterface
                    interface = WeeklyMapInterface()
                    
                    control_state = {
                        'filters': {
                            'metrics': {
                                'metric_type': 'duration',
                                'aggregation_method': 'median'
                            }
                        }
                    }
                    
                    map_obj = interface._create_weekly_map(joined_data, control_state)
                    
                    from streamlit_folium import st_folium
                    st_folium(map_obj, width=700, height=500)
                    
                    st.success(f"✅ Map B displayed with {len(joined_data)} features")
                else:
                    st.error("❌ No data after join")
                    
            except Exception as e:
                st.error(f"❌ Error creating Map B: {e}")
                import traceback
                st.code(traceback.format_exc())
        else:
            st.warning("⚠️ Required data not available for Map B")
'''
    
    # Append to maps_page.py
    with open('maps_page.py', 'a', encoding='utf-8') as f:
        f.write('\n\n# DEBUG VERSION\n')
        f.write(debug_content)
    
    print("✅ Added debug_render_maps_page function to maps_page.py")

def update_app_py_for_debug():
    """Update app.py to use debug version temporarily."""
    
    # Read app.py
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace the maps_page function to use debug version
    old_function = '''def maps_page():
    """Maps visualization page"""
    render_maps_page()'''
    
    new_function = '''def maps_page():
    """Maps visualization page"""
    try:
        render_maps_page()
    except Exception as e:
        st.error(f"❌ Error in main maps page: {e}")
        st.info("🔧 Switching to debug mode...")
        debug_render_maps_page()'''
    
    if old_function in content:
        new_content = content.replace(old_function, new_function)
        
        with open('app.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print("✅ Updated app.py to use debug fallback")
    else:
        print("❌ Could not find maps_page function in app.py")

def main():
    """Apply simple fixes."""
    
    print("=" * 60)
    print("APPLYING SIMPLE MAP FIXES")
    print("=" * 60)
    
    print("\n1. Creating debug maps page...")
    create_debug_maps_page()
    
    print("\n2. Updating app.py for debug fallback...")
    update_app_py_for_debug()
    
    print("\n" + "=" * 60)
    print("SIMPLE FIXES APPLIED")
    print("=" * 60)
    
    print("\n📋 What was added:")
    print("✅ Debug version of maps page with extensive logging")
    print("✅ Simple maps without complex controls")
    print("✅ Fallback to debug mode if main maps fail")
    print("✅ Direct data join without filtering")
    
    print("\n🚀 Next steps:")
    print("1. Run: streamlit run app.py")
    print("2. Navigate to Maps page")
    print("3. If main maps fail, debug version will show")
    print("4. Debug version shows data status and simple maps")

if __name__ == "__main__":
    main()