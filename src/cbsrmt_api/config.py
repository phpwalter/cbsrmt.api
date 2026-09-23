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
    oauth_client_id: str | None = None
    oauth_client_secret: str | None = None
    oauth_token_algorithm: str = "HS256"
    oauth_token_ttl_seconds: int = Field(default=3600, ge=60, le=86400)

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    rate_limit_limit: int = Field(default=100, ge=1)
    rate_limit_window_seconds: int = Field(default=60, ge=1)

    # Episode MP3 files stay outside the repository. AUDIO_ROOT points at the
    # local directory containing four-digit files such as 0523.mp3.
    audio_root: str | None = None
    audio_url_prefix: str = "/audio"
    audio_public_base_url: str = "http://127.0.0.1:8000/audio"

    @property
    def algorithms(self) -> list[str]:
        return [item.strip() for item in self.auth_algorithms.split(",") if item.strip()]

    @property
    def origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
