from __future__ import annotations

import math

from pyproj import CRS, Geod, Transformer
from pyproj.exceptions import ProjError
from shapely import from_wkt
from shapely.errors import GEOSException
from shapely.geometry import Polygon

EARTH_RADIUS_M = 6_371_008.8
WGS84 = Geod(ellps="WGS84")


def validate_lonlat(points, minimum: int):
    if len(points) < minimum:
        raise ValueError(f"At least {minimum} longitude/latitude points are required.")
    for lon, lat in points:
        if not math.isfinite(lon) or not math.isfinite(lat):
            raise ValueError("Coordinates must be finite numbers.")
        if not -180 <= lon <= 180 or not -90 <= lat <= 90:
            raise ValueError("WGS84 longitude/latitude must be within [-180,180]/[-90,90].")


def distance_result(total: float, unit: str, segments: int, method: str):
    if unit not in {"m", "km"}:
        raise ValueError("Distance unit must be m or km.")
    return {
        "distance": round(total / 1000 if unit == "km" else total, 3),
        "unit": unit,
        "segments": segments,
        "method": method,
        "epsg": 4326,
    }


def haversine_distance(points: list[tuple[float, float]], unit: str = "m") -> dict:
    validate_lonlat(points, 2)
    total = 0.0
    for start, end in zip(points, points[1:]):
        lon1, lat1 = map(math.radians, start)
        lon2, lat2 = map(math.radians, end)
        a = (
            math.sin((lat2 - lat1) / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
        )
        total += 2 * EARTH_RADIUS_M * math.asin(math.sqrt(min(1.0, max(0.0, a))))
    return distance_result(total, unit, len(points) - 1, "haversine_sphere")


def geodesic_distance(points: list[tuple[float, float]], unit: str = "m") -> dict:
    validate_lonlat(points, 2)
    total = sum(WGS84.inv(*start, *end)[2] for start, end in zip(points, points[1:]))
    return distance_result(total, unit, len(points) - 1, "wgs84_geodesic")


def polygon_area_lambert(points: list[tuple[float, float]], unit: str = "m2") -> dict:
    """Compatibility entry point; area now uses the WGS84 ellipsoid, not a local plane."""
    validate_lonlat(points, 3)
    if unit not in {"m2", "km2", "ha"}:
        raise ValueError("Area unit must be m2, km2 or ha.")
    if len(set(points)) < 3:
        raise ValueError("A polygon requires three distinct vertices.")
    unwrapped = [points[0]]
    for lon, lat in points[1:]:
        previous = unwrapped[-1][0]
        lon += 360 * round((previous - lon) / 360)
        unwrapped.append((lon, lat))
    polygon = Polygon(unwrapped)
    if not polygon.is_valid or polygon.area == 0:
        raise ValueError("Polygon must be simple, non-degenerate and free of self-intersections.")
    lons, lats = zip(*points)
    area, perimeter = WGS84.polygon_area_perimeter(lons, lats)
    divisor, digits = {"m2": (1, 3), "km2": (1_000_000, 6), "ha": (10_000, 4)}[unit]
    return {
        "area": round(abs(area) / divisor, digits),
        "unit": unit,
        "method": "wgs84_geodesic",
        "epsg": 4326,
        "perimeter_m": round(perimeter, 3),
    }


def transform_coordinate(x: float, y: float, from_epsg: int = 4326, to_epsg: int = 3857) -> dict:
    if not math.isfinite(x) or not math.isfinite(y):
        raise ValueError("Coordinates must be finite numbers.")
    try:
        source, target = CRS.from_epsg(from_epsg), CRS.from_epsg(to_epsg)
        if source.is_geographic:
            validate_lonlat([(x, y)], 1)
        if to_epsg == 3857 and source.is_geographic and abs(y) > 85.0511287798066:
            raise ValueError("Web Mercator display latitude must be within ±85.05112878 degrees.")
        transformer = Transformer.from_crs(source, target, always_xy=True, allow_ballpark=False)
        tx, ty = transformer.transform(x, y, errcheck=True)
    except ProjError as exc:
        raise ValueError(
            "Invalid CRS or coordinate transformation; check EPSG and required grids."
        ) from exc
    if not math.isfinite(tx) or not math.isfinite(ty):
        raise ValueError("Transformation returned non-finite coordinates.")
    return {
        "x": round(tx, 6),
        "y": round(ty, 6),
        "from_epsg": from_epsg,
        "to_epsg": to_epsg,
        "axis_order": "xy",
        "accuracy_m": transformer.accuracy,
        "note": "EPSG transformation only; project-specific datum/height parameters require separate validation.",
    }


def wkt_bbox(wkt: str) -> dict:
    epsg_hint = "unknown"
    geometry_text = wkt.strip()
    if geometry_text.upper().startswith("SRID="):
        prefix, separator, geometry_text = geometry_text.partition(";")
        if not separator or not prefix[5:].isdigit():
            raise ValueError("Invalid EWKT SRID prefix.")
        epsg_hint = f"EPSG:{int(prefix[5:])}"
    try:
        geometry = from_wkt(geometry_text)
    except GEOSException as exc:
        raise ValueError("Invalid WKT geometry.") from exc
    if geometry.is_empty or not geometry.is_valid:
        raise ValueError("WKT geometry must be non-empty and topologically valid.")
    bounds = geometry.bounds
    if not all(math.isfinite(value) for value in bounds):
        raise ValueError("WKT bounds must be finite.")
    return dict(zip(("min_x", "min_y", "max_x", "max_y"), bounds), epsg_hint=epsg_hint)
