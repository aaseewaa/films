"""
Async-подключение к PostgreSQL через SQLAlchemy 2.

Тут только инфраструктура — ORM-модели в app/models/.
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


# ─── Engine ──────────────────────────────────────────────────────
# Один engine на всё приложение, держит пул соединений.
engine = create_async_engine(
    settings.async_database_url,
    echo=settings.db_echo,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True,  # проверка живости соединения перед использованием
    pool_recycle=1800,   # переоткрывать соединения раз в 30 мин
)


# ─── Session factory ─────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # важно для FastAPI: после commit объекты остаются доступны
    autoflush=False,
)


# ─── Базовый класс моделей ───────────────────────────────────────
class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей. От него наследуются все таблицы."""
    pass


# ─── Зависимость FastAPI для получения сессии ────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Используется как Depends(get_db) в роутах.

    Пример:
        @router.get("/films")
        async def list_films(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
