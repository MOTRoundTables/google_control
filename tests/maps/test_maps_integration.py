"""
Simple test to verify Maps page integration works correctly.
"""

import sys
import os

def test_maps_page_import():
    """Test that maps page can be imported successfully."""
    try:
        from components.maps.maps_page import MapsPageInterface, render_maps_page
        print("✅ Maps page modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import maps page: {e}")
        return False

def test_app_integration():
    """Test that app.py can import and use maps page."""
    try:
        from app import main, maps_page
        print("✅ App integration successful")
        return True
    except ImportError as e:
        print(f"❌ Failed to import app with maps integration: {e}")
        return False

def test_maps_interface_creation():
    """Test that MapsPageInterface can be created."""
    try:
        from components.maps.maps_page import MapsPageInterface
        interface = MapsPageInterface()
        
        # Check that all required components are initialized
        assert hasattr(interface, 'spatial_manager')
        assert hasattr(interface, 'hourly_interface')
        assert hasattr(interface, 'weekly_interface')
        assert hasattr(interface, 'default_shapefile_path')
        
        print("✅ MapsPageInterface created successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to create MapsPageInterface: {e}")
        return False

def test_session_state_initialization():
    """Test session state initialization."""
    try:
        from components.maps.maps_page import MapsPageInterface
        import streamlit as st
        
        # Mock session state
        if not hasattr(st, 'session_state'):
            st.session_state = {}
        
        interface = MapsPageInterface()
        interface._initialize_session_state()
        
        # Check required session state variables
        required_vars = [
            'maps_shapefile_path',
            'maps_results_path', 
            'maps_shapefile_data',
            'maps_hourly_results',
            'maps_weekly_results',
            'maps_preferences'
        ]
        
        for var in required_vars:
            assert var in st.session_state, f"Missing session state variable: {var}"
        
        print("✅ Session state initialization successful")
        return True
    except Exception as e:
        print(f"❌ Session state initialization failed: {e}")
        return False

def test_data_availability_check():
    """Test data availability checking."""
    try:
        from components.maps.maps_page import MapsPageInterface
        import streamlit as st
        import pandas as pd
        import geopandas as gpd
        from shapely.geometry import LineString
        
        # Mock session state
        if not hasattr(st, 'session_state'):
            st.session_state = {}
        
        interface = MapsPageInterface()
        interface._initialize_session_state()
        
        # Test with no data
        assert not interface._check_data_availability(), "Should return False with no data"
        
        # Test with only shapefile
        st.session_state.maps_shapefile_data = gpd.GeoDataFrame({
            'Id': ['test'],
            'From': ['A'],
            'To': ['B'],
            'geometry': [LineString([(0, 0), (1, 1)])]
        })
        assert not interface._check_data_availability(), "Should return False with only shapefile"
        
        # Test with both shapefile and results
        st.session_state.maps_hourly_results = pd.DataFrame({
            'link_id': ['s_A-B'],
            'date': ['2024-01-01'],
            'hour': [8],
            'avg_duration_sec': [120],
            'avg_speed_kmh': [50]
        })
        assert interface._check_data_availability(), "Should return True with both data types"
        
        print("✅ Data availability check working correctly")
        return True
    except Exception as e:
        print(f"❌ Data availability check failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing Maps page integration...\n")
    
    tests = [
        test_maps_page_import,
        test_app_integration,
        test_maps_interface_creation,
        test_session_state_initialization,
        test_data_availability_check
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}\n")
    
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Maps page integration is working correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)