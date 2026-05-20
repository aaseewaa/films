"""
Новинки в кино: афиша по городу пользователя.

GET /api/news — фильмы в прокате в городе (парсинг Кинопоиска + обогащение из БД/TMDB).
"""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_current_user
from app.database import get_db
from app.integrations.city_ref import list_cities
from app.schemas.news import NewsFilmItem, NewsResponse
from app.services.news_service import NewsService

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get(
    "",
    response_model=NewsResponse,
    summary="Новинки в кино в городе пользователя",
)
async def get_news(
    scope: Annotated[
        Literal["city", "world"],
        Query(description="city — афиша в городе; world — в мировом прокате"),
    ] = "world",
    city: Annotated[
        str | None,
        Query(description="Город (если не передан — из профиля или Москва)"),
    ] = None,
    lang: Annotated[Literal["ru", "en"], Query()] = "ru",
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    user: CurrentUser | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NewsResponse:
    """
  Афиша «сейчас в кино» для города.

  - Город: query `city` → иначе `city` из JWT-профиля → иначе Москва.
  - Источник: парсинг https://www.kinopoisk.ru/afisha/city/{id}/ (кэш 6 ч).
  - Карточки обогащаются постером/описанием из нашей БД и TMDB now_playing.
  - `ticket_url` ведёт на покупку билетов на Кинопоиске.
    """
    service = NewsService(db)
    if scope == "world":
        result = await service.get_worldwide(lang=lang, limit=limit)
    else:
        city_raw = city or (user.city if user else None)
        result = await service.get_news(city_raw=city_raw, lang=lang, limit=limit)
    return NewsResponse(**result)


@router.get(
    "/upcoming",
    response_model=NewsResponse,
    summary="Скоро в прокате (карусель)",
)
async def get_upcoming(
    lang: Annotated[Literal["ru", "en"], Query()] = "ru",
    limit: Annotated[int, Query(ge=1, le=20)] = 8,
    db: AsyncSession = Depends(get_db),
) -> NewsResponse:
    service = NewsService(db)
    return NewsResponse(**await service.get_upcoming(lang=lang, limit=limit))


@router.get(
    "/film/{entity_id}",
    response_model=NewsFilmItem,
    summary="Афиша фильма в городе пользователя",
)
async def get_film_afisha(
    entity_id: int,
    city: Annotated[str | None, Query()] = None,
    lang: Annotated[Literal["ru", "en"], Query()] = "ru",
    user: CurrentUser | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NewsFilmItem:
    from fastapi import HTTPException

    if user is None:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    service = NewsService(db)
    city_raw = city or user.city
    item = await service.get_film_afisha(
        entity_id=entity_id, city_raw=city_raw, lang=lang,
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Фильм не найден")
    return NewsFilmItem(**{k: v for k, v in item.items() if k != "city"})


@router.get("/cities", summary="Поддерживаемые города для афиши")
async def get_news_cities() -> list[dict]:
    """Список городов с id Кинопоиска (для select на регистрации)."""
    return [{"name": c.name, "slug": c.slug, "kp_city_id": c.kp_city_id} for c in list_cities()]
