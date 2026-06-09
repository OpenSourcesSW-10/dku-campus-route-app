"""
TMI location API.

일반 사용자는 승인된 TMI만 조회.
인증된 사용자는 제안 가능, 관리자는 pending 데이터 승인/검수.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Building, IndoorMap, Room, TmiLocation, User
from app.routers.auth import require_admin_user, require_authenticated_user
from app.schemas.tmi import TmiLocationCreateRequest, TmiLocationResponse, TmiLocationStatusUpdateRequest
from app.security import new_id, utc_now_text


router = APIRouter(prefix="/api/tmi", tags=["tmi"])


@router.get("", response_model=list[TmiLocationResponse])
def list_public_tmi_locations(
    location_type: str | None = Query(default=None),
    building_id: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    # 공개 API는 승인된 데이터만 반환. pending 데이터는 관리자 화면에서만 확인.
    query = db.query(TmiLocation).filter(TmiLocation.status.in_(["approved", "verified"]))
    if location_type:
        query = query.filter(TmiLocation.location_type == location_type)
    if building_id:
        query = query.filter(TmiLocation.building_id == building_id)
    if tag:
        query = query.filter(TmiLocation.representative_tags.contains(tag))
    return query.order_by(TmiLocation.created_at.desc()).all()


@router.post("", response_model=TmiLocationResponse, status_code=status.HTTP_201_CREATED)
def create_tmi_location(
    request: TmiLocationCreateRequest,
    current_user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    # 사용자가 보낸 building/room/map 참조가 실제 DB에 있는지 먼저 확인, 잘못된 데이터 감소.
    _validate_tmi_references(db, request)
    location = TmiLocation(
        tmi_location_id=new_id("TMI"),
        name=request.name,
        location_type=request.locationType,
        building_id=request.buildingId,
        room_id=request.roomId,
        indoor_map_id=request.indoorMapId,
        floor_number=request.floorNumber,
        latitude=request.latitude,
        longitude=request.longitude,
        map_x=request.mapX,
        map_y=request.mapY,
        representative_tags=request.representativeTags,
        status="pending",
        verified_count=0,
        created_by=current_user.user_id,
        created_at=utc_now_text(),
    )
    db.add(location)
    db.commit()
    db.refresh(location)
    return location


@router.get("/admin/list", response_model=list[TmiLocationResponse])
def list_admin_tmi_locations(
    status_filter: str | None = Query(default=None, alias="status"),
    _: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    query = db.query(TmiLocation)
    if status_filter:
        query = query.filter(TmiLocation.status == status_filter)
    return query.order_by(TmiLocation.created_at.desc()).all()


@router.patch("/admin/{tmi_location_id}/status", response_model=TmiLocationResponse)
def update_tmi_location_status(
    tmi_location_id: str,
    request: TmiLocationStatusUpdateRequest,
    _: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    # 승인/검증 상태가 되면 verified_count 증가. 추후 신뢰도 표시나 정렬에 활용 가능.
    location = db.get(TmiLocation, tmi_location_id)
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"errorCode": "TMI_LOCATION_NOT_FOUND", "message": "TMI 위치를 찾을 수 없습니다."},
        )
    location.status = request.status
    if request.status in {"approved", "verified"}:
        location.verified_count += 1
    db.commit()
    db.refresh(location)
    return location


@router.get("/{tmi_location_id}", response_model=TmiLocationResponse)
def get_public_tmi_location(tmi_location_id: str, db: Session = Depends(get_db)):
    location = (
        db.query(TmiLocation)
        .filter(TmiLocation.tmi_location_id == tmi_location_id, TmiLocation.status.in_(["approved", "verified"]))
        .first()
    )
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"errorCode": "TMI_LOCATION_NOT_FOUND", "message": "승인된 TMI 위치를 찾을 수 없습니다."},
        )
    return location


def _validate_tmi_references(db: Session, request: TmiLocationCreateRequest) -> None:
    # TMI는 건물, 강의실, 실내 지도 중 일부만 연결 가능. 값이 들어온 항목만 검증.
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
    if request.indoorMapId and not db.get(IndoorMap, request.indoorMapId):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"errorCode": "INDOOR_MAP_NOT_FOUND", "message": "실내 지도를 찾을 수 없습니다."},
        )
