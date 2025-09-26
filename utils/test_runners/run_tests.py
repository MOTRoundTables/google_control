#!/usr/bin/env python3
"""
Simple test runner for map visualization project setup.
"""

import sys
import importlib
from pathlib import Path


def test_library_imports():
    """Test that all required libraries can be imported."""
    print("Testing library imports...")
    
    libraries = [
        ('geopandas', 'gpd'),
        ('folium', 'folium'),
        ('pyproj', 'pyproj'),
        ('shapely.geometry', 'shapely_geom'),
        ('streamlit', 'st'),
        ('pandas', 'pd'),
        ('numpy', 'np')
    ]
    
    for lib_name, alias in libraries:
        try:
            lib = importlib.import_module(lib_name)
            print(f"  ✓ {lib_name} imported successfully")
        except ImportError as e:
            print(f"  ✗ Failed to import {lib_name}: {e}")
            return False
    
    return True


def test_module_imports():
    """Test that all map visualization modules can be imported."""
    print("\nTesting module imports...")
    
    modules = [
        'spatial_data',
        'map_data', 
        'map_renderer',
        'symbology',
        'controls',
        'map_config'
    ]
    
    for module_name in modules:
        try:
            module = importlib.import_module(module_name)
            print(f"  ✓ {module_name} imported successfully")
        except ImportError as e:
            print(f"  ✗ Failed to import {module_name}: {e}")
            return False
    
    return True


def test_class_instantiation():
    """Test that main classes can be instantiated."""
    print("\nTesting class instantiation...")
    
    try:
        from spatial_data import SpatialDataManager
        from map_data import MapDataProcessor  
        from map_renderer import MapRenderer
        from symbology import SymbologyEngine
        from controls import InteractiveControls
        from map_config import MapSymbologyConfig
        
        classes = [
            ('SpatialDataManager', SpatialDataManager),
            ('MapDataProcessor', MapDataProcessor),
            ('MapRenderer', MapRenderer),
            ('SymbologyEngine', SymbologyEngine),
            ('InteractiveControls', InteractiveControls),
            ('MapSymbologyConfig', MapSymbologyConfig)
        ]
        
        for class_name, class_obj in classes:
            try:
                instance = class_obj()
                print(f"  ✓ {class_name} instantiated successfully")
            except Exception as e:
                print(f"  ✗ Failed to instantiate {class_name}: {e}")
                return False
        
        return True
        
    except ImportError as e:
        print(f"  ✗ Import error during instantiation test: {e}")
        return False


def test_file_structure():
    """Test that required files exist."""
    print("\nTesting file structure...")
    
    required_files = [
        'spatial_data.py',
        'map_data.py', 
        'map_renderer.py',
        'symbology.py',
        'controls.py',
        'map_config.py',
        'requirements.txt',
        'pytest.ini',
        'tests/__init__.py',
        'tests/conftest.py',
        'tests/map_visualization/__init__.py',
        'tests/map_visualization/test_project_setup.py'
    ]
    
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            print(f"  ✓ {file_path} exists")
        else:
            print(f"  ✗ {file_path} missing")
            return False
    
    return True


def test_requirements_content():
    """Test that requirements.txt contains geospatial libraries."""
    print("\nTesting requirements.txt content...")
    
    required_libs = ['geopandas', 'folium', 'pyproj', 'shapely']
    
    try:
        with open('requirements.txt', 'r') as f:
            content = f.read()
        
        for lib in required_libs:
            if lib in content:
                print(f"  ✓ {lib} found in requirements.txt")
            else:
                print(f"  ✗ {lib} missing from requirements.txt")
                return False
        
        return True
        
    except FileNotFoundError:
        print("  ✗ requirements.txt not found")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("MAP VISUALIZATION PROJECT SETUP TESTS")
    print("=" * 60)
    
    tests = [
        test_library_imports,
        test_module_imports,
        test_class_instantiation,
        test_file_structure,
        test_requirements_content
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        if test_func():
            passed += 1
        print()
    
    print("=" * 60)
    print(f"RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Project setup is complete.")
        return 0
    else:
        print("❌ Some tests failed. Please check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())