from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.rooms import RoomSearchResponse
from app.services.resolver import resolve_room_keyword

router = APIRouter(prefix="/api/rooms", tags=["rooms"])


ERROR_MESSAGES = {
    "EMPTY_KEYWORD": "검색어를 입력해 주세요.",
    "ROOM_NUMBER_NOT_FOUND": "검색어에서 호실 번호를 찾을 수 없습니다.",
    "BUILDING_NOT_FOUND": "검색한 건물을 찾을 수 없습니다.",
    "ROOM_NOT_FOUND": "검색한 강의실을 찾을 수 없습니다.",
    "INDOOR_MAP_NOT_FOUND": "해당 강의실의 실내 지도 정보를 찾을 수 없습니다.",
    "POSITION_NOT_FOUND": "강의실 좌표가 아직 등록되지 않았습니다.",
}


@router.get("/search", response_model=RoomSearchResponse)
def search_room(keyword: str = Query(...), db: Session = Depends(get_db)):
    # "소프트305" 같은 입력을 강의실 검색 결과로 변환한다.
    result = resolve_room_keyword(db, keyword)
    if result.error_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "errorCode": result.error_code,
                "message": ERROR_MESSAGES.get(result.error_code, "검색 처리 중 오류가 발생했습니다."),
            },
        )
    return result.payload
