from dataclasses import dataclass, field
from heapq import heappop, heappush
from typing import Any

from app.algorithms.cost_function import RouteCostContext, build_route_cost_context, calculate_dynamic_edge_cost


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
    node_ids = {_node_id(node) for node in nodes}
    if start_node_id not in node_ids or end_node_id not in node_ids:
        return PathResult(found=False)

    cost_context = context or build_route_cost_context(route_type)
    graph = _build_graph(edges, cost_context)
    distances = {start_node_id: 0.0}
    previous_node: dict[str, str] = {}
    previous_edge: dict[str, Any] = {}
    queue: list[tuple[float, str]] = [(0.0, start_node_id)]

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
) -> list[str]:
    # 실제 DB 조회는 app.services.indoor_graph.find_indoor_node_route에서 담당한다.
    raise NotImplementedError("Use app.services.indoor_graph.find_indoor_node_route for DB-backed routing.")


def find_outdoor_path(
    start_outdoor_node_id: str,
    end_outdoor_node_id: str,
    route_type: str = "DEFAULT",
) -> list[str]:
    # 7주차 외부 그래프 서비스에서 DB와 연결한다.
    raise NotImplementedError("Outdoor pathfinding is connected in the week 7 outdoor graph service.")


def _build_graph(edges: list[Any], context: RouteCostContext) -> dict[str, list[tuple[str, Any, float]]]:
    graph: dict[str, list[tuple[str, Any, float]]] = {}
    for edge in edges:
        from_node_id = str(getattr(edge, "from_node_id"))
        to_node_id = str(getattr(edge, "to_node_id"))
        edge_cost = calculate_dynamic_edge_cost(edge, context)
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
