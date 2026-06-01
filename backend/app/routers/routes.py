from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Room
from app.schemas.routes import IndoorRouteRequest, RouteDetailResponse, RouteRequest
from app.services.indoor_graph import find_indoor_route
from app.services.resolver import resolve_room_keyword


router = APIRouter(prefix="/api/routes", tags=["routes"])


ERROR_MESSAGES = {
    "FROM_ROOM_NOT_FOUND": "출발 강의실을 찾을 수 없습니다.",
    "TO_ROOM_NOT_FOUND": "도착 강의실을 찾을 수 없습니다.",
    "DIFFERENT_BUILDING_ROUTE_NOT_SUPPORTED_IN_WEEK6": "6주차 실내 경로 API는 같은 건물 경로만 지원합니다.",
    "FROM_ROOM_NEAREST_NODE_NOT_FOUND": "출발 강의실과 연결된 실내 노드가 없습니다.",
    "TO_ROOM_NEAREST_NODE_NOT_FOUND": "도착 강의실과 연결된 실내 노드가 없습니다.",
    "INDOOR_ROUTE_NOT_FOUND": "실내 경로를 찾을 수 없습니다.",
    "START_EMPTY_KEYWORD": "출발지를 입력해야 합니다.",
    "DESTINATION_EMPTY_KEYWORD": "도착지를 입력해야 합니다.",
    "START_ROOM_NUMBER_NOT_FOUND": "출발지에서 호실 번호를 찾을 수 없습니다.",
    "DESTINATION_ROOM_NUMBER_NOT_FOUND": "도착지에서 호실 번호를 찾을 수 없습니다.",
    "START_BUILDING_NOT_FOUND": "출발지 건물을 찾을 수 없습니다.",
    "DESTINATION_BUILDING_NOT_FOUND": "도착지 건물을 찾을 수 없습니다.",
    "START_ROOM_NOT_FOUND": "출발 강의실을 찾을 수 없습니다.",
    "DESTINATION_ROOM_NOT_FOUND": "도착 강의실을 찾을 수 없습니다.",
    "START_INDOOR_MAP_NOT_FOUND": "출발 강의실의 층별 실내 지도를 찾을 수 없습니다.",
    "DESTINATION_INDOOR_MAP_NOT_FOUND": "도착 강의실의 층별 실내 지도를 찾을 수 없습니다.",
    "ROOM_NOT_FOUND": "강의실을 찾을 수 없습니다.",
}


@router.post("/indoor", response_model=RouteDetailResponse)
def create_indoor_route(request: IndoorRouteRequest, db: Session = Depends(get_db)):
    result = find_indoor_route(db, request.fromRoomId, request.toRoomId, request.routeType, request.preferences)
    if result.error_code:
        raise _route_error(result.error_code)
    return result.payload


@router.post("", response_model=list[RouteDetailResponse])
def create_routes(request: RouteRequest, db: Session = Depends(get_db)):
    start_result = resolve_room_keyword(db, request.start)
    if start_result.error_code or not start_result.payload:
        raise _route_error(f"START_{start_result.error_code or 'ROOM_NOT_FOUND'}")

    destination_result = resolve_room_keyword(db, request.destination)
    if destination_result.error_code or not destination_result.payload:
        raise _route_error(f"DESTINATION_{destination_result.error_code or 'ROOM_NOT_FOUND'}")

    start_room = db.get(Room, start_result.payload.roomId)
    destination_room = db.get(Room, destination_result.payload.roomId)
    if not start_room or not destination_room:
        raise _route_error("ROOM_NOT_FOUND")

    responses: list[RouteDetailResponse] = []
    errors: list[dict[str, str]] = []
    for route_type in request.routeTypes:
        result = find_indoor_route(db, start_room.room_id, destination_room.room_id, route_type, request.preferences)
        if result.payload:
            responses.append(result.payload)
        elif result.error_code:
            errors.append({
                "routeType": route_type,
                "errorCode": result.error_code,
                "message": ERROR_MESSAGES.get(result.error_code, "경로 계산 중 오류가 발생했습니다."),
            })

    if not responses:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"errors": errors})
    return responses


def _route_error(error_code: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"errorCode": error_code, "message": ERROR_MESSAGES.get(error_code, "경로 계산 중 오류가 발생했습니다.")},
    )
