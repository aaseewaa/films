"""
Эндпоинты рекомендаций.

GET /api/recommendations?for_film_id=N&mode=content   — content-based
GET /api/recommendations?for_film_id=N&mode=semantic  — через эмбеддинги
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
    summary="Рекомендации (content-based или semantic)",
)
async def recommendations(
    for_film_id: Annotated[int | None, Query(description="ID фильма")] = None,
    for_person_id: Annotated[int | None, Query(description="ID персоны")] = None,
    mode: Annotated[
        Literal["content", "semantic"],
        Query(description=(
            "Режим: 'content' — взвешенный score по атрибутам "
            "(жанр, режиссёр, актёр, keyword, год); "
            "'semantic' — близость векторов описаний через pgvector"
        )),
    ] = "content",
    lang: Annotated[Literal["ru", "en"], Query()] = "ru",
    limit: Annotated[int, Query(ge=1, le=30)] = 10,
    db: AsyncSession = Depends(get_db),
) -> RecommendationsResponse:
    """
    Рекомендации в двух режимах.

    ## Content-based (mode=content, по умолчанию)

    Взвешенный score по совпадениям атрибутов:
    - **общий режиссёр**: +3
    - **общий актёр** (топ-5): +2 (кап 6)
    - **общий жанр**: +1 (кап 3)
    - **общий keyword** (атмосферный тег TMDB): +1.5 (кап 6) — НОВОЕ
    - **близкий год** (±5): +0.5

    ## Semantic (mode=semantic)

    Близость векторов описаний через pgvector. Использует многоязычную модель
    `paraphrase-multilingual-MiniLM-L12-v2` и косинусное расстояние.

    Находит фильмы где **смысл описания близок**, даже если у них разные
    жанры, актёры и режиссёры. Аналог подхода Letterboxd/Spotify.

    ## Сравнение

    На карточке фильма можно показать рекомендации в обоих режимах и
    сравнить выдачу — это демонстрирует разницу подходов.
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
        try:
            result = await service.for_film(
                for_film_id, lang=lang, limit=limit, mode=mode,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Ошибка рекомендаций: {exc}")
        if result is None:
            raise HTTPException(status_code=404, detail=f"Фильм {for_film_id} не найден")
    else:
        try:
            result = await service.for_person(
                for_person_id, lang=lang, limit=limit, mode=mode,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Ошибка рекомендаций: {exc}")
        if result is None:
            raise HTTPException(status_code=404, detail=f"Режиссёр {for_person_id} не найден")

    return RecommendationsResponse(**result)
