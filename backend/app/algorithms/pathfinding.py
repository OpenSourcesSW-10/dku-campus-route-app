"""
Week 3 pathfinding skeleton.

Actual indoor Dijkstra is scheduled for week 5, and integrated outdoor +
indoor routing is scheduled for week 6. For week 3 we keep the function
signatures stable so API and DB work can grow without reshuffling files.
"""

from typing import Any


def dijkstra(
    nodes: list[Any],
    edges: list[Any],
    start_node_id: str,
    end_node_id: str,
    route_type: str = "FAST",
) -> list[str]:
    # 5주차에 DCF 기반 최단 경로 탐색으로 채울 예정인 자리이다.
    raise NotImplementedError("Dijkstra implementation is scheduled for week 5.")


def find_indoor_path(
    indoor_map_id: str,
    start_indoor_node_id: str,
    end_indoor_node_id: str,
    route_type: str = "FAST",
) -> list[str]:
    # 실내 지도 노드와 간선을 이용한 경로 계산 자리이다.
    raise NotImplementedError("Indoor pathfinding is scheduled for week 5.")


def find_outdoor_path(
    start_outdoor_node_id: str,
    end_outdoor_node_id: str,
    route_type: str = "FAST",
) -> list[str]:
    # 캠퍼스 실외 노드와 간선을 이용한 경로 계산 자리이다.
    raise NotImplementedError("Outdoor pathfinding is scheduled for week 6.")
