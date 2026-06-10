"""
Indoor routing service.

방 단위 검색 결과를 실제 실내 그래프 노드로 연결.
Dijkstra 결과를 프론트가 층별 실내 지도에 표시할 수 있는 세그먼트 구조로 변환.
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.algorithms.cost_function import build_route_cost_context, normalize_route_type
from app.algorithms.pathfinding import PathResult, dijkstra_result
from app.models import IndoorEdge, IndoorMap, IndoorNode, Room
from app.schemas.routes import RouteDetailResponse, RoutePoint, RouteSegmentResponse


ROUTE_TITLES = {
    "DEFAULT": "기본 경로",
    "COMFORTABLE": "편한 길",
    "RAINY": "비 오는 날",
}

ROUTE_REASONS = {
    "DEFAULT": "거리와 예상 시간을 중심으로 계산한 기본 실내 경로입니다.",
    "COMFORTABLE": "계단과 경사 비용을 크게 반영하고 엘리베이터/램프를 선호한 경로입니다.",
    "RAINY": "실외와 비가림 없는 구간 비용을 크게 반영한 경로입니다.",
}


@dataclass
class IndoorRouteServiceResult:
    payload: RouteDetailResponse | None = None
    error_code: str | None = None


def find_indoor_route(
    db: Session,
    from_room_id: str,
    to_room_id: str,
    route_type: str = "DEFAULT",
    preferences: Any | None = None,
) -> IndoorRouteServiceResult:
    # 강의실 API는 room_id 입력, 실제 그래프는 nearest_indoor_node_id 기준 계산.
    from_room = db.get(Room, from_room_id)
    if not from_room:
        return IndoorRouteServiceResult(error_code="FROM_ROOM_NOT_FOUND")
    to_room = db.get(Room, to_room_id)
    if not to_room:
        return IndoorRouteServiceResult(error_code="TO_ROOM_NOT_FOUND")
    if from_room.building_id != to_room.building_id:
        return IndoorRouteServiceResult(error_code="DIFFERENT_BUILDING_ROUTE_NOT_SUPPORTED_IN_WEEK6")
    if not from_room.nearest_indoor_node_id:
        return IndoorRouteServiceResult(error_code="FROM_ROOM_NEAREST_NODE_NOT_FOUND")
    if not to_room.nearest_indoor_node_id:
        return IndoorRouteServiceResult(error_code="TO_ROOM_NEAREST_NODE_NOT_FOUND")
    return find_indoor_node_route(
        db,
        from_room.building_id,
        from_room.nearest_indoor_node_id,
        to_room.nearest_indoor_node_id,
        route_type,
        preferences,
    )


def find_indoor_node_route(
    db: Session,
    building_id: str,
    start_indoor_node_id: str,
    end_indoor_node_id: str,
    route_type: str = "DEFAULT",
    preferences: Any | None = None,
) -> IndoorRouteServiceResult:
    # 같은 건물 안에서는 층이 달라도 하나의 건물 그래프 대상으로 탐색.
    # 층간 이동은 indoor_edges의 stair/elevator/ramp 간선으로 표현.
    nodes = db.query(IndoorNode).filter(IndoorNode.building_id == building_id).all()
    indoor_map_ids = [map_id for (map_id,) in db.query(IndoorMap.indoor_map_id).filter(IndoorMap.building_id == building_id).all()]
    edges = db.query(IndoorEdge).filter(IndoorEdge.indoor_map_id.in_(indoor_map_ids)).all()
    normalized_route_type = normalize_route_type(route_type)
    context = build_route_cost_context(normalized_route_type, preferences)
    result = dijkstra_result(nodes, edges, start_indoor_node_id, end_indoor_node_id, normalized_route_type, context)
    if not result.found:
        return IndoorRouteServiceResult(error_code="INDOOR_ROUTE_NOT_FOUND")
    node_by_id = {node.indoor_node_id: node for node in nodes}
    edge_by_id = {edge.indoor_edge_id: edge for edge in edges}
    segments = _build_indoor_segments(building_id, result, node_by_id, edge_by_id)
    return IndoorRouteServiceResult(
        payload=RouteDetailResponse(
            routeType=normalized_route_type,
            title=ROUTE_TITLES[normalized_route_type],
            totalCost=result.total_cost,
            totalDistance=result.total_distance,
            totalEstimatedTime=result.total_estimated_time,
            reason=ROUTE_REASONS[normalized_route_type],
            segments=segments,
        )
    )


def find_cross_building_indoor_route(
    db: Session,
    start_indoor_node_id: str,
    end_indoor_node_id: str,
    route_type: str = "DEFAULT",
    preferences: Any | None = None,
) -> IndoorRouteServiceResult:
    # 공학관 구름다리처럼 건물 ID는 다르지만 indoor_edges로 직접 연결된 그래프를 탐색.
    nodes = db.query(IndoorNode).all()
    edges = db.query(IndoorEdge).all()
    normalized_route_type = normalize_route_type(route_type)
    context = build_route_cost_context(normalized_route_type, preferences)
    result = dijkstra_result(nodes, edges, start_indoor_node_id, end_indoor_node_id, normalized_route_type, context)
    if not result.found:
        return IndoorRouteServiceResult(error_code="INDOOR_ROUTE_NOT_FOUND")
    node_by_id = {node.indoor_node_id: node for node in nodes}
    edge_by_id = {edge.indoor_edge_id: edge for edge in edges}
    segments = _build_indoor_segments("", result, node_by_id, edge_by_id)
    return IndoorRouteServiceResult(
        payload=RouteDetailResponse(
            routeType=normalized_route_type,
            title=ROUTE_TITLES[normalized_route_type],
            totalCost=result.total_cost,
            totalDistance=result.total_distance,
            totalEstimatedTime=result.total_estimated_time,
            reason="건물 내부 경로와 구름다리 연결을 함께 사용한 실내 연결 경로입니다.",
            segments=segments,
        )
    )


def _build_indoor_segments(
    building_id: str,
    result: PathResult,
    node_by_id: dict[str, IndoorNode],
    edge_by_id: dict[str, IndoorEdge],
) -> list[RouteSegmentResponse]:
    # 프론트는 한 번에 한 층의 실내 지도만 표시 가능.
    # Dijkstra 결과를 같은 indoorMapId/floorNumber 단위로 분리 반환.
    if not result.node_ids:
        return []

    segments: list[RouteSegmentResponse] = []
    current_node_ids = [result.node_ids[0]]
    current_edge_ids: list[str] = []

    for index, edge_id in enumerate(result.edge_ids):
        if index + 1 >= len(result.node_ids):
            break
        from_node = node_by_id.get(result.node_ids[index])
        to_node = node_by_id.get(result.node_ids[index + 1])
        edge = edge_by_id.get(edge_id)
        if not from_node or not to_node:
            continue

        is_vertical = (
            from_node.floor_number != to_node.floor_number
            or from_node.indoor_map_id != to_node.indoor_map_id
            or from_node.building_id != to_node.building_id
        )
        if is_vertical:
            # 층/지도/건물 변경 지점은 일반 실내 선이 아니라 별도 이동 안내로 분리.
            segments.append(_build_floor_segment(building_id, current_node_ids, current_edge_ids, node_by_id))
            segments.append(_build_vertical_segment(building_id, from_node, to_node, edge_id, edge))
            current_node_ids = [to_node.indoor_node_id]
            current_edge_ids = []
            continue

        current_node_ids.append(to_node.indoor_node_id)
        current_edge_ids.append(edge_id)

    segments.append(_build_floor_segment(building_id, current_node_ids, current_edge_ids, node_by_id))
    return [segment for segment in segments if segment.pathPoints]


def _build_floor_segment(
    building_id: str,
    node_ids: list[str],
    edge_ids: list[str],
    node_by_id: dict[str, IndoorNode],
) -> RouteSegmentResponse:
    # INDOOR 세그먼트의 pathPoints는 반드시 같은 지도 좌표계 유지.
    first_node = node_by_id[node_ids[0]]
    return RouteSegmentResponse(
        type="INDOOR",
        buildingId=first_node.building_id or building_id,
        floorNumber=first_node.floor_number,
        indoorMapId=first_node.indoor_map_id,
        instruction=f"{first_node.floor_number}층 실내 경로를 따라 이동하세요.",
        nodeIds=node_ids,
        edgeIds=edge_ids,
        pathPoints=[
            RoutePoint(
                nodeId=node_id,
                pointType="NODE",
                x=node_by_id[node_id].x,
                y=node_by_id[node_id].y,
                floorNumber=node_by_id[node_id].floor_number,
                indoorMapId=node_by_id[node_id].indoor_map_id,
                label=node_by_id[node_id].label,
            )
            for node_id in node_ids
            if node_id in node_by_id
        ],
    )


def _build_vertical_segment(
    building_id: str,
    from_node: IndoorNode,
    to_node: IndoorNode,
    edge_id: str,
    edge: IndoorEdge | None,
) -> RouteSegmentResponse:
    # VERTICAL 세그먼트는 프론트가 선으로 억지 연결하지 않고 "층 이동 안내"로 표현하기 위한 구간.
    transition_type = _transition_type(edge, from_node, to_node)
    transition_label = {
        "ELEVATOR": "엘리베이터",
        "STAIRS": "계단",
        "RAMP": "경사로",
        "BRIDGE": "구름다리",
    }.get(transition_type, "층간 이동 통로")
    if transition_type == "BRIDGE":
        instruction = f"{transition_label}를 이용해 {from_node.floor_number}층에서 {to_node.floor_number}층 연결 구간으로 이동하세요."
    else:
        instruction = f"{transition_label}를 이용해 {from_node.floor_number}층에서 {to_node.floor_number}층으로 이동하세요."
    return RouteSegmentResponse(
        type="VERTICAL",
        buildingId=from_node.building_id or building_id,
        floorNumber=from_node.floor_number,
        indoorMapId=from_node.indoor_map_id,
        toFloorNumber=to_node.floor_number,
        toIndoorMapId=to_node.indoor_map_id,
        transitionType=transition_type,
        instruction=instruction,
        nodeIds=[from_node.indoor_node_id, to_node.indoor_node_id],
        edgeIds=[edge_id],
        pathPoints=[
            _indoor_route_point(from_node, edge_id),
            _indoor_route_point(to_node, edge_id),
        ],
    )


def _transition_type(edge: IndoorEdge | None, from_node: IndoorNode, to_node: IndoorNode) -> str:
    # DB edge_type이 비어 있어도 node_type을 함께 확인해 계단/엘리베이터 안정 판별.
    edge_type = str(getattr(edge, "edge_type", "") or "").upper()
    node_types = {str(from_node.node_type).upper(), str(to_node.node_type).upper()}
    if getattr(edge, "is_elevator", False) or edge_type == "ELEVATOR" or "ELEVATOR" in node_types:
        return "ELEVATOR"
    if getattr(edge, "has_stairs", False) or edge_type in {"STAIR", "STAIRS"} or node_types & {"STAIR", "STAIRS"}:
        return "STAIRS"
    if getattr(edge, "is_ramp", False) or edge_type == "RAMP" or "RAMP" in node_types:
        return "RAMP"
    if edge_type in {"BRIDGE", "COVERED_BRIDGE"} or "BRIDGE" in node_types:
        return "BRIDGE"
    return edge_type or "VERTICAL"


def _indoor_route_point(node: IndoorNode, edge_id: str | None = None) -> RoutePoint:
    return RoutePoint(
        nodeId=node.indoor_node_id,
        sourceEdgeId=edge_id,
        pointType="NODE",
        x=node.x,
        y=node.y,
        floorNumber=node.floor_number,
        indoorMapId=node.indoor_map_id,
        label=node.label,
    )
