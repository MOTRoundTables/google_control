"""
Test that all features implemented in previous tasks are properly connected and functional.
"""

def test_module_imports():
    """Test that all required modules can be imported."""
    modules_to_test = [
        'spatial_data',
        'map_data', 
        'map_renderer',
        'symbology',
        'controls',
        'map_a_hourly',
        'map_b_weekly',
        'kpi_engine',
        'performance_optimizer',
        'data_quality',
        'quality_reporting',
        'export_manager',
        'link_details_panel'
    ]
    
    imported_modules = []
    failed_modules = []
    
    for module_name in modules_to_test:
        try:
            __import__(module_name)
            imported_modules.append(module_name)
            print(f"✅ {module_name}")
        except ImportError as e:
            failed_modules.append((module_name, str(e)))
            print(f"❌ {module_name}: {e}")
    
    print(f"\nImport Results: {len(imported_modules)}/{len(modules_to_test)} modules imported successfully")
    
    if failed_modules:
        print("\nFailed imports:")
        for module, error in failed_modules:
            print(f"  - {module}: {error}")
    
    return len(failed_modules) == 0

def test_maps_page_dependencies():
    """Test that maps page can import all its dependencies."""
    try:
        from components.maps.maps_page import MapsPageInterface
        
        # Test that the interface can access all its components
        interface = MapsPageInterface()
        
        # Check spatial manager
        assert hasattr(interface, 'spatial_manager')
        assert interface.spatial_manager is not None
        print("✅ Spatial manager accessible")
        
        # Check hourly interface
        assert hasattr(interface, 'hourly_interface')
        assert interface.hourly_interface is not None
        print("✅ Hourly interface accessible")
        
        # Check weekly interface
        assert hasattr(interface, 'weekly_interface')
        assert interface.weekly_interface is not None
        print("✅ Weekly interface accessible")
        
        return True
        
    except Exception as e:
        print(f"❌ Maps page dependencies test failed: {e}")
        return False

def test_map_interfaces():
    """Test that map interfaces can be created and have required methods."""
    try:
        from components.maps.map_a_hourly import HourlyMapInterface
        from components.maps.map_b_weekly import WeeklyMapInterface
        
        # Test hourly interface
        hourly_interface = HourlyMapInterface()
        required_hourly_methods = [
            'render_hourly_map_page',
            '_calculate_data_bounds',
            '_apply_filters',
            '_create_hourly_map'
        ]
        
        for method in required_hourly_methods:
            assert hasattr(hourly_interface, method), f"Missing method: {method}"
        
        print("✅ Hourly map interface has all required methods")
        
        # Test weekly interface
        weekly_interface = WeeklyMapInterface()
        required_weekly_methods = [
            'render_weekly_map_page',
            '_calculate_data_bounds',
            '_apply_filters_and_aggregate',
            '_create_weekly_map'
        ]
        
        for method in required_weekly_methods:
            assert hasattr(weekly_interface, method), f"Missing method: {method}"
        
        print("✅ Weekly map interface has all required methods")
        
        return True
        
    except Exception as e:
        print(f"❌ Map interfaces test failed: {e}")
        return False

def test_core_components():
    """Test that core components can be created."""
    components_to_test = [
        ('spatial_data', 'SpatialDataManager'),
        ('map_data', 'MapDataProcessor'),
        ('map_renderer', 'MapVisualizationRenderer'),
        ('symbology', 'SymbologyEngine'),
        ('controls', 'InteractiveControls'),
        ('kpi_engine', 'KPIEngine'),
        ('performance_optimizer', 'PerformanceOptimizer')
    ]
    
    created_components = []
    failed_components = []
    
    for module_name, class_name in components_to_test:
        try:
            module = __import__(module_name)
            component_class = getattr(module, class_name)
            component_instance = component_class()
            created_components.append(f"{module_name}.{class_name}")
            print(f"✅ {module_name}.{class_name}")
        except Exception as e:
            failed_components.append((f"{module_name}.{class_name}", str(e)))
            print(f"❌ {module_name}.{class_name}: {e}")
    
    print(f"\nComponent Creation Results: {len(created_components)}/{len(components_to_test)} components created successfully")
    
    if failed_components:
        print("\nFailed component creation:")
        for component, error in failed_components:
            print(f"  - {component}: {error}")
    
    return len(failed_components) == 0

def test_file_structure():
    """Test that all required files exist."""
    import os
    
    required_files = [
        'maps_page.py',
        'spatial_data.py',
        'map_data.py',
        'map_renderer.py',
        'symbology.py',
        'controls.py',
        'map_a_hourly.py',
        'map_b_weekly.py',
        'kpi_engine.py',
        'performance_optimizer.py',
        'data_quality.py',
        'quality_reporting.py',
        'export_manager.py',
        'link_details_panel.py'
    ]
    
    existing_files = []
    missing_files = []
    
    for file_name in required_files:
        if os.path.exists(file_name):
            existing_files.append(file_name)
            print(f"✅ {file_name}")
        else:
            missing_files.append(file_name)
            print(f"❌ {file_name} - File not found")
    
    print(f"\nFile Structure Results: {len(existing_files)}/{len(required_files)} files exist")
    
    if missing_files:
        print("\nMissing files:")
        for file_name in missing_files:
            print(f"  - {file_name}")
    
    return len(missing_files) == 0

def test_integration_completeness():
    """Test that the integration is complete and functional."""
    try:
        # Test that app.py has the Maps page integrated
        from app import main
        
        # Test that maps_page can be called
        from app import maps_page
        
        # Test that all map components work together
        from components.maps.maps_page import MapsPageInterface
        interface = MapsPageInterface()
        
        # Test session state initialization
        interface._initialize_session_state()
        
        # Test data availability check
        has_data = interface._check_data_availability()
        # Should be False initially (no data loaded)
        assert not has_data, "Should return False when no data is loaded"
        
        print("✅ Integration completeness test passed")
        return True
        
    except Exception as e:
        print(f"❌ Integration completeness test failed: {e}")
        return False

def main():
    """Run all connectivity tests."""
    print("Testing feature connectivity and integration...\n")
    
    tests = [
        ("Module Imports", test_module_imports),
        ("Maps Page Dependencies", test_maps_page_dependencies),
        ("Map Interfaces", test_map_interfaces),
        ("Core Components", test_core_components),
        ("File Structure", test_file_structure),
        ("Integration Completeness", test_integration_completeness)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n=== {test_name} ===")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
        print()
    
    print("=" * 50)
    print(f"FINAL RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All features are properly connected and functional!")
        print("✅ Maps page integration is complete and ready for use.")
        return True
    else:
        print("⚠️ Some features may not be properly connected.")
        print("Please check the failed tests above.")
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)