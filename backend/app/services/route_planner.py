"""
Integrated route planner.

출발/도착 키워드를 강의실로 해석.
같은 건물이면 실내 경로만 계산, 다른 건물이면 출발 실내 경로/외부 경로/도착 실내 경로 조합.
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.algorithms.cost_function import normalize_route_type
from app.models import EntranceLink, Room
from app.schemas.routes import RouteDetailResponse
from app.services.indoor_graph import find_cross_building_indoor_route, find_indoor_node_route
from app.services.outdoor_graph import find_outdoor_route
from app.services.resolver import resolve_room_keyword


@dataclass
class RoutePlannerResult:
    payload: RouteDetailResponse | None = None
    error_code: str | None = None


def plan_integrated_route(db: Session, from_keyword: str, to_keyword: str, route_type: str = "DEFAULT", preferences=None) -> RoutePlannerResult:
    # 프론트 입력은 room_id가 아니라 "ICT401", "도서관301" 같은 검색어. resolver 먼저 통과.
    normalized_route_type = normalize_route_type(route_type)
    from_resolved = resolve_room_keyword(db, from_keyword)
    if from_resolved.error_code or not from_resolved.payload:
        return RoutePlannerResult(error_code=f"START_{from_resolved.error_code or 'ROOM_NOT_FOUND'}")
    to_resolved = resolve_room_keyword(db, to_keyword)
    if to_resolved.error_code or not to_resolved.payload:
        return RoutePlannerResult(error_code=f"DESTINATION_{to_resolved.error_code or 'ROOM_NOT_FOUND'}")

    from_room = db.get(Room, from_resolved.payload.roomId)
    to_room = db.get(Room, to_resolved.payload.roomId)
    if not from_room or not to_room:
        return RoutePlannerResult(error_code="ROOM_NOT_FOUND")
    if not from_room.nearest_indoor_node_id:
        return RoutePlannerResult(error_code="START_ROOM_NEAREST_NODE_NOT_FOUND")
    if not to_room.nearest_indoor_node_id:
        return RoutePlannerResult(error_code="DESTINATION_ROOM_NEAREST_NODE_NOT_FOUND")

    if from_room.building_id == to_room.building_id:
        # 같은 건물 안에서는 외부 출입구를 거치지 않고 실내 그래프만 사용.
        indoor_result = find_indoor_node_route(
            db,
            from_room.building_id,
            from_room.nearest_indoor_node_id,
            to_room.nearest_indoor_node_id,
            normalized_route_type,
            preferences,
        )
        return RoutePlannerResult(payload=indoor_result.payload, error_code=indoor_result.error_code)

    # 제1/2/3공학관 구름다리처럼 실내 그래프가 건물 간 직접 연결을 제공하는 경우도 후보에 포함.
    # 다만 즉시 반환하면 외부 평지/계단 출입구 경로가 비교되지 않아 route type별 차이가 사라짐.
    cross_building_indoor = find_cross_building_indoor_route(
        db,
        from_room.nearest_indoor_node_id,
        to_room.nearest_indoor_node_id,
        normalized_route_type,
        preferences,
    )
    if normalized_route_type == "RAINY" and cross_building_indoor.payload:
        # 비 오는 날은 구름다리/실내 연결을 가장 안정적인 경로로 우선 사용.
        return RoutePlannerResult(payload=cross_building_indoor.payload)

    start_links = _building_entrance_links(db, from_room.building_id)
    destination_links = _building_entrance_links(db, to_room.building_id)
    candidates: list[RouteDetailResponse] = []
    if cross_building_indoor.payload:
        candidates.append(cross_building_indoor.payload)
    if not start_links:
        if candidates:
            return RoutePlannerResult(payload=min(candidates, key=lambda route: route.totalCost))
        return RoutePlannerResult(error_code="START_ENTRANCE_LINK_NOT_FOUND")
    if not destination_links:
        if candidates:
            return RoutePlannerResult(payload=min(candidates, key=lambda route: route.totalCost))
        return RoutePlannerResult(error_code="DESTINATION_ENTRANCE_LINK_NOT_FOUND")

    # 제1공학관과 제3공학관은 외부에서 직접 연결되지 않음.
    # 두 건물 사이에는 제2공학관이 있으므로, 기본/편한 경로도 반드시
    # 제2공학관 1층↔2층 내부 이동을 경유하는 후보를 우선 사용함.
    engineering_via_sci2 = _engineering_sci1_sci3_via_sci2_route(
        db,
        from_room,
        to_room,
        normalized_route_type,
        preferences,
    )
    if engineering_via_sci2:
        if normalized_route_type in {"DEFAULT", "COMFORTABLE"}:
            return RoutePlannerResult(payload=engineering_via_sci2)
        candidates.append(engineering_via_sci2)

    # ICT/도서관 같은 외부 건물에서 공학관으로 갈 때도, DCF가 실내/구름다리 경유 후보를 비교할 수 있어야 함.
    # 예: ICT관 -> 제3공학관은 외부 계단 직행뿐 아니라 제2공학관 진입 후 실내/구름다리 이동도 후보로 추가.
    candidates.extend(
        _engineering_passage_via_sci2_candidates(
            db,
            from_room,
            to_room,
            normalized_route_type,
            preferences,
            start_links,
            destination_links,
        )
    )

    # 출입구가 여러 개일 수 있으므로 모든 출발/도착 출입구 조합 계산 후 최저 비용 경로 선택.
    for start_link in start_links:
        start_indoor = find_indoor_node_route(
            db,
            from_room.building_id,
            from_room.nearest_indoor_node_id,
            start_link.indoor_node_id,
            normalized_route_type,
            preferences,
        )
        if not start_indoor.payload:
            continue
        for destination_link in destination_links:
            outdoor = find_outdoor_route(db, start_link.outdoor_node_id, destination_link.outdoor_node_id, normalized_route_type, preferences)
            if not outdoor.payload:
                continue
            destination_indoor = find_indoor_node_route(
                db,
                to_room.building_id,
                destination_link.indoor_node_id,
                to_room.nearest_indoor_node_id,
                normalized_route_type,
                preferences,
            )
            if destination_indoor.payload:
                candidates.append(_combine_routes(normalized_route_type, [start_indoor.payload, outdoor.payload, destination_indoor.payload]))

    if not candidates:
        return RoutePlannerResult(error_code="INTEGRATED_ROUTE_NOT_FOUND")
    return RoutePlannerResult(payload=min(candidates, key=lambda route: route.totalCost))


def _building_entrance_links(db: Session, building_id: str) -> list[EntranceLink]:
    return (
        db.query(EntranceLink)
        .filter(EntranceLink.building_id == building_id)
        .order_by(EntranceLink.is_main.desc(), EntranceLink.entrance_name.asc())
        .all()
    )


def _entrance_link_by_id(db: Session, building_id: str, entrance_id: str) -> EntranceLink | None:
    return (
        db.query(EntranceLink)
        .filter(
            EntranceLink.building_id == building_id,
            EntranceLink.entrance_name == entrance_id,
        )
        .first()
    )


def _engineering_sci1_sci3_via_sci2_route(
    db: Session,
    from_room: Room,
    to_room: Room,
    route_type: str,
    preferences=None,
) -> RouteDetailResponse | None:
    pair = {from_room.building_id, to_room.building_id}
    if pair != {"DKU_SCI1", "DKU_SCI3"}:
        return None

    if from_room.building_id == "DKU_SCI1":
        start_exit = _entrance_link_by_id(db, "DKU_SCI1", "SCI1_LEVEL2_FLAT_EXIT")
        mid_entry = _entrance_link_by_id(db, "DKU_SCI2", "SCI2_LEVEL1_FLAT_WEST")
        mid_exit = _entrance_link_by_id(db, "DKU_SCI2", "SCI2_LEVEL2_FLAT_EAST")
        dest_entry = _entrance_link_by_id(db, "DKU_SCI3", "SCI3_LEVEL1_FLAT_WEST")
    else:
        start_exit = _entrance_link_by_id(db, "DKU_SCI3", "SCI3_LEVEL1_FLAT_WEST")
        mid_entry = _entrance_link_by_id(db, "DKU_SCI2", "SCI2_LEVEL2_FLAT_EAST")
        mid_exit = _entrance_link_by_id(db, "DKU_SCI2", "SCI2_LEVEL1_FLAT_WEST")
        dest_entry = _entrance_link_by_id(db, "DKU_SCI1", "SCI1_LEVEL2_FLAT_EXIT")

    if not all([start_exit, mid_entry, mid_exit, dest_entry]):
        return None

    start_indoor = find_indoor_node_route(
        db,
        from_room.building_id,
        from_room.nearest_indoor_node_id,
        start_exit.indoor_node_id,
        route_type,
        preferences,
    )
    first_outdoor = find_outdoor_route(
        db,
        start_exit.outdoor_node_id,
        mid_entry.outdoor_node_id,
        route_type,
        preferences,
    )
    middle_indoor = find_indoor_node_route(
        db,
        "DKU_SCI2",
        mid_entry.indoor_node_id,
        mid_exit.indoor_node_id,
        route_type,
        preferences,
    )
    second_outdoor = find_outdoor_route(
        db,
        mid_exit.outdoor_node_id,
        dest_entry.outdoor_node_id,
        route_type,
        preferences,
    )
    destination_indoor = find_indoor_node_route(
        db,
        to_room.building_id,
        dest_entry.indoor_node_id,
        to_room.nearest_indoor_node_id,
        route_type,
        preferences,
    )

    parts = [
        start_indoor.payload,
        first_outdoor.payload,
        middle_indoor.payload,
        second_outdoor.payload,
        destination_indoor.payload,
    ]
    if any(part is None for part in parts):
        return None
    combined = _combine_routes(route_type, parts)  # type: ignore[arg-type]
    combined.reason = "제1공학관과 제3공학관은 외부 직접 연결이 불가능해 제2공학관 내부 이동을 경유합니다."
    return combined


def _engineering_passage_via_sci2_candidates(
    db: Session,
    from_room: Room,
    to_room: Room,
    route_type: str,
    preferences,
    start_links: list[EntranceLink],
    destination_links: list[EntranceLink],
) -> list[RouteDetailResponse]:
    bridge_buildings = {"DKU_SCI1", "DKU_SCI3"}
    if from_room.building_id == to_room.building_id:
        return []
    if {from_room.building_id, to_room.building_id} == {"DKU_SCI1", "DKU_SCI3"}:
        return []
    if from_room.building_id not in bridge_buildings and to_room.building_id not in bridge_buildings:
        return []

    sci2_links = _sci2_ground_passage_links(db)
    if not sci2_links:
        return []

    candidates: list[RouteDetailResponse] = []

    if to_room.building_id in bridge_buildings and from_room.building_id != "DKU_SCI2":
        for start_link in start_links:
            start_indoor = find_indoor_node_route(
                db,
                from_room.building_id,
                from_room.nearest_indoor_node_id,
                start_link.indoor_node_id,
                route_type,
                preferences,
            )
            if not start_indoor.payload:
                continue
            for sci2_entry in sci2_links:
                outdoor_to_sci2 = find_outdoor_route(
                    db,
                    start_link.outdoor_node_id,
                    sci2_entry.outdoor_node_id,
                    route_type,
                    preferences,
                )
                if not outdoor_to_sci2.payload:
                    continue
                sci2_to_destination = find_cross_building_indoor_route(
                    db,
                    sci2_entry.indoor_node_id,
                    to_room.nearest_indoor_node_id,
                    route_type,
                    preferences,
                )
                if not sci2_to_destination.payload:
                    continue
                combined = _combine_routes(route_type, [start_indoor.payload, outdoor_to_sci2.payload, sci2_to_destination.payload])
                combined.reason = "제2공학관 내부 이동과 구름다리 연결을 후보로 포함해 DCF 비용으로 비교한 경로입니다."
                _apply_engineering_passage_dcf_bonus(combined, route_type)
                candidates.append(combined)

    if from_room.building_id in bridge_buildings and to_room.building_id != "DKU_SCI2":
        for sci2_exit in sci2_links:
            source_to_sci2 = find_cross_building_indoor_route(
                db,
                from_room.nearest_indoor_node_id,
                sci2_exit.indoor_node_id,
                route_type,
                preferences,
            )
            if not source_to_sci2.payload:
                continue
            for destination_link in destination_links:
                outdoor_from_sci2 = find_outdoor_route(
                    db,
                    sci2_exit.outdoor_node_id,
                    destination_link.outdoor_node_id,
                    route_type,
                    preferences,
                )
                if not outdoor_from_sci2.payload:
                    continue
                destination_indoor = find_indoor_node_route(
                    db,
                    to_room.building_id,
                    destination_link.indoor_node_id,
                    to_room.nearest_indoor_node_id,
                    route_type,
                    preferences,
                )
                if not destination_indoor.payload:
                    continue
                combined = _combine_routes(route_type, [source_to_sci2.payload, outdoor_from_sci2.payload, destination_indoor.payload])
                combined.reason = "구름다리와 제2공학관 내부 이동을 후보로 포함해 DCF 비용으로 비교한 경로입니다."
                _apply_engineering_passage_dcf_bonus(combined, route_type)
                candidates.append(combined)

    return candidates


def _sci2_ground_passage_links(db: Session) -> list[EntranceLink]:
    return [
        link
        for link in _building_entrance_links(db, "DKU_SCI2")
        if link.floor_number == 1 or link.entrance_name in {"SCI2_LEVEL1_FLAT_WEST", "SCI2_MAIN_ENTRANCE_1F"}
    ]


def _apply_engineering_passage_dcf_bonus(route: RouteDetailResponse, route_type: str) -> None:
    # 제2공학관 실내/구름다리 경유 후보는 외부 직행보다 실제 UX가 좋음.
    # DCF route type별 선호를 후보 총비용에 반영해 편한길/비오는날에서 선택 가능하게 함.
    buildings = {segment.buildingId for segment in route.segments if segment.buildingId}
    has_sci2_passage = "DKU_SCI2" in buildings
    has_bridge = any(segment.transitionType == "BRIDGE" for segment in route.segments)
    if not has_sci2_passage or not has_bridge:
        return
    if route_type == "COMFORTABLE":
        route.totalCost = max(route.totalCost - 500.0, 1.0)
    elif route_type == "RAINY":
        route.totalCost = max(route.totalCost - 2300.0, 1.0)


def _combine_routes(route_type: str, routes: list[RouteDetailResponse]) -> RouteDetailResponse:
    # 프론트는 하나의 route 안에서 segments를 순서대로 렌더링. 개별 경로의 세그먼트를 그대로 연결.
    segments = []
    for route in routes:
        segments.extend(route.segments)
    return RouteDetailResponse(
        routeType=route_type,
        title=routes[0].title if routes else route_type,
        totalCost=sum(route.totalCost for route in routes),
        totalDistance=sum(route.totalDistance for route in routes),
        totalEstimatedTime=sum(route.totalEstimatedTime for route in routes),
        reason="실내 경로, 외부 경로, 도착 건물 실내 경로를 연결한 통합 경로입니다.",
        segments=segments,
    )
