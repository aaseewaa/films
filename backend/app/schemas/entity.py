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
    title_en: str | None = None
    directed_count: int | None = None  # фильмы как режиссёр в нашей БД
    acted_count: int | None = None   # фильмы как актёр в нашей БД
    series_count: int | None = None  # сериалы (пока не загружаем)

    model_config = ConfigDict(from_attributes=True)


class FilmRef(BaseModel):
    """Краткая ссылка на фильм (для фильмографии персоны)."""

    id: int
    title: str
    original_title: str | None = None
    release_year: int | None = None
    images: ImageURLs = ImageURLs()
    role_type: str | None = None
    media_kind: str | None = None  # фильм | мультфильм | сериал
    genres: list[str] = []
    country: str | None = None
    director: str | None = None
    actors: list[str] = []

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


class PersonAwardItem(BaseModel):
    """Одна номинация / победа персоны (award_nomination.person_id)."""

    status: Literal["won", "nominated"]
    year: int
    award_name: str
    category_name: str | None = None
    film_title: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PersonAwardsBlock(BaseModel):
    wins_count: int = 0
    nominations_count: int = 0  # только status=nominated (без побед)
    items: list[PersonAwardItem] = []

    model_config = ConfigDict(from_attributes=True)


# ─── Полные схемы сущностей ─────────────────────────────────────


class FilmRead(BaseModel):
    """Полная карточка фильма."""

    id: int
    entity_type: Literal["film"] = "film"

    title: str
    original_title: str | None = None
    summary: str | None = None
    description: str | None = None

    release_year: int | None = None
    release_date: date | None = None
    runtime_min: int | None = None
    age_rating: str | None = None

    images: ImageURLs = ImageURLs()

    backdrop_url: str | None = None
    stills_urls: list[str] = []
    media_kind: str | None = None  # фильм | мультфильм | сериал

    genres: list[TaxonomyTermRead] = []
    production_countries: str | None = None
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
    title_en: str | None = None
    summary: str | None = None
    description: str | None = None  # биография

    birth_date: date | None = None
    death_date: date | None = None
    birth_place: str | None = None
    primary_profession: str | None = None
    is_director: bool = False
    is_actor: bool = False
    directed_count: int | None = None
    acted_count: int | None = None
    series_count: int | None = None
    crew_roles: list[str] = []

    images: ImageURLs = ImageURLs()

    filmography: list[FilmRef] = []
    # Граф влияний — только для режиссёров
    influenced_by: list[InfluenceRef] = []  # повлияли на эту персону
    influenced: list[InfluenceRef] = []     # эта персона повлияла на других

    awards: PersonAwardsBlock | None = None

    external_ids: dict = {}

    model_config = ConfigDict(from_attributes=True)
