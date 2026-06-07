"""
Outdoor routing service.

외부 노드/간선 그래프에서 경로 계산.
선택된 간선의 상세 geometry를 프론트 지도 Polyline용 pathPoints로 변환.
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.algorithms.cost_function import build_route_cost_context, normalize_route_type
from app.algorithms.pathfinding import PathResult, dijkstra_result
from app.models import OutdoorEdge, OutdoorNode
from app.schemas.routes import RouteDetailResponse, RoutePoint, RouteSegmentResponse
from app.services.route_geometry import GeometryPoint, edge_geometry_points, same_point


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
    # 외부 간선이 없으면 실제 길 계산 근거 없음. 임시 직선을 성공 경로로 만들지 않음.
    nodes = db.query(OutdoorNode).all()
    edges = db.query(OutdoorEdge).all()
    normalized_route_type = normalize_route_type(route_type)
    if not edges:
        return OutdoorRouteServiceResult(error_code="OUTDOOR_ROUTE_NOT_FOUND")

    context = build_route_cost_context(normalized_route_type, preferences)
    result = dijkstra_result(nodes, edges, start_outdoor_node_id, end_outdoor_node_id, normalized_route_type, context)
    if not result.found:
        return OutdoorRouteServiceResult(error_code="OUTDOOR_ROUTE_NOT_FOUND")

    node_by_id = {node.outdoor_node_id: node for node in nodes}
    edge_by_id = {edge.outdoor_edge_id: edge for edge in edges}
    segment = _build_outdoor_segment(result, node_by_id, edge_by_id)
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


def _build_outdoor_segment(
    result: PathResult,
    node_by_id: dict[str, OutdoorNode],
    edge_by_id: dict[str, OutdoorEdge],
) -> RouteSegmentResponse:
    # edgeIds 순서와 nodeIds 순서를 함께 사용해 각 간선의 상세 좌표를 실제 이동 방향대로 연결.
    path_points: list[RoutePoint] = []
    for index, edge_id in enumerate(result.edge_ids):
        if index + 1 >= len(result.node_ids):
            break
        from_node = node_by_id.get(result.node_ids[index])
        to_node = node_by_id.get(result.node_ids[index + 1])
        edge = edge_by_id.get(edge_id)
        if not from_node or not to_node or not edge:
            continue
        edge_points = _edge_route_points(edge, from_node, to_node)
        if path_points and edge_points and _same_route_point(path_points[-1], edge_points[0]):
            # 인접 간선의 끝점/시작점이 같으면 중복 점 제거. 프론트 polyline 흔들림 방지.
            edge_points = edge_points[1:]
        path_points.extend(edge_points)

    if not path_points:
        path_points = [_node_route_point(node_by_id[node_id]) for node_id in result.node_ids if node_id in node_by_id]

    return RouteSegmentResponse(
        type="OUTDOOR",
        nodeIds=result.node_ids,
        edgeIds=result.edge_ids,
        pathPoints=path_points,
    )


def _edge_route_points(edge: OutdoorEdge, from_node: OutdoorNode, to_node: OutdoorNode) -> list[RoutePoint]:
    # 잘못된 polyline이 DB에 들어와도 API 전체 실패 방지. 해당 간선만 노드 직선으로 fallback.
    try:
        geometry_points = edge_geometry_points(edge, from_node, to_node)
    except ValueError:
        geometry_points = [
            GeometryPoint(x=from_node.map_x, y=from_node.map_y, latitude=from_node.latitude, longitude=from_node.longitude),
            GeometryPoint(x=to_node.map_x, y=to_node.map_y, latitude=to_node.latitude, longitude=to_node.longitude),
        ]

    route_points: list[RoutePoint] = []
    for index, point in enumerate(geometry_points):
        is_start = index == 0
        is_end = index == len(geometry_points) - 1
        node = from_node if is_start else to_node if is_end else None
        route_points.append(
            RoutePoint(
                nodeId=node.outdoor_node_id if node else f"{edge.outdoor_edge_id}:shape:{index}",
                sourceEdgeId=edge.outdoor_edge_id,
                # NODE는 실제 그래프 노드, SHAPE는 길 모양을 만들기 위한 중간 좌표.
                pointType="NODE" if node else "SHAPE",
                x=point.x,
                y=point.y,
                latitude=point.latitude,
                longitude=point.longitude,
                label=node.label if node else None,
            )
        )
    return route_points


def _node_route_point(node: OutdoorNode) -> RoutePoint:
    return RoutePoint(
        nodeId=node.outdoor_node_id,
        pointType="NODE",
        x=node.map_x,
        y=node.map_y,
        latitude=node.latitude,
        longitude=node.longitude,
        label=node.label,
    )


def _same_route_point(first: RoutePoint, second: RoutePoint) -> bool:
    # RoutePoint를 geometry 비교 함수로 넘기기 위한 얇은 adapter.
    return same_point(
        GeometryPoint(x=first.x, y=first.y, latitude=first.latitude, longitude=first.longitude),
        GeometryPoint(x=second.x, y=second.y, latitude=second.latitude, longitude=second.longitude),
    )
