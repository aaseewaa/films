"""
FastAPI-зависимости (Depends) для авторизации.

Использование в эндпоинтах:
    @router.get("/profile")
    async def profile(user: CurrentUser = Depends(require_user)):
        return user

    @router.get("/something-optional")
    async def somefunc(user: CurrentUser | None = Depends(get_current_user)):
        if user:
            ... # авторизован
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.database import get_db
from app.services.auth_service import AuthService
from app.services.catalog_service import CatalogService
from app.services.entity_service import EntityService


@dataclass
class CurrentUser:
    """Минимальный набор полей текущего пользователя из токена + БД."""
    id: int
    email: str
    display_name: str
    role: str
    city: str | None
    preferred_language_id: int | None


# HTTPBearer берёт токен из заголовка Authorization: Bearer <token>
# auto_error=False позволяет токену быть необязательным
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser | None:
    """Возвращает текущего юзера или None если токена нет/невалиден."""
    if creds is None:
        return None

    user_id = decode_access_token(creds.credentials)
    if user_id is None:
        return None

    sql = text("""
        SELECT u.id, u.email::text AS email, u.display_name, u.preferred_language_id,
               u.is_active, u.extra_metadata,
               r.code::text AS role
        FROM app_user u
        JOIN app_role r ON r.id = u.role_id
        WHERE u.id = :uid
    """)
    row = (await db.execute(sql, {"uid": user_id})).mappings().first()
    if not row or not row["is_active"]:
        return None

    extra = row["extra_metadata"] or {}
    return CurrentUser(
        id=row["id"],
        email=row["email"],
        display_name=row["display_name"],
        role=row["role"],
        city=extra.get("city"),
        preferred_language_id=row["preferred_language_id"],
    )


async def require_user(
    user: CurrentUser | None = Depends(get_current_user),
) -> CurrentUser:
    """Требует авторизации. Если её нет — 401."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(db)


def get_catalog_service(db: AsyncSession = Depends(get_db)) -> CatalogService:
    return CatalogService(db)


def get_entity_service(db: AsyncSession = Depends(get_db)) -> EntityService:
    return EntityService(db)


# Type aliases for annotations in tests and type checkers.
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
CatalogServiceDep = Annotated[CatalogService, Depends(get_catalog_service)]
EntityServiceDep = Annotated[EntityService, Depends(get_entity_service)]
