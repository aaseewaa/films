"""
Эндпоинты графа влияний для визуализации.

GET /api/graph/director/{id}?depth=2
GET /api/graph/full?limit=50
"""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.graph import GraphCentersResponse, GraphResponse
from app.services.graph_service import GraphService
from app.services.radial_graph_service import RadialGraphService
from app.services.semantic_radial_service import SemanticRadialService

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get(
    "/director/{director_id}",
    response_model=GraphResponse,
    summary="Локальный граф вокруг режиссёра",
)
async def director_graph(
    director_id: int,
    depth: Annotated[
        int,
        Query(ge=1, le=3, description="Глубина обхода (1-3 шага)"),
    ] = 2,
    lang: Annotated[Literal["ru", "en"], Query()] = "ru",
    max_nodes: Annotated[
        int,
        Query(ge=10, le=200, description="Максимум узлов для визуализации"),
    ] = 50,
    db: AsyncSession = Depends(get_db),
) -> GraphResponse:
    """
    Граф влияний вокруг конкретного режиссёра.

    Возвращает данные в формате готовом для react-force-graph-2d:
    - `nodes`: массив узлов с id, name, image, метриками
    - `links`: массив рёбер source/target/weight/confidence

    Использует рекурсивный CTE для обхода графа на N шагов в обе стороны.
    """
    service = GraphService(db)
    result = await service.get_director_graph(
        director_id=director_id,
        depth=depth,
        lang=lang,
        max_nodes=max_nodes,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Режиссёр с id={director_id} не найден",
        )
    return GraphResponse(**result)


@router.get(
    "/full",
    response_model=GraphResponse,
    summary="Главный граф (топ N влиятельных + связи между ними)",
)
async def full_graph(
    limit: Annotated[
        int,
        Query(ge=10, le=100, description="Сколько топ-режиссёров взять"),
    ] = 50,
    lang: Annotated[Literal["ru", "en"], Query()] = "ru",
    db: AsyncSession = Depends(get_db),
) -> GraphResponse:
    """
    Глобальный граф для страницы 'Граф влияний'.

    Берём топ-N самых упоминаемых режиссёров и все связи между ними.
    Идеально для красивой главной визуализации.
    """
    service = GraphService(db)
    result = await service.get_full_graph(limit=limit, lang=lang)
    return GraphResponse(**result)

@router.get(
    "/centers",
    response_model=GraphCentersResponse,
    summary="Пул центров для главной (случайный режиссёр)",
)
async def graph_centers(
    limit: Annotated[
        int, Query(ge=10, le=200, description="Максимум кандидатов"),
    ] = 80,
    min_incoming: Annotated[
        int,
        Query(
            ge=1,
            le=10,
            description="Минимум входящих связей (учителей) у центра",
        ),
    ] = 2,
    lang: Annotated[Literal["ru", "en"], Query()] = "ru",
    db: AsyncSession = Depends(get_db),
) -> GraphCentersResponse:
    """
    Режиссёры с достаточным числом входящих влияний для радиального графа.

    Используется на главной для «Случайный режиссёр» вместо захардкоженного списка.
    """
    service = RadialGraphService(db)
    centers = await service.get_center_candidates(
        limit=limit, min_incoming=min_incoming, lang=lang,
    )
    return GraphCentersResponse(
        centers=centers,
        min_incoming=min_incoming,
        limit=limit,
    )


@router.get(
    "/director/{center_id}/radial",
    summary="Радиальная карточка: центр, учителя (кольцо 1) и их учителя (кольцо 2)",
)
async def director_radial(
    center_id: int,
    top_n: Annotated[int, Query(ge=1, le=8, description="Учителей вокруг центра")] = 4,
    ring2_n: Annotated[
        int, Query(ge=0, le=6, description="Учителей у каждого узла кольца 1"),
    ] = 4,
    lang: Annotated[Literal["ru", "en"], Query()] = "ru",
    db: AsyncSession = Depends(get_db),
):
    """
  Возвращает центр и два кольца «учителей» (source → target).

  Кольцо 1: кто повлиял на центр. Кольцо 2: кто повлиял на каждого из кольца 1.
    """
    service = RadialGraphService(db)
    result = await service.get_radial(
        center_id, top_n=top_n, ring2_n=ring2_n, lang=lang,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Режиссёр {center_id} не найден или не помечен как is_director",
        )
    return result


@router.get(
    "/director/{center_id}/semantic-radial",
    summary="Гибридный радиальный граф (explicit + semantic neighbors)",
)
async def director_semantic_radial(
    center_id: int,
    top_n: Annotated[int, Query(ge=1, le=8, description="Сколько узлов вокруг центра")] = 4,
    lang: Annotated[Literal["ru", "en"], Query()] = "ru",
    db: AsyncSession = Depends(get_db),
):
    service = SemanticRadialService(db)
    result = await service.get_radial(center_id, top_n=top_n, lang=lang)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Режиссёр {center_id} не найден или не помечен как is_director",
        )
    return result