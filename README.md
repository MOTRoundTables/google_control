# Google Maps Link Monitoring System

A comprehensive traffic monitoring and analysis system that processes Google Maps link data and provides interactive visualizations for spatial and temporal analysis.

## 🎯 Overview

This system processes large-scale CSV datasets from Google Maps traffic monitoring and provides three specialized components:

1. **🔍 Dataset Control & Validation**: Validate Google Maps polyline data against reference shapefiles using geometric similarity analysis
2. **⚙️ Data Processing Pipeline**: Process millions of CSV records with timezone-aware analysis and quality reporting
3. **🗺️ Interactive Maps**: Two specialized map visualizations for hourly and weekly traffic pattern analysis

## ✨ Key Features

### Dataset Control & Validation
- **Polyline Validation**: Geometric similarity testing using Hausdorff distance, length ratios, and coverage analysis
- **Configuration-Based Testing**: Individual route assessment with transparent result metrics
- **Data Completeness Analysis**: Auto-detect missing observations with Code 94/95 gap analysis
- **Spatial Visualization**: Failed observations shapefile with mixed geometry sources

### Data Processing Pipeline
- **Large Dataset Support**: Process millions of rows with chunked reading and memory optimization
- **Timezone Intelligence**: Israeli timezone handling with DST transitions and holiday detection
- **Quality Reporting**: Comprehensive data validation with Hebrew encoding support
- **Performance Monitoring**: Real-time processing metrics and error tracking

### Interactive Maps
- **Map A - Hourly Analysis**: Multi-date picker with hour-specific traffic visualization
- **Map B - Weekly Patterns**: Weekly aggregation showing temporal traffic patterns
- **Advanced Filtering**: Length, speed, time filters with above/below/between operators
- **Export Capabilities**: GeoJSON, Shapefile, CSV, PNG exports with QGIS compatibility

## 🚀 Quick Start

### 1. Automated Setup (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd google_agg

# Run automated setup (installs everything)
python setup.py

# Launch the application
streamlit run app.py
```

**Performance Tip**: Install optional dependency `pyogrio` (>=0.7) to speed up shapefile export. The control module auto-detects it and falls back to GeoPandas when it is missing.

### 2. Manual Installation

```bash
# Install Python 3.8+ (3.11+ recommended)
# Install dependencies
pip install -r requirements.txt

# Create directories
mkdir -p output/control output/aggregation logs

# Run the application
streamlit run app.py
```

### 3. Verification

```bash
# Check installation
python setup.py --check

# Run basic tests
python setup.py --test
```

## 📁 Project Structure

```
google_agg/
├── app.py                          # Main Streamlit application
├── setup.py                       # Automated setup script
├── requirements.txt                # Python dependencies
├── package_setup.py               # Package installation config
│
├── components/                     # Modular component architecture
│   ├── control/                   # Dataset Control & Validation
│   │   ├── page.py                # UI and validation pipeline
│   │   ├── validator.py           # Geometric validation engine
│   │   ├── report.py              # Reporting and aggregation
│   │   └── methodology.md         # Technical documentation
│   ├── aggregation/               # Data Aggregation Pipeline
│   │   ├── pipeline.py            # Core CSV processing
│   │   ├── quality.py             # Data quality analysis
│   │   └── optimizer.py           # Memory optimization
│   └── maps/                      # Interactive Maps
│       ├── maps_page.py           # Maps interface
│       ├── map_a_hourly.py        # Hourly traffic analysis
│       ├── map_b_weekly.py        # Weekly pattern analysis
│       └── spatial_data.py        # Shapefile management
│
├── utils/                         # Utilities and support tools
│   ├── debug/                     # Debug scripts
│   ├── fixes/                     # Data fixing utilities
│   ├── test_runners/              # Test automation
│   └── setup/                     # Setup utilities
│
├── test_data/                     # Sample datasets
│   ├── control/                   # Control test cases and scenarios
│   └── aggregation/               # Map test data and shapefiles
├── output/                        # All system outputs
│   ├── control/                   # Control validation outputs (timestamped folders)
│   └── aggregation/               # Aggregation outputs (organized by source)
└── docs/                          # Documentation
```

## 📖 Usage Guide

### 🌐 Web Interface

After running `streamlit run app.py`, open your browser to `http://localhost:8501`

The application provides three main components:

#### 🔍 Dataset Control & Validation
**Purpose**: Validate Google Maps polyline data against reference shapefiles

**Required Files**:
- CSV file with Google Maps data (Name, Polyline, Timestamp columns)
- Reference shapefile (ZIP package recommended)

**Key Features**:
- **Geometric Testing**: Hausdorff distance, length similarity, coverage analysis
- **Auto-Date Detection**: Automatically detects analysis period from CSV timestamps
- **Comprehensive Reporting**: Validation results, missing observations, failed observations
- **Spatial Visualization**: Interactive shapefiles with mixed geometry sources

**Output Files**:
```
output/control/DD_MM_YY_HH_MM/      # Timestamped validation outputs
├── validated_data.csv              # All validation results
├── failed_observations.csv         # Combined failure analysis
├── missing_observations.csv        # Code 94 - temporal gaps
├── best_valid_observations.csv     # Best route for each link
├── link_report.csv                 # Link-level summary
├── link_report_shapefile.zip       # Complete spatial package
└── failed_observations_shapefile.zip # Failed observations spatial
```

#### ⚙️ Data Aggregation Pipeline
**Purpose**: Process large CSV datasets with quality analysis

**Features**:
- **Timezone-Aware Processing**: Israeli timezone with DST handling
- **Data Quality Metrics**: Validation, outlier detection, duplicate handling
- **Holiday Integration**: Israeli holidays with custom holiday support
- **Performance Monitoring**: Real-time processing statistics

**Output Files**:
```
output/aggregation/from_control_DD_MM_YY_HH_MM/  # Source-traced aggregation outputs
├── hourly_agg.csv                  # Hourly aggregated data
├── weekly_hourly_profile.csv       # Weekly pattern analysis
├── data_quality_report.csv         # Quality metrics
└── processing_summary.json         # Processing statistics
```

#### 🗺️ Interactive Maps
**Purpose**: Spatial and temporal traffic pattern visualization

**Map A - Hourly Analysis**:
- Multi-date selection with hour-specific filtering
- Duration vs Speed visualization toggle
- Advanced filtering (length, speed, time ranges)
- Interactive tooltips and click-through analysis

**Map B - Weekly Patterns**:
- Weekly hourly aggregation across all data
- Mean/median aggregation options
- Context display showing date span and coverage

**Common Features**:
- **Symbology System**: Sequential color palettes with multiple classification methods
- **Spatial Selection**: Box and lasso selection tools
- **Export Options**: GeoJSON, Shapefile, CSV, PNG, QGIS compatibility
- **Performance**: Zoom-dependent simplification for large networks

### 📊 Data Requirements

#### CSV Data Format
Your CSV should include these columns:

| Column | Type | Description | Required |
|--------|------|-------------|----------|
| Name | String | Link identifier (e.g., "s_123-456") | ✅ |
| Timestamp | DateTime | Observation time | ✅ |
| Polyline | String | Google Maps encoded polyline | ✅ |
| Duration | Float | Travel time in seconds | ✅ |
| Distance | Float | Distance in meters | ✅ |
| Speed | Float | Speed in km/h | ✅ |
| RouteAlternative | Integer | Route alternative number | ⚠️ |
| SegmentID | String | Segment identifier | ⚠️ |

#### Shapefile Format
Reference shapefile should contain:

| Field | Type | Description |
|-------|------|-------------|
| From | String/Integer | Origin node ID |
| To | String/Integer | Destination node ID |
| Geometry | LineString | Reference route geometry |

**Join Rule**: CSV links are joined as `Name = "s_" + From + "-" + To`

### 🛠️ Advanced Usage

#### Command Line Options
```bash
# Full setup with verification
python setup.py

# Check current installation
python setup.py --check

# Run component tests
python setup.py --test

# Development testing
python utils/test_runners/test_validation_minimal.py
python utils/debug/debug_validation.py
```

#### Environment Configuration
Set these environment variables for customization:

```bash
# Optional: Custom data paths
export DATA_PATH="/path/to/your/data"

# Optional: Performance tuning
export CHUNK_SIZE=50000
export MAX_MEMORY_MB=4096

# Optional: Logging
export LOG_LEVEL=INFO
```

### 🔧 Troubleshooting

#### Common Issues

**1. GDAL Installation Issues (Windows)**
```bash
# Option 1: Use conda
conda install -c conda-forge gdal

# Option 2: Pre-compiled wheels
# Download from: https://www.lfd.uci.edu/~gohlke/pythonlibs/
pip install GDAL-x.x.x-cpxx-cpxxm-win_amd64.whl
```

**2. Memory Issues with Large Files**
- Reduce chunk size in processing settings
- Use the data processing component to pre-process large files
- Consider splitting very large CSV files

**3. Hebrew Encoding Issues**
- The system auto-detects Hebrew encoding (cp1255)
- Output files use UTF-8 with BOM
- Check the encoding detection in processing logs

**4. Shapefile Issues**
- Use ZIP packages containing all components (.shp, .shx, .dbf, .prj)
- Ensure CRS is defined (automatically reprojected to EPSG:2039)
- Check that From/To fields create valid link IDs

#### Getting Help

1. **Check Installation**: `python setup.py --check`
2. **Review Logs**: Check `logs/` directory for detailed error messages
3. **Test Components**: `python setup.py --test`
4. **Documentation**: Read `components/control/methodology.md` for technical details

### 📈 Performance Tips

- **Large Datasets**: Use chunked processing with appropriate memory limits
- **Map Performance**: Enable zoom-dependent simplification for networks >10k links
- **Validation Speed**: Use Hausdorff-only testing for initial analysis, add length/coverage for detailed validation
- **Memory Management**: Process in batches if dealing with >1M records

## 🧪 Test Data

The system includes comprehensive test data for development and validation:

### Available Test Datasets

```
test_data/
├── control/                        # Dataset Control test data
│   ├── cases/                      # Various test scenarios and edge cases
│   ├── original_test_data_full.csv # Small validation dataset
│   └── data.csv                    # Large test dataset (700k+ records)
└── aggregation/                    # Map and aggregation test data
    └── google_results_to_golan_17_8_25/
        └── *.shp                   # Reference shapefile package
```

### Creating Your Own Test Data

```bash
# Use utilities to generate test scenarios
python utils/test_runners/test_validation_minimal.py
python utils/debug/debug_validation.py
```

## 🔒 System Requirements

### Minimum Requirements
- **Python**: 3.8+ (3.11+ recommended)
- **RAM**: 4GB (8GB+ recommended for large datasets)
- **Storage**: 2GB free space
- **OS**: Windows 10+, macOS 10.15+, Linux

### Recommended Setup
- **Python**: 3.11+
- **RAM**: 16GB+ for processing >1M records
- **Storage**: 10GB+ for large datasets and outputs
- **Environment**: Anaconda/Miniconda for easier dependency management

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. **Fork the Repository**
2. **Create Feature Branch**: `git checkout -b feature/your-feature`
3. **Make Changes**: Follow existing code patterns
4. **Add Tests**: Include tests for new functionality
5. **Update Docs**: Update README and component documentation
6. **Test Everything**: Run `python setup.py --test`
7. **Submit PR**: Include detailed description

### Development Guidelines

- **Code Style**: Follow existing patterns and PEP 8
- **Testing**: All features must include comprehensive tests
- **Documentation**: Update methodology.md for technical changes
- **Performance**: Consider memory usage for large dataset scenarios

## 📜 License

This project is licensed under the MIT License. See the LICENSE file for details.

## 🆘 Support & Troubleshooting

### Quick Diagnostics
```bash
# Check everything
python setup.py --check

# Test core functionality
python setup.py --test

# View system info
python -c "import sys; print(sys.version); import platform; print(platform.system())"
```

### Common Solutions
1. **Installation Issues**: Try `conda install -c conda-forge gdal geopandas`
2. **Memory Errors**: Reduce chunk size in processing settings
3. **Encoding Issues**: System auto-handles Hebrew; check logs if issues persist
4. **Performance**: Enable chunked processing for datasets >100k records

### Getting Help
- **Documentation**: Check `components/control/methodology.md` for technical details
- **Error Logs**: Review `logs/` directory for detailed error information
- **Component Tests**: Run individual component tests to isolate issues

## 🏗️ Architecture

The system uses a modular component architecture:

- **🔍 Control Component**: Standalone validation with comprehensive reporting
- **⚙️ Processing Component**: Scalable data pipeline with quality analysis
- **🗺️ Maps Component**: Interactive visualization with advanced filtering
- **🛠️ Utils**: Support utilities for debugging, testing, and setup

Each component can be used independently or as part of the integrated system.

## 📈 Version History

### Version 2.0.0 (Current)
- ✅ Complete modular architecture
- ✅ Dataset Control with Code 94/95 analysis
- ✅ Auto-date detection for completeness analysis
- ✅ Mixed-geometry shapefile generation
- ✅ Interactive maps with advanced filtering
- ✅ Comprehensive setup system
- ✅ Hebrew encoding support
- ✅ Performance optimizations (45x faster CRS transformations)

### Version 1.0.0
- Core processing pipeline
- Basic validation functionality
- Map visualization foundations