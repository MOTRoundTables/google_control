"""
Test the MapDataProcessor fix for the missing join_results_to_shapefile method.
"""

import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString

def test_map_data_processor_methods():
    """Test that MapDataProcessor has all required methods."""
    
    try:
        from components.maps.map_data import MapDataProcessor
        
        processor = MapDataProcessor()
        
        # Check that all required methods/attributes exist
        required_methods = [
            'join_results_to_shapefile',
            'prepare_map_data',
            'joiner',
            'filter_manager', 
            'aggregation_engine'
        ]
        
        missing_methods = []
        for method in required_methods:
            if not hasattr(processor, method):
                missing_methods.append(method)
        
        if missing_methods:
            print(f"❌ Missing methods: {missing_methods}")
            return False
        
        print("✅ All required methods/attributes present:")
        for method in required_methods:
            print(f"   - {method}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing MapDataProcessor: {e}")
        return False

def test_join_results_to_shapefile():
    """Test the join_results_to_shapefile method."""
    
    try:
        from components.maps.map_data import MapDataProcessor
        
        processor = MapDataProcessor()
        
        # Create sample data
        gdf = gpd.GeoDataFrame({
            'Id': ['link_1', 'link_2'],
            'From': ['A', 'B'],
            'To': ['B', 'C'],
            'geometry': [
                LineString([(0, 0), (1, 1)]),
                LineString([(1, 1), (2, 2)])
            ]
        })
        
        results_df = pd.DataFrame({
            'link_id': ['s_A-B', 's_B-C'],
            'avg_duration_sec': [120, 180],
            'avg_speed_kmh': [50, 40]
        })
        
        # Test the join
        joined_data = processor.join_results_to_shapefile(gdf, results_df)
        
        print("✅ join_results_to_shapefile method works:")
        print(f"   - Input shapefile: {len(gdf)} features")
        print(f"   - Input results: {len(results_df)} records")
        print(f"   - Joined data: {len(joined_data)} features")
        print(f"   - Columns: {list(joined_data.columns)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing join_results_to_shapefile: {e}")
        return False

def test_map_interfaces_import():
    """Test that map interfaces can be imported without errors."""
    
    try:
        from components.maps.map_a_hourly import HourlyMapInterface
        from components.maps.map_b_weekly import WeeklyMapInterface
        
        # Create interfaces
        hourly_interface = HourlyMapInterface()
        weekly_interface = WeeklyMapInterface()
        
        # Check that they have data_processor
        if not hasattr(hourly_interface, 'data_processor'):
            print("❌ HourlyMapInterface missing data_processor")
            return False
        
        if not hasattr(weekly_interface, 'data_processor'):
            print("❌ WeeklyMapInterface missing data_processor")
            return False
        
        # Check that data_processor has the required method
        if not hasattr(hourly_interface.data_processor, 'join_results_to_shapefile'):
            print("❌ HourlyMapInterface.data_processor missing join_results_to_shapefile")
            return False
        
        if not hasattr(weekly_interface.data_processor, 'join_results_to_shapefile'):
            print("❌ WeeklyMapInterface.data_processor missing join_results_to_shapefile")
            return False
        
        print("✅ Map interfaces import successfully:")
        print("   - HourlyMapInterface created")
        print("   - WeeklyMapInterface created")
        print("   - Both have data_processor with join_results_to_shapefile method")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing map interfaces: {e}")
        return False

def test_aggregation_engine_access():
    """Test that aggregation_engine can be accessed from map interfaces."""
    
    try:
        from components.maps.map_b_weekly import WeeklyMapInterface
        
        interface = WeeklyMapInterface()
        
        # Check aggregation_engine access
        if not hasattr(interface.data_processor, 'aggregation_engine'):
            print("❌ data_processor missing aggregation_engine")
            return False
        
        aggregation_engine = interface.data_processor.aggregation_engine
        
        # Check required methods
        required_methods = [
            'calculate_date_span_context',
            'compute_weekly_aggregation',
            'compute_aggregation_statistics'
        ]
        
        missing_methods = []
        for method in required_methods:
            if not hasattr(aggregation_engine, method):
                missing_methods.append(method)
        
        if missing_methods:
            print(f"❌ AggregationEngine missing methods: {missing_methods}")
            return False
        
        print("✅ AggregationEngine access works:")
        print("   - aggregation_engine accessible from data_processor")
        for method in required_methods:
            print(f"   - {method} method available")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing aggregation engine access: {e}")
        return False

def main():
    """Run all MapDataProcessor fix tests."""
    
    print("=" * 60)
    print("TESTING MAPDATAPROCESSOR FIX")
    print("=" * 60)
    
    tests = [
        ("MapDataProcessor Methods", test_map_data_processor_methods),
        ("join_results_to_shapefile", test_join_results_to_shapefile),
        ("Map Interfaces Import", test_map_interfaces_import),
        ("AggregationEngine Access", test_aggregation_engine_access)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*15} {test_name} {'='*15}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
        print()
    
    print("=" * 60)
    print(f"FINAL RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! MapDataProcessor fix is working.")
        print("\n📋 The AttributeError should now be resolved.")
        print("You can now run the Maps page without the join_results_to_shapefile error.")
        return True
    else:
        print("⚠️ Some tests failed. The fix may not be complete.")
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)