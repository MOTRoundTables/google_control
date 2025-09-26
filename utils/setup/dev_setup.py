#!/usr/bin/env python3
"""
Development setup script for Maps Link Monitoring Application
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        return False

def main():
    """Main setup function"""
    print("🚀 Setting up Maps Link Monitoring Application for development")
    print("=" * 60)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Install dependencies
    if not run_command("pip install -r requirements.txt", "Installing dependencies"):
        print("⚠️  Dependency installation failed. Please install manually.")
    
    # Generate test data if not exists
    if not os.path.exists("data_test_small.csv"):
        print("📊 Generating test data...")
        if not run_command("python populate_test_data.py", "Generating test data"):
            print("⚠️  Test data generation failed")
    else:
        print("✅ Test data already exists")
    
    # Verify test data
    if not run_command("python verify_test_data.py", "Verifying test data integrity"):
        print("⚠️  Test data verification failed")
    
    # Run basic tests
    if not run_command("python test_quality_simple.py", "Running basic tests"):
        print("⚠️  Basic tests failed")
    
    # Show summary
    if not run_command("python test_data_summary.py", "Displaying data summary"):
        print("⚠️  Could not display data summary")
    
    print("\n" + "=" * 60)
    print("🎉 Development setup complete!")
    print("\nNext steps:")
    print("1. Run 'python app.py' to start the application")
    print("2. Run 'python test_integration.py' for integration tests")
    print("3. Check 'README.md' for detailed usage instructions")
    print("4. Review 'README_test_data.md' for test data documentation")

if __name__ == "__main__":
    main()