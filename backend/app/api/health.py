"""
Health-check эндпоинты.

GET /health         — приложение живо
GET /health/db      — приложение видит БД и расширения работают
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", summary="Базовая проверка")
async def health() -> dict:
    """Просто возвращает что приложение живо."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
    }


@router.get("/db", summary="Проверка соединения с БД")
async def health_db(db: AsyncSession = Depends(get_db)) -> dict:
    """
    Проверяет:
      1. соединение с PostgreSQL
      2. что расширения citext и pg_trgm установлены
      3. что в БД есть ключевые таблицы
    """
    # 1. Простой SELECT
    result = await db.execute(text("SELECT 1"))
    if result.scalar() != 1:
        return {"status": "error", "detail": "SELECT 1 failed"}

    # 2. Расширения
    ext_query = text(
        "SELECT extname FROM pg_extension "
        "WHERE extname IN ('citext', 'pg_trgm', 'vector') "
        "ORDER BY extname"
    )
    extensions = [row[0] for row in (await db.execute(ext_query)).all()]

    # 3. Ключевые таблицы
    tables_query = text(
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema='public' AND table_name IN "
        "('entity', 'film', 'person', 'entity_translation', 'language')"
    )
    expected_tables_present = (await db.execute(tables_query)).scalar()

    # 4. Сколько фильмов в БД
    films_count = (await db.execute(text("SELECT count(*) FROM film"))).scalar()
    persons_count = (await db.execute(text("SELECT count(*) FROM person"))).scalar()

    return {
        "status": "ok",
        "db": "connected",
        "extensions": extensions,
        "core_tables_present": f"{expected_tables_present}/5",
        "data": {
            "films": films_count,
            "persons": persons_count,
        },
    }
