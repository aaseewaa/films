"""
Pydantic-схемы для эндпоинта /api/search.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import ImageURLs


class SearchHit(BaseModel):
    """Одна строка результата поиска (фильм, персона, и т.д.)."""

    entity_id: int = Field(..., description="ID сущности")
    entity_type: Literal["film", "person", "studio", "article", "collection"]
    title: str
    summary: str | None = None
    images: ImageURLs = ImageURLs()
    language_code: str | None = None  # на каком языке найдено (важно для semantic)

    # Метаданные специфичные для типа
    release_year: int | None = None  # для фильмов
    is_director: bool | None = None  # для персон
    is_actor: bool | None = None     # для персон

    # Релевантность
    score: float = Field(..., description="Ранжирующий score [0-1]")
    match_type: Literal["fulltext", "fuzzy", "exact", "semantic"] = Field(
        ..., description="Какой механизм нашёл результат"
    )

    model_config = ConfigDict(from_attributes=True)


class SearchResponse(BaseModel):
    """Ответ /api/search."""

    query: str
    detected_language: str  # ru/en
    items: list[SearchHit]
    total: int
    limit: int
    offset: int
    mode: Literal["hybrid", "semantic"] = "hybrid"
    used_strategies: list[str] = Field(
        default_factory=list,
        description="Какие стратегии поиска применялись",
    )
