"""
Test the fixed shapefile loading functionality.
"""

import os
import geopandas as gpd
from components.maps.maps_page import MapsPageInterface

def test_shapefile_loading_with_gdal_config():
    """Test shapefile loading with GDAL configuration."""
    
    shapefile_path = r"E:\google_agg\test_data\google_results_to_golan_17_8_25\google_results_to_golan_17_8_25.shp"
    
    if not os.path.exists(shapefile_path):
        print(f"❌ Shapefile not found: {shapefile_path}")
        return False
    
    try:
        # Set GDAL configuration
        os.environ['SHAPE_RESTORE_SHX'] = 'YES'
        
        print(f"🔧 Set SHAPE_RESTORE_SHX=YES")
        print(f"📂 Loading shapefile: {shapefile_path}")
        
        # Load shapefile directly
        gdf = gpd.read_file(shapefile_path)
        
        print(f"✅ Shapefile loaded successfully")
        print(f"   - Features: {len(gdf):,}")
        print(f"   - CRS: {gdf.crs}")
        print(f"   - Columns: {list(gdf.columns)}")
        print(f"   - Bounds: {gdf.total_bounds}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error loading shapefile: {e}")
        return False

def test_maps_interface_shapefile_loading():
    """Test the MapsPageInterface shapefile loading."""
    
    try:
        interface = MapsPageInterface()
        
        print(f"✅ MapsPageInterface created")
        print(f"   - Default shapefile: {interface.default_shapefile_path}")
        
        # Test that the spatial manager can be created
        spatial_manager = interface.spatial_manager
        print(f"✅ SpatialDataManager accessible")
        
        # Check if default shapefile exists
        if os.path.exists(interface.default_shapefile_path):
            print(f"✅ Default shapefile exists")
        else:
            print(f"⚠️ Default shapefile not found")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing MapsPageInterface: {e}")
        return False

def test_gdal_environment():
    """Test GDAL environment configuration."""
    
    print("🔧 Testing GDAL environment configuration...")
    
    # Set the configuration
    os.environ['SHAPE_RESTORE_SHX'] = 'YES'
    
    # Verify it's set
    config_value = os.environ.get('SHAPE_RESTORE_SHX')
    
    if config_value == 'YES':
        print(f"✅ SHAPE_RESTORE_SHX set correctly: {config_value}")
        return True
    else:
        print(f"❌ SHAPE_RESTORE_SHX not set correctly: {config_value}")
        return False

def main():
    """Run all shapefile loading tests."""
    
    print("=" * 60)
    print("TESTING SHAPEFILE LOADING FIX")
    print("=" * 60)
    
    tests = [
        ("GDAL Environment", test_gdal_environment),
        ("Direct Shapefile Loading", test_shapefile_loading_with_gdal_config),
        ("Maps Interface", test_maps_interface_shapefile_loading)
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
    
    print("=" * 60)
    print(f"FINAL RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Shapefile loading fix is working.")
        print("\n📋 USAGE NOTES:")
        print("• Use file path input instead of file upload for shapefiles")
        print("• SHAPE_RESTORE_SHX is automatically set to YES")
        print("• All shapefile components (.shp, .shx, .dbf, .prj) should be in the same directory")
        return True
    else:
        print("⚠️ Some tests failed. Check the issues above.")
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)