"""
Geometry helpers for outdoor edge polylines.

DB 담당자가 제공하는 상세 경로 좌표는 JSON 배열, GeoJSON, 문자열 구분 형식 등으로 입력 가능.
이 모듈은 입력 형식 표준화, 선택된 간선을 역방향으로 지날 때 좌표 순서 반전 처리.
프론트는 반환된 좌표를 그대로 Polyline으로 렌더링 가능.
"""

import json
from dataclasses import dataclass
from math import asin, cos, hypot, radians, sin, sqrt
from typing import Any


@dataclass(frozen=True)
class GeometryPoint:
    x: float | None = None
    y: float | None = None
    latitude: float | None = None
    longitude: float | None = None


def parse_polyline_points(value: str | None) -> list[GeometryPoint]:
    # 빈 값은 "상세 좌표 없음"으로 처리. 오류가 아니어야 기존 노드-노드 직선 fallback 가능.
    if not value or not str(value).strip():
        return []

    text = str(value).strip()
    try:
        raw = json.loads(text)
    except json.JSONDecodeError:
        raw = _parse_delimited_points(text)

    if isinstance(raw, dict) and str(raw.get("type", "")).lower() == "linestring":
        return [_geojson_point(item) for item in raw.get("coordinates", [])]
    if not isinstance(raw, list):
        raise ValueError("polyline_points must be a JSON array or GeoJSON LineString")

    points = [_point_from_value(item) for item in raw]
    if len(points) < 2:
        raise ValueError("polyline_points must contain at least two points")
    if not all(_is_complete(point) for point in points):
        raise ValueError("each polyline point must contain x/y or latitude/longitude")
    return points


def normalize_polyline_points(value: str | None) -> str | None:
    # import 시점에 다양한 입력 형식을 하나의 JSON 형식으로 저장, 런타임 처리 비용과 예외 가능성 축소.
    points = parse_polyline_points(value)
    if not points:
        return None
    return json.dumps([_point_dict(point) for point in points], ensure_ascii=False, separators=(",", ":"))


def edge_geometry_points(edge: Any, from_node: Any, to_node: Any) -> list[GeometryPoint]:
    # Dijkstra 결과는 양방향 간선을 역방향으로 통과할 수 있으므로 실제 이동 방향 먼저 판단.
    points = parse_polyline_points(getattr(edge, "polyline_points", None))
    traversal_is_forward = (
        str(getattr(edge, "from_node_id", "")) == str(getattr(from_node, "outdoor_node_id", ""))
        and str(getattr(edge, "to_node_id", "")) == str(getattr(to_node, "outdoor_node_id", ""))
    )
    if points and not traversal_is_forward:
        points = list(reversed(points))

    start = node_geometry_point(from_node)
    end = node_geometry_point(to_node)
    if not points:
        return [start, end]
    # DB polyline이 시작/끝 노드 좌표를 생략해도 프론트 경로가 끊기지 않도록 endpoint 보강.
    if not same_point(points[0], start):
        points.insert(0, start)
    if not same_point(points[-1], end):
        points.append(end)
    return deduplicate_points(points)


def node_geometry_point(node: Any) -> GeometryPoint:
    return GeometryPoint(
        x=_optional_float(getattr(node, "map_x", None)),
        y=_optional_float(getattr(node, "map_y", None)),
        latitude=_optional_float(getattr(node, "latitude", None)),
        longitude=_optional_float(getattr(node, "longitude", None)),
    )


def polyline_length(points: list[GeometryPoint]) -> float:
    return sum(point_distance(start, end) for start, end in zip(points, points[1:]))


def point_distance(start: GeometryPoint, end: GeometryPoint) -> float:
    # 위도/경도가 있으면 지구 곡률 기반 거리, 없으면 지도 이미지 좌표계 거리로 계산.
    if None not in (start.latitude, start.longitude, end.latitude, end.longitude):
        return _haversine_meters(start.latitude, start.longitude, end.latitude, end.longitude)
    if None not in (start.x, start.y, end.x, end.y):
        return hypot(end.x - start.x, end.y - start.y)
    return 0.0


def same_point(first: GeometryPoint, second: GeometryPoint, tolerance: float = 0.001) -> bool:
    # 좌표 비교는 import 과정의 소수점/픽셀 오차를 고려해 tolerance 적용.
    if None not in (first.x, first.y, second.x, second.y):
        return abs(first.x - second.x) <= tolerance and abs(first.y - second.y) <= tolerance
    if None not in (first.latitude, first.longitude, second.latitude, second.longitude):
        return abs(first.latitude - second.latitude) <= tolerance / 111_000 and abs(first.longitude - second.longitude) <= tolerance / 111_000
    return False


def deduplicate_points(points: list[GeometryPoint]) -> list[GeometryPoint]:
    result: list[GeometryPoint] = []
    for point in points:
        if not result or not same_point(result[-1], point):
            result.append(point)
    return result


def _point_from_value(value: Any) -> GeometryPoint:
    if isinstance(value, dict):
        x = _optional_float(value.get("x"))
        y = _optional_float(value.get("y"))
        latitude = _optional_float(value.get("latitude", value.get("lat")))
        longitude = _optional_float(value.get("longitude", value.get("lng", value.get("lon"))))
        return GeometryPoint(x=x, y=y, latitude=latitude, longitude=longitude)
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return GeometryPoint(x=_optional_float(value[0]), y=_optional_float(value[1]))
    raise ValueError(f"unsupported polyline point: {value!r}")


def _geojson_point(value: Any) -> GeometryPoint:
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        raise ValueError(f"invalid GeoJSON coordinate: {value!r}")
    return GeometryPoint(longitude=_optional_float(value[0]), latitude=_optional_float(value[1]))


def _parse_delimited_points(value: str) -> list[list[float]]:
    points: list[list[float]] = []
    for item in value.split(";"):
        values = [part.strip() for part in item.split(",")]
        if len(values) != 2:
            raise ValueError("delimited polyline_points must use 'x,y;x,y' format")
        points.append([float(values[0]), float(values[1])])
    return points


def _is_complete(point: GeometryPoint) -> bool:
    return None not in (point.x, point.y) or None not in (point.latitude, point.longitude)


def _point_dict(point: GeometryPoint) -> dict[str, float]:
    if None not in (point.x, point.y):
        return {"x": point.x, "y": point.y}
    return {"latitude": point.latitude, "longitude": point.longitude}


def _optional_float(value: Any) -> float | None:
    if value is None or str(value).strip().lower() in {"", "none", "null", "nan"}:
        return None
    return float(value)


def _haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_m = 6_371_000
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    lat_delta = radians(lat2 - lat1)
    lon_delta = radians(lon2 - lon1)
    haversine = sin(lat_delta / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(lon_delta / 2) ** 2
    return 2 * earth_radius_m * asin(sqrt(haversine))
