from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy import inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


connect_args = {}
if settings.database_url.startswith("sqlite"):
    # FastAPI 요청 처리 중 SQLite 세션을 여러 스레드에서 사용할 수 있게 설정.
    connect_args["check_same_thread"] = False

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    # 모든 SQLAlchemy 모델이 상속하는 기준 클래스.
    pass


def get_db() -> Generator[Session, None, None]:
    # FastAPI Depends에서 요청마다 DB 세션 열기/닫기 처리.
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_sqlite_schema() -> None:
    # create_all은 기존 테이블에 새 컬럼을 추가하지 않음. SQLite 개발 DB만 보정.
    if not settings.database_url.startswith("sqlite"):
        return

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    static_cost_columns = {
        "cost_fast": "FLOAT DEFAULT 1.0",
        "cost_comfortable": "FLOAT DEFAULT 1.0",
        "cost_indoor": "FLOAT DEFAULT 1.0",
    }
    extra_columns = {
        "indoor_edges": {
            "is_bidirectional": "BOOLEAN DEFAULT 1",
        },
        "outdoor_nodes": {
            "map_x": "FLOAT",
            "map_y": "FLOAT",
            "outdoor_level": "VARCHAR(50)",
            "altitude_m": "FLOAT",
        },
        "outdoor_edges": {
            "is_bidirectional": "BOOLEAN DEFAULT 1",
            "altitude_gain": "FLOAT",
            "polyline_points": "TEXT",
        },
        "entrance_links": {
            "floor_number": "INTEGER",
        },
        "users": {
            "student_id": "VARCHAR(30)",
            "password_hash": "VARCHAR(255) DEFAULT ''",
            "role": "VARCHAR(30) DEFAULT 'USER'",
            "created_at": "VARCHAR(30)",
        },
        "tmi_locations": {
            "room_id": "VARCHAR(80)",
            "indoor_map_id": "VARCHAR(80)",
            "floor_number": "INTEGER",
            "map_x": "FLOAT",
            "map_y": "FLOAT",
            "representative_tags": "TEXT",
            "status": "VARCHAR(30) DEFAULT 'pending'",
            "verified_count": "INTEGER DEFAULT 0",
            "created_by": "VARCHAR(80)",
            "created_at": "VARCHAR(30)",
        },
        "reports": {
            "target_type": "VARCHAR(30) DEFAULT 'GENERAL'",
            "target_id": "VARCHAR(80)",
            "tmi_location_id": "VARCHAR(80)",
            "building_id": "VARCHAR(80)",
            "room_id": "VARCHAR(80)",
            "tags": "TEXT",
            "status": "VARCHAR(30) DEFAULT 'pending'",
            "verified_count": "INTEGER DEFAULT 0",
            "created_at": "VARCHAR(30)",
        },
    }

    with engine.begin() as connection:
        for table_name in ("indoor_edges", "outdoor_edges"):
            if table_name not in existing_tables:
                continue
            existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, column_type in static_cost_columns.items():
                if column_name not in existing_columns:
                    # 주차별 모델 확장 후에도 기존 로컬 SQLite DB 삭제 없이 테스트 가능하게 보정.
                    connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))

        for table_name, columns in extra_columns.items():
            if table_name not in existing_tables:
                continue
            existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, column_type in columns.items():
                if column_name not in existing_columns:
                    # PostgreSQL 배포는 migration 도구 권장, 과제 로컬 검증은 SQLite 자동 보정으로 충분.
                    connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))
