"""
GET /api/search — гибридный поиск по сущностям.
"""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_current_user
from app.database import get_db
from app.schemas.search import SearchResponse
from app.services.search_service import SearchService

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("", response_model=SearchResponse, summary="Гибридный поиск")
async def search(
    request: Request,
    q: Annotated[str, Query(min_length=1, max_length=200, description="Поисковый запрос")],
    lang: Annotated[Literal["ru", "en"] | None, Query(description="Язык запроса (если не задан — детектится)")] = None,
    type: Annotated[Literal["film", "person"] | None, Query(description="Тип сущности")] = None,
    genre: Annotated[str | None, Query(description="Код жанра (например, sci-fi)")] = None,
    year_from: Annotated[int | None, Query(ge=1880, le=2100)] = None,
    year_to: Annotated[int | None, Query(ge=1880, le=2100)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> SearchResponse:
    """
    Гибридный поиск: полнотекстовый (с морфологией) + нечёткий (опечатки).

    Стратегия:
    - Сначала полнотекстовый поиск через tsvector
    - Если результатов мало — добавляется нечёткий через pg_trgm
    - Возвращается ranked-список с meta-полем `match_type`

    Если пользователь авторизован — поисковый запрос пишется в его историю.
    Иначе — пишется анонимно с session_id (IP-адрес).
    """
    service = SearchService(db)
    result = await service.hybrid_search(
        query=q,
        lang=lang,
        entity_type=type,
        genre_code=genre,
        year_from=year_from,
        year_to=year_to,
        limit=limit,
        offset=offset,
    )

    # Запись в search_history (best-effort, не критично если упадёт)
    try:
        await _log_search(
            db,
            user_id=current_user.id if current_user else None,
            query_text=q,
            normalized=q.lower().strip(),
            language_code=result["detected_language"],
            results_count=result["total"],
            ip=str(request.client.host) if request.client else None,
            session_id=request.client.host if request.client else "anon",
        )
    except Exception:
        pass

    return SearchResponse(**result)


async def _log_search(
    db: AsyncSession,
    *,
    user_id: int | None,
    query_text: str,
    normalized: str,
    language_code: str,
    results_count: int,
    ip: str | None,
    session_id: str,
) -> None:
    """
    Пишет запись в search_history.
    Если есть user_id — привязывает к пользователю, иначе использует session_id.
    """
    sql = text("""
        INSERT INTO search_history
            (user_id, session_id, search_type, query_text, normalized_query,
             language_id, results_count, ip_address, searched_at)
        VALUES (:uid, :sid, 'fulltext', :q, :nq,
                (SELECT id FROM language WHERE code = :lc),
                :rc, CAST(:ip AS inet), now())
    """)
    await db.execute(sql, {
        "uid": user_id,
        "q": query_text,
        "nq": normalized,
        "lc": language_code,
        "rc": results_count,
        "ip": ip,
        "sid": session_id[:64] if user_id is None else None,
    })
    await db.commit()
