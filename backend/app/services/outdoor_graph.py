from dataclasses import dataclass
from math import hypot

from sqlalchemy.orm import Session

from app.algorithms.cost_function import build_route_cost_context, normalize_route_type
from app.algorithms.pathfinding import PathResult, dijkstra_result
from app.models import OutdoorEdge, OutdoorNode
from app.schemas.routes import RouteDetailResponse, RoutePoint, RouteSegmentResponse


ROUTE_TITLES = {
    "DEFAULT": "기본 경로",
    "COMFORTABLE": "편한 길",
    "RAINY": "비 오는 날",
}

OUTDOOR_REASONS = {
    "DEFAULT": "외부 보행로 그래프를 기준으로 계산한 기본 외부 경로입니다.",
    "COMFORTABLE": "계단과 경사 비용을 반영한 외부 경로입니다.",
    "RAINY": "비가림 여부와 실내/지붕 통로 선호를 반영한 외부 경로입니다.",
}


@dataclass
class OutdoorRouteServiceResult:
    payload: RouteDetailResponse | None = None
    error_code: str | None = None


def find_outdoor_route(
    db: Session,
    start_outdoor_node_id: str,
    end_outdoor_node_id: str,
    route_type: str = "DEFAULT",
    preferences=None,
) -> OutdoorRouteServiceResult:
    nodes = db.query(OutdoorNode).all()
    edges = db.query(OutdoorEdge).all()
    normalized_route_type = normalize_route_type(route_type)
    if not edges:
        return _fallback_direct_outdoor_route(nodes, start_outdoor_node_id, end_outdoor_node_id, normalized_route_type)

    context = build_route_cost_context(normalized_route_type, preferences)
    result = dijkstra_result(nodes, edges, start_outdoor_node_id, end_outdoor_node_id, normalized_route_type, context)
    if not result.found:
        return OutdoorRouteServiceResult(error_code="OUTDOOR_ROUTE_NOT_FOUND")

    node_by_id = {node.outdoor_node_id: node for node in nodes}
    segment = _build_outdoor_segment(result, node_by_id)
    return OutdoorRouteServiceResult(
        payload=RouteDetailResponse(
            routeType=normalized_route_type,
            title=ROUTE_TITLES[normalized_route_type],
            totalCost=result.total_cost,
            totalDistance=result.total_distance,
            totalEstimatedTime=result.total_estimated_time,
            reason=OUTDOOR_REASONS[normalized_route_type],
            segments=[segment],
        )
    )


def _build_outdoor_segment(result: PathResult, node_by_id: dict[str, OutdoorNode]) -> RouteSegmentResponse:
    return RouteSegmentResponse(
        type="OUTDOOR",
        nodeIds=result.node_ids,
        edgeIds=result.edge_ids,
        pathPoints=[
            RoutePoint(
                nodeId=node_id,
                x=node_by_id[node_id].map_x,
                y=node_by_id[node_id].map_y,
                latitude=node_by_id[node_id].latitude,
                longitude=node_by_id[node_id].longitude,
                label=node_by_id[node_id].label,
            )
            for node_id in result.node_ids
            if node_id in node_by_id
        ],
    )


def _fallback_direct_outdoor_route(
    nodes: list[OutdoorNode],
    start_outdoor_node_id: str,
    end_outdoor_node_id: str,
    route_type: str,
) -> OutdoorRouteServiceResult:
    node_by_id = {node.outdoor_node_id: node for node in nodes}
    start = node_by_id.get(start_outdoor_node_id)
    end = node_by_id.get(end_outdoor_node_id)
    if not start or not end:
        return OutdoorRouteServiceResult(error_code="OUTDOOR_ROUTE_NOT_FOUND")

    distance = _direct_distance(start, end)
    estimated_time = distance / 1.2 if distance else 0.0
    segment = RouteSegmentResponse(
        type="OUTDOOR",
        nodeIds=[start_outdoor_node_id, end_outdoor_node_id],
        edgeIds=[],
        pathPoints=[
            RoutePoint(
                nodeId=start.outdoor_node_id,
                x=start.map_x,
                y=start.map_y,
                latitude=start.latitude,
                longitude=start.longitude,
                label=start.label,
            ),
            RoutePoint(
                nodeId=end.outdoor_node_id,
                x=end.map_x,
                y=end.map_y,
                latitude=end.latitude,
                longitude=end.longitude,
                label=end.label,
            ),
        ],
    )
    return OutdoorRouteServiceResult(
        payload=RouteDetailResponse(
            routeType=route_type,
            title=ROUTE_TITLES[route_type],
            totalCost=max(distance + estimated_time, 1.0),
            totalDistance=distance,
            totalEstimatedTime=estimated_time,
            reason="outdoor_edges 자료가 아직 없어 외부 노드 사이를 임시 직선 세그먼트로 연결했습니다.",
            segments=[segment],
        )
    )


def _direct_distance(start: OutdoorNode, end: OutdoorNode) -> float:
    if start.map_x is not None and start.map_y is not None and end.map_x is not None and end.map_y is not None:
        return hypot(end.map_x - start.map_x, end.map_y - start.map_y)
    if start.latitude is not None and start.longitude is not None and end.latitude is not None and end.longitude is not None:
        return hypot(end.latitude - start.latitude, end.longitude - start.longitude) * 111_000
    return 1.0
