"""
Загрузка российского кино из TMDB (discover).

Не тянет Marvel/коллекции из load_tmdb_extra — только подборки по стране RU
и русскому языку оригинала.

Запуск:
    cd backend
    source venv/bin/activate
    python -m scripts.load_tmdb_ru

    python -m scripts.load_tmdb_ru --top-actors 8
    python -m scripts.load_tmdb_ru --only modern   # только 1992+
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
log = logging.getLogger("loader-ru")
logging.getLogger("httpx").setLevel(logging.WARNING)

RU_DISCOVER: list[dict] = [
    {
        "id": "all",
        "label": "Россия — лучшие по рейтингу",
        "params": {
            "with_origin_country": "RU",
            "sort_by": "vote_average.desc",
            "vote_count.gte": 50,
        },
        "pages": 6,
    },
    {
        "id": "soviet",
        "label": "Россия / СССР — до 1991",
        "params": {
            "with_origin_country": "RU",
            "primary_release_date.lte": "1991-12-31",
            "sort_by": "vote_average.desc",
            "vote_count.gte": 25,
        },
        "pages": 5,
    },
    {
        "id": "modern",
        "label": "Россия — с 1992 года",
        "params": {
            "with_origin_country": "RU",
            "primary_release_date.gte": "1992-01-01",
            "sort_by": "vote_average.desc",
            "vote_count.gte": 40,
        },
        "pages": 6,
    },
    {
        "id": "lang",
        "label": "Оригинальный язык — русский",
        "params": {
            "with_original_language": "ru",
            "sort_by": "vote_average.desc",
            "vote_count.gte": 80,
        },
        "pages": 4,
    },
]


async def check_tmdb_connection(tmdb: TmdbClient) -> None:
    """Проверка сети до долгого прогона."""
    try:
        genres = await tmdb.genres()
        if not genres:
            raise RuntimeError("пустой ответ")
        log.info("TMDB API доступен (%d жанров в справочнике)", len(genres))
    except Exception as exc:
        raise SystemExit(
            "Нет связи с api.themoviedb.org. Проверь интернет, VPN и TMDB_API_KEY в .env.\n"
            f"Ошибка: {exc}"
        ) from exc


async def collect_discover_ids(
    tmdb: TmdbClient,
    queries: list[dict],
) -> dict[str, set[int]]:
    """Собирает TMDB id по списку discover-запросов."""
    result: dict[str, set[int]] = {}
    for q in queries:
        label = q["label"]
        all_ids: set[int] = set()
        failed_pages = 0
        log.info("Discover: %s (страниц %d)", label, q["pages"])
        for page in range(1, q["pages"] + 1):
            try:
                rows = await fetch_discover_page(tmdb, q["params"], page)
                if not rows and page == 1:
                    log.warning("  %s — страница %d: пустой ответ", label, page)
                all_ids.update(m["id"] for m in rows if m.get("id"))
                await asyncio.sleep(0.15)
            except Exception as exc:
                failed_pages += 1
                log.warning("  %s — страница %d: %s", label, page, exc)
        if failed_pages == q["pages"]:
            log.error("  %s — все страницы недоступны, блок пропущен", label)
        log.info("  → %d уникальных id", len(all_ids))
        result[label] = all_ids
    return result


async def main(*, top_actors: int, only: str | None) -> None:
    if not settings.tmdb_api_key:
        raise SystemExit("TMDB_API_KEY не задан в .env")

    queries = RU_DISCOVER
    if only:
        queries = [q for q in RU_DISCOVER if q["id"] == only]
        if not queries:
            raise SystemExit(
                f"Неизвестный --only={only!r}. Варианты: "
                + ", ".join(q["id"] for q in RU_DISCOVER)
            )

    log.info("═══════════════════════════════════════════════════")
    log.info(" Загрузка российского кино (TMDB discover)")
    log.info("═══════════════════════════════════════════════════")

    grand = {"new": 0, "skipped": 0, "errors": 0}
    seen: set[int] = set()

    async with TmdbClient(api_key=settings.tmdb_api_key) as tmdb:
        await check_tmdb_connection(tmdb)

        async with AsyncSessionLocal() as lang_db:
            languages = await get_languages(lang_db)

        batches = await collect_discover_ids(tmdb, queries)

        if not any(batches.values()):
            raise SystemExit(
                "Не получено ни одного TMDB id. Сеть или API недоступны — "
                "проверь интернет и повтори позже."
            )

        for label, tmdb_ids in batches.items():
            new_batch = tmdb_ids - seen
            seen |= tmdb_ids
            if not new_batch:
                continue
            log.info("")
            log.info("Загрузка: %s (%d новых id после дедупа)", label, len(new_batch))

            async with AsyncSessionLocal() as db:
                stats = await load_tmdb_ids(
                    tmdb,
                    db,
                    new_batch,
                    label=label,
                    languages=languages,
                    top_actors=top_actors,
                )
            grand["new"] += stats["new"]
            grand["skipped"] += stats["skipped"]
            grand["errors"] += stats["errors"]

    log.info("")
    log.info("═══════════════════════════════════════════════════")
    log.info(" DONE (всего уникальных id в выдаче: %d)", len(seen))
    log.info("   новых фильмов:   %d", grand["new"])
    log.info("   уже было в БД:   %d", grand["skipped"])
    log.info("   ошибок:          %d", grand["errors"])
    log.info("═══════════════════════════════════════════════════")
    log.info("Дальше: generate_embeddings, load_tmdb_images")


def cli() -> None:
    p = argparse.ArgumentParser(description="Загрузка российского кино из TMDB")
    p.add_argument("--top-actors", type=int, default=10, help="Актёров на фильм")
    p.add_argument(
        "--only",
        choices=[q["id"] for q in RU_DISCOVER],
        help="Только один блок: all, soviet, modern, lang",
    )
    args = p.parse_args()
    asyncio.run(main(top_actors=args.top_actors, only=args.only))


if __name__ == "__main__":
    cli()
