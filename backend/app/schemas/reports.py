from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import OrmModel


ReportStatus = Literal["pending", "approved", "rejected", "verified"]


class ReportCreateRequest(BaseModel):
    reportType: str = Field(min_length=1, max_length=30)
    targetType: str = Field(min_length=1, max_length=30)
    targetId: str | None = None
    tmiLocationId: str | None = None
    buildingId: str | None = None
    roomId: str | None = None
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)
    tags: str | None = None


class ReportStatusUpdateRequest(BaseModel):
    status: ReportStatus


class ReportResponse(OrmModel):
    # 강의실 정보 또는 TMI 제보 내용을 담는 응답.
    report_id: str
    user_id: str | None = None
    report_type: str
    target_type: str
    target_id: str | None = None
    tmi_location_id: str | None = None
    building_id: str | None = None
    room_id: str | None = None
    title: str
    content: str
    tags: str | None = None
    status: str
    verified_count: int
    created_at: str | None = None
