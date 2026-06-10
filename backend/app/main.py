from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, SessionLocal, engine, ensure_sqlite_schema
from app.routers import auth, buildings, indoor, outdoor, reference, reports, rooms, routes, status, tmi
from app.seed.available_data import import_available_week8_data, raise_for_failed_reports
from app.seed.sample_data import seed_database


def create_app() -> FastAPI:
    # FastAPI 앱 생성 및 프론트엔드 연동용 API 라우터 연결.
    app = FastAPI(title=settings.app_name, debug=settings.debug)

    # 프론트엔드 개발 서버와 연동할 수 있도록 CORS 허용.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.frontend_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(buildings.router)
    app.include_router(auth.router)
    app.include_router(rooms.router)
    app.include_router(indoor.router)
    app.include_router(outdoor.router)
    app.include_router(reference.router)
    app.include_router(routes.router)
    app.include_router(tmi.router)
    app.include_router(reports.router)
    app.include_router(status.router)

    @app.on_event("startup")
    def on_startup() -> None:
        # 서버 시작 시 테이블 생성. 제출/배포 설정이면 실제 week7 데이터, 로컬 기본값이면 파일럿 seed 사용.
        Base.metadata.create_all(bind=engine)
        ensure_sqlite_schema()
        if settings.import_data_on_start:
            _import_deployment_data()
        else:
            _seed_pilot_data()

    @app.get("/")
    def health_check():
        return {"message": "DKU Campus Map Week 8 Final API is running"}

    @app.get("/maps/{map_file_name}")
    def get_map_asset(map_file_name: str):
        # 프론트는 DB 응답의 map_file_url 값을 그대로 사용해 지도 파일 요청.
        path = _find_map_asset(map_file_name)
        if path is None:
            raise HTTPException(status_code=404, detail={"errorCode": "MAP_ASSET_NOT_FOUND", "message": "지도 파일을 찾을 수 없습니다."})
        return FileResponse(path)

    return app


app = create_app()


def _seed_pilot_data() -> None:
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()


def _import_deployment_data() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    data_root = _resolve_data_root(backend_root)
    db = SessionLocal()
    try:
        reports = import_available_week8_data(db, data_root, replace=False)
        raise_for_failed_reports(reports)
    except Exception as exc:
        db.rollback()
        raise RuntimeError(f"Failed to import deployment data from {data_root}") from exc
    finally:
        db.close()


def _find_map_asset(map_file_name: str) -> Path | None:
    safe_name = Path(map_file_name).name
    backend_root = Path(__file__).resolve().parents[1]
    project_root = Path(__file__).resolve().parents[4]
    deployment_data_root = _resolve_data_root(backend_root)
    configured_roots = [Path(root.strip()) for root in settings.map_asset_roots.split(",") if root.strip()]
    default_roots = [
        deployment_data_root / "내부 구조 설계" / "SVG",
        deployment_data_root / "내부 구조 설계" / "PNG(1000X707)",
        deployment_data_root / "외부 구조 설계_최종" / "PNG",
        deployment_data_root / "외부 구조 설계_최종" / "SVG",
        deployment_data_root / "외부 구조 설계" / "PNG",
        deployment_data_root / "외부 구조 설계" / "SVG",
        deployment_data_root / "PNG(1000X707)",
        deployment_data_root,
        project_root / "DB" / "내부 구조 설계" / "SVG",
        project_root / "DB" / "내부 구조 설계" / "PNG(1000X707)",
        project_root / "DB" / "외부 구조 설계_최종" / "PNG",
        project_root / "DB" / "외부 구조 설계_최종" / "SVG",
        project_root / "DB" / "외부 구조 설계" / "PNG",
        project_root / "DB" / "외부 구조 설계" / "SVG",
        project_root / "DB" / "pdf24_convertPdfTo",
        project_root / "DB" / "PNG(1000X707)",
        project_root / "DB" / "PNG",
        project_root / "DB",
    ]

    if safe_name == "campus-map.png":
        for campus_map in (
            deployment_data_root / "외부 구조 설계_최종" / "PNG" / "캠퍼스 지도.png",
            deployment_data_root / "외부 구조 설계_최종" / "캠퍼스 지도.png",
            deployment_data_root / "외부 구조 설계" / "PNG" / "캠퍼스 지도.png",
            deployment_data_root / "외부 구조 설계" / "캠퍼스 지도.png",
            project_root / "DB" / "외부 구조 설계_최종" / "PNG" / "캠퍼스 지도.png",
            project_root / "DB" / "외부 구조 설계_최종" / "캠퍼스 지도.png",
            project_root / "DB" / "외부 구조 설계" / "PNG" / "캠퍼스 지도.png",
            project_root / "DB" / "외부 구조 설계" / "캠퍼스 지도.png",
        ):
            if campus_map.exists():
                return campus_map

    for root in configured_roots + default_roots:
        if not root.exists():
            continue
        direct = root / safe_name
        if direct.exists() and direct.is_file():
            return direct
        for candidate in root.rglob(safe_name):
            if candidate.is_file():
                return candidate
    return None


def _resolve_data_root(backend_root: Path) -> Path:
    data_root = Path(settings.deployment_data_root)
    if data_root.is_absolute():
        return data_root
    return backend_root / data_root
