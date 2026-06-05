
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


    HOST: str = "0.0.0.0"
    PORT: int = 4318
    DEBUG: bool = False
    WORKERS: int = 4


    SECRET_KEY: str = "8898d4b27fe2440438ea1fa28e93b2aa43d25de6f0f519159444a7201a0092a3"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30


    DATABASE_URL: str = "sqlite+aiosqlite:///./groozer.db"

    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:4318",
        "http://127.0.0.1:4318",
    ]


    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: List[str] = ["jpg", "jpeg", "png", "webp", "pdf"]


    ADMIN_EMAIL: str = "admin@groozer.local"
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "Admin123"

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_flag(cls, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "development", "dev"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "production", "prod"}:
                return False
        return value


settings = Settings()
