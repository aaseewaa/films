"""
Настройки приложения. Читаются из .env через pydantic-settings.

Использование:
    from app.config import settings
    print(settings.database_url)

Никогда не хардкодь значения — всё через .env.
"""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Все настройки приложения в одном месте."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── База данных ──────────────────────────────────────────────
    database_url: str = Field(
        ...,
        description="PostgreSQL connection URL with asyncpg driver",
    )
    db_echo: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10

    # ─── Приложение ───────────────────────────────────────────────
    app_name: str = "FMW API"
    app_version: str = "0.1.0"
    app_debug: bool = True

    # ─── Языки ────────────────────────────────────────────────────
    default_language: str = "ru"
    supported_languages: str = "ru,en"

    # ─── CORS ─────────────────────────────────────────────────────
    cors_origins: str = "http://localhost:5173"

    # ─── Внешние API ──────────────────────────────────────────────
    tmdb_api_key: str = ""
    omdb_api_key: str = ""

    # ─── Безопасность ─────────────────────────────────────────────
    secret_key: str = Field(
        default="dev-only-secret-change-in-production",
        description="JWT signing key; override via SECRET_KEY in production",
    )
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # неделя

    # ─── Загрузки (аватары) ─────────────────────────────────────
    uploads_dir: str = "uploads"
    avatar_max_bytes: int = 2 * 1024 * 1024  # 2 MB

    # ─── Удобные свойства ─────────────────────────────────────────
    @property
    def supported_languages_list(self) -> list[str]:
        return [lang.strip() for lang in self.supported_languages.split(",") if lang.strip()]

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Кэшированный getter, чтобы .env читался один раз за процесс."""
    return Settings()


# Удобный синглтон для импорта: from app.config import settings
settings = get_settings()
