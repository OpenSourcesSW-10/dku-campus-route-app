"""
Building lookup API.

프론트의 건물 선택 UI, 지도 마커, 층 선택 UI에서 사용하는 기본 조회 endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Building, IndoorMap
from app.schemas.buildings import BuildingFloorResponse, BuildingResponse

router = APIRouter(prefix="/api/buildings", tags=["buildings"])


@router.get("", response_model=list[BuildingResponse])
def list_buildings(db: Session = Depends(get_db)):
    # 지도 마커와 건물 선택 UI에 사용할 건물 목록 반환.
    return (
        db.query(Building)
        .options(selectinload(Building.aliases))
        .order_by(Building.name)
        .all()
    )


@router.get("/{building_id}/floors", response_model=list[BuildingFloorResponse])
def list_building_floors(building_id: str, db: Session = Depends(get_db)):
    # 프론트엔드가 건물 선택 후 층 선택 UI를 만들 수 있게 층 목록 반환.
    building = db.get(Building, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="BUILDING_NOT_FOUND")
    return (
        db.query(IndoorMap)
        .filter(IndoorMap.building_id == building_id)
        .order_by(IndoorMap.floor_number.asc())
        .all()
    )


@router.get("/{building_id}", response_model=BuildingResponse)
def get_building(building_id: str, db: Session = Depends(get_db)):
    # 특정 건물 상세 정보 조회.
    building = (
        db.query(Building)
        .options(selectinload(Building.aliases))
        .filter(Building.building_id == building_id)
        .first()
    )
    if not building:
        raise HTTPException(status_code=404, detail="BUILDING_NOT_FOUND")
    return building
