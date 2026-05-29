"""
Эндпоинты каталога:
  GET /api/films         — список фильмов с фильтрами
  GET /api/persons       — список персон с фильтрами
  GET /api/genres        — все жанры с количеством фильмов
  GET /api/popular       — подборки для главной страницы
"""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_catalog_service
from app.services.catalog_service import CatalogService
from app.schemas.catalog import (
    FilmsResponse,
    GenreItem,
    PersonsResponse,
    PopularResponse,
)
router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/films", response_model=FilmsResponse, summary="Каталог фильмов")
async def list_films(
    lang: Annotated[Literal["ru", "en"], Query(description="Язык переводов")] = "ru",
    genre: Annotated[
        str | None,
        Query(description="Код жанра (action, drama, comedy, ...)"),
    ] = None,
    country: Annotated[
        str | None,
        Query(description="ISO-код страны производства (US, FR, ...)"),
    ] = None,
    year_from: Annotated[int | None, Query(ge=1880, le=2100)] = None,
    year_to: Annotated[int | None, Query(ge=1880, le=2100)] = None,
    catalog: Annotated[
        Literal["films", "animation"],
        Query(
            description="films — без мультфильмов; animation — только анимация (tmdb-16)",
        ),
    ] = "films",
    sort_by: Annotated[
        Literal["popularity", "vote_average", "year", "year_asc", "title"],
        Query(
            description="Сортировка: popularity (редакционные → популярность, без приоритета "
            "свежих релизов), vote_average, year (новые), year_asc (старые), title (А–Я)",
        ),
    ] = "popularity",
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
    service: CatalogService = Depends(get_catalog_service),
) -> FilmsResponse:
    """
    Каталог фильмов с фильтрами и сортировкой.

    Используется для:
    - Страницы "Все фильмы"
    - Страницы фильмов по жанру: `?genre=drama`
    - Страницы фильмов по годам: `?year_from=2000&year_to=2010`
    - Топ-листов: `?sort_by=vote_average`
    """
    result = await service.list_films(
        lang=lang,
        catalog=catalog,
        genre=genre,
        country=country,
        year_from=year_from,
        year_to=year_to,
        sort_by=sort_by,
        limit=limit,
        offset=offset,
    )
    return FilmsResponse(**result)


@router.get(
    "/production-countries",
    response_model=list[GenreItem],
    summary="Страны производства для фильтра",
)
async def list_production_countries(
    lang: Annotated[Literal["ru", "en"], Query()] = "ru",
    service: CatalogService = Depends(get_catalog_service),
) -> list[GenreItem]:
    items = await service.list_production_countries(lang=lang)
    return [GenreItem(**item) for item in items]


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
    service: CatalogService = Depends(get_catalog_service),
) -> PersonsResponse:
    """
    Каталог персон (режиссёры и актёры) с фильтрами и сортировкой.

    Используется для:
    - Страницы "Все режиссёры": `?is_director=true&sort_by=influences`
    - Страницы "Все актёры": `?is_actor=true`
    - Топ влиятельных режиссёров: `?is_director=true&sort_by=influences`
    """
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
    service: CatalogService = Depends(get_catalog_service),
) -> list[GenreItem]:
    """
    Все жанры с переводом названия на запрошенный язык и количеством
    фильмов в каждом жанре. Сортировка по убыванию количества фильмов.

    Используется для:
    - Меню/sidebar с навигацией по жанрам
    - Автокомплита фильтра жанра
    """
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
    service: CatalogService = Depends(get_catalog_service),
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
    result = await service.popular(lang=lang, limit=limit)
    return PopularResponse(**result)
