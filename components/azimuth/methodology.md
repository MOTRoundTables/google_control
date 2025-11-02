# Link Direction Coding Methodology

**Last Updated:** 2025-10-21
**Component:** Azimuth Preprocessing

---

## Overview

This document defines the methodology for assigning octant-based directional codes to road network polylines. The system calculates geodesic azimuths (compass bearings), classifies them into 8 directional sectors, and generates new directional IDs that encode the orientation at both start and end nodes.

### Key Outputs
- Directional IDs encoding start/end compass orientations
- Four coordinated output files (shapefiles, CSV, Excel)
- Quality assurance diagnostics for axis-order validation

---

## Visual Workflow: From Two-Sided Links to Directional IDs

This section provides a step-by-step visual guide to understanding how the azimuth preprocessing algorithm transforms road network links into directional IDs.

### Step 1: Input - Two-Sided Links on Map

**Starting Point:** A road network where each link may appear twice (once for each direction)

**Example:** Link **909** appears in the attribute table with two entries:
- Entry 1: Direction from Node A to Node B (northbound)
- Entry 2: Direction from Node B to Node A (southbound)

**Problem:** Both entries share the same ID (**909**), making it impossible to distinguish between directional variants for route alternative queries.

### Step 2: Algorithm Processing

The azimuth preprocessing algorithm performs the following transformations:

#### 2.1 Crow Flight Geometry Creation
- Simplifies each polyline to a straight line from start point to end point
- Creates "crow flight" geometry for directional analysis
- Preserves original complex geometry in separate output file

#### 2.2 Azimuth Calculation
For each link, the system calculates geodesic azimuths using WGS84 ellipsoid:

**Forward Azimuth (A→B):**
- Compass bearing from start node to end node
- Example: 22.5° (pointing Northeast)

**Backward Azimuth (B→A):**
- Compass bearing from end node to start node
- Example: 202.5° (pointing Southwest)

#### 2.3 Octant Classification
Each azimuth is mapped to one of 8 directional sectors:

**The Compass Rose - 8 Octants:**

| Octant | Direction | Azimuth Range | Center Angle |
|:------:|-----------|---------------|--------------|
| **1** | N (North) | 337.5° - 22.5° | 0° |
| **2** | NE (Northeast) | 22.5° - 67.5° | 45° |
| **3** | E (East) | 67.5° - 112.5° | 90° |
| **4** | SE (Southeast) | 112.5° - 157.5° | 135° |
| **5** | S (South) | 157.5° - 202.5° | 180° |
| **6** | SW (Southwest) | 202.5° - 247.5° | 225° |
| **7** | W (West) | 247.5° - 292.5° | 270° |
| **8** | NW (Northwest) | 292.5° - 337.5° | 315° |

**Visual Representation:**
```
                    N (1)
                     0°
                     |
        NW (8)       |       NE (2)
         315°        |        45°
                     |
    W (7) ------  Center  ------ E (3)
     270°            |           90°
                     |
        SW (6)       |       SE (4)
         225°        |        135°
                     |
                    S (5)
                    180°
```

#### 2.4 Directional ID Construction

**ID Format:** `{original_id}-{start_octant}{end_octant}`

**Encoding Logic:**
- **First Digit (Start Octant):** Represents the direction at the **start node** (backward azimuth B→A)
- **Second Digit (End Octant):** Represents the direction at the **end node** (forward azimuth A→B)

### Step 3: Output - Directional IDs

**Result:** Each directional variant receives a unique ID encoding its orientation

**Example for Link 909:**

**Northbound Travel (South→North):**
- Start node (bottom): Octant **2** (NE, azimuth ~22.5°)
- End node (top): Octant **5** (S, azimuth ~202.5°)
- **New ID:** `909-25`

**Southbound Travel (North→South):**
- Start node (top): Octant **5** (S, azimuth ~202.5°)
- End node (bottom): Octant **2** (NE, azimuth ~22.5°)
- **New ID:** `909-52`

### Step 4: Applying to Node Intersections

**At each node, the octant code indicates the compass direction:**

**Example Node with 4 Approaches:**
```
        Approach from N (octant 1)
                 |
                 |
    W (7) ----(Node)---- E (3)
                 |
                 |
        Approach from S (5)
```

**Use Case:** When querying Google Maps for route alternatives:
- `909-25` requests routes approaching from **NE** (octant 2) and departing toward **S** (octant 5)
- `909-52` requests routes approaching from **S** (octant 5) and departing toward **NE** (octant 2)

This enables **direction-specific route queries** that distinguish between different turning movements at intersections.

### Complete Workflow Summary

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: Input Road Network                                     │
│ • Two-sided links with duplicate IDs (e.g., 909, 909)         │
│ • Complex polyline geometries                                  │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: Crow Flight Simplification                            │
│ • Create straight-line geometry from start to end             │
│ • Preserve original geometry in separate output               │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: Azimuth Calculation (WGS84 Geodesic)                 │
│ • Forward azimuth (A→B): e.g., 22.5° (NE)                     │
│ • Backward azimuth (B→A): e.g., 202.5° (SW)                   │
│ • Axis-order correction if needed                             │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: Octant Classification                                 │
│ • Map azimuths to 8 compass sectors (1-8)                     │
│ • Start octant: backward azimuth → octant 2 (NE)              │
│ • End octant: forward azimuth → octant 5 (S)                  │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: Directional ID Generation                             │
│ • Format: {original_id}-{start_octant}{end_octant}            │
│ • Example: 909-25 (NE→S direction)                            │
│ • Example: 909-52 (S→NE direction)                            │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 6: Output Files                                          │
│ • Azimuth ID shapefile (original geometry + new IDs)          │
│ • Crow flight shapefile (diagnostics + straight geometry)     │
│ • Crow CSV (tabular format)                                   │
│ • Excel A-B (Google Maps query format)                        │
└─────────────────────────────────────────────────────────────────┘
```

### Key Benefits of Directional IDs

1. **Direction-Specific Queries:** Query Google Maps for routes specific to approach/departure orientations
2. **Intersection Analysis:** Distinguish between different turning movements at complex junctions
3. **Asymmetric Traffic:** Model directional differences in traffic patterns
4. **Route Alternatives:** Request alternatives for specific directional scenarios

---

## Input Requirements

### Polyline Network
- **CRS:** Any defined coordinate reference system (commonly EPSG:2039 for Israel)
- **Geometry Type:** LineString or MultiLineString
- **Required:** Each feature must have a valid geometry with defined CRS

### Identifier Column

#### Auto-Detection Priority
The processing script auto-detects a suitable ID field using the `pick_id_field()` function, searching for fields in this **exact priority order**:

1. `keta_id`
2. `ketaid`  ← **Common field in Israel road network shapefiles**
3. `link_id`
4. `segment_id`
5. `linkid`
6. `id`
7. `Id`
8. `ID`

**Detection Logic:**
- The first matching field name found in the input shapefile is selected
- Field name matching is **case-sensitive**
- If no suitable field is found, a synthetic `_rowid_` field is created (sequential numbers starting from 1)

#### Field Name Mapping in Outputs

**Original ID Field → Output Field Names:**

| Input Shapefile | Detection Result | Output Files |
|----------------|------------------|--------------|
| Field detected (e.g., `ketaid`) | Uses detected field values | **Azimuth ID Shapefile:** `Id` only<br>**Crow Shapefile/CSV:** `kid` (original) + `Id` (new directional ID) |
| No field found | Creates synthetic `_rowid_` | Same as above, using row numbers as IDs |

**Example:**
- **Input shapefile** has `ketaid` field with values: `1234`, `5678`, `909`
- **Azimuth ID shapefile** output:
  - `Id` = `1234-51`, `5678-32`, `909-25` (directional IDs)
- **Crow shapefile/CSV** output:
  - `kid` = `1234`, `5678`, `909` (original values from `ketaid`)
  - `Id` = `1234-51`, `5678-32`, `909-25` (new directional IDs)

#### What Happens to Other Fields
- **Other input fields are NOT preserved** in output files (e.g., `to`, `from`, `name`)
- Only the detected ID field and geometry are retained
- If you need other attributes, join outputs back to original shapefile using the `kid` field

---

## Geometry Processing

### 1. Geometry Validation and Simplification

**MultiLineString Handling:**
- Multi-part features are merged using `linemerge`
- If multiple parts remain after merging, the **longest part** is selected
- Ensures a unique start and end vertex for each feature

**Vertex Order:**
- **Start Point (A):** First vertex of the polyline (as digitized)
- **End Point (B):** Last vertex of the polyline (as digitized)
- All directional logic follows this digitized order

### 2. Crow Flight Geometry

For each feature, a simplified "crow flight" geometry is created:
- **Type:** Straight LineString from point A to point B
- **CRS:** Original coordinate reference system
- **Purpose:** Diagnostic analysis and simplified directional representation

### 3. Coordinate System Handling

**WGS84 Transformation:**
- Features are reprojected to **EPSG:4326** for geodesic calculations
- Axis order enforced as **(longitude, latitude)** to prevent azimuth swapping
- Modern PROJ/GeoPandas versions may use latitude-first; explicit lon/lat order prevents errors

---

## Azimuth Calculation Methodology

### 1. Geodesic Azimuth Computation

Azimuths are calculated using the **WGS84 ellipsoid** via `pyproj.Geod.inv`:

**Forward Azimuth (A→B):**
- Compass bearing from start point to end point
- Field: `azi_a_raw`

**Backward Azimuth (B→A):**
- Compass bearing from end point to start point
- Field: `azi_b_raw`

### 2. Axis-Order Diagnostic

The system includes automatic detection and correction of coordinate order ambiguity:

**Detection Process:**
1. Calculate azimuths with standard **(lon, lat)** order → `azi_a_raw`, `azi_b_raw`
2. Calculate azimuths with swapped **(lat, lon)** order → `azi_a_sw`, `azi_b_sw`
3. Compute **planar bearing** from original CRS coordinates → `azi_a_pl`, `azi_b_pl`
4. Compare both geodesic results against planar reference
5. Select the azimuth calculation that best matches planar bearing (within 45° tolerance)

**Correction Flag:**
- `axis_fix = 1`: Swapped azimuths were used (axis-order correction applied)
- `axis_fix = 0`: Raw azimuths were used (no correction needed)

**Interpretation:**
- `axis_fix = 1` indicates the CRS reported coordinates in reverse order (lat/lon instead of lon/lat)
- The diagnostic prevents 180-degree orientation errors

### 3. Diagnostic Fields in Output

| Field | Description |
|-------|-------------|
| `azi_a_raw` | Geodesic azimuth A→B with standard lon/lat order |
| `azi_b_raw` | Geodesic azimuth B→A with standard lon/lat order |
| `azi_a_sw` | Geodesic azimuth A→B with swapped lat/lon order |
| `azi_b_sw` | Geodesic azimuth B→A with swapped lat/lon order |
| `azi_a_pl` | Planar XY bearing A→B in original CRS |
| `azi_b_pl` | Planar XY bearing B→A in original CRS |
| `axis_fix` | Binary flag: 1 if axis swap was applied, 0 otherwise |

---

## Octant Classification System

### Octant Assignment

Azimuths are classified into **8 directional sectors** (octants), each representing a 45-degree compass sector:

| Code | Direction | Azimuth Range | Center |
|:----:|-----------|---------------|--------|
| **1** | N (North) | 337.5° - 22.5° | 0° |
| **2** | NE (Northeast) | 22.5° - 67.5° | 45° |
| **3** | E (East) | 67.5° - 112.5° | 90° |
| **4** | SE (Southeast) | 112.5° - 157.5° | 135° |
| **5** | S (South) | 157.5° - 202.5° | 180° |
| **6** | SW (Southwest) | 202.5° - 247.5° | 225° |
| **7** | W (West) | 247.5° - 292.5° | 270° |
| **8** | NW (Northwest) | 292.5° - 337.5° | 315° |

### Boundary Rules

- Azimuth at **lower bound** belongs to that sector
- Azimuth at **upper bound** belongs to the **next** sector
- North wraps around: 360° → 0°

---

## Directional ID Construction

### ID Format

**Pattern:** `{original_id}-{start_octant}{end_octant}`

### Octant Encoding Logic

**Start Octant (First Digit):**
- Stand at node **A**, looking toward node **B**
- Encode the **backward azimuth (B→A)**
- Represents the compass sector of the **start node**
- Fields: `code_start`, `dir_start`

**End Octant (Second Digit):**
- Stand at node **B**, looking back toward node **A**
- Encode the **forward azimuth (A→B)**
- Represents the compass sector of the **end node**
- Fields: `code_end`, `dir_end`

### Example

**Link 462** - North-to-South direction:
- Start node faces **North** (backward azimuth B→A): octant **1**
- End node faces **South** (forward azimuth A→B): octant **5**
- **New ID:** `462-15`

**Link 462** - South-to-North direction (reverse):
- Start node faces **South**: octant **5**
- End node faces **North**: octant **1**
- **New ID:** `462-51`

---

## Output Files

The system generates four coordinated output files with automatic path generation:

### 1. Azimuth ID Shapefile
**Filename:** `{date}_base_map_azimut_id.shp`
**CRS:** Original input CRS (e.g., EPSG:2039)
**Fields:**
- `Id`: New directional ID
- `geometry`: Original polyline geometry

**Purpose:** Spatial reference with directional IDs for GIS mapping

### 2. Crow Flight Shapefile
**Filename:** `{date}_base_map_crow_only.shp`
**CRS:** Original input CRS
**Fields:**
- `Id`, `kid`: New and original IDs
- `code_start`, `dir_start`: Start node octant code and direction name
- `code_end`, `dir_end`: End node octant code and direction name
- `code_a`, `dir_a`, `azi_a`: Forward azimuth (A→B) octant, direction, degrees
- `code_b`, `dir_b`, `azi_b`: Backward azimuth (B→A) octant, direction, degrees
- `travel_mode`: Format `{start_octant}-{end_octant}`
- `axis_fix`: Axis-order correction flag
- Diagnostic fields: `azi_a_raw`, `azi_b_raw`, `azi_a_sw`, `azi_b_sw`, `azi_a_pl`, `azi_b_pl`
- `geometry`: Straight-line crow flight geometry

**Purpose:** Quality assurance and diagnostic analysis

### 3. Crow Flight CSV
**Filename:** `{date}_base_map_crow_only.csv`
**Encoding:** UTF-8 with BOM
**Fields:** Same as crow shapefile + `geometry_wkt`

**Purpose:** Tabular analysis without GIS software

**Note:** Close this file before rerunning to avoid file lock errors

### 4. Excel Route Alternatives
**Filename:** `{date}_a_b.xlsx`
**Sheet:** `links`
**CRS:** WGS84 (lat, lon coordinates)
**Fields (Hebrew headers):**
- `שם מקטע` (Link Name): Directional ID
- `אופן` (Mode): Travel mode (always 0 for driving)
- `נקודת התחלה` (Start Point): `lat,lon` coordinate string
- `נקודת סיום` (End Point): `lat,lon` coordinate string

**Purpose:** Ready for Google Maps API route alternative queries

### File Organization

**Automatic Path Structure:**
```
runs/{batch_id}/input/maps/
├── basemap/
│   └── {date}_azimut_base_map/
│       ├── {date}_base_map_azimut_id.shp
│       ├── {date}_base_map_crow_only.shp
│       └── {date}_base_map_crow_only.csv
└── a_b/
    └── {date}_a_b.xlsx
```

**Example:** Input `2_11_2025_base_map.zip`
- Batch: `2_11_25`
- Date: `2_11_2025`
- Output: `runs/2_11_25/input/maps/basemap/2_11_2025_azimut_base_map/`

---

## Quality Assurance

### Axis-Order Diagnostic Reporting

The system reports:
- **Total features processed**
- **Axis corrections applied:** Count of features where `axis_fix = 1`
- **Bearing comparisons:** Average and maximum angular differences between geodesic and planar bearings
- **Orientation flips:** Count of bearings with >90° difference (potential issues)

### Validation Metrics

For quality assurance, the system calculates:
- **Planar vs Geodesic Difference (avg):** Mean angular difference
- **Planar vs Geodesic Difference (max):** Maximum observed difference
- **Flipped Bearings:** Count where difference exceeds 90° (indicates potential errors)

---

## Assumptions and Edge Cases

### Data Quality Requirements
1. **Zero-length lines:** Features with identical start/end points should be removed before processing
2. **Invalid geometries:** Null or malformed geometries are automatically filtered out
3. **CRS requirement:** Input must have a defined coordinate reference system

### Technical Constraints
1. **Shapefile field limits:** `Id` field name is short to avoid truncation (10-character limit)
2. **Vertex order dependency:** Results reflect the digitized direction of polylines
3. **No reverse twin creation:** Each feature is processed as-is; reverse directions must exist in input

### Coordinate System Behavior
1. **Output CRS:** Matches original input CRS
2. **Bearing calculations:** Always performed on WGS84 for geodesic accuracy
3. **Planar vs Geodesic:** Small differences (<5°) are normal and expected

---

## Reproducibility and Logging

### Recommended Log Contents

For auditability and reproducibility, record:
- **Script version:** Component version or commit hash
- **Input file path:** Full path to input shapefile
- **Detected ID field:** Auto-detected identifier column
- **Feature count:** Total features processed
- **Input CRS:** Original coordinate reference system
- **Axis corrections:** Count of features requiring axis-order fixes
- **Processing timestamp:** Date and time of processing
- **Output paths:** All generated file paths

### Example Log Entry
```
Azimuth Preprocessing Log
========================
Date: 2025-11-02 14:30:00
Input: runs/2_11_25/input/maps/basemap/2_11_2025_base_map.zip
Batch: 2_11_25
CRS: EPSG:2039
ID Field: keta_id

Features processed: 1,234
Axis corrections: 56
Average bearing difference: 2.3°
Maximum bearing difference: 8.7°
Orientation flips: 0

Outputs:
- Azimuth ID: runs/2_11_25/input/maps/basemap/2_11_2025_azimut_base_map/2_11_2025_base_map_azimut_id.shp
- Crow shapefile: runs/2_11_25/input/maps/basemap/2_11_2025_azimut_base_map/2_11_2025_base_map_crow_only.shp
- Crow CSV: runs/2_11_25/input/maps/basemap/2_11_2025_azimut_base_map/2_11_2025_base_map_crow_only.csv
- Excel: runs/2_11_25/input/maps/a_b/2_11_2025_a_b.xlsx
```

---

## Use Cases

### 1. Direction-Specific Route Alternatives
- Query Google Maps for routes specific to approach/departure orientations
- Distinguish between different turning movements at intersections
- Analyze asymmetric traffic patterns by direction

### 2. Junction Modeling
- Model each directional combination at complex intersections
- Separate traffic flows by compass orientation
- Support turning movement analysis

### 3. Traffic Analysis
- Direction-specific travel time analysis
- Asymmetric congestion pattern detection
- Peak hour directional flow analysis

---

## Technical Notes

- **Azimuth normalization:** All azimuths normalized to 0-360° range (0° = North, clockwise)
- **Geodesic accuracy:** WGS84 ellipsoid provides high accuracy for global locations
- **Geometry preservation:** Original CRS and geometry topology maintained in outputs
- **Crow flight simplification:** Uses original CRS coordinates for consistency
- **Excel compatibility:** WGS84 lat/lon format ensures Google Maps API compatibility
