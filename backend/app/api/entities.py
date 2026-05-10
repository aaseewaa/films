"""
GET /api/entity/{id} — карточка сущности (фильм или персона).
"""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.entity import FilmRead, PersonRead
from app.services.entity_service import EntityService

router = APIRouter(prefix="/api/entity", tags=["entity"])


@router.get(
    "/{entity_id}",
    summary="Карточка сущности (фильм или персона)",
    responses={
        404: {"description": "Сущность не найдена или не опубликована"},
    },
)
async def get_entity(
    request: Request,
    entity_id: int,
    lang: Annotated[Literal["ru", "en"], Query(description="Язык переводов")] = "ru",
    db: AsyncSession = Depends(get_db),
) -> FilmRead | PersonRead:
    """
    Универсальная карточка сущности.

    Автоматически определяет тип (film / person) и возвращает соответствующую
    структуру со всеми связями: жанры, режиссёры, актёры, фильмография,
    граф влияний (для режиссёров).
    """
    service = EntityService(db)
    data = await service.get_entity(entity_id, lang=lang)

    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity {entity_id} not found or not published",
        )

    # Запись в view_history (best-effort)
    try:
        await _log_view(
            db,
            entity_id=entity_id,
            ip=str(request.client.host) if request.client else None,
            session_id=request.client.host if request.client else "anon",
        )
    except Exception:
        pass

    if data["entity_type"] == "film":
        return FilmRead(**data)
    elif data["entity_type"] == "person":
        return PersonRead(**data)
    else:
        # Защита на будущее, пока не должно срабатывать
        raise HTTPException(
            status_code=501,
            detail=f"Entity type '{data['entity_type']}' not supported yet",
        )


async def _log_view(
    db: AsyncSession, *, entity_id: int, ip: str | None, session_id: str
) -> None:
    """Пишет в view_history. Использует session_id (CHECK требует user_id или session_id)."""
    sql = text("""
        INSERT INTO view_history
            (user_id, session_id, entity_id, viewed_at, ip_address)
        VALUES (NULL, :sid, :eid, now(), CAST(:ip AS inet))
    """)
    await db.execute(sql, {"eid": entity_id, "ip": ip, "sid": session_id[:64]})
    await db.commit()
