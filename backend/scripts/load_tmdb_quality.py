"""
Догрузка «взрослого» мирового кино — без анимации и без Marvel/Pixar-коллекций.

Используй, когда load_tmdb --source top_rated дал 0 новых (всё уже есть),
а на сайте много мультиков из load_tmdb_extra.

Запуск:
    cd backend && source venv/bin/activate
    python -m scripts.load_tmdb_quality
    python -m scripts.load_tmdb_quality --pages-scale 1.5   # больше страниц

После:
    python -m scripts.generate_embeddings
"""
from __future__ import annotations

import argparse
import asyncio
import logging

from app.config import settings
from app.database import AsyncSessionLocal
from scripts.load_tmdb import get_languages
from scripts.load_tmdb_extra import fetch_discover_page, load_tmdb_ids
from scripts.tmdb_client import TmdbClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
log = logging.getLogger("loader-quality")

# TMDB genre 16 = Animation — исключаем везде
WITHOUT_ANIMATION = "16"

# Discover: высокий vote_count + без мультиков
QUALITY_DISCOVER: list[dict] = [
    {
        "label": "Драма — мировой канон",
        "params": {
            "with_genres": "18",
            "without_genres": WITHOUT_ANIMATION,
            "sort_by": "vote_average.desc",
            "vote_count.gte": 2500,
        },
        "pages": 12,
    },
    {
        "label": "Триллер / криминал",
        "params": {
            "with_genres": "53,80",
            "without_genres": WITHOUT_ANIMATION,
            "sort_by": "vote_average.desc",
            "vote_count.gte": 2000,
        },
        "pages": 10,
    },
    {
        "label": "Военное и историческое",
        "params": {
            "with_genres": "10752,36",
            "without_genres": WITHOUT_ANIMATION,
            "sort_by": "vote_average.desc",
            "vote_count.gte": 800,
        },
        "pages": 6,
    },
    {
        "label": "США — золотая эра 1970–1999",
        "params": {
            "with_origin_country": "US",
            "primary_release_date.gte": "1970-01-01",
            "primary_release_date.lte": "1999-12-31",
            "without_genres": WITHOUT_ANIMATION,
            "sort_by": "vote_average.desc",
            "vote_count.gte": 1200,
        },
        "pages": 10,
    },
    {
        "label": "Великобритания — артхаус и классика",
        "params": {
            "with_origin_country": "GB",
            "without_genres": WITHOUT_ANIMATION,
            "sort_by": "vote_average.desc",
            "vote_count.gte": 600,
        },
        "pages": 8,
    },
    {
        "label": "Франция",
        "params": {
            "with_origin_country": "FR",
            "without_genres": WITHOUT_ANIMATION,
            "sort_by": "vote_average.desc",
            "vote_count.gte": 400,
        },
        "pages": 8,
    },
    {
        "label": "Италия",
        "params": {
            "with_origin_country": "IT",
            "without_genres": WITHOUT_ANIMATION,
            "sort_by": "vote_average.desc",
            "vote_count.gte": 350,
        },
        "pages": 8,
    },
    {
        "label": "Япония (живое кино)",
        "params": {
            "with_origin_country": "JP",
            "without_genres": WITHOUT_ANIMATION,
            "sort_by": "vote_average.desc",
            "vote_count.gte": 500,
        },
        "pages": 8,
    },
    {
        "label": "Германия",
        "params": {
            "with_origin_country": "DE",
            "without_genres": WITHOUT_ANIMATION,
            "sort_by": "vote_average.desc",
            "vote_count.gte": 400,
        },
        "pages": 6,
    },
    {
        "label": "Корея — новая волна",
        "params": {
            "with_origin_country": "KR",
            "without_genres": WITHOUT_ANIMATION,
            "sort_by": "vote_average.desc",
            "vote_count.gte": 300,
        },
        "pages": 6,
    },
    {
        "label": "Чёрно-белая классика",
        "params": {
            "primary_release_date.lte": "1975-12-31",
            "without_genres": WITHOUT_ANIMATION,
            "sort_by": "vote_average.desc",
            "vote_count.gte": 800,
        },
        "pages": 8,
    },
]


async def main(*, pages_scale: float, top_actors: int) -> None:
    if not settings.tmdb_api_key:
        raise SystemExit("TMDB_API_KEY не задан в .env")

    log.info("═══ Quality loader (без анимации) ═══")

    grand = {"new": 0, "skipped": 0, "errors": 0}

    async with TmdbClient(api_key=settings.tmdb_api_key) as tmdb:
        async with AsyncSessionLocal() as lang_db:
            languages = await get_languages(lang_db)

        for q in QUALITY_DISCOVER:
            pages = max(1, int(q["pages"] * pages_scale))
            log.info("Discover: %s (pages=%d)", q["label"], pages)
            all_ids: set[int] = set()
            for page in range(1, pages + 1):
                try:
                    rows = await fetch_discover_page(tmdb, q["params"], page)
                    all_ids.update(m["id"] for m in rows if m.get("id"))
                    await asyncio.sleep(0.15)
                except Exception as exc:
                    log.warning("  page %d: %s", page, exc)

            log.info("  TMDB id: %d", len(all_ids))
            async with AsyncSessionLocal() as db:
                stats = await load_tmdb_ids(
                    tmdb, db, all_ids,
                    label=q["label"],
                    languages=languages,
                    top_actors=top_actors,
                )
            grand["new"] += stats["new"]
            grand["skipped"] += stats["skipped"]
            grand["errors"] += stats["errors"]
            log.info("  → new=%d skipped=%d", stats["new"], stats["skipped"])

    log.info("═══ DONE: new=%d skipped=%d errors=%d ═══",
             grand["new"], grand["skipped"], grand["errors"])
    if grand["new"]:
        log.info("Дальше: python -m scripts.generate_embeddings")


def cli() -> None:
    p = argparse.ArgumentParser(description="Догрузка качественного кино без анимации")
    p.add_argument(
        "--pages-scale", type=float, default=1.0,
        help="Множитель числа страниц discover (1.5 = на 50%% больше фильмов)",
    )
    p.add_argument("--top-actors", type=int, default=8)
    args = p.parse_args()
    asyncio.run(main(pages_scale=args.pages_scale, top_actors=args.top_actors))


if __name__ == "__main__":
    cli()
