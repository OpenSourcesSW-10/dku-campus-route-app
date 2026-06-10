"""
Shared pathfinding utilities.

실내/외부 경로 서비스는 모두 같은 Dijkstra 구현 사용.
그래프의 의미는 서비스 계층에서 결정, 이 파일은 노드/간선/비용만 받아
가장 낮은 비용의 node sequence와 edge sequence 계산.
"""

from dataclasses import dataclass, field
from heapq import heappop, heappush
from typing import Any

from app.algorithms.cost_function import BLOCKED_COST, RouteCostContext, build_route_cost_context, calculate_dynamic_edge_cost


@dataclass
class PathResult:
    found: bool
    node_ids: list[str] = field(default_factory=list)
    edge_ids: list[str] = field(default_factory=list)
    total_cost: float = 0.0
    total_distance: float = 0.0
    total_estimated_time: float = 0.0


def dijkstra(
    nodes: list[Any],
    edges: list[Any],
    start_node_id: str,
    end_node_id: str,
    route_type: str = "DEFAULT",
    context: RouteCostContext | None = None,
) -> list[str]:
    result = dijkstra_result(nodes, edges, start_node_id, end_node_id, route_type, context)
    return result.node_ids


def dijkstra_result(
    nodes: list[Any],
    edges: list[Any],
    start_node_id: str,
    end_node_id: str,
    route_type: str = "DEFAULT",
    context: RouteCostContext | None = None,
) -> PathResult:
    # 시작/도착 노드가 그래프에 없으면 예외 대신 found=False 반환, API 계층에서 404로 변환.
    node_ids = {_node_id(node) for node in nodes}
    if start_node_id not in node_ids or end_node_id not in node_ids:
        return PathResult(found=False)

    cost_context = context or build_route_cost_context(route_type)
    graph = _build_graph(edges, cost_context)
    distances = {start_node_id: 0.0}
    previous_node: dict[str, str] = {}
    previous_edge: dict[str, Any] = {}
    queue: list[tuple[float, str]] = [(0.0, start_node_id)]

    # priority queue에는 현재까지 발견된 누적 비용이 낮은 후보부터 삽입.
    while queue:
        current_cost, current_node_id = heappop(queue)
        if current_node_id == end_node_id:
            break
        if current_cost > distances.get(current_node_id, float("inf")):
            continue

        for next_node_id, edge, edge_cost in graph.get(current_node_id, []):
            candidate_cost = current_cost + edge_cost
            if candidate_cost < distances.get(next_node_id, float("inf")):
                distances[next_node_id] = candidate_cost
                previous_node[next_node_id] = current_node_id
                previous_edge[next_node_id] = edge
                heappush(queue, (candidate_cost, next_node_id))

    if end_node_id not in distances:
        return PathResult(found=False)

    path_node_ids = _reconstruct_nodes(start_node_id, end_node_id, previous_node)
    path_edges = [previous_edge[node_id] for node_id in path_node_ids[1:] if node_id in previous_edge]
    return PathResult(
        found=True,
        node_ids=path_node_ids,
        edge_ids=[_edge_id(edge) for edge in path_edges],
        total_cost=distances[end_node_id],
        total_distance=sum(float(getattr(edge, "distance", 0) or 0) for edge in path_edges),
        total_estimated_time=sum(float(getattr(edge, "estimated_time", 0) or 0) for edge in path_edges),
    )


def find_indoor_path(
    indoor_map_id: str,
    start_indoor_node_id: str,
    end_indoor_node_id: str,
    route_type: str = "DEFAULT",
    db=None,
) -> list[str]:
    """DB-backed indoor path compatibility wrapper.

    New code should use ``app.services.indoor_graph.find_indoor_node_route``
    when it also needs segment coordinates and route metadata.
    """
    # 과거 주차 코드 호출 시에도 최신 DB 기반 서비스로 연결되도록 남겨둔 호환 wrapper.
    from app.database import SessionLocal
    from app.models import IndoorMap
    from app.services.indoor_graph import find_indoor_node_route

    owns_session = db is None
    session = db or SessionLocal()
    try:
        indoor_map = session.get(IndoorMap, indoor_map_id)
        if not indoor_map:
            return []
        result = find_indoor_node_route(
            session,
            indoor_map.building_id,
            start_indoor_node_id,
            end_indoor_node_id,
            route_type,
        )
        return _payload_node_ids(result.payload)
    finally:
        if owns_session:
            session.close()


def find_outdoor_path(
    start_outdoor_node_id: str,
    end_outdoor_node_id: str,
    route_type: str = "DEFAULT",
    db=None,
) -> list[str]:
    """DB-backed outdoor path compatibility wrapper."""
    # 외부 경로의 실제 구현은 services.outdoor_graph가 담당.
    # 테스트/이전 코드에서 node id 목록만 필요할 때 사용.
    from app.database import SessionLocal
    from app.services.outdoor_graph import find_outdoor_route

    owns_session = db is None
    session = db or SessionLocal()
    try:
        result = find_outdoor_route(session, start_outdoor_node_id, end_outdoor_node_id, route_type)
        return _payload_node_ids(result.payload)
    finally:
        if owns_session:
            session.close()


def _build_graph(edges: list[Any], context: RouteCostContext) -> dict[str, list[tuple[str, Any, float]]]:
    graph: dict[str, list[tuple[str, Any, float]]] = {}
    for edge in edges:
        from_node_id = str(getattr(edge, "from_node_id"))
        to_node_id = str(getattr(edge, "to_node_id"))
        edge_cost = calculate_dynamic_edge_cost(edge, context)
        if edge_cost >= BLOCKED_COST:
            # 접근성 모드에서 계단처럼 사용할 수 없는 간선은 "비싸지만 가능"이 아니라 탐색 후보에서 제외.
            continue
        graph.setdefault(from_node_id, []).append((to_node_id, edge, edge_cost))
        if getattr(edge, "is_bidirectional", True):
            graph.setdefault(to_node_id, []).append((from_node_id, edge, edge_cost))
    return graph


def _reconstruct_nodes(start_node_id: str, end_node_id: str, previous_node: dict[str, str]) -> list[str]:
    current = end_node_id
    reversed_path = [current]
    while current != start_node_id:
        current = previous_node[current]
        reversed_path.append(current)
    return list(reversed(reversed_path))


def _node_id(node: Any) -> str:
    return str(
        getattr(node, "node_id", None)
        or getattr(node, "indoor_node_id", None)
        or getattr(node, "outdoor_node_id", None)
    )


def _edge_id(edge: Any) -> str:
    return str(
        getattr(edge, "edge_id", None)
        or getattr(edge, "indoor_edge_id", None)
        or getattr(edge, "outdoor_edge_id", None)
    )


def _payload_node_ids(payload: Any | None) -> list[str]:
    if payload is None:
        return []

    node_ids: list[str] = []
    for segment in payload.segments:
        for node_id in segment.nodeIds:
            if not node_ids or node_ids[-1] != node_id:
                node_ids.append(node_id)
    return node_ids
