from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


connect_args = {}
if settings.database_url.startswith("sqlite"):
    # FastAPI 요청 처리 중 SQLite 세션을 여러 스레드에서 쓸 수 있게 한다.
    connect_args["check_same_thread"] = False

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    # 모든 SQLAlchemy 모델이 상속하는 기준 클래스이다.
    pass


def get_db() -> Generator[Session, None, None]:
    # FastAPI Depends에서 요청마다 DB 세션을 열고 닫는다.
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
