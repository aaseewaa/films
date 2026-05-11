"""
Эндпоинты пользовательских данных:
  - /api/favorites — избранное (watchlist)
  - /api/ratings — пользовательские оценки
  - /api/history — история поисков и просмотров
"""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, require_user
from app.database import get_db
from app.schemas.user_data import (
    EntityRatingStats,
    FavoriteAddRequest,
    FavoriteCheckResponse,
    FavoritesResponse,
    HistoryResponse,
    RateRequest,
    RatingItem,
    SearchHistoryItem,
    ViewHistoryItem,
)
from app.services.user_data_service import UserDataService

router = APIRouter(prefix="/api", tags=["user_data"])


# ─── Избранное ───────────────────────────────────────────────────


@router.post(
    "/favorites/{entity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Добавить в избранное",
)
async def add_favorite(
    entity_id: int,
    body: FavoriteAddRequest = FavoriteAddRequest(),
    user: CurrentUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Добавить фильм/режиссёра в избранное. Если уже есть — обновляет статус."""
    service = UserDataService(db)
    await service.add_to_favorites(
        user.id, entity_id, status=body.status, note=body.note
    )


@router.delete(
    "/favorites/{entity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить из избранного",
)
async def remove_favorite(
    entity_id: int,
    user: CurrentUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = UserDataService(db)
    removed = await service.remove_from_favorites(user.id, entity_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Не найдено в избранном")


@router.get(
    "/favorites",
    response_model=FavoritesResponse,
    summary="Мой список избранного",
)
async def list_favorites(
    lang: Annotated[Literal["ru", "en"], Query()] = "ru",
    type: Annotated[Literal["film", "person"] | None, Query(description="Фильтр по типу")] = None,
    status_filter: Annotated[
        Literal["want_to_watch", "watching", "watched", "dropped"] | None,
        Query(alias="status", description="Фильтр по статусу"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    user: CurrentUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> FavoritesResponse:
    service = UserDataService(db)
    result = await service.list_favorites(
        user.id, lang=lang, entity_type=type, status=status_filter,
        limit=limit, offset=offset,
    )
    return FavoritesResponse(**result)


@router.get(
    "/favorites/check/{entity_id}",
    response_model=FavoriteCheckResponse,
    summary="Проверить, в избранном ли сущность",
)
async def check_favorite(
    entity_id: int,
    user: CurrentUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> FavoriteCheckResponse:
    """Быстрый эндпоинт для иконки сердечка на карточке."""
    service = UserDataService(db)
    result = await service.check_favorite(user.id, entity_id)
    return FavoriteCheckResponse(**result)


# ─── Оценки ──────────────────────────────────────────────────────


@router.put(
    "/ratings/{entity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Поставить или обновить оценку",
)
async def rate_entity(
    entity_id: int,
    body: RateRequest,
    user: CurrentUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = UserDataService(db)
    await service.rate_entity(
        user.id, entity_id,
        rating=body.rating, would_recommend=body.would_recommend,
    )


@router.delete(
    "/ratings/{entity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить мою оценку",
)
async def unrate_entity(
    entity_id: int,
    user: CurrentUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = UserDataService(db)
    removed = await service.remove_rating(user.id, entity_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Оценка не найдена")


@router.get(
    "/ratings/me/{entity_id}",
    response_model=RatingItem | None,
    summary="Моя оценка конкретной сущности",
)
async def get_my_rating(
    entity_id: int,
    user: CurrentUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> RatingItem | None:
    service = UserDataService(db)
    row = await service.get_my_rating(user.id, entity_id)
    return RatingItem(**row) if row else None


@router.get(
    "/ratings/stats/{entity_id}",
    response_model=EntityRatingStats,
    summary="Сводная статистика оценок сущности",
)
async def entity_rating_stats(
    entity_id: int,
    db: AsyncSession = Depends(get_db),
) -> EntityRatingStats:
    """Средняя пользовательская оценка и процент рекомендующих. Без авторизации."""
    service = UserDataService(db)
    stats = await service.get_entity_rating_stats(entity_id)
    return EntityRatingStats(**stats)


# ─── История ─────────────────────────────────────────────────────


@router.get(
    "/history",
    response_model=HistoryResponse,
    summary="История поисков и просмотров",
)
async def my_history(
    lang: Annotated[Literal["ru", "en"], Query()] = "ru",
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    user: CurrentUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> HistoryResponse:
    """
    Возвращает последние N поисков и N просмотров текущего пользователя.
    Используется для виджетов "Недавно искали" и "Продолжить просмотр".
    """
    service = UserDataService(db)
    searches = await service.get_search_history(user.id, limit=limit)
    views = await service.get_view_history(user.id, lang=lang, limit=limit)

    return HistoryResponse(
        searches=[SearchHistoryItem(**s) for s in searches],
        views=[ViewHistoryItem(**v) for v in views],
    )
