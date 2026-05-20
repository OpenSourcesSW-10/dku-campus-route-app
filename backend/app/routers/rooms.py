from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.rooms import RoomSearchResponse
from app.services.resolver import resolve_room_keyword

router = APIRouter(prefix="/api/rooms", tags=["week3-rooms"])


@router.get("/search", response_model=RoomSearchResponse)
def search_room(keyword: str = Query(...), db: Session = Depends(get_db)):
    # "소프트305" 같은 입력을 강의실 검색 결과로 변환한다.
    result = resolve_room_keyword(db, keyword)
    if result.error_code:
        raise HTTPException(status_code=404, detail=result.error_code)
    return result.payload
