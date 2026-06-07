"""
Outdoor map API.

캠퍼스 지도 위에 표시할 외부 노드, 외부 간선, 건물 출입구 연결 정보 제공.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import EntranceLink, OutdoorEdge, OutdoorNode
from app.schemas.outdoor import OutdoorMapResponse


router = APIRouter(prefix="/api/outdoor", tags=["outdoor-map"])


@router.get("/map", response_model=OutdoorMapResponse)
def get_outdoor_map(db: Session = Depends(get_db)):
    # 외부 경로 계산과 지도 표시가 같은 데이터를 보도록 DB의 outdoor graph 그대로 반환.
    nodes = db.query(OutdoorNode).order_by(OutdoorNode.outdoor_node_id.asc()).all()
    edges = db.query(OutdoorEdge).order_by(OutdoorEdge.outdoor_edge_id.asc()).all()
    entrance_links = (
        db.query(EntranceLink)
        .order_by(EntranceLink.building_id.asc(), EntranceLink.entrance_name.asc())
        .all()
    )
    return OutdoorMapResponse(
        map_file_url="/maps/campus-map.png",
        canvas_width=None,
        canvas_height=None,
        nodes=nodes,
        edges=edges,
        entrance_links=entrance_links,
    )
