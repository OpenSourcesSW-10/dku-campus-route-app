"""
Indoor map API.

프론트가 특정 건물/층의 실내 지도 이미지와 강의실 좌표, 실내 그래프를 함께 불러오는 endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Building, IndoorMap
from app.schemas.indoor import IndoorMapResponse

router = APIRouter(prefix="/api/buildings", tags=["week3-indoor-map"])


@router.get("/{building_id}/floors/{floor}/indoor-map", response_model=IndoorMapResponse)
def get_floor_indoor_map(building_id: str, floor: int, db: Session = Depends(get_db)):
    # 건물과 층 번호로 실내 지도, 강의실 좌표, 실내 그래프를 한 번에 반환.
    # 프론트가 같은 좌표계 위에 방 하이라이트와 경로선을 함께 그리기 위한 응답.
    building = db.get(Building, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="BUILDING_NOT_FOUND")

    indoor_map = (
        db.query(IndoorMap)
        .options(
            selectinload(IndoorMap.rooms),
            selectinload(IndoorMap.room_positions),
            selectinload(IndoorMap.indoor_nodes),
            selectinload(IndoorMap.indoor_edges),
        )
        .filter(
            IndoorMap.building_id == building_id,
            IndoorMap.floor_number == floor,
        )
        .first()
    )
    if not indoor_map:
        raise HTTPException(status_code=404, detail="INDOOR_MAP_NOT_FOUND")
    return indoor_map
