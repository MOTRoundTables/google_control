"""
Create a clean distribution package for the Google Maps Link Monitoring System.
This script creates a ZIP file containing only git-tracked files (no user data, output, or temporary files).
"""

import zipfile
import subprocess
from pathlib import Path
from datetime import datetime

def get_git_tracked_files():
    """Get list of all files tracked by git."""
    try:
        result = subprocess.run(
            ['git', 'ls-files'],
            capture_output=True,
            text=True,
            check=True
        )
        files = [line.strip() for line in result.stdout.split('\n') if line.strip()]
        return files
    except subprocess.CalledProcessError as e:
        print(f"Error getting git files: {e}")
        return []

def create_distribution_zip():
    """Create distribution ZIP with git-tracked files only."""

    # Get current directory
    root_dir = Path.cwd()

    # Create output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"google_maps_monitoring_system_{timestamp}.zip"
    zip_path = root_dir / zip_filename

    print(f"Creating distribution package: {zip_filename}")
    print(f"Root directory: {root_dir}")
    print()

    # Get git-tracked files
    git_files = get_git_tracked_files()

    if not git_files:
        print("ERROR: No git files found. Make sure you're in a git repository.")
        return None

    print(f"Found {len(git_files)} files tracked by git")
    print()

    # Create ZIP file
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
        for file_path in git_files:
            full_path = root_dir / file_path

            if not full_path.exists():
                print(f"Warning: File not found (skipping): {file_path}")
                continue

            # Add file to ZIP with relative path
            arcname = f"google_maps_monitoring/{file_path}"
            zipf.write(full_path, arcname)

            # Print progress for every 50 files
            if git_files.index(file_path) % 50 == 0:
                print(f"  Added {git_files.index(file_path) + 1}/{len(git_files)} files...")

    print()
    print(f"[OK] Distribution package created successfully!")
    print(f"File: {zip_path}")
    print(f"Size: {zip_path.stat().st_size / (1024*1024):.2f} MB")
    print()

    return zip_path

def create_setup_instructions():
    """Create setup instructions document."""

    instructions = """# Google Maps Link Monitoring System - Setup Instructions

## Quick Start Guide

### Prerequisites
- Python 3.9 or higher
- pip (Python package manager)
- Git (optional, for updates)

### Installation Steps

#### 1. Extract the Package
Extract the ZIP file to your desired location:
```
google_maps_monitoring/
├── app.py
├── components/
├── tests/
├── requirements.txt
└── ...
```

#### 2. Create Virtual Environment (Recommended)

**Windows:**
```bash
cd google_maps_monitoring
python -m venv venv
venv\\Scripts\\activate
```

**macOS/Linux:**
```bash
cd google_maps_monitoring
python3 -m venv venv
source venv/bin/activate
```

#### 3. Install Dependencies

**Standard Installation:**
```bash
pip install -r requirements.txt
```

**If you encounter GDAL/geospatial library errors on Windows:**
1. Install GDAL from: https://www.lfd.uci.edu/~gohlke/pythonlibs/
2. Or use Conda:
   ```bash
   conda create -n maps_env python=3.9
   conda activate maps_env
   conda install -c conda-forge geopandas folium streamlit
   pip install -r requirements.txt
   ```

#### 4. Verify Installation

Run the test suite to verify everything is working:
```bash
pytest tests/ -v
```

If you don't want to run all tests (takes time), run a quick smoke test:
```bash
python -c "import streamlit; import geopandas; import folium; print('✅ All imports successful!')"
```

#### 5. Launch the Application

```bash
streamlit run app.py
```

The application will open in your default web browser at http://localhost:8501

### First-Time Setup

1. **Prepare Your Data:**
   - CSV file with Google Maps monitoring data
   - Reference shapefile (as ZIP or individual .shp file)

2. **Test with Sample Data:**
   - Sample data is available in `test_data/` folder
   - Use `test_data/control/cases/case_all_valid.csv` for quick testing
   - Use `test_data/aggregation/data_test_small.csv` for aggregation testing

3. **Navigate the Application:**
   - **Dataset Control**: Validate polyline data against reference shapefiles
   - **Aggregation**: Process and aggregate large CSV datasets
   - **Aggregated Maps**: Visualize traffic patterns on interactive maps

### Directory Structure

After running the application, you'll see:
```
google_maps_monitoring/
├── output/
│   ├── control/          # Validation outputs (timestamped folders)
│   │   └── DD_MM_YY_HH_MM/
│   └── aggregation/      # Aggregation outputs (timestamped folders)
│       └── from_control_DD_MM_YY_HH_MM/
├── test_data/            # Sample datasets
├── components/           # Application modules
└── tests/                # Test suite
```

### Troubleshooting

#### Import Errors
- **Error:** `ModuleNotFoundError: No module named 'geopandas'`
  - **Solution:** Run `pip install -r requirements.txt` again

#### GDAL/Fiona Errors (Windows)
- **Error:** `ImportError: DLL load failed`
  - **Solution 1:** Install from Conda: `conda install -c conda-forge geopandas`
  - **Solution 2:** Download GDAL wheel from Gohlke's site and install manually

#### Streamlit Won't Start
- **Error:** `streamlit: command not found`
  - **Solution:** Make sure virtual environment is activated
  - **Solution:** Try `python -m streamlit run app.py`

#### Port Already in Use
- **Error:** `Port 8501 is already in use`
  - **Solution:** Use a different port: `streamlit run app.py --server.port 8502`

#### Hebrew Text Corruption
- The system automatically handles Hebrew encoding
- If you see corrupted text, check that CSV files are saved with UTF-8 or Windows-1255 encoding

### Performance Tips

1. **Large Files:** Adjust chunk size in Aggregation settings (default: 50,000)
2. **Memory Issues:** Process data in smaller date ranges
3. **Slow Maps:** Use filtering to reduce displayed data points

### Getting Help

- Check methodology documentation in the app (Methodology pages)
- Review `test_data/*/README.md` for data format requirements
- Run tests to verify your environment: `pytest tests/ -v`

### System Requirements

**Minimum:**
- 4 GB RAM
- 2 GB free disk space
- Windows 10, macOS 10.14+, or Linux

**Recommended:**
- 8 GB RAM
- 5 GB free disk space
- SSD for better performance with large files

### Updates

To update the application:
1. Download the new ZIP file
2. Extract to a new folder
3. Copy your data files to the new installation
4. Reinstall dependencies: `pip install -r requirements.txt --upgrade`

---

## Advanced Configuration

### Streamlit Configuration

The application includes default Streamlit configuration in `.streamlit/config.toml`.
You can customize theme, server settings, and more.

### Validation Parameters

Default validation parameters can be adjusted in the Dataset Control page:
- Hausdorff distance threshold (default: 5.0m)
- Length ratio tolerance (default: 0.90-1.10)
- Coverage minimum (default: 85%)

### Map Symbology

Map visualization colors and classification can be configured through the Maps interface.

---

**Version:** 1.0
**Last Updated:** """ + datetime.now().strftime("%Y-%m-%d") + """

For technical documentation, see:
- `components/control/methodology.md` - Control validation methodology
- `components/aggregation/methodology.md` - Data aggregation methodology
- `test_data/*/README.md` - Data format requirements
"""

    setup_file = Path("SETUP_INSTRUCTIONS.md")
    setup_file.write_text(instructions, encoding='utf-8')
    print(f"[OK] Setup instructions created: {setup_file}")
    return setup_file

if __name__ == "__main__":
    print("=" * 80)
    print("Google Maps Link Monitoring System - Distribution Package Creator")
    print("=" * 80)
    print()

    # Create setup instructions
    setup_file = create_setup_instructions()

    # Create distribution ZIP
    zip_file = create_distribution_zip()

    if zip_file:
        print()
        print("=" * 80)
        print("Package Created Successfully!")
        print("=" * 80)
        print()
        print("Distribution Files:")
        print(f"   - {zip_file.name}")
        print(f"   - {setup_file.name}")
        print()
        print("Next Steps:")
        print("   1. Send the ZIP file to your recipient")
        print("   2. Include SETUP_INSTRUCTIONS.md with the ZIP")
        print("   3. They should follow the instructions to set up the environment")
        print()
        print("[OK] Ready for distribution!")
    else:
        print()
        print("[ERROR] Failed to create distribution package")
