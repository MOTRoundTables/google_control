"""
Installation Verification Script for Google Maps Link Monitoring System

This script verifies that all dependencies are correctly installed and the system
is ready to use. Run this after installing requirements.txt.

Usage:
    python verify_installation.py
"""

import sys
from pathlib import Path
from datetime import datetime

class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(80)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}\n")

def print_section(text):
    """Print a section header"""
    print(f"\n{Colors.BOLD}{text}{Colors.RESET}")
    print("-" * len(text))

def print_success(text):
    """Print success message"""
    print(f"{Colors.GREEN}[OK]{Colors.RESET} {text}")

def print_error(text):
    """Print error message"""
    print(f"{Colors.RED}[ERROR]{Colors.RESET} {text}")

def print_warning(text):
    """Print warning message"""
    print(f"{Colors.YELLOW}[WARNING]{Colors.RESET} {text}")

def print_info(text):
    """Print info message"""
    print(f"{Colors.BLUE}[INFO]{Colors.RESET} {text}")

def check_python_version():
    """Check Python version compatibility"""
    print_section("1. Python Version Check")

    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"

    print_info(f"Python version: {version_str}")

    if version.major == 3 and version.minor >= 9:
        print_success(f"Python {version_str} is compatible (>= 3.9 required)")
        return True
    else:
        print_error(f"Python {version_str} is not compatible. Python 3.9+ required.")
        print_info("Please upgrade Python: https://www.python.org/downloads/")
        return False

def check_core_imports():
    """Check if core libraries can be imported"""
    print_section("2. Core Dependencies Check")

    dependencies = [
        ("streamlit", "Streamlit web framework"),
        ("pandas", "Data manipulation library"),
        ("numpy", "Numerical computing library"),
        ("geopandas", "Geospatial data library"),
        ("folium", "Interactive maps library"),
        ("shapely", "Geometric operations library"),
        ("pyproj", "Coordinate transformations"),
        ("fiona", "Geospatial file I/O"),
        ("rtree", "Spatial indexing"),
        ("holidays", "Holiday detection"),
        ("chardet", "Character encoding detection"),
        ("polyline", "Google Maps polyline codec"),
    ]

    failed_imports = []
    successful_imports = []

    for module_name, description in dependencies:
        try:
            __import__(module_name)
            version = None
            try:
                module = sys.modules[module_name]
                version = getattr(module, '__version__', None)
            except:
                pass

            version_str = f"v{version}" if version else ""
            print_success(f"{module_name:<20} {version_str:<15} - {description}")
            successful_imports.append(module_name)
        except ImportError as e:
            print_error(f"{module_name:<20} {'NOT FOUND':<15} - {description}")
            failed_imports.append((module_name, str(e)))

    print()
    if failed_imports:
        print_error(f"Failed to import {len(failed_imports)} module(s)")
        print_info("Run: pip install -r requirements.txt")
        return False
    else:
        print_success(f"All {len(successful_imports)} core dependencies imported successfully")
        return True

def check_optional_imports():
    """Check optional dependencies"""
    print_section("3. Optional Dependencies Check")

    optional_deps = [
        ("pytest", "Testing framework"),
        ("memory_profiler", "Memory profiling"),
        ("matplotlib", "Plotting library"),
        ("plotly", "Interactive plotting"),
        ("streamlit_folium", "Folium integration for Streamlit"),
        ("streamlit_option_menu", "Enhanced navigation menu"),
    ]

    missing_optional = []

    for module_name, description in optional_deps:
        try:
            __import__(module_name)
            print_success(f"{module_name:<25} - {description}")
        except ImportError:
            print_warning(f"{module_name:<25} - {description} (optional, not critical)")
            missing_optional.append(module_name)

    if missing_optional:
        print()
        print_info(f"{len(missing_optional)} optional package(s) not installed (this is OK)")

    return True

def check_project_structure():
    """Verify project directory structure"""
    print_section("4. Project Structure Check")

    required_paths = [
        ("app.py", "Main application file"),
        ("requirements.txt", "Dependencies list"),
        ("components/", "Application components"),
        ("components/control/", "Control validation module"),
        ("components/aggregation/", "Data aggregation module"),
        ("components/maps/", "Maps visualization module"),
        ("test_data/", "Sample test data"),
        ("tests/", "Test suite"),
    ]

    missing_paths = []

    for path_str, description in required_paths:
        path = Path(path_str)
        if path.exists():
            if path.is_file():
                size_kb = path.stat().st_size / 1024
                print_success(f"{path_str:<30} ({size_kb:.1f} KB) - {description}")
            else:
                print_success(f"{path_str:<30} (directory) - {description}")
        else:
            print_error(f"{path_str:<30} NOT FOUND - {description}")
            missing_paths.append(path_str)

    print()
    if missing_paths:
        print_error(f"{len(missing_paths)} required path(s) missing")
        print_info("Make sure you extracted the ZIP file completely")
        return False
    else:
        print_success("All required project files and directories present")
        return True

def check_test_data():
    """Check if test data is available"""
    print_section("5. Test Data Availability")

    test_files = [
        "test_data/control/cases/case_all_valid.csv",
        "test_data/aggregation/data_test_small.csv",
        "test_data/aggregation/google_results_to_golan_17_8_25.zip",
    ]

    available = 0

    for test_file in test_files:
        path = Path(test_file)
        if path.exists():
            size_kb = path.stat().st_size / 1024
            print_success(f"{test_file} ({size_kb:.1f} KB)")
            available += 1
        else:
            print_warning(f"{test_file} (not found)")

    print()
    if available > 0:
        print_success(f"{available}/{len(test_files)} test files available")
        return True
    else:
        print_warning("No test data files found (optional)")
        return True

def check_streamlit_config():
    """Check Streamlit configuration"""
    print_section("6. Streamlit Configuration")

    config_file = Path(".streamlit/config.toml")

    if config_file.exists():
        print_success(f"Streamlit config found: {config_file}")

        # Try to read and validate config
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if '[theme]' in content:
                    print_info("  Custom theme configuration detected")
                if '[server]' in content:
                    print_info("  Server configuration detected")
            return True
        except Exception as e:
            print_warning(f"  Could not read config: {e}")
            return True
    else:
        print_warning("No custom Streamlit config found (will use defaults)")
        return True

def run_quick_functionality_test():
    """Run a quick functionality test"""
    print_section("7. Quick Functionality Test")

    try:
        print_info("Testing data processing functions...")

        # Test imports from components
        from components.aggregation.pipeline import validate_csv_columns, normalize_column_names
        print_success("  Aggregation pipeline functions imported")

        from components.control.validator import ValidationParameters
        print_success("  Control validator imported")

        from components.maps.spatial_data import CoordinateSystemManager
        print_success("  Maps spatial data functions imported")

        # Test basic pandas/geopandas operations
        import pandas as pd
        import geopandas as gpd
        from shapely.geometry import Point

        df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
        gdf = gpd.GeoDataFrame(
            {'name': ['Point1', 'Point2']},
            geometry=[Point(0, 0), Point(1, 1)],
            crs='EPSG:4326'
        )

        print_success("  Pandas and GeoPandas basic operations work")

        # Test polyline encoding/decoding
        import polyline
        coords = [(38.5, -120.2), (40.7, -120.95), (43.252, -126.453)]
        encoded = polyline.encode(coords)
        decoded = polyline.decode(encoded)

        print_success("  Polyline encoding/decoding works")

        print()
        print_success("All functionality tests passed")
        return True

    except Exception as e:
        print_error(f"Functionality test failed: {e}")
        print_info("This might indicate missing dependencies or import errors")
        return False

def check_write_permissions():
    """Check if we can write to output directories"""
    print_section("8. File System Permissions")

    test_dirs = ['output', 'output/control', 'output/aggregation']

    all_ok = True

    for dir_name in test_dirs:
        dir_path = Path(dir_name)

        try:
            # Create directory if it doesn't exist
            dir_path.mkdir(parents=True, exist_ok=True)

            # Try to write a test file
            test_file = dir_path / '.write_test'
            test_file.write_text('test', encoding='utf-8')
            test_file.unlink()

            print_success(f"{dir_name}/ - Read/write OK")

        except Exception as e:
            print_error(f"{dir_name}/ - Cannot write: {e}")
            all_ok = False

    print()
    if all_ok:
        print_success("All output directories are writable")
    else:
        print_error("Some directories are not writable - check permissions")

    return all_ok

def generate_report(results):
    """Generate a summary report"""
    print_header("Installation Verification Report")

    total_checks = len(results)
    passed_checks = sum(1 for r in results.values() if r)

    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python: {sys.version}")
    print(f"Platform: {sys.platform}")
    print()

    print(f"Total Checks: {total_checks}")
    print(f"Passed: {Colors.GREEN}{passed_checks}{Colors.RESET}")
    print(f"Failed: {Colors.RED}{total_checks - passed_checks}{Colors.RESET}")
    print()

    # Detailed results
    print("Detailed Results:")
    for check_name, passed in results.items():
        status = f"{Colors.GREEN}PASS{Colors.RESET}" if passed else f"{Colors.RED}FAIL{Colors.RESET}"
        print(f"  [{status}] {check_name}")

    print()

    if all(results.values()):
        print_success("=" * 80)
        print_success("All checks passed! Your installation is ready to use.".center(80))
        print_success("=" * 80)
        print()
        print(f"{Colors.BOLD}Next Steps:{Colors.RESET}")
        print("  1. Run the application: streamlit run app.py")
        print("  2. Open your browser to: http://localhost:8501")
        print("  3. Navigate to 'Dataset Control' or 'Aggregation' to get started")
        print()
        print(f"{Colors.BOLD}Quick Test:{Colors.RESET}")
        print("  - Use test data in test_data/control/ for quick validation tests")
        print("  - Use test_data/aggregation/ for aggregation pipeline tests")
        print()
        return True
    else:
        print_error("=" * 80)
        print_error("Some checks failed. Please review errors above.".center(80))
        print_error("=" * 80)
        print()
        print(f"{Colors.BOLD}Common Solutions:{Colors.RESET}")
        print("  1. Install missing dependencies: pip install -r requirements.txt")
        print("  2. Upgrade pip: python -m pip install --upgrade pip")
        print("  3. For GDAL errors on Windows, try:")
        print("     - conda install -c conda-forge geopandas")
        print("     - Or download from: https://www.lfd.uci.edu/~gohlke/pythonlibs/")
        print()
        return False

def main():
    """Main verification function"""
    print_header("Google Maps Link Monitoring System - Installation Verification")

    print(f"{Colors.BOLD}This script will verify that your installation is complete and working.{Colors.RESET}")
    print()

    # Run all checks
    results = {}

    results["Python Version"] = check_python_version()
    results["Core Dependencies"] = check_core_imports()
    results["Optional Dependencies"] = check_optional_imports()
    results["Project Structure"] = check_project_structure()
    results["Test Data"] = check_test_data()
    results["Streamlit Config"] = check_streamlit_config()
    results["Functionality"] = run_quick_functionality_test()
    results["File Permissions"] = check_write_permissions()

    # Generate summary report
    success = generate_report(results)

    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print_warning("Verification interrupted by user")
        sys.exit(1)
    except Exception as e:
        print()
        print_error(f"Unexpected error during verification: {e}")
        import traceback
        print()
        print("Traceback:")
        print(traceback.format_exc())
        sys.exit(1)
