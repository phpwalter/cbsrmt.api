from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000

    database_url: str = "postgresql://root@localhost:5432/cbsrmt"
    database_min_pool: int = Field(default=1, ge=1, le=20)
    database_max_pool: int = Field(default=10, ge=1, le=100)

    auth_enabled: bool = True
    auth_jwks_url: str | None = None
    auth_issuer: str | None = None
    auth_audience: str | None = None
    auth_algorithms: str = "RS256"
    jwt_secret: str | None = None

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    rate_limit_limit: int = Field(default=100, ge=1)
    rate_limit_window_seconds: int = Field(default=60, ge=1)

    @property
    def algorithms(self) -> list[str]:
        return [item.strip() for item in self.auth_algorithms.split(",") if item.strip()]

    @property
    def origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
