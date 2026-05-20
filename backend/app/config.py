from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # .env 값이 있으면 아래 기본값을 덮어쓴다.
    app_name: str = "DKU Campus Map Week 3 API"
    database_url: str = "sqlite:///./week3_backend.db"
    debug: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
