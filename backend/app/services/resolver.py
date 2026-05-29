import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import Building, BuildingAlias, IndoorMap, Room, RoomPosition
from app.schemas.rooms import IndoorMapSummary, RoomSearchResponse


@dataclass
class ResolveResult:
    payload: RoomSearchResponse | None = None
    error_code: str | None = None


def normalize_keyword(keyword: str) -> str:
    # 검색어 비교가 쉬워지도록 앞뒤 공백과 중간 공백을 제거한다.
    return re.sub(r"\s+", "", keyword.strip())


def extract_room_number(keyword: str) -> str | None:
    # 검색어 끝의 3~4자리 호실 번호를 추출한다.
    match = re.search(r"(\d{3,4})호?$", normalize_keyword(keyword))
    return match.group(1) if match else None


def extract_building_part(keyword: str, room_number: str) -> str:
    # 호실 번호 앞부분을 건물명 또는 약칭 후보로 사용한다.
    normalized = normalize_keyword(keyword)
    return normalized[: normalized.rfind(room_number)]


def estimate_floor(room_number: str) -> int:
    # 일반적인 호실 규칙에 따라 첫 숫자를 층 번호로 추정한다.
    if len(room_number) < 3 or not room_number[0].isdigit():
        return 1
    return int(room_number[0])


def resolve_building_alias(db: Session, alias_text: str) -> Building | None:
    # 별칭, 약칭, 정식 건물명을 모두 비교해 하나의 Building으로 해석한다.
    normalized_alias_text = normalize_keyword(alias_text).lower()

    alias = (
        db.query(BuildingAlias)
        .join(Building)
        .filter(BuildingAlias.alias == alias_text)
        .order_by(BuildingAlias.priority.asc())
        .first()
    )
    if alias:
        return alias.building

    for candidate_alias in (
        db.query(BuildingAlias)
        .join(Building)
        .order_by(BuildingAlias.priority.asc())
        .all()
    ):
        if normalize_keyword(candidate_alias.alias).lower() == normalized_alias_text:
            return candidate_alias.building

    for building in db.query(Building).all():
        normalized_short_code = normalize_keyword(building.short_code).lower()
        normalized_name = normalize_keyword(building.name).lower()
        if normalized_alias_text in {normalized_short_code, normalized_name}:
            return building
        if normalized_alias_text and normalized_alias_text in normalized_name:
            return building

    return (
        db.query(Building)
        .filter(
            (Building.short_code == alias_text)
            | (Building.name == alias_text)
            | (Building.name.contains(alias_text))
        )
        .first()
    )


def resolve_room_keyword(db: Session, keyword: str) -> ResolveResult:
    # 검색어를 room, indoor_map, position까지 이어지는 응답으로 조립한다.
    if not normalize_keyword(keyword):
        return ResolveResult(error_code="EMPTY_KEYWORD")

    exact_room = resolve_exact_room(db, keyword)
    if exact_room:
        indoor_map = db.get(IndoorMap, exact_room.indoor_map_id)
        if not indoor_map:
            return ResolveResult(error_code="INDOOR_MAP_NOT_FOUND")
        building = db.get(Building, exact_room.building_id)
        if not building:
            return ResolveResult(error_code="BUILDING_NOT_FOUND")
        return ResolveResult(payload=build_room_search_response(db, building, exact_room, indoor_map))

    room_number = extract_room_number(keyword)
    if not room_number:
        return ResolveResult(error_code="ROOM_NUMBER_NOT_FOUND")

    building_part = extract_building_part(keyword, room_number)
    building = resolve_building_alias(db, building_part)
    if not building:
        return ResolveResult(error_code="BUILDING_NOT_FOUND")

    floor_number = estimate_floor(room_number)
    room = (
        db.query(Room)
        .filter(
            Room.building_id == building.building_id,
            Room.room_number == room_number,
            Room.floor_number == floor_number,
        )
        .first()
    )
    if not room:
        room = (
            db.query(Room)
            .filter(
                Room.building_id == building.building_id,
                Room.room_number == room_number,
            )
            .order_by(Room.floor_number.asc())
            .first()
        )
    if not room:
        return ResolveResult(error_code="ROOM_NOT_FOUND")

    indoor_map = db.get(IndoorMap, room.indoor_map_id)
    if not indoor_map:
        return ResolveResult(error_code="INDOOR_MAP_NOT_FOUND")

    return ResolveResult(payload=build_room_search_response(db, building, room, indoor_map))


def resolve_exact_room(db: Session, keyword: str) -> Room | None:
    # room_id나 room_code를 그대로 입력한 경우를 우선 처리한다.
    normalized_keyword = normalize_keyword(keyword).lower()
    if not normalized_keyword:
        return None
    for room in db.query(Room).all():
        if normalize_keyword(room.room_id).lower() == normalized_keyword:
            return room
        if normalize_keyword(room.room_code).lower() == normalized_keyword:
            return room
    return None


def build_room_search_response(
    db: Session,
    building: Building,
    room: Room,
    indoor_map: IndoorMap,
) -> RoomSearchResponse:
    # Room, Building, IndoorMap, RoomPosition을 프론트엔드 검색 응답으로 묶는다.
    position = (
        db.query(RoomPosition)
        .filter(RoomPosition.room_id == room.room_id)
        .first()
    )

    return RoomSearchResponse(
        roomId=room.room_id,
        roomCode=room.room_code,
        buildingId=building.building_id,
        buildingName=building.name,
        floorNumber=room.floor_number,
        floorLabel=indoor_map.floor_label,
        roomNumber=room.room_number,
        indoorMap=IndoorMapSummary(
            indoorMapId=indoor_map.indoor_map_id,
            mapFileUrl=indoor_map.map_file_url,
            canvasWidth=indoor_map.canvas_width,
            canvasHeight=indoor_map.canvas_height,
        ),
        position=position,
        nearestIndoorNodeId=room.nearest_indoor_node_id,
    )
