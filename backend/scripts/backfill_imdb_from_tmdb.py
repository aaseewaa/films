"""
Проставляет IMDb id (nm…) режиссёрам, у которых есть TMDB, но нет валидного imdb.

load_tmdb создаёт person только с external_ids.tmdb — без этого шага
load_wikidata_influences_v2 видит лишь ~300 режиссёров, а не всех.

Запуск (из backend/, venv активен):
    python -m scripts.backfill_imdb_from_tmdb
    python -m scripts.backfill_imdb_from_tmdb --limit 100 --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from scripts.tmdb_client import TmdbClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
log = logging.getLogger("backfill-imdb")

LANG = "en-US"


def extract_imdb(person_json: dict) -> str | None:
    imdb = person_json.get("imdb_id")
    if not imdb:
        ext = person_json.get("external_ids") or {}
        imdb = ext.get("imdb_id")
    if imdb and str(imdb).startswith("nm"):
        return str(imdb)
    return None


async def set_imdb(db: AsyncSession, person_id: int, imdb: str) -> None:
    await db.execute(
        text("""
            UPDATE entity
            SET external_ids = external_ids || jsonb_build_object('imdb', CAST(:imdb AS text))
            WHERE id = :id
        """),
        {"id": person_id, "imdb": imdb},
    )


async def main(*, limit: int | None, dry_run: bool, only_directors: bool) -> None:
    if not settings.tmdb_api_key:
        raise SystemExit("TMDB_API_KEY не задан в .env")

    role_filter = "p.is_director = true" if only_directors else "true"

    async with AsyncSessionLocal() as db:
        sql = f"""
            SELECT p.id AS person_id,
                   (e.external_ids->>'tmdb')::int AS tmdb_id,
                   et.title AS name
            FROM person p
            JOIN entity e ON e.id = p.id
            LEFT JOIN entity_translation et
              ON et.entity_id = p.id
             AND et.language_id = (SELECT id FROM language WHERE code = 'en' LIMIT 1)
            WHERE {role_filter}
              AND e.external_ids ? 'tmdb'
              AND (
                NOT (e.external_ids ? 'imdb')
                OR e.external_ids->>'imdb' IS NULL
                OR e.external_ids->>'imdb' = ''
                OR e.external_ids->>'imdb' NOT LIKE 'nm%'
              )
            ORDER BY p.id
        """
        if limit:
            sql += f" LIMIT {int(limit)}"
        rows = [dict(r) for r in (await db.execute(text(sql))).mappings().all()]

    log.info("к обработке: %d персон (dry_run=%s)", len(rows), dry_run)

    stats = {"updated": 0, "no_imdb_in_tmdb": 0, "errors": 0}

    async with TmdbClient(api_key=settings.tmdb_api_key) as tmdb:
        for i, row in enumerate(rows):
            pid, tid, name = row["person_id"], row["tmdb_id"], row["name"] or "?"
            try:
                data = await tmdb.person_full(tid, language=LANG)
                imdb = extract_imdb(data)
                if not imdb:
                    stats["no_imdb_in_tmdb"] += 1
                    log.debug("[%d] TMDB без imdb: %s (tmdb=%s)", i, name, tid)
                    continue
                if dry_run:
                    log.info("[%d] would set %s → %s", i, name, imdb)
                    stats["updated"] += 1
                    continue
                async with AsyncSessionLocal() as db:
                    await set_imdb(db, pid, imdb)
                    await db.commit()
                stats["updated"] += 1
                if stats["updated"] % 50 == 0:
                    log.info("  … обновлено %d", stats["updated"])
            except Exception as exc:
                stats["errors"] += 1
                log.warning("[%d] %s (tmdb=%s): %s", i, name, tid, exc)

    log.info("─── DONE ───")
    log.info("обновлено imdb:     %d", stats["updated"])
    log.info("нет imdb в TMDB:   %d", stats["no_imdb_in_tmdb"])
    log.info("ошибок:            %d", stats["errors"])
    log.info("после прогона проверьте:")
    log.info("  SELECT count(*) FROM person p JOIN entity e ON e.id=p.id")
    log.info("  WHERE p.is_director AND e.external_ids->>'imdb' LIKE 'nm%%';")
    log.info("затем: python -m scripts.load_wikidata_influences_v2")


def cli() -> None:
    p = argparse.ArgumentParser(description="IMDb id из TMDB → entity.external_ids")
    p.add_argument("--limit", type=int, default=None, help="Макс. персон за прогон")
    p.add_argument("--dry-run", action="store_true", help="Только показать, без UPDATE")
    p.add_argument(
        "--all-persons",
        action="store_true",
        help="Не только is_director, а все person с tmdb без imdb",
    )
    args = p.parse_args()
    asyncio.run(
        main(
            limit=args.limit,
            dry_run=args.dry_run,
            only_directors=not args.all_persons,
        )
    )


if __name__ == "__main__":
    cli()
