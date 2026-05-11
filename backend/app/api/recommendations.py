"""
Эндпоинты рекомендаций.

GET /api/recommendations?for_film_id=N  — похожие фильмы
GET /api/recommendations?for_person_id=N — похожие режиссёры
"""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.recommendations import RecommendationsResponse
from app.services.recommendations_service import RecommendationsService

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get(
    "",
    response_model=RecommendationsResponse,
    summary="Content-based рекомендации",
)
async def recommendations(
    for_film_id: Annotated[int | None, Query(description="ID фильма для 'похожее'")] = None,
    for_person_id: Annotated[int | None, Query(description="ID персоны для 'похожие режиссёры'")] = None,
    lang: Annotated[Literal["ru", "en"], Query()] = "ru",
    limit: Annotated[int, Query(ge=1, le=30)] = 10,
    db: AsyncSession = Depends(get_db),
) -> RecommendationsResponse:
    """
    Content-based рекомендации.

    Для **фильма** (`for_film_id`): похожие фильмы по общим режиссёрам,
    актёрам, жанрам, году. Алгоритм взвешенного score:
    - общий режиссёр: +3
    - общий актёр: +2
    - общий жанр: +1
    - близкий год (±5): +0.5

    Для **персоны** (`for_person_id`): похожие режиссёры. Учитывает прямые
    связи в графе влияний (+5) и общие жанры режиссуры (+1).

    Каждая рекомендация имеет поле `reasons` — список причин почему
    рекомендуется (для UI: 'Потому что общий режиссёр').
    """
    if not for_film_id and not for_person_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Укажи for_film_id ИЛИ for_person_id",
        )
    if for_film_id and for_person_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Укажи только одно: for_film_id ИЛИ for_person_id",
        )

    service = RecommendationsService(db)

    if for_film_id:
        result = await service.for_film(for_film_id, lang=lang, limit=limit)
        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"Фильм {for_film_id} не найден",
            )
    else:
        result = await service.for_person(for_person_id, lang=lang, limit=limit)
        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"Режиссёр {for_person_id} не найден",
            )

    return RecommendationsResponse(**result)
