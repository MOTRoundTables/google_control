# Google Maps Link Monitoring System - Setup Instructions

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
venv\Scripts\activate
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
**Last Updated:** 2025-10-06

For technical documentation, see:
- `components/control/methodology.md` - Control validation methodology
- `components/aggregation/methodology.md` - Data aggregation methodology
- `test_data/*/README.md` - Data format requirements
