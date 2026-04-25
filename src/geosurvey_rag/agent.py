from __future__ import annotations

import re
from dataclasses import dataclass

from geosurvey_rag.schemas import ToolCall
from geosurvey_rag.tools.geodesy import haversine_distance, polygon_area_lambert, wkt_bbox


COORD_RE = re.compile(r"\((-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)\)")


@dataclass
class GeoAgent:
    """Small deterministic tool router that mirrors production Agent patterns."""

    def maybe_run_tools(self, question: str) -> list[ToolCall]:
        calls: list[ToolCall] = []
        coords = [(float(x), float(y)) for x, y in COORD_RE.findall(question)]

        if len(coords) >= 2 and any(keyword in question for keyword in ["距离", "里程", "路线"]):
            result = haversine_distance(coords, unit="m")
            calls.append(ToolCall(name="haversine_distance", arguments={"points": coords}, result=result))

        if len(coords) >= 3 and any(keyword in question for keyword in ["面积", "地块", "宗地"]):
            result = polygon_area_lambert(coords, unit="m2")
            calls.append(ToolCall(name="polygon_area_lambert", arguments={"polygon": coords}, result=result))

        if "POLYGON" in question.upper() or "LINESTRING" in question.upper() or "POINT" in question.upper():
            try:
                result = wkt_bbox(question)
            except ValueError:
                result = {"error": "未能从问题中解析出有效 WKT 坐标。"}
            calls.append(ToolCall(name="wkt_bbox", arguments={"wkt": question}, result=result))

        return calls


def format_tool_summary(calls: list[ToolCall]) -> str:
    if not calls:
        return ""
    rows = []
    for call in calls:
        rows.append(f"- {call.name}: {call.result}")
    return "\n".join(rows)
