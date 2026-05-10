"""
Эндпоинты каталога:
  GET /api/films         — список фильмов с фильтрами
  GET /api/persons       — список персон с фильтрами
  GET /api/genres        — все жанры с количеством фильмов
  GET /api/popular       — подборки для главной страницы
"""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.catalog import (
    FilmsResponse,
    GenreItem,
    PersonsResponse,
    PopularResponse,
)
from app.services.catalog_service import CatalogService

router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/films", response_model=FilmsResponse, summary="Каталог фильмов")
async def list_films(
    lang: Annotated[Literal["ru", "en"], Query(description="Язык переводов")] = "ru",
    genre: Annotated[
        str | None,
        Query(description="Код жанра (action, drama, comedy, ...)"),
    ] = None,
    year_from: Annotated[int | None, Query(ge=1880, le=2100)] = None,
    year_to: Annotated[int | None, Query(ge=1880, le=2100)] = None,
    sort_by: Annotated[
        Literal["popularity", "vote_average", "year", "title"],
        Query(description="Сортировка: popularity (популярность), vote_average (рейтинг), year (год), title (название)"),
    ] = "popularity",
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
    db: AsyncSession = Depends(get_db),
) -> FilmsResponse:
    """
    Каталог фильмов с фильтрами и сортировкой.

    Используется для:
    - Страницы "Все фильмы"
    - Страницы фильмов по жанру: `?genre=drama`
    - Страницы фильмов по годам: `?year_from=2000&year_to=2010`
    - Топ-листов: `?sort_by=vote_average`
    """
    service = CatalogService(db)
    result = await service.list_films(
        lang=lang,
        genre=genre,
        year_from=year_from,
        year_to=year_to,
        sort_by=sort_by,
        limit=limit,
        offset=offset,
    )
    return FilmsResponse(**result)


@router.get("/persons", response_model=PersonsResponse, summary="Каталог персон")
async def list_persons(
    lang: Annotated[Literal["ru", "en"], Query()] = "ru",
    is_director: Annotated[
        bool | None,
        Query(description="Только режиссёры (true) или не режиссёры (false)"),
    ] = None,
    is_actor: Annotated[bool | None, Query(description="Только актёры")] = None,
    sort_by: Annotated[
        Literal["influences", "name", "birth_year"],
        Query(description="influences (по числу влияний), name (имя), birth_year (год рождения)"),
    ] = "influences",
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
    db: AsyncSession = Depends(get_db),
) -> PersonsResponse:
    """
    Каталог персон (режиссёры и актёры) с фильтрами и сортировкой.

    Используется для:
    - Страницы "Все режиссёры": `?is_director=true&sort_by=influences`
    - Страницы "Все актёры": `?is_actor=true`
    - Топ влиятельных режиссёров: `?is_director=true&sort_by=influences`
    """
    service = CatalogService(db)
    result = await service.list_persons(
        lang=lang,
        is_director=is_director,
        is_actor=is_actor,
        sort_by=sort_by,
        limit=limit,
        offset=offset,
    )
    return PersonsResponse(**result)


@router.get(
    "/genres",
    response_model=list[GenreItem],
    summary="Список жанров с количеством фильмов",
)
async def list_genres(
    lang: Annotated[Literal["ru", "en"], Query()] = "ru",
    db: AsyncSession = Depends(get_db),
) -> list[GenreItem]:
    """
    Все жанры с переводом названия на запрошенный язык и количеством
    фильмов в каждом жанре. Сортировка по убыванию количества фильмов.

    Используется для:
    - Меню/sidebar с навигацией по жанрам
    - Автокомплита фильтра жанра
    """
    service = CatalogService(db)
    items = await service.list_genres(lang=lang)
    return [GenreItem(**item) for item in items]


@router.get(
    "/popular",
    response_model=PopularResponse,
    summary="Подборки для главной страницы",
)
async def popular(
    lang: Annotated[Literal["ru", "en"], Query()] = "ru",
    limit: Annotated[
        int,
        Query(ge=4, le=24, description="Количество элементов в каждой подборке"),
    ] = 12,
    db: AsyncSession = Depends(get_db),
) -> PopularResponse:
    """
    Три подборки для главной страницы одним запросом:
    - **top_rated_films**: топ-фильмы по рейтингу TMDB (классика)
    - **popular_films**: топ-фильмы по популярности (современные хиты)
    - **influential_directors**: режиссёры с наибольшим числом влияний в графе

    Используется для:
    - Главной страницы сайта
    - Виджета "Что посмотреть" в sidebar
    """
    service = CatalogService(db)
    result = await service.popular(lang=lang, limit=limit)
    return PopularResponse(**result)
