"""
Pydantic-схемы для API коллекций.

Коллекции - это редакторские подборки фильмов/режиссёров.
Технически - это сущность entity с entity_type='collection',
наследуется от entity через FK id REFERENCES entity(id) CASCADE.

Имена и описания - в entity_translation (как у фильмов).
Содержимое - через таблицу collection_item.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import ImageURLs


class CollectionItem(BaseModel):
    """Один элемент коллекции (фильм или другая сущность)."""
    entity_id: int
    entity_type: Literal["film", "person", "article", "collection"]
    title: str
    summary: str | None = None
    images: ImageURLs = ImageURLs()
    release_year: int | None = None
    position: int = 0
    note: str | None = None

    model_config = ConfigDict(from_attributes=True)


class CollectionSummary(BaseModel):
    """Краткая инфа о коллекции для списка /api/collections."""
    id: int
    kind: Literal["custom", "editorial", "auto"]
    title: str
    summary: str | None = None
    cover_image: str | None = None  # primary_image_url cover-сущности
    items_count: int = 0
    is_featured: bool = False
    tags: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class CollectionDetail(BaseModel):
    """Полная коллекция с её содержимым."""
    id: int
    kind: Literal["custom", "editorial", "auto"]
    title: str
    summary: str | None = None
    description: str | None = None
    cover_image: str | None = None
    items_count: int = 0
    tags: list[str] = Field(default_factory=list)
    items: list[CollectionItem]

    model_config = ConfigDict(from_attributes=True)


class CollectionsListResponse(BaseModel):
    """Ответ /api/collections."""
    items: list[CollectionSummary]
    total: int
    limit: int
    offset: int
