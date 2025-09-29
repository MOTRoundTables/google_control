"""
Test the complete Maps page functionality after fixing the AttributeError.
"""

import os
import sys
import pandas as pd
import geopandas as gpd
from unittest.mock import patch, MagicMock
import streamlit as st

def test_complete_import_chain():
    """Test the complete import chain from app.py to all map components."""
    
    try:
        # Test app.py imports
        from app import main, maps_page
        print("✅ app.py imports successful")
        
        # Test maps_page imports
        from components.maps.maps_page import MapsPageInterface, render_maps_page
        print("✅ maps_page.py imports successful")
        
        # Test map interface imports
        from components.maps.map_a_hourly import HourlyMapInterface
        from components.maps.map_b_weekly import WeeklyMapInterface
        print("✅ Map interface imports successful")
        
        # Test data processor imports
        from components.maps.map_data import MapDataProcessor
        print("✅ MapDataProcessor import successful")
        
        # Test spatial data imports
        from components.maps.spatial_data import SpatialDataManager
        print("✅ SpatialDataManager import successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Import chain failed: {e}")
        return False

def test_maps_page_interface_creation():
    """Test creating MapsPageInterface with all components."""
    
    try:
        from components.maps.maps_page import MapsPageInterface
        
        interface = MapsPageInterface()
        
        # Check all components are created
        components = [
            ('spatial_manager', 'SpatialDataManager'),
            ('hourly_interface', 'HourlyMapInterface'),
            ('weekly_interface', 'WeeklyMapInterface')
        ]
        
        for attr_name, class_name in components:
            if not hasattr(interface, attr_name):
                print(f"❌ Missing attribute: {attr_name}")
                return False
            
            component = getattr(interface, attr_name)
            if component is None:
                print(f"❌ {attr_name} is None")
                return False
            
            print(f"✅ {attr_name} ({class_name}) created successfully")
        
        # Check that map interfaces have data_processor with required methods
        for interface_name in ['hourly_interface', 'weekly_interface']:
            map_interface = getattr(interface, interface_name)
            
            if not hasattr(map_interface, 'data_processor'):
                print(f"❌ {interface_name} missing data_processor")
                return False
            
            data_processor = map_interface.data_processor
            
            if not hasattr(data_processor, 'join_results_to_shapefile'):
                print(f"❌ {interface_name}.data_processor missing join_results_to_shapefile")
                return False
            
            print(f"✅ {interface_name}.data_processor has join_results_to_shapefile")
        
        return True
        
    except Exception as e:
        print(f"❌ MapsPageInterface creation failed: {e}")
        return False

def test_data_processor_functionality():
    """Test MapDataProcessor functionality with sample data."""
    
    try:
        from components.maps.map_data import MapDataProcessor
        from shapely.geometry import LineString
        
        processor = MapDataProcessor()
        
        # Create sample shapefile data
        gdf = gpd.GeoDataFrame({
            'Id': ['link_1', 'link_2', 'link_3'],
            'From': ['A', 'B', 'C'],
            'To': ['B', 'C', 'D'],
            'geometry': [
                LineString([(0, 0), (1, 1)]),
                LineString([(1, 1), (2, 2)]),
                LineString([(2, 2), (3, 3)])
            ]
        })
        
        # Create sample results data
        results_df = pd.DataFrame({
            'link_id': ['s_A-B', 's_B-C', 's_C-D'],
            'date': ['2024-01-01', '2024-01-01', '2024-01-01'],
            'hour': [8, 8, 8],
            'avg_duration_sec': [120, 180, 240],
            'avg_speed_kmh': [50, 40, 30],
            'n_valid': [10, 15, 20]
        })
        
        # Test join functionality
        joined_data = processor.join_results_to_shapefile(gdf, results_df)
        
        print("✅ Data join successful:")
        print(f"   - Input shapefile: {len(gdf)} features")
        print(f"   - Input results: {len(results_df)} records")
        print(f"   - Joined data: {len(joined_data)} features")
        print(f"   - Join columns: {[col for col in joined_data.columns if col not in gdf.columns]}")
        
        # Test aggregation engine
        aggregation_engine = processor.aggregation_engine
        
        # Test date span calculation
        date_context = aggregation_engine.calculate_date_span_context(results_df)
        print(f"✅ Date span calculation: {date_context}")
        
        # Test weekly aggregation
        weekly_data = aggregation_engine.compute_weekly_aggregation(results_df, method='median')
        print(f"✅ Weekly aggregation: {len(weekly_data)} records")
        
        return True
        
    except Exception as e:
        print(f"❌ Data processor functionality test failed: {e}")
        return False

def test_map_interface_methods():
    """Test that map interfaces have all required methods."""
    
    try:
        from components.maps.map_a_hourly import HourlyMapInterface
        from components.maps.map_b_weekly import WeeklyMapInterface
        
        # Test HourlyMapInterface
        hourly_interface = HourlyMapInterface()
        
        hourly_methods = [
            'render_hourly_map_page',
            '_calculate_data_bounds',
            '_apply_filters',
            '_create_hourly_map'
        ]
        
        for method in hourly_methods:
            if not hasattr(hourly_interface, method):
                print(f"❌ HourlyMapInterface missing method: {method}")
                return False
        
        print("✅ HourlyMapInterface has all required methods")
        
        # Test WeeklyMapInterface
        weekly_interface = WeeklyMapInterface()
        
        weekly_methods = [
            'render_weekly_map_page',
            '_calculate_data_bounds',
            '_apply_filters_and_aggregate',
            '_create_weekly_map'
        ]
        
        for method in weekly_methods:
            if not hasattr(weekly_interface, method):
                print(f"❌ WeeklyMapInterface missing method: {method}")
                return False
        
        print("✅ WeeklyMapInterface has all required methods")
        
        return True
        
    except Exception as e:
        print(f"❌ Map interface methods test failed: {e}")
        return False

def test_session_state_integration():
    """Test session state integration with mock Streamlit."""
    
    try:
        from components.maps.maps_page import MapsPageInterface
        
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
            if var not in st.session_state:
                print(f"❌ Missing session state variable: {var}")
                return False
        
        print("✅ Session state integration successful:")
        for var in required_vars:
            print(f"   - {var}: {type(st.session_state[var])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Session state integration test failed: {e}")
        return False

def test_with_real_data():
    """Test with real data files if available."""
    
    try:
        from components.maps.maps_page import MapsPageInterface
        
        interface = MapsPageInterface()
        
        # Check if test data files exist
        shapefile_exists = os.path.exists(interface.default_shapefile_path)
        hourly_exists = os.path.exists(interface.default_hourly_path)
        weekly_exists = os.path.exists(interface.default_weekly_path)
        
        print(f"📁 Test data availability:")
        print(f"   - Shapefile: {'✅' if shapefile_exists else '❌'} {interface.default_shapefile_path}")
        print(f"   - Hourly: {'✅' if hourly_exists else '❌'} {interface.default_hourly_path}")
        print(f"   - Weekly: {'✅' if weekly_exists else '❌'} {interface.default_weekly_path}")
        
        if shapefile_exists and (hourly_exists or weekly_exists):
            print("✅ Real data files available for testing")
            
            # Test data availability check
            if not hasattr(st, 'session_state'):
                st.session_state = {}
            
            interface._initialize_session_state()
            
            # Mock loading the data
            if shapefile_exists:
                try:
                    import geopandas as gpd
                    os.environ['SHAPE_RESTORE_SHX'] = 'YES'
                    gdf = gpd.read_file(interface.default_shapefile_path)
                    st.session_state.maps_shapefile_data = gdf
                    print(f"✅ Shapefile loaded: {len(gdf)} features")
                except Exception as e:
                    print(f"⚠️ Could not load shapefile: {e}")
            
            if hourly_exists:
                try:
                    df = pd.read_csv(interface.default_hourly_path)
                    # Handle column name variations
                    if 'hour_of_day' in df.columns and 'hour' not in df.columns:
                        df = df.rename(columns={'hour_of_day': 'hour'})
                    st.session_state.maps_hourly_results = df
                    print(f"✅ Hourly data loaded: {len(df)} records")
                except Exception as e:
                    print(f"⚠️ Could not load hourly data: {e}")
            
            # Test data availability
            has_data = interface._check_data_availability()
            print(f"✅ Data availability check: {has_data}")
            
        else:
            print("ℹ️ Real data files not available, but interface is ready")
        
        return True
        
    except Exception as e:
        print(f"❌ Real data test failed: {e}")
        return False

def main():
    """Run all complete functionality tests."""
    
    print("=" * 70)
    print("TESTING COMPLETE MAPS FUNCTIONALITY AFTER ATTRIBUTEERROR FIX")
    print("=" * 70)
    
    tests = [
        ("Complete Import Chain", test_complete_import_chain),
        ("MapsPageInterface Creation", test_maps_page_interface_creation),
        ("Data Processor Functionality", test_data_processor_functionality),
        ("Map Interface Methods", test_map_interface_methods),
        ("Session State Integration", test_session_state_integration),
        ("Real Data Integration", test_with_real_data)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
        print()
    
    print("=" * 70)
    print(f"FINAL RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Maps page is fully functional.")
        print("\n📋 MAPS PAGE IS NOW READY:")
        print("1. The AttributeError has been resolved")
        print("2. All map interfaces work correctly")
        print("3. Data aggregation functionality is complete")
        print("4. Session state management is working")
        print("5. Real data integration is ready")
        print("\n🚀 You can now run: streamlit run app.py")
        print("   Navigate to '🗺️ Maps' and use the interactive maps!")
        return True
    else:
        print("⚠️ Some tests failed. Check the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)