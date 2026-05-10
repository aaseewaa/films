"""
Pydantic-схемы для эндпоинтов /api/entity/{id}.
"""
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import ImageURLs, TaxonomyTermRead


# ─── Маленькие "ссылочные" схемы (для вложенных связей) ──────────


class PersonRef(BaseModel):
    """Краткая ссылка на персону (для крю фильма, влияний и т.д.)."""

    id: int
    title: str
    images: ImageURLs = ImageURLs()
    role_type: str | None = None       # "director", "actor", ... — для крю фильма
    character_name: str | None = None  # для актёров
    billing_order: int | None = None

    model_config = ConfigDict(from_attributes=True)


class FilmRef(BaseModel):
    """Краткая ссылка на фильм (для фильмографии персоны)."""

    id: int
    title: str
    release_year: int | None = None
    images: ImageURLs = ImageURLs()
    role_type: str | None = None

    model_config = ConfigDict(from_attributes=True)


class InfluenceRef(BaseModel):
    """Связь влияния между двумя режиссёрами."""

    person_id: int
    title: str
    images: ImageURLs = ImageURLs()
    weight: int
    confidence: float
    relation_note: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ─── Полные схемы сущностей ─────────────────────────────────────


class FilmRead(BaseModel):
    """Полная карточка фильма."""

    id: int
    entity_type: Literal["film"] = "film"

    title: str
    summary: str | None = None
    description: str | None = None

    release_year: int | None = None
    release_date: date | None = None
    runtime_min: int | None = None
    age_rating: str | None = None

    images: ImageURLs = ImageURLs()

    genres: list[TaxonomyTermRead] = []
    directors: list[PersonRef] = []
    cast: list[PersonRef] = []  # актёры, отсортированы по billing_order

    extra_metadata: dict = {}    # vote_average, popularity, budget, revenue, tagline
    external_ids: dict = {}      # {"tmdb": "...", "imdb": "..."}

    model_config = ConfigDict(from_attributes=True)


class PersonRead(BaseModel):
    """Полная карточка персоны."""

    id: int
    entity_type: Literal["person"] = "person"

    title: str
    summary: str | None = None
    description: str | None = None  # биография

    birth_date: date | None = None
    death_date: date | None = None
    birth_place: str | None = None
    primary_profession: str | None = None
    is_director: bool = False
    is_actor: bool = False

    images: ImageURLs = ImageURLs()

    filmography: list[FilmRef] = []
    # Граф влияний — только для режиссёров
    influenced_by: list[InfluenceRef] = []  # повлияли на эту персону
    influenced: list[InfluenceRef] = []     # эта персона повлияла на других

    external_ids: dict = {}

    model_config = ConfigDict(from_attributes=True)
