"""
Точка входа FastAPI-приложения.
"""
from contextlib import asynccontextmanager

import structlog
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import (
    auth, catalog, entities, graph, health, news, recommendations, search, user_data,
)

from app.api.collections import router as collections_router
from app.api.articles import router as articles_router

from app.config import settings
from app.database import engine

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ],
)
log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("startup", app=settings.app_name, version=settings.app_version)
    yield
    log.info("shutdown")
    await engine.dispose()


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Роутеры ─────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(search.router)
app.include_router(entities.router)
app.include_router(catalog.router)
app.include_router(auth.router)
app.include_router(user_data.router)
app.include_router(graph.router)              # день 7: граф для визуализации
app.include_router(recommendations.router)    # день 7: рекомендации
app.include_router(collections_router)
app.include_router(articles_router)
app.include_router(news.router)

_uploads = Path(settings.uploads_dir)
_uploads.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_uploads)), name="uploads")


@app.get("/", tags=["root"])
async def root() -> dict:
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "endpoints": {
            "search": "/api/search?q=...",
            "entity": "/api/entity/{id}",
            "films": "/api/films",
            "persons": "/api/persons",
            "genres": "/api/genres",
            "popular": "/api/popular",
            "auth": "/api/auth/(register|login|me)",
            "favorites": "/api/favorites",
            "ratings": "/api/ratings/{id}",
            "history": "/api/history",
            "graph_director": "/api/graph/director/{id}?depth=2",
            "graph_full": "/api/graph/full?limit=50",
            "recommendations": "/api/recommendations?for_film_id=...",
            "news": "/api/news?city=...",
        },
    }
