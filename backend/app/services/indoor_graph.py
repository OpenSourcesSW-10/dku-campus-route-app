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
    nodes = db.query(IndoorNode).filter(IndoorNode.building_id == building_id).all()
    indoor_map_ids = [map_id for (map_id,) in db.query(IndoorMap.indoor_map_id).filter(IndoorMap.building_id == building_id).all()]
    edges = db.query(IndoorEdge).filter(IndoorEdge.indoor_map_id.in_(indoor_map_ids)).all()
    normalized_route_type = normalize_route_type(route_type)
    context = build_route_cost_context(normalized_route_type, preferences)
    result = dijkstra_result(nodes, edges, start_indoor_node_id, end_indoor_node_id, normalized_route_type, context)
    if not result.found:
        return IndoorRouteServiceResult(error_code="INDOOR_ROUTE_NOT_FOUND")
    node_by_id = {node.indoor_node_id: node for node in nodes}
    segment = _build_indoor_segment(building_id, result, node_by_id)
    return IndoorRouteServiceResult(
        payload=RouteDetailResponse(
            routeType=normalized_route_type,
            title=ROUTE_TITLES[normalized_route_type],
            totalCost=result.total_cost,
            totalDistance=result.total_distance,
            totalEstimatedTime=result.total_estimated_time,
            reason=ROUTE_REASONS[normalized_route_type],
            segments=[segment],
        )
    )


def _build_indoor_segment(building_id: str, result: PathResult, node_by_id: dict[str, IndoorNode]) -> RouteSegmentResponse:
    first_node = node_by_id[result.node_ids[0]]
    return RouteSegmentResponse(
        type="INDOOR",
        buildingId=building_id,
        floorNumber=first_node.floor_number,
        indoorMapId=first_node.indoor_map_id,
        nodeIds=result.node_ids,
        edgeIds=result.edge_ids,
        pathPoints=[
            RoutePoint(
                nodeId=node_id,
                x=node_by_id[node_id].x,
                y=node_by_id[node_id].y,
                floorNumber=node_by_id[node_id].floor_number,
                indoorMapId=node_by_id[node_id].indoor_map_id,
                label=node_by_id[node_id].label,
            )
            for node_id in result.node_ids
            if node_id in node_by_id
        ],
    )
