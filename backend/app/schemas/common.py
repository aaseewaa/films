"""
Общие Pydantic-схемы для API.
"""
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Стандартный ответ с пагинацией."""

    items: list[T]
    total: int
    limit: int
    offset: int

    model_config = ConfigDict(from_attributes=True)


class ImageURLs(BaseModel):
    """Картинки сущности (постер фильма, фото персоны)."""

    primary: str | None = None
    thumbnail: str | None = None


class TaxonomyTermRead(BaseModel):
    """Жанр, страна, тег и т.д."""

    id: int
    code: str | None
    term_type: str
    name: str  # переведённое название на запрошенном языке

    model_config = ConfigDict(from_attributes=True)


class LanguageRead(BaseModel):
    id: int
    code: str
    native_name: str

    model_config = ConfigDict(from_attributes=True)
