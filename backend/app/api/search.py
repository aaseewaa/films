"""
GET /api/search — гибридный поиск + семантический режим.

Режимы:
  - hybrid (default): полнотекстовый + fuzzy (как было)
  - semantic: через эмбеддинги pgvector — поиск по смыслу
"""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_current_user
from app.database import get_db
from app.schemas.search import SearchResponse
from app.services.search_service import SearchService
from app.services.semantic_service import SemanticService

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("", response_model=SearchResponse, summary="Гибридный или семантический поиск")
async def search(
    request: Request,
    q: Annotated[str, Query(min_length=1, max_length=200, description="Поисковый запрос")],
    mode: Annotated[
        Literal["hybrid", "semantic"],
        Query(description=(
            "Режим: 'hybrid' — полнотекстовый+fuzzy (по умолчанию); "
            "'semantic' — поиск по смыслу через эмбеддинги pgvector"
        )),
    ] = "hybrid",
    lang: Annotated[Literal["ru", "en"] | None, Query()] = None,
    type: Annotated[Literal["film", "person"] | None, Query()] = None,
    genre: Annotated[str | None, Query()] = None,
    year_from: Annotated[int | None, Query(ge=1880, le=2100)] = None,
    year_to: Annotated[int | None, Query(ge=1880, le=2100)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> SearchResponse:
    """
    Поиск в двух режимах.

    ## Hybrid (mode=hybrid, по умолчанию)
    - **Полнотекстовый** через PostgreSQL tsvector с морфологическим стеммингом
    - **Нечёткий** через pg_trgm (опечатки, частичные совпадения)
    - Автодетекция языка по наличию кириллицы
    - Адаптивный порог триграммного сходства

    ## Semantic (mode=semantic)
    - Запрос превращается в вектор через multilingual-e5-small (порог similarity 38%)
    - PostgreSQL находит сущности с близкими векторами описаний через HNSW-индекс
    - Многоязычность: русский запрос находит английское описание и наоборот
    - Решает запросы типа «фильм где герой не помнит кто он» → Memento, Bourne Identity
    """
    if mode == "semantic":
        semantic = SemanticService(db)
        hits_raw = await semantic.semantic_search(
            query=q,
            lang=lang,
            entity_type=type,
            limit=limit,
            offset=offset,
        )

        # Приводим к формату SearchResponse
        items = []
        for h in hits_raw:
            items.append({
                "entity_id": h["entity_id"],
                "entity_type": h["entity_type"],
                "title": h["title"],
                "summary": h["summary"],
                "language_code": h["language_code"],
                "match_type": "semantic",
                "score": h["similarity"],
                "images": h["images"],
            })

        result = {
            "items": items,
            "total": len(items),
            "limit": limit,
            "offset": offset,
            "query": q,
            "detected_language": lang or "auto",
            "mode": "semantic",
        }
    else:
        # Старый режим - hybrid
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
        result["mode"] = "hybrid"

    # Запись в search_history (best-effort)
    try:
        await _log_search(
            db,
            user_id=current_user.id if current_user else None,
            query_text=q,
            normalized=q.lower().strip(),
            language_code=result.get("detected_language", lang or "auto"),
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
        "lc": language_code if language_code != "auto" else "ru",
        "rc": results_count,
        "ip": ip,
        "sid": session_id[:64] if user_id is None else None,
    })
    await db.commit()
