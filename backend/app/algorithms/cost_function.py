"""
Week 3 dynamic cost function skeleton.

DCF is completed later, but the backend already exposes the intended function
shape: edge attributes + route_weight_profiles + optional user preferences.
"""

from typing import Any


def calculate_edge_cost(edge: Any, weights: Any, preferences: dict | None = None) -> float:
    # 간선 속성과 경로 옵션별 가중치를 합쳐 Dijkstra에서 사용할 비용을 만든다.
    cost = 0.0
    cost += getattr(edge, "distance", 0) * getattr(weights, "weight_distance", 1)
    cost += getattr(edge, "estimated_time", 0) * getattr(weights, "weight_time", 1)
    cost += _boolean_penalty(edge, weights, "has_stairs", "penalty_stairs")
    cost += getattr(edge, "slope_level", 0) * getattr(weights, "penalty_slope", 0)
    cost += getattr(edge, "complexity_level", 0) * getattr(weights, "penalty_complexity", 0)

    if not getattr(edge, "is_covered", True):
        cost += getattr(weights, "penalty_uncovered", 0)
    if not getattr(edge, "is_indoor", False):
        cost += getattr(weights, "penalty_outdoor", 0)

    cost -= _boolean_bonus(edge, weights, "is_indoor", "bonus_indoor")
    cost -= _boolean_bonus(edge, weights, "is_covered", "bonus_covered")
    cost -= _boolean_bonus(edge, weights, "is_elevator", "bonus_elevator")
    cost -= _boolean_bonus(edge, weights, "is_ramp", "bonus_ramp")
    cost -= _boolean_bonus(edge, weights, "is_shortcut", "bonus_shortcut")

    edge_type = getattr(edge, "edge_type", "")
    if edge_type == "BUILDING_PASSAGE":
        cost -= getattr(weights, "bonus_building_passage", 0)
    if edge_type in {"BRIDGE", "COVERED_BRIDGE"}:
        cost -= getattr(weights, "bonus_bridge", 0)

    cost += _preference_penalty(edge, preferences or {})
    return max(cost, 1.0)


def _boolean_penalty(edge: Any, weights: Any, edge_attr: str, weight_attr: str) -> float:
    # 간선 속성이 True일 때만 해당 패널티를 더한다.
    return getattr(weights, weight_attr, 0) if getattr(edge, edge_attr, False) else 0.0


def _boolean_bonus(edge: Any, weights: Any, edge_attr: str, weight_attr: str) -> float:
    # 간선 속성이 True일 때만 해당 보너스를 비용에서 뺀다.
    return getattr(weights, weight_attr, 0) if getattr(edge, edge_attr, False) else 0.0


def _preference_penalty(edge: Any, preferences: dict) -> float:
    # 사용자 선호 옵션이 켜졌을 때 피해야 할 구간의 비용을 크게 올린다.
    penalty = 0.0
    if preferences.get("avoidStairs") and getattr(edge, "has_stairs", False):
        penalty += 1000
    if preferences.get("preferIndoor") and not getattr(edge, "is_indoor", False):
        penalty += 80
    if preferences.get("rainMode") and not getattr(edge, "is_covered", True):
        penalty += 120
    if preferences.get("accessibilityMode") and not getattr(edge, "is_accessible", True):
        penalty += 1000
    return penalty
