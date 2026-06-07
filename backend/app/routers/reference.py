"""
Reference data API.

DB 브랜치의 분류/출입구 CSV를 프론트에서 표시명 변환과 필터 UI에 사용할 수 있게 제공.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import EdgeType, EntranceMaster, IndoorNodeType, RoomCategory
from app.schemas.reference import ReferenceDataResponse


router = APIRouter(prefix="/api/reference-data", tags=["reference-data"])


@router.get("", response_model=ReferenceDataResponse)
def get_reference_data(db: Session = Depends(get_db)):
    # 경로 계산 필수값은 아니지만, 프론트의 타입 표시명/출입구 목록 UI에 사용.
    return ReferenceDataResponse(
        edgeTypes=db.query(EdgeType).order_by(EdgeType.edge_type).all(),
        indoorNodeTypes=db.query(IndoorNodeType).order_by(IndoorNodeType.node_type).all(),
        roomCategories=db.query(RoomCategory).order_by(RoomCategory.room_type).all(),
        entrances=db.query(EntranceMaster).order_by(EntranceMaster.building_id, EntranceMaster.floor_number).all(),
    )
