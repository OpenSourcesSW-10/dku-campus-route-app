from pydantic import BaseModel

from app.schemas.common import OrmModel
from app.schemas.indoor import RoomPositionResponse


class IndoorMapSummary(BaseModel):
    # 강의실 검색 결과에서 필요한 실내 지도 요약 정보이다.
    indoorMapId: str
    mapFileUrl: str
    canvasWidth: int
    canvasHeight: int


class RoomResponse(OrmModel):
    # 일반 강의실 데이터 응답이다.
    room_id: str
    building_id: str
    indoor_map_id: str
    room_code: str
    room_number: str
    floor_number: int
    room_type: str
    nearest_indoor_node_id: str | None = None
    description: str | None = None


class RoomSearchResponse(BaseModel):
    # 검색어 하나를 실내 지도 하이라이트까지 연결한 응답이다.
    type: str = "ROOM"
    roomId: str
    roomCode: str
    buildingId: str
    buildingName: str
    floorNumber: int
    floorLabel: str
    roomNumber: str
    indoorMap: IndoorMapSummary
    position: RoomPositionResponse | None = None
    nearestIndoorNodeId: str | None = None
