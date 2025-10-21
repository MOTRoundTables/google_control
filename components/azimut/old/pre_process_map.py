# -*- coding: utf-8 -*-
# All comments are in English

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, MultiLineString
from shapely.ops import linemerge
from pyproj import Geod

IN_SHP    = r"runs/1_11_25/input/maps/basemap/1_11_2025_base_map/1_11_2025_base_map.shp"           # input layer with geometry and a keta-like id field
OUT_SHP   = r"runs/1_11_25/input/maps/basemap/1_11_2025_base_map_azimut/1_11_2025_base_map_azimut_id.shp"   # original geometry + Id only
CROW_SHP  = r"runs/1_11_25/input/maps/basemap/1_11_2025_base_map_azimut/1_11_2025_base_map_crow_only.shp" # crow-line geometry + Id only
OUT_XLSX  = r"runs/1_11_25/input/maps/a_b/1_11_2025_a_b.xlsx"        # Excel with Hebrew headers

KETA_FIELD = None  # if None, auto-detect from candidates
KETA_CANDIDATES = [
    "ketaid", "keta_id", "KETA_ID", "keta", "KETA",
    "link_id", "LINK_ID", "segment_id", "SEGMENT_ID",
    "id", "ID"
]

geod = Geod(ellps="WGS84")

def detect_keta_field(gdf, preferred="keta_id", candidates=None):
    """Detect the keta id column name. Case-sensitive first, then case-insensitive."""
    if candidates is None:
        candidates = KETA_CANDIDATES
    cols = list(gdf.columns)
    if preferred in cols:
        return preferred
    for c in candidates:
        if c in cols:
            return c
    cols_lower = {c.lower(): c for c in cols}
    if preferred.lower() in cols_lower:
        return cols_lower[preferred.lower()]
    for c in candidates:
        if c.lower() in cols_lower:
            return cols_lower[c.lower()]
    raise KeyError(
        f"Could not find a keta id column. Columns available: {cols}. "
        f"Tried preferred='{preferred}' and candidates={candidates}."
    )

def to_linestring(geom):
    """Return a single LineString (merge MultiLineString, choose longest if needed)."""
    if isinstance(geom, LineString):
        return geom
    if isinstance(geom, MultiLineString):
        merged = linemerge(geom)
        if isinstance(merged, LineString):
            return merged
        parts = list(merged) if isinstance(merged, MultiLineString) else list(geom)
        return max(parts, key=lambda ls: ls.length)
    raise TypeError("Geometry must be LineString or MultiLineString")

def end_points(ls):
    """Return start and end (x1, y1, x2, y2) from a LineString in its CRS."""
    x1, y1 = ls.coords[0]
    x2, y2 = ls.coords[-1]
    return (x1, y1, x2, y2)

def bearings_lonlat(lon1, lat1, lon2, lat2):
    """Return forward and back azimuths normalized to [0,360)."""
    fwd, back, _ = geod.inv(lon1, lat1, lon2, lat2)
    return (fwd + 360) % 360, (back + 360) % 360

def octant_code(azi):
    """Map azimuth to octant 1..8 using 45° sectors centered on NESW."""
    ranges = [
        (337.5, 360.0, 1, "N"),
        (0.0,   22.5,  1, "N"),
        (22.5,  67.5,  2, "NE"),
        (67.5,  112.5, 3, "E"),
        (112.5, 157.5, 4, "SE"),
        (157.5, 202.5, 5, "S"),
        (202.5, 247.5, 6, "SW"),
        (247.5, 292.5, 7, "W"),
        (292.5, 337.5, 8, "NW"),
    ]
    for lo, hi, code, _ in ranges:
        if lo > hi:
            if azi >= lo or azi < hi:
                return code
        else:
            if lo <= azi < hi:
                return code
    return 1

def main():
    import os

    gdf = gpd.read_file(IN_SHP)
    if gdf.crs is None:
        raise ValueError("Input layer has no CRS. Expected EPSG:2039.")
    orig_crs = gdf.crs

    # Create output directories if they don't exist
    os.makedirs(os.path.dirname(OUT_SHP), exist_ok=True)
    os.makedirs(os.path.dirname(CROW_SHP), exist_ok=True)
    os.makedirs(os.path.dirname(OUT_XLSX), exist_ok=True)

    keta_col = KETA_FIELD or detect_keta_field(gdf, preferred="keta_id", candidates=KETA_CANDIDATES)

    gdf_ll = gdf.to_crs(4326)

    records = []
    crow_geoms = []

    for i in range(len(gdf)):
        ls_ll = to_linestring(gdf_ll.geometry.iloc[i])
        lon1, lat1, lon2, lat2 = end_points(ls_ll)
        az_a, az_b = bearings_lonlat(lon1, lat1, lon2, lat2)
        a_code = octant_code(az_a)
        b_code = octant_code(az_b)

        kid = gdf.iloc[i][keta_col]
        new_id = f"{kid}-{a_code}{b_code}"

        ls_orig = to_linestring(gdf.geometry.iloc[i])
        x1, y1, x2, y2 = end_points(ls_orig)
        crow_geoms.append(LineString([(x1, y1), (x2, y2)]))

        records.append({
            "Id": new_id,
            "start_latlon": f"{lat1:.15f},{lon1:.15f}",
            "end_latlon":   f"{lat2:.15f},{lon2:.15f}",
            "mode": 0
        })

    gdf_id_only = gpd.GeoDataFrame({"Id": [r["Id"] for r in records]},
                                   geometry=gdf.geometry.values,
                                   crs=orig_crs)
    try:
        gdf_id_only.to_file(OUT_SHP)
    except Exception as e:
        print(f"Error writing OUT_SHP: {e}")
        raise

    crow_gdf = gpd.GeoDataFrame({"Id": [r["Id"] for r in records]},
                                geometry=crow_geoms, crs=orig_crs)
    try:
        crow_gdf.to_file(CROW_SHP)
    except Exception as e:
        print(f"Error writing CROW_SHP: {e}")
        raise

    df = pd.DataFrame(records)
    df_excel = pd.DataFrame({
        "שם מקטע": df["Id"],
        "אופן נסיעה": df["mode"],
        "נקודת התחלה": df["start_latlon"],
        "נקודת סיום": df["end_latlon"],
    })
    with pd.ExcelWriter(OUT_XLSX, engine="xlsxwriter") as writer:
        df_excel.to_excel(writer, sheet_name="links", index=False)

    print("Wrote:", OUT_SHP)
    print("Wrote:", CROW_SHP)
    print("Wrote:", OUT_XLSX)
    print("CRS:", orig_crs)
    print("Keta field:", keta_col)

if __name__ == "__main__":
    main()
