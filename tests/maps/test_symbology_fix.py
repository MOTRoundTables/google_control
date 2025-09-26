"""
Test the SymbologyEngine fix for the missing classify_and_color_data method.
"""

import numpy as np

def test_symbology_engine_methods():
    """Test that SymbologyEngine has all required methods."""
    
    try:
        from components.maps.symbology import SymbologyEngine
        
        engine = SymbologyEngine()
        
        # Check that all required methods/attributes exist
        required_methods = [
            'classify_and_color_data',
            'create_symbology',
            'classifier',
            'color_manager',
            'style_calculator'
        ]
        
        missing_methods = []
        for method in required_methods:
            if not hasattr(engine, method):
                missing_methods.append(method)
        
        if missing_methods:
            print(f"❌ Missing methods: {missing_methods}")
            return False
        
        print("✅ All required methods/attributes present:")
        for method in required_methods:
            print(f"   - {method}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing SymbologyEngine: {e}")
        return False

def test_classify_and_color_data():
    """Test the classify_and_color_data method."""
    
    try:
        from components.maps.symbology import SymbologyEngine
        
        engine = SymbologyEngine()
        
        # Create sample data
        values = np.array([120, 180, 240, 300, 360, 420, 480, 540, 600, 660])
        
        # Test duration classification
        class_breaks, colors = engine.classify_and_color_data(
            values, 'duration', method='quantiles', n_classes=5
        )
        
        print("✅ classify_and_color_data method works:")
        print(f"   - Input values: {len(values)} values")
        print(f"   - Class breaks: {class_breaks}")
        print(f"   - Colors: {colors}")
        print(f"   - Number of classes: {len(colors)}")
        
        # Test speed classification
        class_breaks_speed, colors_speed = engine.classify_and_color_data(
            values, 'speed', method='quantiles', n_classes=3
        )
        
        print("✅ Speed classification also works:")
        print(f"   - Speed class breaks: {class_breaks_speed}")
        print(f"   - Speed colors: {colors_speed}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing classify_and_color_data: {e}")
        return False

def test_map_interface_compatibility():
    """Test that map interfaces can use the SymbologyEngine."""
    
    try:
        from components.maps.map_a_hourly import HourlyMapInterface
        from components.maps.map_b_weekly import WeeklyMapInterface
        
        # Create interfaces
        hourly_interface = HourlyMapInterface()
        weekly_interface = WeeklyMapInterface()
        
        # Check that they have symbology engines
        if not hasattr(hourly_interface, 'symbology'):
            print("❌ HourlyMapInterface missing symbology")
            return False
        
        if not hasattr(weekly_interface, 'symbology'):
            print("❌ WeeklyMapInterface missing symbology")
            return False
        
        # Check that symbology engines have the required method
        if not hasattr(hourly_interface.symbology, 'classify_and_color_data'):
            print("❌ HourlyMapInterface.symbology missing classify_and_color_data")
            return False
        
        if not hasattr(weekly_interface.symbology, 'classify_and_color_data'):
            print("❌ WeeklyMapInterface.symbology missing classify_and_color_data")
            return False
        
        print("✅ Map interface compatibility:")
        print("   - HourlyMapInterface has symbology with classify_and_color_data")
        print("   - WeeklyMapInterface has symbology with classify_and_color_data")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing map interface compatibility: {e}")
        return False

def test_classification_methods():
    """Test different classification methods."""
    
    try:
        from components.maps.symbology import SymbologyEngine
        
        engine = SymbologyEngine()
        values = np.array([10, 20, 30, 40, 50, 60, 70, 80, 90, 100])
        
        methods = ['quantiles', 'equal_interval']
        
        for method in methods:
            try:
                class_breaks, colors = engine.classify_and_color_data(
                    values, 'duration', method=method, n_classes=4
                )
                print(f"✅ {method} classification works:")
                print(f"   - Breaks: {class_breaks}")
                print(f"   - Colors: {len(colors)} colors")
            except Exception as e:
                print(f"❌ {method} classification failed: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing classification methods: {e}")
        return False

def test_with_list_input():
    """Test with list input (not numpy array)."""
    
    try:
        from components.maps.symbology import SymbologyEngine
        
        engine = SymbologyEngine()
        
        # Test with Python list
        values_list = [120, 180, 240, 300, 360]
        
        class_breaks, colors = engine.classify_and_color_data(
            values_list, 'speed', method='quantiles', n_classes=3
        )
        
        print("✅ List input works:")
        print(f"   - Input: {values_list}")
        print(f"   - Breaks: {class_breaks}")
        print(f"   - Colors: {colors}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing list input: {e}")
        return False

def main():
    """Run all SymbologyEngine fix tests."""
    
    print("=" * 60)
    print("TESTING SYMBOLOGYENGINE FIX")
    print("=" * 60)
    
    tests = [
        ("SymbologyEngine Methods", test_symbology_engine_methods),
        ("classify_and_color_data", test_classify_and_color_data),
        ("Map Interface Compatibility", test_map_interface_compatibility),
        ("Classification Methods", test_classification_methods),
        ("List Input Support", test_with_list_input)
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
        print("🎉 All tests passed! SymbologyEngine fix is working.")
        print("\n📋 The AttributeError should now be resolved.")
        print("The Maps page should now render correctly with proper symbology.")
        return True
    else:
        print("⚠️ Some tests failed. The fix may not be complete.")
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)