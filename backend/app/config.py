from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # .env 값이 있으면 아래 기본값을 덮어쓴다.
    app_name: str = "DKU Campus Map Week 7 API"
    database_url: str = "sqlite:///./week3_backend.db"
    debug: bool = True
    frontend_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    map_asset_roots: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def frontend_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]


settings = Settings()
