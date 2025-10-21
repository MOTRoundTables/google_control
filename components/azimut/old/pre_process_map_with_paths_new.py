# -*- coding: utf-8 -*-
"""
pre_process_map_with_paths.py

Per-feature heading and octant Ids.
- One crow-line per feature.
- No creation of a reversed twin. If the reverse exists in the input, it will be processed as its own feature.
- Start point = first vertex in the original geometry as digitized.
- New Id = {kid}-{a}{b}  where a is A→B octant, b is B→A octant.
- Crow shapefile carries Id plus start/end coordinates, azimuths, and octant diagnostics.
- Excel contains kid, Id, code/dir/azimuth for A and B.

Requires: geopandas, shapely, pyproj, pandas
"""

from __future__ import annotations

import os
import math
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
OUT_SHP   = r"runs/1_11_25/input/maps/basemap/1_11_2025_azimut_base_map/1_11_2025_base_map_azimut_id.shp"
CROW_SHP  = r"runs/1_11_25/input/maps/basemap/1_11_2025_azimut_base_map/1_11_2025_base_map_crow_only.shp"
OUT_XLSX  = r"runs/1_11_25/input/maps/a_b/1_11_2025_a_b.xlsx"
CROW_CSV  = str(Path(CROW_SHP).with_suffix(".csv"))
# ------------------------------------------------------------------

# If you want to override via environment variables (optional):
IN_SHP   = os.getenv("IN_SHP", IN_SHP)
OUT_SHP  = os.getenv("OUT_SHP", OUT_SHP)
CROW_SHP = os.getenv("CROW_SHP", CROW_SHP)
OUT_XLSX = os.getenv("OUT_XLSX", OUT_XLSX)
CROW_CSV = os.getenv("CROW_CSV", CROW_CSV)


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


def planar_bearing_from_north(x1: float, y1: float, x2: float, y2: float) -> float | None:
    """Planar heading in degrees, 0 deg = North, clockwise, using original CRS coordinates."""
    dx = x2 - x1
    dy = y2 - y1
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return None
    angle = math.degrees(math.atan2(dx, dy))
    return normalize_bearing(angle)


def angular_distance(a: float, b: float) -> float:
    """Smallest absolute angular separation between two bearings."""
    return abs((a - b + 180.0) % 360.0 - 180.0)


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
    if crs is None:
        raise ValueError("Input layer has no CRS; bearings require a defined coordinate reference system.")

    # Ensure valid line geometry
    gdf = gdf[gdf.geometry.notna()].copy()
    gdf["geometry"] = gdf["geometry"].apply(to_linestring)
    gdf = gdf[gdf.geometry.notna()].copy()

    kid_field = pick_id_field(gdf)

    # Compute bearings on WGS84 using explicit reprojection to avoid axis-order ambiguity.
    geod = Geod(ellps="WGS84")
    gdf_ll = gdf.to_crs(4326)

    rows = []
    excel_rows = []
    crow_geoms = []
    axis_fix_count = 0

    for geom_orig, geom_ll, kid_val in zip(gdf.geometry, gdf_ll.geometry, gdf[kid_field]):
        ls_orig = to_linestring(geom_orig)
        ls_ll = to_linestring(geom_ll)
        if ls_orig is None or ls_ll is None:
            continue

        # endpoints in lon/lat for geodesic bearings
        (x1_ll, y1_ll), (x2_ll, y2_ll) = endpoints_xy(ls_ll)

        fwd_az, back_az, _ = geod.inv(x1_ll, y1_ll, x2_ll, y2_ll)
        fwd_az = normalize_bearing(fwd_az)
        back_az = normalize_bearing(back_az)

        # axis-order diagnostic: swap lon/lat deliberately
        fwd_az_swap, back_az_swap, _ = geod.inv(y1_ll, x1_ll, y2_ll, x2_ll)
        fwd_az_swap = normalize_bearing(fwd_az_swap)
        back_az_swap = normalize_bearing(back_az_swap)

        # crow line in original CRS
        (x1, y1), (x2, y2) = endpoints_xy(ls_orig)
        crow = LineString([(x1, y1), (x2, y2)])

        planar_ab = planar_bearing_from_north(x1, y1, x2, y2)
        planar_ba = planar_bearing_from_north(x2, y2, x1, y1)

        # Compare geodesic bearings against planar heading to spot 180-degree inversions.
        use_axis_swap = False
        if planar_ab is not None:
            diff_regular = angular_distance(fwd_az, planar_ab)
            diff_swap = angular_distance(fwd_az_swap, planar_ab)
            if diff_swap + 1e-9 < diff_regular and diff_swap <= 45.0:
                use_axis_swap = True

        if use_axis_swap:
            axis_fix_count += 1
            fwd_use = fwd_az_swap
            back_use = back_az_swap
        else:
            fwd_use = fwd_az
            back_use = back_az

        code_a, dir_a = octant(fwd_use)
        code_b, dir_b = octant(back_use)

        start_coord = f"{y1_ll:.15f},{x1_ll:.15f}"
        end_coord = f"{y2_ll:.15f},{x2_ll:.15f}"
        travel_mode = f"{code_a}-{code_b}"

        kid_str = str(kid_val)
        new_id = f"{kid_str}-{code_a}{code_b}"  # start heading first

        rows.append({
            "kid": kid_str,
            "Id": new_id,
            "code_a": code_a,
            "dir_a": dir_a,
            "azi_a": fwd_use,
            "code_b": code_b,
            "dir_b": dir_b,
            "azi_b": back_use,
            "start_lat": y1_ll,
            "start_lon": x1_ll,
            "end_lat": y2_ll,
            "end_lon": x2_ll,
            "start_x": x1,
            "start_y": y1,
            "end_x": x2,
            "end_y": y2,
            "start_coord": start_coord,
            "end_coord": end_coord,
            "travel_mode": travel_mode,
            "azi_a_raw": fwd_az,
            "azi_b_raw": back_az,
            "azi_a_sw": fwd_az_swap,
            "azi_b_sw": back_az_swap,
            "azi_a_pl": float("nan") if planar_ab is None else planar_ab,
            "azi_b_pl": float("nan") if planar_ba is None else planar_ba,
            "axis_fix": int(use_axis_swap),
        })
        crow_geoms.append(crow)

        excel_rows.append({
            "שםמקטע": new_id,
            "אופןנסיעה": 0,
            "נקודתהתחלה": start_coord,
            "נקודתסיום": end_coord,
        })

    # Build crow GDF with attributes
    crow_df = gpd.GeoDataFrame(rows, geometry=crow_geoms, crs=crs)

    # Write shapefiles
    ensure_folder(OUT_SHP)
    ensure_folder(CROW_SHP)
    ensure_folder(OUT_XLSX)
    ensure_folder(CROW_CSV)

    # 1) original geometry + Id only
    id_map = dict(zip(crow_df["kid"], crow_df["Id"]))
    out_gdf = gdf[["geometry"]].copy()
    # map by position if kid not unique: fall back to ordered merge
    if gdf[kid_field].is_unique:
        out_gdf["Id"] = gdf[kid_field].astype(str).map(id_map)
    else:
        # fallback: align by index order
        out_gdf["Id"] = [rows[i]["Id"] for i in range(len(out_gdf))]

    try:
        out_gdf.to_file(OUT_SHP)
    except PermissionError:
        print(f"Warning: could not overwrite {OUT_SHP}; close the file if you need it refreshed.")

    # 2) crow geometry + diagnostics
    crow_fields = [
        "Id",
        "kid",
        "code_a",
        "dir_a",
        "azi_a",
        "code_b",
        "dir_b",
        "azi_b",
        "start_lon",
        "start_lat",
        "end_lon",
        "end_lat",
        "start_x",
        "start_y",
        "end_x",
        "end_y",
        "travel_mode",
        "azi_a_raw",
        "azi_b_raw",
        "azi_a_sw",
        "azi_b_sw",
        "azi_a_pl",
        "azi_b_pl",
        "axis_fix",
    ]
    crow_min = crow_df[crow_fields + ["geometry"]].copy()
    try:
        crow_min.to_file(CROW_SHP)
    except PermissionError:
        print(f"Warning: could not overwrite {CROW_SHP}; close the file if you need it refreshed.")

    # 3) Excel summary
    xls = pd.DataFrame(
        excel_rows,
        columns=["שםמקטע", "אופןנסיעה", "נקודתהתחלה", "נקודתסיום"],
    )
    xls = pd.DataFrame(
        [
            {
                "שם מקטע": r["Id"],
                "אופן": r["travel_mode"],
                "נסיעה": r["dir_a"],
                "נקודת התחלה": r["start_coord"],
                "נקודת סיום": r["end_coord"],
            }
            for r in rows
        ],
        columns=["שם מקטע", "אופן", "נסיעה", "נקודת התחלה", "נקודת סיום"],
    )
    Path(OUT_XLSX).parent.mkdir(parents=True, exist_ok=True)
    try:
        xls.to_excel(OUT_XLSX, index=False, sheet_name="links")
    except PermissionError:
        print(f"Warning: could not overwrite {OUT_XLSX}; close the file if you need it refreshed.")

    # 4) Crow diagnostics CSV (matches crow shapefile fields)
    crow_csv_df = crow_df.copy()
    crow_csv_df["geometry_wkt"] = crow_csv_df.geometry.to_wkt()
    crow_csv_df = crow_csv_df.drop(columns="geometry")
    crow_csv_df.to_csv(CROW_CSV, index=False, encoding="utf-8-sig")

    if axis_fix_count:
        print(f"Applied axis-order correction on {axis_fix_count} feature(s) using planar cross-checks.")

    print("Done.")
    print(f"Wrote: {OUT_SHP}")
    print(f"Wrote: {CROW_SHP}")
    print(f"Wrote: {OUT_XLSX}")
    print(f"Wrote: {CROW_CSV}")


if __name__ == "__main__":
    main()
