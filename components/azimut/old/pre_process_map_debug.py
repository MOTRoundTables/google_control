# -*- coding: utf-8 -*-
"""
pre_process_map_debug.py

Per-feature heading (A→B) with extensive diagnostics.
Outputs:
  1) OUT_SHP  : original geometry + new_id
  2) CROW_SHP : crow-line with rich fields (coords, azimuths, codes, labels, planar azimuths)
  3) OUT_XLSX : same attributes in Excel

Notes:
- Start A is the first vertex of each original polyline; end B is the last vertex.
- Geodesic azimuths are computed on WGS84. Octants use non-overlapping bins.
- new_id = {kid}-{a}{b} where 'a' is A→B octant and 'b' is B→A octant.

Diagnostic fields in crow layer:
  ax, ay, bx, by         -> start/end coords in ORIGINAL CRS
  azi_a, azi_b           -> geodesic A→B and B→A in degrees [0,360)
  code_a, code_b         -> 1..8
  lab_a, lab_b           -> 'N','NE','E','SE','S','SW','W','NW'
  azi_ap, azi_bp         -> planar bearings in original CRS for cross-check
  az_a_lls, az_b_lls     -> geodesic if lon/lat were accidentally swapped (axis-order test)

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
from shapely.ops import linemerge, transform
from pyproj import Geod, Transformer

# ------------------------------------------------------------------
# User paths
IN_SHP    = r"runs/1_11_25/input/maps/basemap/1_11_2025_base_map/1_11_2025_base_map.shp"
OUT_SHP   = r"runs/1_11_25/input/maps/basemap/azimut_base_map/1_11_2025_base_map_azimut_id.shp"
CROW_SHP  = r"runs/1_11_25/input/maps/basemap/azimut_base_map/1_11_2025_base_map_crow_only.shp"
OUT_XLSX  = r"runs/1_11_25/input/maps/a_b/1_11_2025_a_b.xlsx"
CROW_CSV  = str(Path(CROW_SHP).with_suffix(".csv"))
# ------------------------------------------------------------------

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


def planar_bearing_from_north(x1, y1, x2, y2) -> float:
    """Planar heading in degrees, 0°=North, clockwise, using original CRS."""
    dx = x2 - x1
    dy = y2 - y1
    # angle from +X (east) is math.degrees(math.atan2(dy, dx))
    # to convert to 0° at North clockwise: use atan2(dx, dy)
    angle = math.degrees(math.atan2(dx, dy))
    return normalize_bearing(angle)


def pick_id_field(gdf: gpd.GeoDataFrame) -> str:
    for c in ["keta_id", "ketaid", "link_id", "segment_id", "linkid", "id", "Id", "ID"]:
        if c in gdf.columns:
            return c
    gdf["_rowid_"] = range(1, len(gdf) + 1)
    return "_rowid_"


def ensure_folder(path_str: str):
    Path(path_str).parent.mkdir(parents=True, exist_ok=True)


def main():
    gdf = read_vector_any(IN_SHP)
    if gdf.empty:
        raise ValueError("Input layer is empty.")

    crs = gdf.crs

    gdf = gdf[gdf.geometry.notna()].copy()
    gdf["geometry"] = gdf["geometry"].apply(to_linestring)
    gdf = gdf[gdf.geometry.notna()].copy()

    kid_field = pick_id_field(gdf)

    # Compute bearings on WGS84
    transformer_ll = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    geod = Geod(ellps="WGS84")

    rows = []
    excel_rows = []
    crow_geoms = []

    for geom_orig, kid_val in zip(gdf.geometry, gdf[kid_field]):
        ls_orig = to_linestring(geom_orig)
        if ls_orig is None:
            continue

        geom_wgs84 = transform(transformer_ll.transform, ls_orig)
        ls_ll = to_linestring(geom_wgs84)
        ls_orig = to_linestring(geom_orig)
        if ls_ll is None or ls_orig is None:
            continue

        # endpoints
        (x1_ll, y1_ll), (x2_ll, y2_ll) = endpoints_xy(ls_ll)
        (x1, y1), (x2, y2) = endpoints_xy(ls_orig)

        # geodesic azimuths (proper lon,lat order)
        fwd_az, back_az, _ = geod.inv(x1_ll, y1_ll, x2_ll, y2_ll)
        fwd_az = normalize_bearing(fwd_az)
        back_az = normalize_bearing(back_az)

        # planar bearings (original CRS) for cross-check
        fwd_az_p = planar_bearing_from_north(x1, y1, x2, y2)
        back_az_p = planar_bearing_from_north(x2, y2, x1, y1)

        # deliberately swap lon/lat to test axis-order issues
        fwd_az_llswap, back_az_llswap, _ = geod.inv(y1_ll, x1_ll, y2_ll, x2_ll)
        fwd_az_llswap = normalize_bearing(fwd_az_llswap)
        back_az_llswap = normalize_bearing(back_az_llswap)

        code_a, lab_a = octant(fwd_az)
        code_b, lab_b = octant(back_az)

        start_coord = f"{y1_ll:.15f},{x1_ll:.15f}"
        end_coord = f"{y2_ll:.15f},{x2_ll:.15f}"
        travel_mode = f"{code_a}-{code_b}"

        # crow line
        crow = LineString([(x1, y1), (x2, y2)])

        kid_str = str(kid_val)
        new_id = f"{kid_str}-{code_a}{code_b}"  # start heading first

        rows.append({
            "kid": kid_str,
            "new_id": new_id,
            "ax": x1, "ay": y1,
            "bx": x2, "by": y2,
            "azi_a": fwd_az, "azi_b": back_az,
            "code_a": code_a, "code_b": code_b,
            "lab_a": lab_a, "lab_b": lab_b,
            "azi_ap": fwd_az_p, "azi_bp": back_az_p,
            "az_a_lls": fwd_az_llswap, "az_b_lls": back_az_llswap,
            "start_lat": y1_ll, "start_lon": x1_ll,
            "end_lat": y2_ll, "end_lon": x2_ll,
            "start_coord": start_coord, "end_coord": end_coord,
            "travel_mode": travel_mode,
        })
        crow_geoms.append(crow)

        excel_rows.append({
            "שםמקטע": new_id,
            "אופןנסיעה": 0,
            "נקודתהתחלה": start_coord,
            "נקודתסיום": end_coord,
        })

    crow_df = gpd.GeoDataFrame(rows, geometry=crow_geoms, crs=crs)

    # 1) original geometry + Id only
    ensure_folder(OUT_SHP)
    out_gdf = gdf[["geometry"]].copy()
    out_gdf["Id"] = [r["new_id"] for r in rows]  # align by row
    try:
        out_gdf.to_file(OUT_SHP)
    except PermissionError:
        print(f"Warning: could not overwrite {OUT_SHP}; close the file if you need it refreshed.")

    # 2) crow geometry + diagnostics
    ensure_folder(CROW_SHP)
    crow_df_for_csv = crow_df.copy()
    try:
        crow_df.to_file(CROW_SHP)
    except PermissionError:
        print(f"Warning: could not overwrite {CROW_SHP}; close the file if you need it refreshed.")

    # 3) Excel summary
    ensure_folder(OUT_XLSX)
    ensure_folder(CROW_CSV)
    summary_df = pd.DataFrame(excel_rows, columns=["שםמקטע", "אופןנסיעה", "נקודתהתחלה", "נקודתסיום"])
    try:
        summary_df.to_excel(OUT_XLSX, index=False, sheet_name="links")
    except PermissionError:
        print(f"Warning: could not overwrite {OUT_XLSX}; close the file if you need it refreshed.")

    # 4) Crow diagnostics CSV
    crow_df_for_csv["geometry_wkt"] = crow_df_for_csv.geometry.to_wkt()
    crow_df_for_csv = crow_df_for_csv.drop(columns="geometry")
    crow_df_for_csv.to_csv(CROW_CSV, index=False, encoding="utf-8-sig")

    print("Done.")
    print(f"Wrote: {OUT_SHP}")
    print(f"Wrote: {CROW_SHP}")
    print(f"Wrote: {OUT_XLSX}")
    print(f"Wrote: {CROW_CSV}")


if __name__ == "__main__":
    main()
