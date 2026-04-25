from __future__ import annotations

import math
import re

EARTH_RADIUS_M = 6_371_008.8


def haversine_distance(points: list[tuple[float, float]], unit: str = "m") -> dict:
    if len(points) < 2:
        raise ValueError("At least two lon/lat points are required.")

    total = 0.0
    for start, end in zip(points, points[1:]):
        lon1, lat1 = map(math.radians, start)
        lon2, lat2 = map(math.radians, end)
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        total += 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))

    value = total / 1000 if unit == "km" else total
    return {"distance": round(value, 3), "unit": unit, "segments": len(points) - 1}


def polygon_area_lambert(points: list[tuple[float, float]], unit: str = "m2") -> dict:
    if len(points) < 3:
        raise ValueError("At least three lon/lat points are required.")

    lon0 = math.radians(sum(point[0] for point in points) / len(points))
    lat0 = math.radians(sum(point[1] for point in points) / len(points))
    projected: list[tuple[float, float]] = []
    for lon, lat in points:
        x = EARTH_RADIUS_M * (math.radians(lon) - lon0) * math.cos(lat0)
        y = EARTH_RADIUS_M * (math.radians(lat) - lat0)
        projected.append((x, y))

    area = 0.0
    closed = projected + [projected[0]]
    for (x1, y1), (x2, y2) in zip(closed, closed[1:]):
        area += x1 * y2 - x2 * y1
    area = abs(area) / 2

    if unit == "km2":
        return {"area": round(area / 1_000_000, 6), "unit": "km2", "method": "local_lambert"}
    if unit == "ha":
        return {"area": round(area / 10_000, 4), "unit": "ha", "method": "local_lambert"}
    return {"area": round(area, 3), "unit": "m2", "method": "local_lambert"}


def transform_coordinate(x: float, y: float, from_epsg: int = 4326, to_epsg: int = 3857) -> dict:
    try:
        from pyproj import Transformer
    except ImportError as exc:
        raise RuntimeError("pyproj is required for coordinate transformation.") from exc

    transformer = Transformer.from_crs(from_epsg, to_epsg, always_xy=True)
    tx, ty = transformer.transform(x, y)
    return {
        "x": round(tx, 6),
        "y": round(ty, 6),
        "from_epsg": from_epsg,
        "to_epsg": to_epsg,
    }


def wkt_bbox(wkt: str) -> dict:
    numbers = [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", wkt)]
    if len(numbers) < 2 or len(numbers) % 2 != 0:
        raise ValueError("WKT does not contain valid coordinate pairs.")

    xs = numbers[0::2]
    ys = numbers[1::2]
    return {
        "min_x": min(xs),
        "min_y": min(ys),
        "max_x": max(xs),
        "max_y": max(ys),
        "epsg_hint": "unknown",
    }
