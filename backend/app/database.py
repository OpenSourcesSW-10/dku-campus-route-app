from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy import inspect, text
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


def ensure_sqlite_schema() -> None:
    # create_all은 기존 테이블에 새 컬럼을 추가하지 않으므로 SQLite 개발 DB만 보정한다.
    if not settings.database_url.startswith("sqlite"):
        return

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    static_cost_columns = {
        "cost_fast": "FLOAT DEFAULT 1.0",
        "cost_comfortable": "FLOAT DEFAULT 1.0",
        "cost_indoor": "FLOAT DEFAULT 1.0",
    }

    with engine.begin() as connection:
        for table_name in ("indoor_edges", "outdoor_edges"):
            if table_name not in existing_tables:
                continue
            existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, column_type in static_cost_columns.items():
                if column_name not in existing_columns:
                    connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))
