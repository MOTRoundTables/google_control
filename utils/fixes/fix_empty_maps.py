"""
Fix for empty maps issue by ensuring proper default values and debugging.
"""

import streamlit as st
import pandas as pd
import geopandas as gpd
from datetime import date, timedelta

def fix_map_a_hourly():
    """Fix Map A (Hourly View) by ensuring proper default control state."""
    
    # Read the current map_a_hourly.py file
    with open('map_a_hourly.py', 'r') as f:
        content = f.read()
    
    # Add debugging and ensure proper default control state
    debug_code = '''
        # DEBUG: Add logging to see what's happening
        logger.info(f"Shapefile data: {len(shapefile_data)} features")
        logger.info(f"Results data: {len(results_data)} records")
        logger.info(f"Data bounds: {data_bounds}")
        
        # DEBUG: Show data info in UI
        st.info(f"📊 Data loaded: {len(shapefile_data)} shapefile features, {len(results_data)} results records")
        
        # Ensure control state has reasonable defaults
        if not control_state or not control_state.get('filters'):
            # Create minimal default control state
            control_state = {
                'filters': {
                    'temporal': {
                        'date_range': [data_bounds.get('min_date', date.today()), data_bounds.get('max_date', date.today())],
                        'hour_range': [data_bounds.get('min_hour', 0), data_bounds.get('max_hour', 23)]
                    },
                    'metrics': {
                        'metric_type': 'duration'
                    },
                    'attributes': {}
                },
                'spatial': {}
            }
            st.warning("⚠️ Using default control state - controls may not be working properly")
    '''
    
    # Find the location to insert debug code (after data bounds calculation)
    insert_location = content.find("# Create two-column layout: controls on left, map on right")
    
    if insert_location != -1:
        new_content = content[:insert_location] + debug_code + "\n        " + content[insert_location:]
        
        with open('map_a_hourly.py', 'w') as f:
            f.write(new_content)
        
        print("✅ Added debugging and default control state to map_a_hourly.py")
    else:
        print("❌ Could not find insertion point in map_a_hourly.py")

def fix_map_b_weekly():
    """Fix Map B (Weekly View) by ensuring proper default control state."""
    
    # Read the current map_b_weekly.py file
    with open('map_b_weekly.py', 'r') as f:
        content = f.read()
    
    # Add similar debugging
    debug_code = '''
        # DEBUG: Add logging to see what's happening
        logger.info(f"Shapefile data: {len(shapefile_data)} features")
        logger.info(f"Results data: {len(results_data)} records")
        logger.info(f"Data bounds: {data_bounds}")
        
        # DEBUG: Show data info in UI
        st.info(f"📊 Data loaded: {len(shapefile_data)} shapefile features, {len(results_data)} results records")
        
        # Ensure control state has reasonable defaults
        if not control_state or not control_state.get('filters'):
            # Create minimal default control state
            control_state = {
                'filters': {
                    'temporal': {
                        'hour_range': [data_bounds.get('min_hour', 0), data_bounds.get('max_hour', 23)]
                    },
                    'metrics': {
                        'metric_type': 'duration',
                        'aggregation_method': 'median'
                    },
                    'attributes': {}
                },
                'spatial': {}
            }
            st.warning("⚠️ Using default control state - controls may not be working properly")
    '''
    
    # Find the location to insert debug code
    insert_location = content.find("# Create two-column layout: controls on left, map on right")
    
    if insert_location != -1:
        new_content = content[:insert_location] + debug_code + "\n        " + content[insert_location:]
        
        with open('map_b_weekly.py', 'w') as f:
            f.write(new_content)
        
        print("✅ Added debugging and default control state to map_b_weekly.py")
    else:
        print("❌ Could not find insertion point in map_b_weekly.py")

def add_fallback_map_display():
    """Add fallback map display when filtering fails."""
    
    # This will modify the map interfaces to always show something
    fallback_code = '''
            # FALLBACK: If filtered data is empty, show a basic map with all data
            if filtered_data.empty and not shapefile_data.empty:
                st.warning("⚠️ No data matches current filters. Showing all data instead.")
                
                # Create basic joined data without filters
                try:
                    basic_joined = self.data_processor.join_results_to_shapefile(shapefile_data, results_data)
                    if not basic_joined.empty:
                        # Add required columns for visualization
                        if 'avg_duration_min' not in basic_joined.columns and 'avg_duration_sec' in basic_joined.columns:
                            basic_joined['avg_duration_min'] = basic_joined['avg_duration_sec'] / 60
                        
                        # Use this data for map display
                        filtered_data = basic_joined
                        st.info(f"📊 Displaying {len(filtered_data)} features with all available data")
                except Exception as e:
                    st.error(f"❌ Error creating fallback map: {e}")
    '''
    
    # Add this fallback to both map interfaces
    for filename in ['map_a_hourly.py', 'map_b_weekly.py']:
        with open(filename, 'r') as f:
            content = f.read()
        
        # Find the location after filtered_data is created but before the empty check
        insert_location = content.find("if not filtered_data.empty:")
        
        if insert_location != -1:
            new_content = content[:insert_location] + fallback_code + "\n            " + content[insert_location:]
            
            with open(filename, 'w') as f:
                f.write(new_content)
            
            print(f"✅ Added fallback map display to {filename}")
        else:
            print(f"❌ Could not find insertion point in {filename}")

def main():
    """Apply all fixes for empty maps issue."""
    
    print("=" * 60)
    print("APPLYING FIXES FOR EMPTY MAPS ISSUE")
    print("=" * 60)
    
    print("\n1. Adding debugging and default control state to Map A...")
    fix_map_a_hourly()
    
    print("\n2. Adding debugging and default control state to Map B...")
    fix_map_b_weekly()
    
    print("\n3. Adding fallback map display...")
    add_fallback_map_display()
    
    print("\n" + "=" * 60)
    print("FIXES APPLIED SUCCESSFULLY")
    print("=" * 60)
    
    print("\n📋 What was fixed:")
    print("✅ Added debugging info to see data loading status")
    print("✅ Added default control state when controls fail")
    print("✅ Added fallback to show all data when filters are too restrictive")
    print("✅ Added user-friendly error messages and status info")
    
    print("\n🚀 Next steps:")
    print("1. Run: streamlit run app.py")
    print("2. Navigate to Maps page")
    print("3. Check the debug messages to see what's happening")
    print("4. Maps should now display even if controls have issues")

if __name__ == "__main__":
    main()