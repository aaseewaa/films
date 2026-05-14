"""
Схемы рекомендаций.

Для карточки фильма — блок "Похожие фильмы".
Для карточки персоны — блок "Похожие режиссёры".
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.common import ImageURLs


class RecommendationItem(BaseModel):
    """Один рекомендуемый элемент с объяснением почему."""

    entity_id: int
    entity_type: Literal["film", "person"]
    title: str
    summary: str | None = None
    images: ImageURLs = ImageURLs()
    release_year: int | None = None        # для фильмов
    score: float                            # релевантность 0-1
    reasons: list[str] = []                 # ["общий режиссёр: Хичкок", "общий жанр: триллер"]

    model_config = ConfigDict(from_attributes=True)


class RecommendationsResponse(BaseModel):
    items: list[RecommendationItem]
    source_entity_id: int
    source_entity_type: str
    algorithm: Literal["content_based", "graph_based", "hybrid", "semantic"] = "content_based"
