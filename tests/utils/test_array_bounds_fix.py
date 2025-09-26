"""
Test the array bounds fix for the ValueError in map_renderer.py.
"""

import numpy as np
from unittest.mock import patch

def test_bounds_evaluation():
    """Test bounds evaluation with different input types."""
    
    try:
        from components.maps.map_renderer import MapRenderer
        
        renderer = MapRenderer()
        
        # Test with None bounds
        map_obj1 = renderer.create_base_map(bounds=None)
        print("✅ None bounds handled correctly")
        
        # Test with tuple bounds
        bounds_tuple = (34.0, 29.0, 36.0, 33.0)
        map_obj2 = renderer.create_base_map(bounds=bounds_tuple)
        print("✅ Tuple bounds handled correctly")
        
        # Test with list bounds
        bounds_list = [34.0, 29.0, 36.0, 33.0]
        map_obj3 = renderer.create_base_map(bounds=bounds_list)
        print("✅ List bounds handled correctly")
        
        # Test with numpy array bounds (this was causing the error)
        bounds_array = np.array([34.0, 29.0, 36.0, 33.0])
        map_obj4 = renderer.create_base_map(bounds=bounds_array)
        print("✅ Numpy array bounds handled correctly")
        
        # Test with empty bounds
        bounds_empty = []
        map_obj5 = renderer.create_base_map(bounds=bounds_empty)
        print("✅ Empty bounds handled correctly")
        
        # Test with wrong size bounds
        bounds_wrong = [34.0, 29.0, 36.0]  # Only 3 elements
        map_obj6 = renderer.create_base_map(bounds=bounds_wrong)
        print("✅ Wrong size bounds handled correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing bounds evaluation: {e}")
        return False

def test_map_renderer_creation():
    """Test MapRenderer creation and basic functionality."""
    
    try:
        from components.maps.map_renderer import MapRenderer
        
        renderer = MapRenderer()
        
        # Check default values
        print(f"✅ MapRenderer created with:")
        print(f"   - Target CRS: {renderer.target_crs}")
        print(f"   - Default zoom: {renderer.default_zoom}")
        print(f"   - Default center: {renderer.default_center}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing MapRenderer creation: {e}")
        return False

def test_map_visualization_renderer():
    """Test MapVisualizationRenderer which uses MapRenderer."""
    
    try:
        from components.maps.map_renderer import MapVisualizationRenderer
        
        renderer = MapVisualizationRenderer()
        
        # Check that it has the renderer
        if not hasattr(renderer, 'renderer'):
            print("❌ MapVisualizationRenderer missing renderer attribute")
            return False
        
        print("✅ MapVisualizationRenderer created successfully")
        print(f"   - Has renderer: {type(renderer.renderer)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing MapVisualizationRenderer: {e}")
        return False

def test_with_geopandas_bounds():
    """Test with bounds from a GeoDataFrame (typical use case)."""
    
    try:
        import geopandas as gpd
        from shapely.geometry import LineString
        from components.maps.map_renderer import MapRenderer
        
        # Create sample GeoDataFrame
        gdf = gpd.GeoDataFrame({
            'Id': ['link_1', 'link_2'],
            'geometry': [
                LineString([(34.0, 29.0), (35.0, 30.0)]),
                LineString([(35.0, 30.0), (36.0, 31.0)])
            ]
        })
        
        # Get bounds (this returns a numpy array)
        bounds = gdf.total_bounds
        print(f"✅ GeoDataFrame bounds: {bounds} (type: {type(bounds)})")
        
        # Test with these bounds
        renderer = MapRenderer()
        map_obj = renderer.create_base_map(bounds=bounds)
        
        print("✅ GeoDataFrame bounds handled correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing with GeoDataFrame bounds: {e}")
        return False

def test_map_interface_integration():
    """Test that map interfaces can create maps without the ValueError."""
    
    try:
        from components.maps.map_a_hourly import HourlyMapInterface
        import pandas as pd
        import geopandas as gpd
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
        
        # Add some results data
        gdf['avg_duration_sec'] = [120, 180]
        gdf['avg_speed_kmh'] = [50, 40]
        gdf['avg_duration_min'] = gdf['avg_duration_sec'] / 60
        
        # Create interface
        interface = HourlyMapInterface()
        
        # Mock control state
        control_state = {
            'filters': {
                'metrics': {
                    'metric_type': 'duration'
                }
            }
        }
        
        # Test creating a map (this was causing the ValueError)
        map_obj = interface._create_hourly_map(gdf, control_state)
        
        print("✅ HourlyMapInterface can create maps without ValueError")
        print(f"   - Map object type: {type(map_obj)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing map interface integration: {e}")
        return False

def main():
    """Run all array bounds fix tests."""
    
    print("=" * 60)
    print("TESTING ARRAY BOUNDS FIX")
    print("=" * 60)
    
    tests = [
        ("Bounds Evaluation", test_bounds_evaluation),
        ("MapRenderer Creation", test_map_renderer_creation),
        ("MapVisualizationRenderer", test_map_visualization_renderer),
        ("GeoDataFrame Bounds", test_with_geopandas_bounds),
        ("Map Interface Integration", test_map_interface_integration)
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
        print("🎉 All tests passed! Array bounds fix is working.")
        print("\n📋 The ValueError should now be resolved.")
        print("Maps should now render correctly without array truth value errors.")
        return True
    else:
        print("⚠️ Some tests failed. The fix may not be complete.")
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)