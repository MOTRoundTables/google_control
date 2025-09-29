#!/usr/bin/env python3
"""
Google Maps Link Monitoring System - Setup Script
=================================================

Complete setup and installation script for new users.
Handles Python environment, dependencies, and initial configuration.

Usage:
    python setup.py          # Full setup
    python setup.py --check  # Check current installation
    python setup.py --test   # Run basic tests
"""

import sys
import os
import subprocess
from pathlib import Path
import platform
import venv
import shutil

# Version requirements
PYTHON_MIN_VERSION = (3, 8)
RECOMMENDED_PYTHON = (3, 11)

def print_header():
    """Print setup header"""
    print("=" * 60)
    print("Google Maps Link Monitoring System Setup")
    print("=" * 60)
    print()

def check_python_version():
    """Check Python version compatibility"""
    current_version = sys.version_info[:2]

    print(f"Python Version: {sys.version}")

    if current_version < PYTHON_MIN_VERSION:
        print(f"ERROR: Python {PYTHON_MIN_VERSION[0]}.{PYTHON_MIN_VERSION[1]}+ required")
        print(f"   Current version: {current_version[0]}.{current_version[1]}")
        print(f"   Please upgrade Python from: https://www.python.org/downloads/")
        return False

    if current_version < RECOMMENDED_PYTHON:
        print(f"WARNING: Python {RECOMMENDED_PYTHON[0]}.{RECOMMENDED_PYTHON[1]}+ recommended")
        print(f"   Current version: {current_version[0]}.{current_version[1]}")
    else:
        print("Python version compatible")

    print()
    return True

def check_system_requirements():
    """Check system-specific requirements"""
    print("System Information:")
    print(f"   Platform: {platform.system()} {platform.release()}")
    print(f"   Architecture: {platform.machine()}")

    # Check for potential GDAL issues on Windows
    if platform.system() == "Windows":
        print("\nNext Steps: Windows-specific notes:")
        print("   - GDAL binaries may be required for geospatial operations")
        print("   - Consider using Anaconda/Miniconda for easier geo library management")
        print("   - Alternative: Install from https://www.lfd.uci.edu/~gohlke/pythonlibs/")

    print()

def install_requirements():
    """Install required packages"""
    print("Installing Dependencies...")

    requirements_file = Path(__file__).parent / "requirements.txt"

    if not requirements_file.exists():
        print("ERROR: requirements.txt not found")
        return False

    try:
        # Upgrade pip first
        print("   Upgrading pip...")
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
                      check=True, capture_output=True)

        # Install requirements
        print("   Installing packages from requirements.txt...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
            check=True,
            capture_output=True,
            text=True
        )

        print("SUCCESS: Dependencies installed successfully")
        return True

    except subprocess.CalledProcessError as e:
        print(f"ERROR: Installing dependencies failed:")
        print(f"   {e.stderr}")
        print("\nTroubleshooting:")
        print("   1. Try: pip install --upgrade pip")
        print("   2. For Windows GDAL issues, try: conda install -c conda-forge gdal")
        print("   3. Or install pre-compiled wheels from: https://www.lfd.uci.edu/~gohlke/pythonlibs/")
        return False

def verify_installation():
    """Verify key packages are installed correctly"""
    print("Verifying Installation...")

    critical_packages = [
        "streamlit",
        "streamlit_option_menu",
        "pandas",
        "geopandas",
        "folium",
        "polyline",
        "chardet"
    ]

    failed_packages = []

    for package in critical_packages:
        try:
            __import__(package)
            print(f"   OK: {package}")
        except ImportError:
            print(f"   FAILED: {package}")
            failed_packages.append(package)

    if failed_packages:
        print(f"\nERROR: {len(failed_packages)} packages failed to import:")
        for pkg in failed_packages:
            print(f"   - {pkg}")
        print("\nTry manual installation:")
        for pkg in failed_packages:
            print(f"   pip install {pkg}")
        return False

    print("SUCCESS: All critical packages verified")
    return True

def create_directories():
    """Create necessary directories"""
    print("Creating Directory Structure...")

    directories = [
        "output",
        "output/test_outputs",
        "output/debug_outputs",
        "control_output",
        "logs"
    ]

    for directory in directories:
        dir_path = Path(directory)
        dir_path.mkdir(exist_ok=True)
        print(f"   SUCCESS: {directory}")

    print("SUCCESS: Directory structure created")
    print()

def check_test_data():
    """Check if test data is available"""
    print("Checking Test Data...")

    test_data_dir = Path("test_data")

    if test_data_dir.exists():
        csv_files = list(test_data_dir.rglob("*.csv"))
        shp_files = list(test_data_dir.rglob("*.shp"))

        print(f"   SUCCESS: Test data directory found")
        print(f"   CSV files: {len(csv_files)}")
        print(f"   Shapefiles: {len(shp_files)}")

        if csv_files and shp_files:
            print("   SUCCESS: Sample data available for testing")
        else:
            print("   WARNING: Limited test data available")
    else:
        print("   WARNING: No test data directory found")
        print("   You'll need to provide your own CSV and shapefile data")

    print()

def run_basic_test():
    """Run basic functionality test"""
    print("Running Basic Tests...")

    try:
        # Test streamlit import
        import streamlit as st
        print("   SUCCESS: Streamlit import")

        # Test geospatial libraries
        import geopandas as gpd
        import folium
        print("   SUCCESS: Geospatial libraries")

        # Test data processing
        import pandas as pd
        import numpy as np
        print("   SUCCESS: Data processing libraries")

        # Test component imports
        from components.control.page import control_page
        from components.processing.pipeline import run_pipeline
        from components.maps.maps_page import render_maps_page
        print("   SUCCESS: Application components")

        print("SUCCESS: Basic functionality test passed")
        return True

    except Exception as e:
        print(f"ERROR: Basic test failed: {e}")
        return False

def display_next_steps():
    """Display next steps for the user"""
    print("Setup Complete!")
    print("\nNext Steps:")
    print("   1. Run the application:")
    print("      streamlit run app.py")
    print()
    print("   2. Open your browser to:")
    print("      http://localhost:8501")
    print()
    print("   3. Upload your CSV and shapefile data")
    print()
    print("Documentation:")
    print("   - README.md: Getting started guide")
    print("   - components/control/methodology.md: Technical details")
    print()
    print("Support:")
    print("   - Check logs/ directory for error details")
    print("   - Run: python setup.py --check")
    print()

def main():
    """Main setup function"""
    import argparse

    parser = argparse.ArgumentParser(description="Setup Google Maps Link Monitoring System")
    parser.add_argument("--check", action="store_true", help="Check current installation")
    parser.add_argument("--test", action="store_true", help="Run basic tests only")

    args = parser.parse_args()

    print_header()

    # Check Python version
    if not check_python_version():
        sys.exit(1)

    # Check system requirements
    check_system_requirements()

    if args.check:
        # Check mode - verify installation
        verify_installation()
        check_test_data()
        run_basic_test()
        return

    if args.test:
        # Test mode - run tests only
        run_basic_test()
        return

    # Full setup mode
    print("Starting Full Setup...")
    print()

    # Install requirements
    if not install_requirements():
        print("\nERROR: Setup failed at dependency installation")
        sys.exit(1)

    print()

    # Verify installation
    if not verify_installation():
        print("\nERROR: Setup failed at verification")
        sys.exit(1)

    print()

    # Create directories
    create_directories()

    # Check test data
    check_test_data()

    # Run basic test
    if not run_basic_test():
        print("\nWARNING: Setup completed with warnings")
        print("   Application may work but some features might be limited")

    print()
    display_next_steps()

if __name__ == "__main__":
    main()