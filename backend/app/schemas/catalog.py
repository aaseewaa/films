"""
Pydantic-схемы для эндпоинтов каталога.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.common import ImageURLs


# ─── Карточка для списка ────────────────────────────────────────


class FilmCard(BaseModel):
    """Краткая карточка фильма для каталога / popular / результатов фильтра."""

    id: int
    entity_type: Literal["film"] = "film"
    title: str
    original_title: str | None = None  # en-перевод как оригинальное название
    summary: str | None = None
    release_year: int | None = None
    runtime_min: int | None = None
    images: ImageURLs = ImageURLs()
    genres: list[str] = []
    director: str | None = None
    actors: list[str] = []
    country: str | None = None
    vote_average: float | None = None
    popularity: float | None = None

    model_config = ConfigDict(from_attributes=True)


class PersonCard(BaseModel):
    """Краткая карточка персоны для каталога."""

    id: int
    entity_type: Literal["person"] = "person"
    title: str
    summary: str | None = None
    images: ImageURLs = ImageURLs()
    is_director: bool = False
    is_actor: bool = False
    primary_profession: str | None = None
    birth_year: int | None = None
    influences_count: int | None = None  # сколько раз был источником влияния

    model_config = ConfigDict(from_attributes=True)


# ─── Ответы со страничной выдачей ───────────────────────────────


class FilmsResponse(BaseModel):
    items: list[FilmCard]
    total: int
    limit: int
    offset: int


class PersonsResponse(BaseModel):
    items: list[PersonCard]
    total: int
    limit: int
    offset: int


# ─── Жанры ───────────────────────────────────────────────────────


class GenreItem(BaseModel):
    id: int
    code: str | None
    name: str  # переведённое имя
    films_count: int  # сколько фильмов в этом жанре

    model_config = ConfigDict(from_attributes=True)


# ─── Главная страница (popular) ─────────────────────────────────


class PopularResponse(BaseModel):
    """Подборки для главной страницы."""

    top_rated_films: list[FilmCard]    # топ по рейтингу
    popular_films: list[FilmCard]      # топ по популярности
    influential_directors: list[PersonCard]  # топ по числу связей в графе
