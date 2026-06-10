"""
Room search API.

사용자가 입력한 자연스러운 검색어를 건물, 층, 호실, 실내 지도 좌표로 해석.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import selectinload
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Building, IndoorMap, Room
from app.schemas.rooms import RoomSearchResponse
from app.services.resolver import build_room_search_response, normalize_keyword, resolve_room_keyword

router = APIRouter(prefix="/api/rooms", tags=["rooms"])


ERROR_MESSAGES = {
    "EMPTY_KEYWORD": "검색어를 입력해 주세요.",
    "ROOM_NUMBER_NOT_FOUND": "검색어에서 호실 번호를 찾을 수 없습니다.",
    "BUILDING_NOT_FOUND": "검색한 건물을 찾을 수 없습니다.",
    "ROOM_NOT_FOUND": "검색한 강의실을 찾을 수 없습니다.",
    "INDOOR_MAP_NOT_FOUND": "해당 강의실의 실내 지도 정보를 찾을 수 없습니다.",
    "POSITION_NOT_FOUND": "강의실 좌표가 아직 등록되지 않았습니다.",
}


@router.get("", response_model=list[RoomSearchResponse])
def list_rooms(
    keyword: str | None = Query(default=None),
    building_id: str | None = Query(default=None),
    floor: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    # 강의실 검색 자동완성/목록 화면용 다건 조회.
    query = db.query(Room).options(
        selectinload(Room.building).selectinload(Building.aliases),
        selectinload(Room.indoor_map),
        selectinload(Room.positions),
    )
    if building_id:
        query = query.filter(Room.building_id == building_id)
    if floor is not None:
        query = query.filter(Room.floor_number == floor)

    rooms = query.all()
    keyword_norm = normalize_keyword(keyword or "").lower()
    if keyword_norm:
        rooms = [room for room in rooms if _matches_room_keyword(room, keyword_norm)]

    rooms.sort(
        key=lambda room: (
            room.building.name if room.building else "",
            room.floor_number,
            room.room_number,
            room.room_code,
        )
    )

    responses: list[RoomSearchResponse] = []
    for room in rooms[:limit]:
        building = room.building or db.get(Building, room.building_id)
        indoor_map = room.indoor_map or db.get(IndoorMap, room.indoor_map_id)
        if not building or not indoor_map:
            continue
        responses.append(build_room_search_response(db, building, room, indoor_map))
    return responses


@router.get("/search", response_model=RoomSearchResponse)
def search_room(keyword: str = Query(...), db: Session = Depends(get_db)):
    # "소프트305" 같은 입력을 강의실 검색 결과로 변환.
    result = resolve_room_keyword(db, keyword)
    if result.error_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "errorCode": result.error_code,
                "message": ERROR_MESSAGES.get(result.error_code, "검색 처리 중 오류가 발생했습니다."),
            },
        )
    return result.payload


@router.get("/{room_id}", response_model=RoomSearchResponse)
def get_room(room_id: str, db: Session = Depends(get_db)):
    # 검색 결과 클릭 후 강의실 상세/실내지도 연결에 사용할 단건 조회.
    room = (
        db.query(Room)
        .options(
            selectinload(Room.building),
            selectinload(Room.indoor_map),
            selectinload(Room.positions),
        )
        .filter(Room.room_id == room_id)
        .first()
    )
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ROOM_NOT_FOUND")
    building = room.building or db.get(Building, room.building_id)
    indoor_map = room.indoor_map or db.get(IndoorMap, room.indoor_map_id)
    if not building:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BUILDING_NOT_FOUND")
    if not indoor_map:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="INDOOR_MAP_NOT_FOUND")
    return build_room_search_response(db, building, room, indoor_map)


def _matches_room_keyword(room: Room, keyword_norm: str) -> bool:
    building = room.building
    aliases = building.aliases if building else []
    room_fields = [
        room.room_id,
        room.room_code,
        room.room_number,
        room.description or "",
    ]
    building_fields = [
        building.building_id if building else room.building_id,
        building.name if building else "",
        building.short_code if building else "",
        *[alias.alias for alias in aliases],
    ]
    compact_fields = [normalize_keyword(value).lower() for value in room_fields + building_fields if value]
    if any(keyword_norm in value for value in compact_fields):
        return True

    room_number_norm = normalize_keyword(room.room_number).lower()
    building_parts = [normalize_keyword(value).lower() for value in building_fields if value]
    return any(keyword_norm == f"{building_part}{room_number_norm}" for building_part in building_parts)
