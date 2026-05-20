"""Схемы для вкладки «Новинки» / афиша в кино."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import ImageURLs


class NewsCinemaHint(BaseModel):
    """Кинотеатр, где идёт фильм (из парсинга афиши)."""

    name: str


class NewsFilmItem(BaseModel):
    """Фильм в прокате в городе пользователя."""

    kinopoisk_id: int | None = None
    title: str
    entity_id: int | None = None
    release_year: int | None = None
    summary: str | None = None
    images: ImageURLs = ImageURLs()
    ticket_url: str
    ticket_provider: Literal["kinopoisk"] = "kinopoisk"
    cinemas: list[str] = Field(default_factory=list)
    in_database: bool = False
    tmdb_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class NewsResponse(BaseModel):
    city: str
    city_kp_id: str
    source: Literal[
        "kinopoisk_afisha", "tmdb_fallback", "tmdb_world", "tmdb_upcoming"
    ] = "kinopoisk_afisha"
    fetched_at: datetime
    items: list[NewsFilmItem]
    total: int
    limit: int
