from geosurvey_rag.tools.geodesy import haversine_distance, polygon_area_lambert, wkt_bbox


def test_haversine_distance_returns_meters() -> None:
    result = haversine_distance([(111.30, 30.70), (111.31, 30.71)])
    assert result["distance"] > 1000
    assert result["unit"] == "m"


def test_polygon_area_lambert_returns_positive_area() -> None:
    result = polygon_area_lambert([(111.30, 30.70), (111.31, 30.70), (111.31, 30.71)])
    assert result["area"] > 0
    assert result["method"] == "local_lambert"


def test_wkt_bbox() -> None:
    result = wkt_bbox("POLYGON((0 0, 2 0, 2 1, 0 1, 0 0))")
    assert result == {"min_x": 0.0, "min_y": 0.0, "max_x": 2.0, "max_y": 1.0, "epsg_hint": "unknown"}
