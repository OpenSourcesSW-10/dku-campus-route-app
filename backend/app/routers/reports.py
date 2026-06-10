"""
User report API.

지도 오류, TMI 오류, 시설 정보 오류 등을 사용자가 제보.
관리자가 검수한 항목만 공개 조회에 노출.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Building, Report, Room, TmiLocation, User
from app.routers.auth import require_admin_user, require_authenticated_user
from app.schemas.reports import ReportCreateRequest, ReportResponse, ReportStatusUpdateRequest
from app.security import new_id, utc_now_text


router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/approved", response_model=list[ReportResponse])
def list_public_approved_reports(
    report_type: str | None = Query(default=None),
    building_id: str | None = Query(default=None),
    room_id: str | None = Query(default=None),
    tmi_location_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    # 공개 제보 목록은 approved/verified 상태만 노출. 미검수 제보의 사용자 화면 노출 방지.
    query = db.query(Report).filter(Report.status.in_(["approved", "verified"]))
    if report_type:
        query = query.filter(Report.report_type == report_type)
    if building_id:
        query = query.filter(Report.building_id == building_id)
    if room_id:
        query = query.filter(Report.room_id == room_id)
    if tmi_location_id:
        query = query.filter(Report.tmi_location_id == tmi_location_id)
    return query.order_by(Report.created_at.desc()).all()


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def create_report(
    request: ReportCreateRequest,
    current_user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    # 제보 대상 ID 오류는 관리자 검수 이전 데이터 품질 저하 원인. 생성 시점에 참조 검증.
    _validate_report_references(db, request)
    report = Report(
        report_id=new_id("REPORT"),
        user_id=current_user.user_id,
        report_type=request.reportType,
        target_type=request.targetType,
        target_id=request.targetId,
        tmi_location_id=request.tmiLocationId,
        building_id=request.buildingId,
        room_id=request.roomId,
        title=request.title,
        content=request.content,
        tags=request.tags,
        status="pending",
        verified_count=0,
        created_at=utc_now_text(),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.get("/admin/list", response_model=list[ReportResponse])
def list_admin_reports(
    status_filter: str | None = Query(default=None, alias="status"),
    report_type: str | None = Query(default=None),
    _: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    query = db.query(Report)
    if status_filter:
        query = query.filter(Report.status == status_filter)
    if report_type:
        query = query.filter(Report.report_type == report_type)
    return query.order_by(Report.created_at.desc()).all()


@router.patch("/admin/{report_id}/status", response_model=ReportResponse)
def update_report_status(
    report_id: str,
    request: ReportStatusUpdateRequest,
    _: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    # 관리자가 승인한 제보는 verified_count 증가. 추후 신뢰도/정렬 기준으로 활용 가능.
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"errorCode": "REPORT_NOT_FOUND", "message": "제보를 찾을 수 없습니다."},
        )
    report.status = request.status
    if request.status in {"approved", "verified"}:
        report.verified_count += 1
    db.commit()
    db.refresh(report)
    return report


def _validate_report_references(db: Session, request: ReportCreateRequest) -> None:
    # report는 건물/강의실/TMI 등 다양한 대상 참조 가능. 값이 있는 항목만 선택 검증.
    if request.buildingId and not db.get(Building, request.buildingId):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"errorCode": "BUILDING_NOT_FOUND", "message": "건물을 찾을 수 없습니다."},
        )
    if request.roomId and not db.get(Room, request.roomId):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"errorCode": "ROOM_NOT_FOUND", "message": "강의실을 찾을 수 없습니다."},
        )
    if request.tmiLocationId and not db.get(TmiLocation, request.tmiLocationId):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"errorCode": "TMI_LOCATION_NOT_FOUND", "message": "TMI 위치를 찾을 수 없습니다."},
        )
