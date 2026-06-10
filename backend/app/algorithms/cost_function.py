"""
Dynamic Cost Function for campus routing.

DB에는 거리, 계단, 경사, 비가림 여부처럼 사실 데이터만 저장.
사용자가 선택한 경로 타입에 따라 실제 비용은 요청 시점에 계산함.
이 구조를 유지하면 같은 그래프 자료로 기본 경로, 편한 길, 비 오는 날 경로를
서로 다른 기준으로 계산 가능.
"""

from dataclasses import dataclass
from typing import Any


BLOCKED_COST = 1_000_000_000.0

ROUTE_TYPE_ALIASES = {
    "FAST": "DEFAULT",
    "BASIC": "DEFAULT",
    "NORMAL": "DEFAULT",
    "DEFAULT": "DEFAULT",
    "COMFORT": "COMFORTABLE",
    "COMFORTABLE": "COMFORTABLE",
    "EASY": "COMFORTABLE",
    "RAIN": "RAINY",
    "RAINY": "RAINY",
    "RAIN_SAFE": "RAINY",
    "INDOOR": "RAINY",
    "INDOOR_FOCUSED": "RAINY",
}


@dataclass
class RouteCostContext:
    route_type: str = "DEFAULT"
    weight_distance: float = 1.0
    weight_time: float = 1.0
    penalty_stairs: float = 0.0
    penalty_slope: float = 0.0
    penalty_complexity: float = 0.0
    penalty_uncovered: float = 0.0
    penalty_outdoor: float = 0.0
    bonus_indoor: float = 0.0
    bonus_covered: float = 0.0
    bonus_elevator: float = 0.0
    bonus_ramp: float = 0.0
    bonus_shortcut: float = 0.0
    bonus_building_passage: float = 0.0
    bonus_bridge: float = 0.0
    avoid_stairs: bool = False
    avoid_slope: bool = False
    prefer_indoor: bool = False
    rain_mode: bool = False
    accessibility_mode: bool = False


STATIC_COST_FIELDS = {
    "DEFAULT": "cost_fast",
    "COMFORTABLE": "cost_comfortable",
    "RAINY": "cost_indoor",
}


DEFAULT_CONTEXTS = {
    # 기본 경로: 거리와 시간 우선, 계단/경사도 완전히 무시하지 않음.
    "DEFAULT": RouteCostContext(
        route_type="DEFAULT",
        weight_distance=1.0,
        weight_time=1.2,
        penalty_stairs=8.0,
        penalty_slope=6.0,
        penalty_complexity=4.0,
        penalty_uncovered=2.0,
        penalty_outdoor=0.0,
    ),
    # 편한 길: 조금 돌아가더라도 계단과 경사 비용을 크게 반영함.
    "COMFORTABLE": RouteCostContext(
        route_type="COMFORTABLE",
        weight_distance=1.0,
        weight_time=1.0,
        penalty_stairs=80.0,
        penalty_slope=45.0,
        penalty_complexity=15.0,
        penalty_uncovered=10.0,
        penalty_outdoor=5.0,
        bonus_elevator=25.0,
        bonus_ramp=20.0,
        bonus_shortcut=8.0,
    ),
    # 비 오는 날 경로: 지붕/건물 내부/구름다리처럼 비를 피할 수 있는 간선 선호.
    "RAINY": RouteCostContext(
        route_type="RAINY",
        weight_distance=1.0,
        weight_time=1.0,
        penalty_stairs=15.0,
        penalty_slope=10.0,
        penalty_complexity=8.0,
        penalty_uncovered=90.0,
        penalty_outdoor=55.0,
        bonus_indoor=25.0,
        bonus_covered=35.0,
        bonus_building_passage=35.0,
        bonus_bridge=25.0,
        rain_mode=True,
        prefer_indoor=True,
    ),
}


def normalize_route_type(route_type: str | None) -> str:
    return ROUTE_TYPE_ALIASES.get((route_type or "DEFAULT").upper(), "DEFAULT")


def build_route_cost_context(
    route_type: str = "DEFAULT",
    preferences: Any | None = None,
    weights: Any | None = None,
) -> RouteCostContext:
    # 기본 profile 복사 후 관리자/사용자 설정으로 덮어씀.
    # 전역 DEFAULT_CONTEXTS 객체 직접 수정 방지를 위해 새 context 생성.
    normalized = normalize_route_type(route_type)
    base = DEFAULT_CONTEXTS[normalized]
    context = RouteCostContext(**base.__dict__)
    _apply_weight_profile(context, weights)
    _apply_preferences(context, preferences)
    return context


def calculate_dynamic_edge_cost(edge: Any, context: RouteCostContext) -> float:
    # 닫힌 길/접근성 모드에서 사용할 수 없는 길은 그래프 탐색 제외용 큰 비용 반환.
    if getattr(edge, "is_closed", False):
        return BLOCKED_COST
    if context.accessibility_mode and (not getattr(edge, "is_accessible", True) or getattr(edge, "has_stairs", False)):
        return BLOCKED_COST

    distance = float(getattr(edge, "distance", 0) or 0)
    estimated_time = float(getattr(edge, "estimated_time", 0) or 0)
    slope_level = float(getattr(edge, "slope_level", 0) or 0)
    complexity_level = float(getattr(edge, "complexity_level", 0) or 0)
    edge_type = str(getattr(edge, "edge_type", "") or "").upper()

    # 비용은 실제 거리/시간 기반으로 시작, 이후 길 성격에 따라 penalty/bonus 조정.
    cost = max(distance, 0.0) * context.weight_distance
    cost += max(estimated_time, 0.0) * context.weight_time
    cost += complexity_level * context.penalty_complexity

    if getattr(edge, "has_stairs", False):
        cost += context.penalty_stairs
    if getattr(edge, "has_slope", False):
        cost += max(slope_level, 1.0) * context.penalty_slope

    if not getattr(edge, "is_covered", True):
        cost += context.penalty_uncovered
    if not getattr(edge, "is_indoor", False):
        cost += context.penalty_outdoor

    if getattr(edge, "is_indoor", False):
        cost -= context.bonus_indoor
    if getattr(edge, "is_covered", False):
        cost -= context.bonus_covered
    if getattr(edge, "is_elevator", False):
        cost -= context.bonus_elevator
    if getattr(edge, "is_ramp", False) or edge_type == "RAMP":
        cost -= context.bonus_ramp
    if getattr(edge, "is_shortcut", False):
        cost -= context.bonus_shortcut

    if edge_type == "BUILDING_PASSAGE":
        cost -= context.bonus_building_passage
    if edge_type in {"BRIDGE", "COVERED_BRIDGE"}:
        cost -= context.bonus_bridge

    cost += _preference_penalty(edge, context)
    return max(cost, 1.0)


def get_static_edge_cost(edge: Any, route_type: str = "DEFAULT") -> float:
    # 기존 정적 DCF 컬럼은 fallback과 과거 데이터 호환용으로 유지.
    field_name = STATIC_COST_FIELDS.get(normalize_route_type(route_type), "cost_fast")
    cost = getattr(edge, field_name, None)
    if cost is None or cost <= 0:
        cost = estimate_static_edge_cost(edge, route_type)
    return max(float(cost), 1.0)


def estimate_static_edge_cost(edge: Any, route_type: str = "DEFAULT") -> float:
    context = build_route_cost_context(route_type)
    return calculate_dynamic_edge_cost(edge, context)


def calculate_edge_cost(edge: Any, weights: Any, preferences: dict | None = None) -> float:
    # 3~5주차 코드와의 호환용 wrapper.
    context = build_route_cost_context(getattr(weights, "route_type", "DEFAULT"), preferences, weights)
    return calculate_dynamic_edge_cost(edge, context)


def _apply_weight_profile(context: RouteCostContext, weights: Any | None) -> None:
    # RouteWeightProfile 같은 DB 기반 profile 입력 시 기본 DCF 가중치 교체.
    if weights is None:
        return
    for field_name in (
        "weight_distance",
        "weight_time",
        "penalty_stairs",
        "penalty_slope",
        "penalty_complexity",
        "penalty_uncovered",
        "penalty_outdoor",
        "bonus_indoor",
        "bonus_covered",
        "bonus_elevator",
        "bonus_ramp",
        "bonus_shortcut",
        "bonus_building_passage",
        "bonus_bridge",
    ):
        value = getattr(weights, field_name, None)
        if value is not None:
            setattr(context, field_name, float(value))


def _apply_preferences(context: RouteCostContext, preferences: Any | None) -> None:
    # API 요청의 개인 선호 옵션은 route type보다 더 구체적인 조건으로 반영.
    if preferences is None:
        return
    context.avoid_stairs = _pref(preferences, "avoidStairs", context.avoid_stairs)
    context.avoid_slope = _pref(preferences, "avoidSlope", context.avoid_slope)
    context.prefer_indoor = _pref(preferences, "preferIndoor", context.prefer_indoor)
    context.rain_mode = _pref(preferences, "rainMode", context.rain_mode)
    context.accessibility_mode = _pref(preferences, "accessibilityMode", context.accessibility_mode)


def _preference_penalty(edge: Any, context: RouteCostContext) -> float:
    # 사용자가 명시적으로 피하고 싶은 조건은 route type 기본값보다 더 강한 벌점 적용.
    penalty = 0.0
    if context.avoid_stairs and getattr(edge, "has_stairs", False):
        penalty += 1000.0
    if context.avoid_slope and getattr(edge, "has_slope", False):
        penalty += 500.0
    if context.prefer_indoor and not getattr(edge, "is_indoor", False):
        penalty += 70.0
    if context.rain_mode and not getattr(edge, "is_covered", True):
        penalty += 120.0
    return penalty


def _pref(preferences: Any, field_name: str, default: bool) -> bool:
    if isinstance(preferences, dict):
        return bool(preferences.get(field_name, default))
    return bool(getattr(preferences, field_name, default))
