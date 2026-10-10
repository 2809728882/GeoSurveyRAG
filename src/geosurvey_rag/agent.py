from __future__ import annotations

import re
from dataclasses import dataclass

from geosurvey_rag.schemas import ToolCall
from geosurvey_rag.tools.geodesy import (
    geodesic_distance,
    polygon_area_lambert,
    transform_coordinate,
    wkt_bbox,
)


NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
COORD_RE = re.compile(rf"\(\s*({NUMBER})\s*,\s*({NUMBER})\s*\)")


def extract_wkt(question: str) -> str | None:
    match = re.search(
        r"\b(?:SRID=\d+;\s*)?(?:MULTIPOLYGON|MULTILINESTRING|MULTIPOINT|POLYGON|LINESTRING|POINT|GEOMETRYCOLLECTION)\s*(?:Z|M|ZM)?\s*\(",
        question,
        re.I,
    )
    if not match:
        return None
    depth = 1
    for index in range(match.end(), len(question)):
        if question[index] == "(":
            depth += 1
        elif question[index] == ")":
            depth -= 1
        if depth == 0:
            return question[match.start() : index + 1]
    return question[match.start() :]


@dataclass
class GeoAgent:
    """Small deterministic tool router that mirrors production Agent patterns."""

    def maybe_run_tools(self, question: str) -> list[ToolCall]:
        calls: list[ToolCall] = []
        normalized = question.replace("（", "(").replace("）", ")").replace("，", ",")
        coords = [(float(x), float(y)) for x, y in COORD_RE.findall(normalized)]

        def call(name, arguments, function, *args, **kwargs):
            try:
                result = function(*args, **kwargs)
            except ValueError as exc:
                result = {"error": str(exc)}
            calls.append(ToolCall(name=name, arguments=arguments, result=result))

        if len(coords) >= 2 and any(keyword in question for keyword in ["距离", "里程", "路线"]):
            unit = "km" if "公里" in question else "m"
            call(
                "geodesic_distance",
                {"points": coords, "unit": unit},
                geodesic_distance,
                coords,
                unit,
            )

        if len(coords) >= 3 and any(keyword in question for keyword in ["面积", "地块", "宗地"]):
            unit = "ha" if "公顷" in question else "m2"
            call(
                "polygon_area",
                {"polygon": coords, "unit": unit},
                polygon_area_lambert,
                coords,
                unit,
            )

        crs_codes = re.findall(r"EPSG\s*[:：]?\s*(\d+)", question, re.I)
        if (
            len(coords) == 1
            and len(crs_codes) == 2
            and any(word in question for word in ["转换", "转为", "转成", "转到"])
        ):
            args = dict(
                x=coords[0][0],
                y=coords[0][1],
                from_epsg=int(crs_codes[0]),
                to_epsg=int(crs_codes[1]),
            )
            call("transform_coordinate", args, transform_coordinate, **args)
        geometry = extract_wkt(question)
        if geometry:
            call("wkt_bbox", {"wkt": geometry}, wkt_bbox, geometry)

        return calls


def format_tool_summary(calls: list[ToolCall]) -> str:
    if not calls:
        return ""
    rows = []
    for call in calls:
        rows.append(f"- {call.name}: {call.result}")
    return "\n".join(rows)
