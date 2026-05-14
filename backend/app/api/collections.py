"""
API: коллекции.
GET /api/collections           - список редакторских подборок
GET /api/collection/{id}       - содержимое одной коллекции
"""
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.collections import CollectionDetail, CollectionsListResponse
from app.services.collections_service import CollectionsService

router = APIRouter(tags=["collections"])


@router.get(
    "/api/collections",
    response_model=CollectionsListResponse,
    summary="Список коллекций (редакторские подборки)",
)
async def list_collections(
    kind: Annotated[
        Optional[Literal["custom", "editorial", "auto"]],
        Query(description="Фильтр по типу: editorial — редакционные, custom — пользовательские, auto — авто"),
    ] = None,
    only_featured: Annotated[bool, Query(description="Только избранные")] = False,
    lang: Annotated[Literal["ru", "en"], Query()] = "ru",
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
    db: AsyncSession = Depends(get_db),
) -> CollectionsListResponse:
    """
    Список коллекций — редакторские подборки фильмов, журналистские selections.

    По умолчанию возвращает все коллекции (без фильтра kind).
    Фильтр `kind=editorial` — только редакционные.
    """
    service = CollectionsService(db)
    result = await service.list_collections(
        kind=kind, lang=lang, only_featured=only_featured,
        limit=limit, offset=offset,
    )
    return CollectionsListResponse(**result)


@router.get(
    "/api/collection/{collection_id}",
    response_model=CollectionDetail,
    summary="Полная коллекция с содержимым",
)
async def get_collection(
    collection_id: int,
    lang: Annotated[Literal["ru", "en"], Query()] = "ru",
    db: AsyncSession = Depends(get_db),
) -> CollectionDetail:
    """
    Содержимое коллекции — фильмы/режиссёры в порядке, заданном редактором.
    """
    service = CollectionsService(db)
    result = await service.get_collection(collection_id, lang=lang)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Коллекция {collection_id} не найдена")
    return CollectionDetail(**result)
