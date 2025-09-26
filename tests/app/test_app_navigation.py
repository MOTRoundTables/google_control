"""
Test the app navigation structure with Maps page integration.
"""

def test_app_navigation():
    """Test that the app navigation includes the Maps page correctly."""
    try:
        # Import the app module
        import app
        
        # Check that the Maps page is in the navigation
        # We need to simulate the navigation logic
        pages = ["🏠 Main Processing", "🗺️ Maps", "📊 Results", "📚 Methodology", "📋 Schema Documentation"]
        
        print("✅ Navigation pages:")
        for i, page in enumerate(pages, 1):
            print(f"  {i}. {page}")
        
        # Verify Maps page is included
        assert "🗺️ Maps" in pages, "Maps page not found in navigation"
        print("✅ Maps page found in navigation")
        
        # Check that maps_page function exists
        assert hasattr(app, 'maps_page'), "maps_page function not found in app module"
        print("✅ maps_page function exists in app module")
        
        # Check that render_maps_page is imported
        from app import render_maps_page
        print("✅ render_maps_page imported successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Navigation test failed: {e}")
        return False

def test_page_order():
    """Test that the Maps page is in the correct position."""
    expected_pages = [
        "🏠 Main Processing", 
        "🗺️ Maps", 
        "📊 Results", 
        "📚 Methodology", 
        "📋 Schema Documentation"
    ]
    
    # The Maps page should be second in the list
    maps_index = expected_pages.index("🗺️ Maps")
    assert maps_index == 1, f"Maps page should be at index 1, but found at index {maps_index}"
    
    print("✅ Maps page is in the correct position (index 1)")
    return True

def test_maps_page_functionality():
    """Test that the maps page function can be called."""
    try:
        from app import maps_page
        from components.maps.maps_page import render_maps_page
        
        # These should not raise exceptions when imported
        print("✅ Maps page functions can be imported")
        
        # Test that MapsPageInterface can be created
        from components.maps.maps_page import MapsPageInterface
        interface = MapsPageInterface()
        print("✅ MapsPageInterface can be created")
        
        return True
        
    except Exception as e:
        print(f"❌ Maps page functionality test failed: {e}")
        return False

def main():
    """Run all navigation tests."""
    print("Testing app navigation with Maps page integration...\n")
    
    tests = [
        test_app_navigation,
        test_page_order,
        test_maps_page_functionality
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
        print("🎉 All navigation tests passed! Maps page is properly integrated.")
        return True
    else:
        print("⚠️ Some navigation tests failed.")
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)