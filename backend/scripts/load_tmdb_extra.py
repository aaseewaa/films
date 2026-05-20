"""
Загрузчик фильмов из TMDB-коллекций (саги, франшизы, тематические подборки)
и discover-запросов (по жанрам/ключевым словам/годам).

Запуск:
    cd backend
    source venv/bin/activate
    python -m scripts.load_tmdb_extra

Идемпотентно. Уже загруженные фильмы пропускаются.
После прогона запусти эмбеддинги:
    python -m scripts.generate_embeddings
"""
from __future__ import annotations

import argparse
import asyncio
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from scripts.tmdb_client import TmdbClient
from scripts.load_tmdb import get_languages, upsert_film

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
log = logging.getLogger("loader-extra")
logging.getLogger("httpx").setLevel(logging.WARNING)


# ═══════════════════════════════════════════════════════════════
#  TMDB COLLECTIONS — режиссёрские/тематические подборки
# ═══════════════════════════════════════════════════════════════
#
# TMDB Collection — это набор связанных фильмов (трилогия, сага).
# Просматривал TMDB вручную, выбрал самые важные для нашей темы:
TMDB_COLLECTIONS = [
    # ── Хичкок и классика саспенса ──────────────────
    (9485,   "Альфред Хичкок — основные фильмы"),       # Hitchcock Collection
    (645,    "James Bond Collection"),                  # все Бонды
    # ── Кубрик ──────────────────────────────────────
    (10,     "Star Wars Collection"),
    # ── Куросава, Японское кино ──────────────────────
    (86322,  "Куросава — самурайские"),
    # ── Тарантино ───────────────────────────────────
    (404609, "Kill Bill Collection"),
    # ── Скорсезе — мафиозные ─────────────────────────
    (87096,  "Avatar Collection"),
    # ── Спилберг ────────────────────────────────────
    (84,     "Indiana Jones Collection"),
    (295,    "Парк Юрского периода"),
    # ── Marvel ──────────────────────────────────────
    (86311,  "The Avengers"),
    (131295, "Captain America"),
    (86097,  "Thor"),
    (131292, "Iron Man"),
    (529892, "Black Panther"),
    (573436, "Spider-Man Home"),
    (131296, "Guardians of the Galaxy"),
    (468552, "Doctor Strange"),
    # ── DC и другие супергероические ────────────────
    (263,    "The Dark Knight"),
    (468031, "Joker"),
    # ── Французская новая волна и итальянские классики ──
    (87359,  "Mission Impossible"),
    (656,    "Pirates of the Caribbean"),
    (1241,   "Гарри Поттер"),
    (33514,  "Властелин Колец"),
    (121938, "Хоббит"),
    (1709,   "Хищник"),
    (8945,   "Безумный Макс"),
    (8650,   "Шрек"),
    # ── Анимация Pixar ─────────────────────────
    (10194,  "Toy Story"),
    (137697, "Cars"),
    # ── Романтика, классика ───────────────────────
    (2806,   "American Pie"),
    (87359,  "Mission Impossible"),
    # ── Хорроры и психо ──────────────────────────
    (3604,   "Halloween"),
    (1733,   "The Mummy"),
    (2602,   "Бэтмен Тима Бёртона"),
]


# ═══════════════════════════════════════════════════════════════
#  TMDB DISCOVER — фильтры по жанрам/ключевым словам/годам
# ═══════════════════════════════════════════════════════════════
#
# Это запросы к /discover/movie с разными комбинациями.
# Каждый загружает топ-N фильмов отвечающих критериям.
TMDB_DISCOVER = [
    # ── Классика чёрно-белого ──────────────────────────
    {
        "label": "Чёрно-белая классика до 1970",
        "params": {
            "primary_release_date.lte": "1970-12-31",
            "sort_by": "vote_average.desc",
            "vote_count.gte": 500,
        },
        "pages": 5,  # ~100 фильмов
    },
    # ── Французская новая волна (через keyword "french-new-wave") ──
    {
        "label": "Французское кино 1955-1975",
        "params": {
            "with_origin_country": "FR",
            "primary_release_date.gte": "1955-01-01",
            "primary_release_date.lte": "1975-12-31",
            "sort_by": "vote_average.desc",
            "vote_count.gte": 100,
        },
        "pages": 4,  # ~80 фильмов
    },
    # ── Итальянский неореализм и классика ──────────────────
    {
        "label": "Итальянское кино 1945-1985",
        "params": {
            "with_origin_country": "IT",
            "primary_release_date.gte": "1945-01-01",
            "primary_release_date.lte": "1985-12-31",
            "sort_by": "vote_average.desc",
            "vote_count.gte": 100,
        },
        "pages": 4,
    },
    # ── Японское кино ──────────────────────────────────
    {
        "label": "Японское кино все эпохи",
        "params": {
            "with_origin_country": "JP",
            "sort_by": "vote_average.desc",
            "vote_count.gte": 200,
        },
        "pages": 5,
    },
    # ── Скандинавское кино (Бергман, Триер, Винтерберг) ──
    {
        "label": "Скандинавское кино",
        "params": {
            "with_origin_country": "SE|DK|NO|FI",
            "sort_by": "vote_average.desc",
            "vote_count.gte": 200,
        },
        "pages": 4,
    },
    # ── Хорроры классика и современность ───────────────
    {
        "label": "Лучшие хорроры",
        "params": {
            "with_genres": 27,
            "sort_by": "vote_average.desc",
            "vote_count.gte": 1000,
        },
        "pages": 5,
    },
    # ── Романтические комедии (для Sex and the City коллекции) ─
    {
        "label": "Романтические комедии",
        "params": {
            "with_genres": "10749,35",
            "sort_by": "vote_average.desc",
            "vote_count.gte": 800,
        },
        "pages": 5,
    },
    # ── Драмы лауреаты Оскара (best of) ─────────────
    {
        "label": "Драмы топ-рейтинг",
        "params": {
            "with_genres": 18,
            "sort_by": "vote_average.desc",
            "vote_count.gte": 2000,
        },
        "pages": 5,
    },
    # ── Триллеры и нуар ────────────────────────────
    {
        "label": "Триллеры",
        "params": {
            "with_genres": 53,
            "sort_by": "vote_average.desc",
            "vote_count.gte": 1500,
        },
        "pages": 5,
    },
    # ── Анимация и мультфильмы (Pixar, Studio Ghibli, Disney) ─
    {
        "label": "Лучшая анимация",
        "params": {
            "with_genres": 16,
            "sort_by": "vote_average.desc",
            "vote_count.gte": 800,
        },
        "pages": 5,
    },
    # ── Военное кино ───────────────────────────────
    {
        "label": "Военное кино",
        "params": {
            "with_genres": 10752,
            "sort_by": "vote_average.desc",
            "vote_count.gte": 500,
        },
        "pages": 3,
    },
    # ── Документальное кино ────────────────────────
    {
        "label": "Документалки топ",
        "params": {
            "with_genres": 99,
            "sort_by": "vote_average.desc",
            "vote_count.gte": 200,
        },
        "pages": 3,
    },
    # ── Кино последних 5 лет (2021-2026) — для анализа новинок ──
    {
        "label": "Новинки 2021-2026",
        "params": {
            "primary_release_date.gte": "2021-01-01",
            "sort_by": "vote_average.desc",
            "vote_count.gte": 500,
        },
        "pages": 6,  # ~120 фильмов
    },
    # ── Российское кино (см. также scripts.load_tmdb_ru) ──
    {
        "label": "Россия — лучшие по рейтингу",
        "params": {
            "with_origin_country": "RU",
            "sort_by": "vote_average.desc",
            "vote_count.gte": 50,
        },
        "pages": 5,
    },
]


# ═══════════════════════════════════════════════════════════════
#  Логика
# ═══════════════════════════════════════════════════════════════

async def fetch_collection(tmdb: TmdbClient, collection_id: int) -> list[dict]:
    """Получает список фильмов в TMDB-коллекции."""
    try:
        return await tmdb.collection_parts(collection_id)
    except RuntimeError:
        return []


async def fetch_discover_page(
    tmdb: TmdbClient,
    params: dict,
    page: int,
) -> list[dict]:
    """Один запрос к discover (через TmdbClient: retry + кэш)."""
    return await tmdb.discover_movies_page(page=page, params=params)


async def load_tmdb_ids(
    tmdb_client: TmdbClient,
    db: AsyncSession,
    tmdb_ids: set[int],
    *,
    label: str,
    languages: dict[str, int],
    top_actors: int = 10,
) -> dict:
    """Загружает фильмы по списку TMDB ID. Возвращает статистику."""
    stats = {"requested": len(tmdb_ids), "new": 0, "skipped": 0, "errors": 0}

    # Узнаём какие уже есть в БД
    if not tmdb_ids:
        return stats

    existing_sql = text("""
        SELECT (external_ids->>'tmdb')::int AS tmdb_id
        FROM entity
        WHERE entity_type = 'film'
          AND external_ids ? 'tmdb'
          AND (external_ids->>'tmdb')::int = ANY(:ids)
    """)
    existing_rows = (await db.execute(existing_sql, {"ids": list(tmdb_ids)})).all()
    existing_set = {row[0] for row in existing_rows}

    new_ids = tmdb_ids - existing_set
    stats["skipped"] = len(existing_set)

    if not new_ids:
        log.info("  [%s] все %d фильмов уже в БД", label, len(tmdb_ids))
        return stats

    log.info("  [%s] нужно загрузить %d новых из %d", label, len(new_ids), len(tmdb_ids))

    for i, tmdb_id in enumerate(new_ids, start=1):
        if i % 20 == 0:
            log.info("    прогресс: %d/%d", i, len(new_ids))

        try:
            # Получаем полные данные фильма
            movie_en = await tmdb_client.movie_full(tmdb_id, language="en-US")
            if not movie_en:
                stats["errors"] += 1
                continue
            movie_ru = await tmdb_client.movie_full(tmdb_id, language="ru-RU")

            # Каждый фильм — своя транзакция
            async with AsyncSessionLocal() as fresh_db:
                try:
                    await upsert_film(
                        fresh_db,
                        movie_ru,
                        movie_en,
                        tmdb=tmdb_client,
                        languages=languages,
                        top_actors_count=top_actors,
                    )
                    await fresh_db.commit()
                    stats["new"] += 1
                except Exception as exc:
                    await fresh_db.rollback()
                    log.warning("    fail film %d: %s", tmdb_id, exc)
                    stats["errors"] += 1

            await asyncio.sleep(0.1)  # rate limit
        except Exception as exc:
            log.warning("    TMDB fail %d: %s", tmdb_id, exc)
            stats["errors"] += 1

    return stats


async def main() -> None:
    if not settings.tmdb_api_key:
        raise SystemExit("TMDB_API_KEY не задан в .env")

    log.info("═══════════════════════════════════════════════════")
    log.info(" Загрузка фильмов из TMDB Collections + Discover")
    log.info("═══════════════════════════════════════════════════")

    grand_total = {"new": 0, "skipped": 0, "errors": 0}

    async with TmdbClient(api_key=settings.tmdb_api_key) as tmdb:
        async with AsyncSessionLocal() as lang_db:
            languages = await get_languages(lang_db)

        # ─── COLLECTIONS ──────────────────────────────
        log.info("")
        log.info("─── COLLECTIONS ───")
        for col_id, col_name in TMDB_COLLECTIONS:
            try:
                parts = await fetch_collection(tmdb, col_id)
                tmdb_ids = {p["id"] for p in parts if p.get("id")}
                log.info("Collection #%d — %s (%d фильмов в коллекции)",
                         col_id, col_name, len(tmdb_ids))

                async with AsyncSessionLocal() as db:
                    stats = await load_tmdb_ids(
                        tmdb,
                        db,
                        tmdb_ids,
                        label=f"col-{col_id}",
                        languages=languages,
                    )
                grand_total["new"] += stats["new"]
                grand_total["skipped"] += stats["skipped"]
                grand_total["errors"] += stats["errors"]
                await asyncio.sleep(0.3)
            except Exception as exc:
                log.warning("Collection %d failed: %s", col_id, exc)

        # ─── DISCOVER ────────────────────────────────
        log.info("")
        log.info("─── DISCOVER ───")
        for q in TMDB_DISCOVER:
            log.info("Discover: %s (pages 1..%d)", q["label"], q["pages"])
            all_ids: set[int] = set()
            for page in range(1, q["pages"] + 1):
                try:
                    results = await fetch_discover_page(tmdb, q["params"], page)
                    all_ids.update(m["id"] for m in results if m.get("id"))
                    await asyncio.sleep(0.15)
                except Exception as exc:
                    log.warning("  page %d failed: %s", page, exc)

            log.info("  собрано %d уникальных TMDB id", len(all_ids))

            async with AsyncSessionLocal() as db:
                stats = await load_tmdb_ids(
                    tmdb,
                    db,
                    all_ids,
                    label=q["label"],
                    languages=languages,
                )
            grand_total["new"] += stats["new"]
            grand_total["skipped"] += stats["skipped"]
            grand_total["errors"] += stats["errors"]

    log.info("")
    log.info("═══════════════════════════════════════════════════")
    log.info(" DONE")
    log.info("   новых фильмов:   %d", grand_total["new"])
    log.info("   уже было:        %d", grand_total["skipped"])
    log.info("   ошибок:          %d", grand_total["errors"])
    log.info("═══════════════════════════════════════════════════")
    log.info("")
    log.info("Следующие шаги:")
    log.info("  1) python -m scripts.generate_embeddings  # эмбеддинги на новые переводы")
    log.info("  2) python -m scripts.load_tmdb_images     # backdrop+stills для новых")
    log.info("  3) python -m scripts.load_wikidata_influences_v2  # новые связи в графе")
    log.info("  4) python -m scripts.load_tmdb_ru              # только российское кино")


if __name__ == "__main__":
    asyncio.run(main())
