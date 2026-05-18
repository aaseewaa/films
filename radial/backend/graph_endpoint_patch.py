"""
Добавь этот эндпоинт в backend/app/api/graph.py.
Внутри существующего файла, после уже имеющихся эндпоинтов /director/{id} и /full.
"""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.radial_graph_service import RadialGraphService

# Найди в graph.py этот router и просто добавь декоратор @router.get(...) ниже
# router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get(
    "/director/{center_id}/radial",
    summary="Радиальная карточка: центр + топ-N значимых связей (глубина 1)",
)
async def director_radial(
    center_id: int,
    top_n: Annotated[int, Query(ge=1, le=8, description="Сколько соседей вернуть")] = 4,
    lang: Annotated[Literal["ru", "en"], Query()] = "ru",
    db: AsyncSession = Depends(get_db),
):
    """
    Возвращает центрального режиссёра и его топ-N соседей по силе связи.

    Используется для радиального layout на главной странице фронта.
    В отличие от /director/{id} возвращает строго ограниченное число
    соседей по убыванию веса связи (director_influence.weight),
    без рекурсии в глубину.

    Структура ответа:
        {
            "center": { "id", "name", "image" },
            "neighbors": [{ "id", "name", "image", "weight", "films_count" }, ...],
            "total_neighbors_in_db": int,
            "top_n_requested": int,
        }
    """
    service = RadialGraphService(db)
    result = await service.get_radial(center_id, top_n=top_n, lang=lang)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Режиссёр {center_id} не найден или не помечен как is_director",
        )
    return result
