"""
GET /api/entity/{id} — карточка сущности (фильм или персона).
"""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_current_user
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
    current_user: CurrentUser | None = Depends(get_current_user),
) -> FilmRead | PersonRead:
    """
    Универсальная карточка сущности.

    Если пользователь авторизован — просмотр привязывается к его истории.
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
            user_id=current_user.id if current_user else None,
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
        raise HTTPException(
            status_code=501,
            detail=f"Entity type '{data['entity_type']}' not supported yet",
        )


async def _log_view(
    db: AsyncSession,
    *,
    user_id: int | None,
    entity_id: int,
    ip: str | None,
    session_id: str,
) -> None:
    """
    Пишет в view_history.
    CHECK-constraint требует user_id или session_id — поэтому если юзера
    нет, передаём session_id (IP-адрес).
    """
    sql = text("""
        INSERT INTO view_history
            (user_id, session_id, entity_id, viewed_at, ip_address)
        VALUES (:uid, :sid, :eid, now(), CAST(:ip AS inet))
    """)
    await db.execute(sql, {
        "uid": user_id,
        "eid": entity_id,
        "ip": ip,
        "sid": session_id[:64] if user_id is None else None,
    })
    await db.commit()
