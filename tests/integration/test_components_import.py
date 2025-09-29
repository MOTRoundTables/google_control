"""
Test that all component imports are working correctly after refactoring.
"""

import sys

def test_control_component():
    """Test Control component imports"""
    try:
        from components.control import control_page
        from components.control.validator import ValidationParameters
        from components.control.report import generate_link_report
        print("SUCCESS: Control component imports successful")
        return True
    except ImportError as e:
        print(f"ERROR: Control component import failed: {e}")
        return False

def test_aggregation_component():
    """Test Processing component imports"""
    try:
        from components.aggregation import run_pipeline
        from components.aggregation.quality import QualityReportingInterface
        from components.aggregation.optimizer import PerformanceOptimizer
        print("SUCCESS: Processing component imports successful")
        return True
    except ImportError as e:
        print(f"ERROR: Processing component import failed: {e}")
        return False

def test_maps_component():
    """Test Maps component imports"""
    try:
        from components.maps import render_maps_page
        from components.maps.map_a_hourly import HourlyMapInterface
        from components.maps.map_b_weekly import WeeklyMapInterface
        from components.maps.spatial_data import SpatialDataManager
        print("SUCCESS: Maps component imports successful")
        return True
    except ImportError as e:
        print(f"ERROR: Maps component import failed: {e}")
        return False

def test_app_imports():
    """Test app.py imports"""
    try:
        # Test that app.py can import from components
        exec("""
from components.aggregation.pipeline import run_pipeline
from components.maps import render_maps_page
from components.control import control_page
""")
        print("SUCCESS: App.py imports successful")
        return True
    except ImportError as e:
        print(f"ERROR: App.py import failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing component imports after refactoring...")
    print("=" * 50)
    
    results = []
    results.append(test_control_component())
    results.append(test_aggregation_component())
    results.append(test_maps_component())
    results.append(test_app_imports())
    
    print()
    if all(results):
        print("SUCCESS: All component imports successful!")
        sys.exit(0)
    else:
        print("ERROR: Some component imports failed")
        sys.exit(1)
