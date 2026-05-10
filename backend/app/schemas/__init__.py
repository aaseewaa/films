"""Pydantic-схемы для API."""
from app.schemas.catalog import (
    FilmCard,
    FilmsResponse,
    GenreItem,
    PersonCard,
    PersonsResponse,
    PopularResponse,
)
from app.schemas.common import (
    ImageURLs,
    LanguageRead,
    PaginatedResponse,
    TaxonomyTermRead,
)
from app.schemas.entity import (
    FilmRead,
    FilmRef,
    InfluenceRef,
    PersonRead,
    PersonRef,
)
from app.schemas.search import SearchHit, SearchResponse

__all__ = [
    # Поиск
    "SearchHit",
    "SearchResponse",
    # Сущности
    "FilmRead",
    "FilmRef",
    "PersonRead",
    "PersonRef",
    "InfluenceRef",
    # Каталог
    "FilmCard",
    "FilmsResponse",
    "PersonCard",
    "PersonsResponse",
    "GenreItem",
    "PopularResponse",
    # Общие
    "ImageURLs",
    "LanguageRead",
    "PaginatedResponse",
    "TaxonomyTermRead",
]
