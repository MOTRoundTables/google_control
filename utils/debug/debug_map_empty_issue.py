"""
Debug the empty map issue by tracing through the data pipeline.
"""

import os
import pandas as pd
import geopandas as gpd
import streamlit as st
from unittest.mock import patch

def test_data_loading():
    """Test if data is being loaded correctly into session state."""
    
    try:
        from maps_page import MapsPageInterface
        
        # Mock session state
        if not hasattr(st, 'session_state'):
            st.session_state = {}
        
        interface = MapsPageInterface()
        interface._initialize_session_state()
        
        # Check if default data files exist
        shapefile_exists = os.path.exists(interface.default_shapefile_path)
        hourly_exists = os.path.exists(interface.default_hourly_path)
        
        print(f"📁 Data file availability:")
        print(f"   - Shapefile: {'✅' if shapefile_exists else '❌'} {interface.default_shapefile_path}")
        print(f"   - Hourly: {'✅' if hourly_exists else '❌'} {interface.default_hourly_path}")
        
        if shapefile_exists and hourly_exists:
            # Try to load the data
            os.environ['SHAPE_RESTORE_SHX'] = 'YES'
            
            # Load shapefile
            gdf = gpd.read_file(interface.default_shapefile_path)
            if 'id' in gdf.columns and 'Id' not in gdf.columns:
                gdf = gdf.rename(columns={'id': 'Id'})
            
            # Load hourly data
            df = pd.read_csv(interface.default_hourly_path)
            if 'hour_of_day' in df.columns and 'hour' not in df.columns:
                df = df.rename(columns={'hour_of_day': 'hour'})
            
            print(f"📊 Data loaded:")
            print(f"   - Shapefile: {len(gdf)} features")
            print(f"   - Hourly data: {len(df)} records")
            print(f"   - Shapefile columns: {list(gdf.columns)}")
            print(f"   - Hourly columns: {list(df.columns)}")
            
            # Store in session state
            st.session_state.maps_shapefile_data = gdf
            st.session_state.maps_hourly_results = df
            
            return gdf, df
        else:
            print("❌ Required data files not found")
            return None, None
            
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return None, None

def test_control_state():
    """Test what the default control state looks like."""
    
    try:
        from map_a_hourly import HourlyMapInterface
        
        interface = HourlyMapInterface()
        
        # Mock some basic data
        gdf = gpd.GeoDataFrame({
            'Id': ['link_1'],
            'From': ['A'],
            'To': ['B'],
            'geometry': [None]
        })
        
        df = pd.DataFrame({
            'link_id': ['s_A-B'],
            'date': ['2025-06-29'],
            'hour': [8],
            'avg_duration_sec': [120],
            'avg_speed_kmh': [50]
        })
        
        # Calculate data bounds
        data_bounds = interface._calculate_data_bounds(df)
        print(f"📊 Data bounds: {data_bounds}")
        
        # This would normally come from the controls, but let's see what a default state looks like
        # We need to mock the controls to see what they return
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing control state: {e}")
        return False

def test_filtering_pipeline():
    """Test the filtering pipeline step by step."""
    
    try:
        gdf, df = test_data_loading()
        
        if gdf is None or df is None:
            print("❌ Cannot test filtering without data")
            return False
        
        from map_a_hourly import HourlyMapInterface
        
        interface = HourlyMapInterface()
        
        # Create a minimal control state (this might be the issue - restrictive defaults)
        control_state = {
            'filters': {
                'temporal': {
                    'date_range': [pd.to_datetime('2025-06-29').date(), pd.to_datetime('2025-07-01').date()],
                    'hour_range': [0, 23]
                },
                'metrics': {
                    'metric_type': 'duration'
                },
                'attributes': {}
            },
            'spatial': {}
        }
        
        print(f"🔍 Testing filtering pipeline:")
        print(f"   - Input shapefile: {len(gdf)} features")
        print(f"   - Input results: {len(df)} records")
        
        # Test temporal filtering
        temporal_filters = control_state.get('filters', {}).get('temporal', {})
        filtered_results = interface._apply_temporal_filters(df, temporal_filters)
        print(f"   - After temporal filters: {len(filtered_results)} records")
        
        # Test attribute filtering
        attribute_filters = control_state.get('filters', {}).get('attributes', {})
        filtered_results = interface._apply_attribute_filters(filtered_results, attribute_filters)
        print(f"   - After attribute filters: {len(filtered_results)} records")
        
        # Test join
        joined_data = interface.data_processor.join_results_to_shapefile(gdf, filtered_results)
        print(f"   - After join: {len(joined_data)} features")
        
        # Check if joined data has the required columns
        if not joined_data.empty:
            print(f"   - Joined columns: {list(joined_data.columns)}")
            
            # Check for required visualization columns
            required_cols = ['avg_duration_sec', 'avg_speed_kmh']
            missing_cols = [col for col in required_cols if col not in joined_data.columns]
            if missing_cols:
                print(f"   - ❌ Missing required columns: {missing_cols}")
            else:
                print(f"   - ✅ All required columns present")
                
                # Check for data values
                duration_values = joined_data['avg_duration_sec'].dropna()
                speed_values = joined_data['avg_speed_kmh'].dropna()
                print(f"   - Duration values: {len(duration_values)} non-null")
                print(f"   - Speed values: {len(speed_values)} non-null")
        else:
            print(f"   - ❌ Joined data is empty!")
        
        return len(joined_data) > 0
        
    except Exception as e:
        print(f"❌ Error testing filtering pipeline: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_map_creation():
    """Test if map creation works with sample data."""
    
    try:
        from map_a_hourly import HourlyMapInterface
        from shapely.geometry import LineString
        
        interface = HourlyMapInterface()
        
        # Create sample data that should definitely work
        gdf = gpd.GeoDataFrame({
            'Id': ['link_1', 'link_2'],
            'From': ['A', 'B'],
            'To': ['B', 'C'],
            'geometry': [
                LineString([(34.0, 29.0), (35.0, 30.0)]),
                LineString([(35.0, 30.0), (36.0, 31.0)])
            ]
        })
        
        # Add results data directly to the GeoDataFrame (simulating successful join)
        gdf['avg_duration_sec'] = [120, 180]
        gdf['avg_speed_kmh'] = [50, 40]
        gdf['avg_duration_min'] = gdf['avg_duration_sec'] / 60
        gdf['n_valid'] = [10, 15]
        
        control_state = {
            'filters': {
                'metrics': {
                    'metric_type': 'duration'
                }
            }
        }
        
        print(f"🗺️ Testing map creation:")
        print(f"   - Input data: {len(gdf)} features")
        print(f"   - Columns: {list(gdf.columns)}")
        
        # Test map creation
        map_obj = interface._create_hourly_map(gdf, control_state)
        
        print(f"   - ✅ Map created successfully: {type(map_obj)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing map creation: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_controls_default_values():
    """Test what default values the controls are providing."""
    
    try:
        from controls import InteractiveControls
        
        controls = InteractiveControls()
        
        # This is tricky because controls need Streamlit context
        # Let's see if we can understand the issue from the code
        
        print("🎛️ Controls investigation:")
        print("   - InteractiveControls created successfully")
        
        # The issue might be that the controls are setting restrictive default filters
        # Let's check if there are any hardcoded filter values
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing controls: {e}")
        return False

def main():
    """Run all diagnostic tests."""
    
    print("=" * 60)
    print("DEBUGGING EMPTY MAP ISSUE")
    print("=" * 60)
    
    tests = [
        ("Data Loading", test_data_loading),
        ("Control State", test_control_state),
        ("Filtering Pipeline", test_filtering_pipeline),
        ("Map Creation", test_map_creation),
        ("Controls Default Values", test_controls_default_values)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"{'✅' if result else '❌'} {test_name}: {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
            results.append((test_name, False))
        print()
    
    print("=" * 60)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 60)
    
    for test_name, result in results:
        print(f"{'✅' if result else '❌'} {test_name}")
    
    # Provide recommendations based on results
    failed_tests = [name for name, result in results if not result]
    
    if failed_tests:
        print(f"\n🔍 LIKELY ISSUES:")
        if "Data Loading" in failed_tests:
            print("• Data files are not being loaded correctly")
        if "Filtering Pipeline" in failed_tests:
            print("• Filters are too restrictive or data join is failing")
        if "Map Creation" in failed_tests:
            print("• Map rendering pipeline has issues")
        
        print(f"\n💡 RECOMMENDATIONS:")
        print("• Check if data is actually loaded in session state")
        print("• Verify that filters are not eliminating all data")
        print("• Ensure data join is working correctly")
        print("• Test with minimal/no filters first")
    else:
        print(f"\n🎉 All tests passed - the issue might be elsewhere!")

if __name__ == "__main__":
    main()