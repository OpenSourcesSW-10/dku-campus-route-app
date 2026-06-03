from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.algorithms.cost_function import normalize_route_type
from app.models import EntranceLink, Room
from app.schemas.routes import RouteDetailResponse
from app.services.indoor_graph import find_indoor_node_route
from app.services.outdoor_graph import find_outdoor_route
from app.services.resolver import resolve_room_keyword


@dataclass
class RoutePlannerResult:
    payload: RouteDetailResponse | None = None
    error_code: str | None = None


def plan_integrated_route(db: Session, from_keyword: str, to_keyword: str, route_type: str = "DEFAULT", preferences=None) -> RoutePlannerResult:
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
        indoor_result = find_indoor_node_route(
            db,
            from_room.building_id,
            from_room.nearest_indoor_node_id,
            to_room.nearest_indoor_node_id,
            normalized_route_type,
            preferences,
        )
        return RoutePlannerResult(payload=indoor_result.payload, error_code=indoor_result.error_code)

    start_links = _building_entrance_links(db, from_room.building_id)
    destination_links = _building_entrance_links(db, to_room.building_id)
    if not start_links:
        return RoutePlannerResult(error_code="START_ENTRANCE_LINK_NOT_FOUND")
    if not destination_links:
        return RoutePlannerResult(error_code="DESTINATION_ENTRANCE_LINK_NOT_FOUND")

    candidates: list[RouteDetailResponse] = []
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


def _combine_routes(route_type: str, routes: list[RouteDetailResponse]) -> RouteDetailResponse:
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
