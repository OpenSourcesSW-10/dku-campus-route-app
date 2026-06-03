from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # .env 값이 있으면 아래 기본값을 덮어쓴다.
    app_name: str = "DKU Campus Map Week 7 API"
    database_url: str = "sqlite:///./week3_backend.db"
    debug: bool = True
    frontend_origins: str = (
        "http://localhost:5173,"
        "http://127.0.0.1:5173,"
        "https://tmimvp.vercel.app,"
        "http://tmimvp.vercel.app"
    )
    map_asset_roots: str = ""
    deployment_data_root: str = "data/week7"
    import_data_on_start: bool = False
    jwt_secret_key: str = "local-dev-change-this-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    email_verification_expire_minutes: int = 10
    enforce_dankook_email: bool = True
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_use_tls: bool = True
    email_delivery_mode: str = "console"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def frontend_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]


settings = Settings()
