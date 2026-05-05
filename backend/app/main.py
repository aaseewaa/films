"""
Точка входа FastAPI-приложения.

Запуск в режиме разработки:
    uvicorn app.main:app --reload

Документация API после запуска:
    http://localhost:8000/docs        — Swagger UI
    http://localhost:8000/redoc       — ReDoc
"""
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.config import settings
from app.database import engine

# ─── Логирование ─────────────────────────────────────────────────
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ],
)
log = structlog.get_logger()


# ─── Жизненный цикл приложения ───────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Что делать при старте и остановке приложения."""
    log.info("startup", app=settings.app_name, version=settings.app_version)
    yield
    log.info("shutdown")
    await engine.dispose()


# ─── Создание приложения ─────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "REST API для информационной системы интеллектуального поиска и "
        "навигации по знаниям в области киноискусства. Дипломный проект."
    ),
    debug=settings.app_debug,
    lifespan=lifespan,
)


# ─── CORS (чтобы фронт мог обращаться к API) ─────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Подключение роутеров ────────────────────────────────────────
app.include_router(health.router)
# Дальше будут: search, entities, graph, recommendations, favorites, history


@app.get("/", tags=["root"])
async def root() -> dict:
    """Корневой эндпоинт — пинг и ссылки на документацию."""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health/db",
    }
