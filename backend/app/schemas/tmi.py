from app.schemas.common import OrmModel


class TmiLocationResponse(OrmModel):
    # 지도 위에 표시할 TMI 마커와 상태 정보를 담는다.
    tmi_location_id: str
    name: str
    location_type: str
    building_id: str | None = None
    room_id: str | None = None
    indoor_map_id: str | None = None
    floor_number: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    map_x: float | None = None
    map_y: float | None = None
    representative_tags: str | None = None
    status: str
    verified_count: int
    created_by: str | None = None
    created_at: str | None = None
