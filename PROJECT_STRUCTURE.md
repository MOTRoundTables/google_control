# Google Maps Link Monitoring System - Project Structure

## Directory Organization

```
google_agg/
├── app.py                          # Main Streamlit application entry point
├── CLAUDE.md                       # Project documentation for Claude Code
├── README.md                       # Project overview and quick start
├── PROJECT_STRUCTURE.md            # This file - detailed folder structure
│
├── components/                     # Modular application components
│   ├── control/                    # Dataset control & validation
│   │   ├── page.py                 # Control validation UI
│   │   ├── validator.py            # Polyline validation logic
│   │   ├── report.py               # Reporting and shapefile generation
│   │   └── methodology.md          # Control validation methodology
│   │
│   ├── aggregation/                # Data aggregation pipeline
│   │   ├── pipeline.py             # Core aggregation engine
│   │   ├── quality.py              # Data quality analysis
│   │   ├── optimizer.py            # Performance optimization
│   │   ├── data_quality.py         # Quality metrics
│   │   └── methodology.md          # Aggregation methodology
│   │
│   └── maps/                       # Interactive map visualizations
│       ├── maps_page.py            # Maps UI integration
│       ├── map_a_hourly.py         # Hourly traffic map
│       ├── map_b_weekly.py         # Weekly pattern map
│       ├── spatial_data.py         # Shapefile loading (EPSG 2039)
│       ├── map_data.py             # Data joining & filtering
│       ├── map_renderer.py         # Folium map rendering
│       ├── symbology.py            # Color schemes & styling
│       ├── controls.py             # UI controls
│       ├── map_config.py           # Configuration management
│       ├── export_manager.py       # Export functionality
│       ├── kpi_engine.py           # KPI calculations
│       └── link_details_panel.py   # Interactive link details
│
├── tests/                          # Comprehensive test suite
│   ├── control/                    # Control component tests
│   ├── aggregation/                # Aggregation tests
│   ├── maps/                       # Maps tests
│   ├── integration/                # End-to-end tests
│   ├── app/                        # App UI tests
│   └── utils/                      # Utility tests
│
├── test_data/                      # Test datasets (gitignored)
│   ├── control/                    # Control validation test cases
│   └── aggregation/                # Aggregation test data
│       └── google_results_to_golan_17_8_25/  # Default shapefile location
│           └── google_results_to_golan_17_8_25.shp
│
├── distribution/                   # Distribution & setup tools
│   ├── create_distribution.py      # Create clean ZIP package
│   ├── verify_installation.py      # Installation verification
│   └── SETUP_INSTRUCTIONS.md       # Setup guide for new users
│
├── utils/                          # Utility scripts
│   ├── debug/                      # Debugging tools
│   ├── fixes/                      # Fix scripts
│   ├── test_runners/               # Test automation
│   └── setup/                      # Setup utilities
│
├── docs/                           # Project documentation
│
└── runs/                           # Output folder (gitignored)
    └── 1_10_25/                    # Run batch identifier
        └── output/
            ├── control/            # Control validation outputs
            │   ├── 05_10_25_16_36/ # Timestamped folder (DD_MM_YY_HH_MM)
            │   │   ├── validated_data.csv
            │   │   ├── link_report.csv
            │   │   ├── link_report_shapefile.zip
            │   │   ├── failed_observations.csv
            │   │   ├── failed_observations_shapefile.zip
            │   │   ├── failed_observations_unique_polylines_shapefile.zip
            │   │   ├── failed_observations_reference_shapefile.zip
            │   │   ├── best_valid_observations.csv
            │   │   ├── no_data_links.csv
            │   │   ├── missing_observations.csv (optional)
            │   │   └── performance_and_parameters_log.txt
            │   ├── 05_10_25_18_51/ # Another validation run
            │   └── ...
            │
            └── aggregation/        # Aggregation outputs
                ├── from_control_05_10_25_16_36/ # Linked to control run
                │   ├── hourly_agg.csv
                │   ├── weekly_hourly_profile.csv
                │   ├── quality_by_link.csv
                │   ├── processing_log.txt
                │   └── run_config.json
                ├── from_control_05_10_25_18_51/
                └── ...
```

## Output Folder Organization

### Control Validation Outputs (`runs/1_10_25/output/control/DD_MM_YY_HH_MM/`)

Each control validation run creates a timestamped folder containing:

**Core CSV files:**
- `validated_data.csv` - All observations with validation results
- `link_report.csv` - Per-link aggregated metrics
- `failed_observations.csv` - Only failed observations (codes 1-3)
- `best_valid_observations.csv` - Best route per timestamp
- `no_data_links.csv` - Links with zero observations

**Shapefiles (ZIP format):**
- `link_report_shapefile.zip` - Link report with reference geometries
- `failed_observations_shapefile.zip` - All failed obs with decoded polylines (one per observation)
- `failed_observations_unique_polylines_shapefile.zip` - Unique routes per link (deduplicated across timestamps)
- `failed_observations_reference_shapefile.zip` - Time-period aggregated failures on reference geometries
- `missing_observations_shapefile.zip` - Missing observations (when completeness enabled)
- `no_data_links_shapefile.zip` - No-data links

**Metadata:**
- `performance_and_parameters_log.txt` - Run configuration and performance metrics

### Aggregation Outputs (`runs/1_10_25/output/aggregation/from_control_DD_MM_YY_HH_MM/`)

Each aggregation run creates a folder linked to its source control run:

**Core CSV files:**
- `hourly_agg.csv` - Hourly aggregations by link, date, hour
- `weekly_hourly_profile.csv` - Weekly patterns by link, daytype, hour
- `quality_by_link.csv` - Data quality metrics per link

**Metadata:**
- `processing_log.txt` - Processing details and statistics
- `run_config.json` - Complete configuration used

## Folder Naming Conventions

### Timestamp Format: `DD_MM_YY_HH_MM`
- **DD** - Day (01-31)
- **MM** - Month (01-12)
- **YY** - Year (2-digit)
- **HH** - Hour (00-23)
- **MM** - Minute (00-59)

Example: `05_10_25_16_36` = October 5, 2025 at 16:36

### Traceability
- Control folders: `DD_MM_YY_HH_MM`
- Aggregation folders: `from_control_DD_MM_YY_HH_MM`

This naming ensures:
1. **Chronological sorting** - Folders sort by date/time
2. **Unique identifiers** - Each run has a unique timestamp
3. **Traceability** - Aggregation links back to source control run
4. **Version control** - Multiple runs coexist without conflicts

## Key Configuration Files

### Default Paths (configurable in UI)
- **Control output**: `runs/1_10_25/output/control/`
- **Aggregation output**: `runs/1_10_25/output/aggregation/`
- **Default shapefile**: `test_data/aggregation/google_results_to_golan_17_8_25/google_results_to_golan_17_8_25.shp`

### Methodology Documentation
- **Control**: `components/control/methodology.md` - Validation algorithms, codes, parameters
- **Aggregation**: `components/aggregation/methodology.md` - Pipeline logic, quality metrics, output schemas
- **Project**: `CLAUDE.md` - Overall system architecture and workflows

## gitignore Strategy

**Tracked by git:**
- All source code (`*.py`)
- Documentation (`*.md`)
- Test files
- Configuration templates

**Ignored by git:**
- `runs/` - All output data
- `test_data/` - Test datasets (too large)
- `*.pyc`, `__pycache__/` - Python cache
- `.streamlit/` - Streamlit cache
- Distribution packages (`*.zip`)

## Running the System

### Application Entry Points
```bash
streamlit run app.py              # Main application
pytest                            # Run all tests
python distribution/create_distribution.py  # Create package
python distribution/verify_installation.py  # Verify installation
```

### Workflow
1. **Control Validation**: Upload CSV + shapefile → validate → get timestamped results
2. **Aggregation**: Use control output → process → get linked aggregation folder
3. **Maps**: Load aggregation results + shapefile → visualize and analyze

## Distribution

The `distribution/` folder contains tools for packaging and deploying the system:
- `create_distribution.py` - Creates clean ZIP with only git-tracked files
- `verify_installation.py` - Tests new installations for completeness
- `SETUP_INSTRUCTIONS.md` - Complete setup guide for new users

Run `python distribution/create_distribution.py` to create a distribution package.
