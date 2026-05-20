from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Building
from app.schemas.buildings import BuildingResponse

router = APIRouter(prefix="/api/buildings", tags=["week3-buildings"])


@router.get("", response_model=list[BuildingResponse])
def list_buildings(db: Session = Depends(get_db)):
    # 지도 마커와 건물 선택 UI에 사용할 건물 목록을 반환한다.
    return (
        db.query(Building)
        .options(selectinload(Building.aliases))
        .order_by(Building.name)
        .all()
    )


@router.get("/{building_id}", response_model=BuildingResponse)
def get_building(building_id: str, db: Session = Depends(get_db)):
    # 특정 건물 상세 정보를 조회한다.
    building = (
        db.query(Building)
        .options(selectinload(Building.aliases))
        .filter(Building.building_id == building_id)
        .first()
    )
    if not building:
        raise HTTPException(status_code=404, detail="BUILDING_NOT_FOUND")
    return building
