"""
Route API endpoints.

프론트는 이 라우터의 응답만으로 외부 지도 Polyline, 실내 SVG 경로,
층간 이동 안내 렌더링 가능해야 함.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.routes import IndoorRouteRequest, RouteDetailResponse, RouteRequest
from app.services.indoor_graph import find_indoor_route
from app.services.route_planner import plan_integrated_route


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
    "START_ROOM_NEAREST_NODE_NOT_FOUND": "출발 강의실과 연결된 실내 노드가 없습니다.",
    "DESTINATION_ROOM_NEAREST_NODE_NOT_FOUND": "도착 강의실과 연결된 실내 노드가 없습니다.",
    "START_ENTRANCE_LINK_NOT_FOUND": "출발 건물의 출입구 연결 정보가 없습니다.",
    "DESTINATION_ENTRANCE_LINK_NOT_FOUND": "도착 건물의 출입구 연결 정보가 없습니다.",
    "OUTDOOR_ROUTE_NOT_FOUND": "건물 사이의 외부 경로를 찾을 수 없습니다.",
    "INTEGRATED_ROUTE_NOT_FOUND": "실내-외부-실내 통합 경로를 찾을 수 없습니다.",
}


@router.post("/indoor", response_model=RouteDetailResponse)
def create_indoor_route(request: IndoorRouteRequest, db: Session = Depends(get_db)):
    # 테스트와 디버깅용. 같은 건물 내부 경로만 별도 계산.
    result = find_indoor_route(db, request.fromRoomId, request.toRoomId, request.routeType, request.preferences)
    if result.error_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"errorCode": result.error_code, "message": ERROR_MESSAGES.get(result.error_code, "경로 계산 중 오류가 발생했습니다.")},
        )
    return result.payload


@router.post("", response_model=list[RouteDetailResponse])
def create_integrated_routes(request: RouteRequest, db: Session = Depends(get_db)):
    # 하나의 요청에서 여러 route type 계산. 프론트가 경로 카드를 동시에 표시 가능.
    responses: list[RouteDetailResponse] = []
    errors: list[dict[str, str]] = []
    for route_type in request.routeTypes:
        result = plan_integrated_route(db, request.start, request.destination, route_type, request.preferences)
        if result.payload:
            responses.append(result.payload)
        elif result.error_code:
            errors.append({
                "routeType": route_type,
                "errorCode": result.error_code,
                "message": ERROR_MESSAGES.get(result.error_code, "경로 계산 중 오류가 발생했습니다."),
            })

    if not responses:
        # 모든 route type이 실패한 경우에만 404 반환.
        # 일부 경로만 성공하면 성공한 경로는 그대로 반환, 실패 상세는 숨김.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"errors": errors})
    return responses
