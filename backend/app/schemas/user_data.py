"""Схемы для пользовательских данных: избранное, оценки, история."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import ImageURLs


# ─── Избранное (watchlist) ───────────────────────────────────────


class FavoriteAddRequest(BaseModel):
    """Добавить в избранное."""
    status: Literal["want_to_watch", "watching", "watched", "dropped"] = "want_to_watch"
    note: str | None = Field(None, max_length=2000)


class FavoriteItem(BaseModel):
    """Элемент избранного с данными сущности."""
    entity_id: int
    entity_type: str
    title: str
    summary: str | None = None
    images: ImageURLs = ImageURLs()
    release_year: int | None = None
    status: str
    note: str | None = None
    added_at: datetime
    watched_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class FavoritesResponse(BaseModel):
    items: list[FavoriteItem]
    total: int
    limit: int
    offset: int


class FavoriteCheckResponse(BaseModel):
    """Быстрая проверка для иконки сердечка на карточке."""
    is_favorite: bool
    status: str | None = None


# ─── Пользовательские оценки ─────────────────────────────────────


class RateRequest(BaseModel):
    rating: int = Field(..., ge=1, le=10, description="Оценка от 1 до 10")
    would_recommend: bool | None = None


class RatingItem(BaseModel):
    entity_id: int
    rating: int
    would_recommend: bool | None
    rated_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EntityRatingStats(BaseModel):
    """Сводная статистика оценок сущности (от всех пользователей)."""
    avg_rating: float | None = None
    total_ratings: int = 0
    recommend_percent: float | None = None  # сколько % рекомендуют (would_recommend=true)


# ─── История ─────────────────────────────────────────────────────


class SearchHistoryItem(BaseModel):
    query_text: str
    results_count: int
    searched_at: datetime
    language_code: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ViewHistoryItem(BaseModel):
    entity_id: int
    entity_type: str
    title: str
    images: ImageURLs = ImageURLs()
    viewed_at: datetime
    duration_seconds: int | None = None

    model_config = ConfigDict(from_attributes=True)


class HistoryResponse(BaseModel):
    """Универсальный ответ для истории — поиски ИЛИ просмотры."""
    searches: list[SearchHistoryItem] = []
    views: list[ViewHistoryItem] = []
