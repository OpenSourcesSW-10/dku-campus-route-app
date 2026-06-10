from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import OrmModel


TmiStatus = Literal["pending", "approved", "rejected", "verified"]


class TmiLocationCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    locationType: str = Field(default="OUTDOOR", min_length=1, max_length=30)
    buildingId: str | None = None
    roomId: str | None = None
    indoorMapId: str | None = None
    floorNumber: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    mapX: float | None = None
    mapY: float | None = None
    representativeTags: str | None = None


class TmiLocationStatusUpdateRequest(BaseModel):
    status: TmiStatus


class TmiLocationResponse(OrmModel):
    # 지도 위에 표시할 TMI 마커와 상태 정보 포함.
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
