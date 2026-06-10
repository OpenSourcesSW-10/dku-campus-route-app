"""
Operational status endpoints.

단순 서버 생존 확인이 아니라 최종 제출 전 DB 자료가 경로 계산에 충분한지 점검.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.readiness import build_week8_readiness_report


router = APIRouter(prefix="/api/status", tags=["status"])


@router.get("/readiness")
@router.get("/week8-readiness", include_in_schema=False)
def get_week8_readiness(db: Session = Depends(get_db)):
    # week8-readiness는 기존 문서/링크 호환용으로 유지, Swagger에는 readiness만 노출.
    return build_week8_readiness_report(db)
