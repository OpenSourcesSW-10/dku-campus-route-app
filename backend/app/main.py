from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, SessionLocal, engine, ensure_sqlite_schema
from app.routers import buildings, indoor, rooms, routes
from app.seed.sample_data import seed_database


def create_app() -> FastAPI:
    # FastAPI 앱을 만들고 3주차 API 라우터를 연결한다.
    app = FastAPI(title=settings.app_name, debug=settings.debug)

    # 프론트엔드 개발 서버와 연동할 수 있도록 CORS를 열어둔다.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(buildings.router)
    app.include_router(rooms.router)
    app.include_router(indoor.router)
    app.include_router(routes.router)

    @app.on_event("startup")
    def on_startup() -> None:
        # 서버 시작 시 테이블을 만들고, 비어 있으면 파일럿 데이터를 넣는다.
        Base.metadata.create_all(bind=engine)
        ensure_sqlite_schema()
        db = SessionLocal()
        try:
            seed_database(db)
        finally:
            db.close()

    @app.get("/")
    def health_check():
        return {"message": "DKU Campus Map Week 3 API is running"}

    return app


app = create_app()
