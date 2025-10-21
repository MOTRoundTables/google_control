# -*- coding: utf-8 -*-
"""
pre_process_map_with_paths.py

Per-feature heading and octant Ids.
- One crow-line per feature.
- No creation of a reversed twin. If the reverse exists in the input, it will be processed as its own feature.
- Start point = first vertex in the original geometry as digitized.
- New Id = {kid}-{a}{b}  where a is A→B octant, b is B→A octant.
- Crow shapefile contains only Id + geometry (per your request).
- Excel contains kid, Id, code/dir/azimuth for A and B.

Requires: geopandas, shapely, pyproj, pandas
"""

from __future__ import annotations

import os
from pathlib import Path
from zipfile import ZipFile

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, MultiLineString
from shapely.ops import linemerge
from pyproj import Geod

# ------------------------------------------------------------------
# User paths (as requested)
IN_SHP    = r"runs/1_11_25/input/maps/basemap/1_11_2025_base_map/1_11_2025_base_map.shp"
OUT_SHP   = r"runs/1_11_25/input/maps/basemap/1_11_2025_base_map_azimut/1_11_2025_base_map_azimut_id.shp"
CROW_SHP  = r"runs/1_11_25/input/maps/basemap/1_11_2025_base_map_azimut/1_11_2025_base_map_crow_only.shp"
OUT_XLSX  = r"runs/1_11_25/input/maps/a_b/1_11_2025_a_b.xlsx"
# ------------------------------------------------------------------

# If you want to override via environment variables (optional):
IN_SHP   = os.getenv("IN_SHP", IN_SHP)
OUT_SHP  = os.getenv("OUT_SHP", OUT_SHP)
CROW_SHP = os.getenv("CROW_SHP", CROW_SHP)
OUT_XLSX = os.getenv("OUT_XLSX", OUT_XLSX)


def _find_shp_in_zip(zip_path: Path) -> str:
    with ZipFile(zip_path, "r") as zf:
        shp_members = [n for n in zf.namelist() if n.lower().endswith(".shp")]
        if not shp_members:
            raise ValueError(f"No .shp found inside zip: {zip_path}")
        shp_members.sort(key=lambda p: (p.count("/"), len(p)))
        return shp_members[0]


def read_vector_any(path_str: str) -> gpd.GeoDataFrame:
    p = Path(path_str)
    if p.suffix.lower() == ".zip":
        inner_shp = _find_shp_in_zip(p)
        uri = f"zip://{p}!{inner_shp}"
        return gpd.read_file(uri)
    return gpd.read_file(p)


def to_linestring(geom):
    if geom is None:
        return None
    if isinstance(geom, LineString):
        return geom
    if isinstance(geom, MultiLineString):
        merged = linemerge(geom)
        if isinstance(merged, LineString):
            return merged
        parts = list(merged.geoms) if hasattr(merged, "geoms") else list(geom.geoms)
        if not parts:
            return None
        return max(parts, key=lambda g: g.length)
    return None


def endpoints_xy(ls: LineString):
    coords = list(ls.coords)
    return coords[0], coords[-1]


def normalize_bearing(deg: float) -> float:
    deg = deg % 360.0
    if deg < 0:
        deg += 360.0
    return deg


def octant(angle_deg: float):
    a = normalize_bearing(angle_deg)
    if a < 22.5 or a >= 337.5:
        return 1, "N"
    elif a >= 22.5 and a < 67.5:
        return 2, "NE"
    elif a >= 67.5 and a < 112.5:
        return 3, "E"
    elif a >= 112.5 and a < 157.5:
        return 4, "SE"
    elif a >= 157.5 and a < 202.5:
        return 5, "S"
    elif a >= 202.5 and a < 247.5:
        return 6, "SW"
    elif a >= 247.5 and a < 292.5:
        return 7, "W"
    else:
        return 8, "NW"


def pick_id_field(gdf: gpd.GeoDataFrame) -> str:
    for c in ["keta_id", "ketaid", "link_id", "segment_id", "linkid", "id", "Id", "ID"]:
        if c in gdf.columns:
            return c
    # fallback: create a synthetic id if nothing exists
    gdf["_rowid_"] = range(1, len(gdf) + 1)
    return "_rowid_"


def ensure_folder(path_str: str):
    p = Path(path_str)
    p.parent.mkdir(parents=True, exist_ok=True)


def main():
    gdf = read_vector_any(IN_SHP)
    if gdf.empty:
        raise ValueError("Input layer is empty.")

    crs = gdf.crs

    # Ensure valid line geometry
    gdf = gdf[gdf.geometry.notna()].copy()
    gdf["geometry"] = gdf["geometry"].apply(to_linestring)
    gdf = gdf[gdf.geometry.notna()].copy()

    kid_field = pick_id_field(gdf)

    # Compute bearings on WGS84
    gdf_ll = gdf.to_crs(4326)
    geod = Geod(ellps="WGS84")

    rows = []
    crow_geoms = []

    for geom_wgs84, geom_orig, kid_val in zip(gdf_ll.geometry, gdf.geometry, gdf[kid_field]):
        ls_ll = to_linestring(geom_wgs84)
        ls_orig = to_linestring(geom_orig)
        if ls_ll is None or ls_orig is None:
            continue

        # endpoints in lon/lat for geodesic bearings
        (x1_ll, y1_ll), (x2_ll, y2_ll) = endpoints_xy(ls_ll)

        fwd_az, back_az, _ = geod.inv(y1_ll, x1_ll, y2_ll, x2_ll)
        fwd_az = normalize_bearing(fwd_az)
        back_az = normalize_bearing(back_az)

        code_a, dir_a = octant(fwd_az)
        code_b, dir_b = octant(back_az)

        # crow line in original CRS
        (x1, y1), (x2, y2) = endpoints_xy(ls_orig)
        crow = LineString([(x1, y1), (x2, y2)])

        kid_str = str(kid_val)
        new_id = f"{kid_str}-{code_a}{code_b}"  # start heading first

        rows.append({
            "kid": kid_str,
            "Id": new_id,
            "code_a": code_a,
            "dir_a": dir_a,
            "azi_a": fwd_az,
            "code_b": code_b,
            "dir_b": dir_b,
            "azi_b": back_az,
        })
        crow_geoms.append(crow)

    # Build crow GDF with attributes
    crow_df = gpd.GeoDataFrame(rows, geometry=crow_geoms, crs=crs)

    # Write shapefiles
    ensure_folder(OUT_SHP)
    ensure_folder(CROW_SHP)
    ensure_folder(OUT_XLSX)

    # 1) original geometry + Id only
    id_map = dict(zip(crow_df["kid"], crow_df["Id"]))
    out_gdf = gdf[["geometry"]].copy()
    # map by position if kid not unique: fall back to ordered merge
    if gdf[kid_field].is_unique:
        out_gdf["Id"] = gdf[kid_field].astype(str).map(id_map)
    else:
        # fallback: align by index order
        out_gdf["Id"] = [rows[i]["Id"] for i in range(len(out_gdf))]

    out_gdf.to_file(OUT_SHP)

    # 2) crow geometry + Id only
    crow_min = crow_df[["Id", "geometry"]].copy()
    crow_min.to_file(CROW_SHP)

    # 3) Excel summary
    xls = pd.DataFrame(rows)[["kid", "Id", "code_a", "dir_a", "azi_a", "code_b", "dir_b", "azi_b"]]
    Path(OUT_XLSX).parent.mkdir(parents=True, exist_ok=True)
    xls.to_excel(OUT_XLSX, index=False)

    print("Done.")
    print(f"Wrote: {OUT_SHP}")
    print(f"Wrote: {CROW_SHP}")
    print(f"Wrote: {OUT_XLSX}")


if __name__ == "__main__":
    main()
