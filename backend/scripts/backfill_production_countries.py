"""
Заполняет production_countries в entity.extra_metadata для уже загруженных фильмов.

Запуск (backend/, venv):
    python -m scripts.backfill_production_countries
    python -m scripts.backfill_production_countries --limit 50
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from scripts.production_countries import build_production_countries
from scripts.tmdb_client import TmdbClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
log = logging.getLogger("backfill-countries")

LANG_EN = "en-US"
LANG_RU = "ru-RU"


async def films_without_countries(db: AsyncSession, limit: int | None) -> list[dict]:
    sql = """
        SELECT e.id, (e.external_ids->>'tmdb')::int AS tmdb_id
        FROM entity e
        JOIN film f ON f.id = e.id
        WHERE e.entity_type = 'film'
          AND e.external_ids ? 'tmdb'
          AND (
            NOT (e.extra_metadata ? 'production_countries')
            OR jsonb_array_length(COALESCE(e.extra_metadata->'production_countries', '[]'::jsonb)) = 0
          )
        ORDER BY e.id
    """
    if limit:
        sql += f" LIMIT {int(limit)}"
    rows = (await db.execute(text(sql))).mappings().all()
    return [dict(r) for r in rows]


async def main(*, limit: int | None) -> None:
    if not settings.tmdb_api_key:
        raise SystemExit("TMDB_API_KEY не задан")

    async with AsyncSessionLocal() as db:
        films = await films_without_countries(db, limit)
    log.info("фильмов без production_countries: %d", len(films))

    updated, skipped, errors = 0, 0, 0

    async with TmdbClient(api_key=settings.tmdb_api_key) as tmdb:
        for i, row in enumerate(films):
            tid = row["tmdb_id"]
            eid = row["id"]
            try:
                en = await tmdb.movie_full(tid, language=LANG_EN)
                ru = await tmdb.movie_full(tid, language=LANG_RU)
                countries = build_production_countries(en, ru)
                if not countries:
                    skipped += 1
                    continue
                async with AsyncSessionLocal() as db:
                    await db.execute(
                        text("""
                            UPDATE entity
                            SET extra_metadata = extra_metadata || CAST(:meta AS jsonb)
                            WHERE id = :id
                        """),
                        {
                            "id": eid,
                            "meta": json.dumps({"production_countries": countries}),
                        },
                    )
                    await db.commit()
                updated += 1
                if updated % 25 == 0:
                    log.info("  обновлено %d…", updated)
            except Exception as exc:
                errors += 1
                log.warning("[%d] tmdb=%s: %s", i, tid, exc)

    log.info("─── DONE ─── updated=%d skipped=%d errors=%d", updated, skipped, errors)


def cli() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=None)
    args = p.parse_args()
    asyncio.run(main(limit=args.limit))


if __name__ == "__main__":
    cli()
