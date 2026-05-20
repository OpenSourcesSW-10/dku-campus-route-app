from app.schemas.common import OrmModel


class ReportResponse(OrmModel):
    # 강의실 정보 또는 TMI 제보 내용을 담는 응답이다.
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
