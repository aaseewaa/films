"""
Дозагрузка русских биографий персон из TMDB (language=ru-RU).

Заполняет entity_translation.description/summary для ru, если поле пустое.
TMDB часто отдаёт biography только на en-US при первичной загрузке.

Запуск (из backend/, venv):
    python -m scripts.backfill_person_bios_tmdb_ru --dry-run --limit 20
    python -m scripts.backfill_person_bios_tmdb_ru --all-persons
    python -m scripts.backfill_person_bios_tmdb_ru --all-persons --min-len 80
"""
from __future__ import annotations

import argparse
import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from scripts.backfill_person_bios_wikipedia import get_languages, update_bio
from scripts.tmdb_client import TmdbClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
log = logging.getLogger("backfill-tmdb-ru")

TMDB_LANG = "ru-RU"
PAUSE_SEC = 0.25


async def fetch_candidates(
    db: AsyncSession,
    *,
    limit: int | None,
    only_directors: bool,
    min_en_len: int,
) -> list[dict]:
    role_filter = "p.is_director = true" if only_directors else "true"
    en_hint = ""
    if min_en_len > 0:
        en_hint = f" AND length(coalesce(trim(et_en.description), '')) >= {int(min_en_len)}"

    sql = f"""
        SELECT
            p.id AS person_id,
            (e.external_ids->>'tmdb')::int AS tmdb_id,
            COALESCE(et_ru.title, et_en.title, p.sort_name) AS name
        FROM person p
        JOIN entity e ON e.id = p.id
        LEFT JOIN entity_translation et_ru
            ON et_ru.entity_id = p.id
           AND et_ru.language_id = (SELECT id FROM language WHERE code = 'ru' LIMIT 1)
        LEFT JOIN entity_translation et_en
            ON et_en.entity_id = p.id
           AND et_en.language_id = (SELECT id FROM language WHERE code = 'en' LIMIT 1)
        WHERE e.entity_type = 'person'
          AND e.status = 'published'
          AND {role_filter}
          AND e.external_ids ? 'tmdb'
          AND coalesce(trim(et_ru.description), '') = ''
          {en_hint}
        ORDER BY p.id
    """
    if limit:
        sql += f" LIMIT {int(limit)}"
    rows = (await db.execute(text(sql))).mappings().all()
    return [dict(r) for r in rows]


async def main(
    *,
    limit: int | None,
    dry_run: bool,
    only_directors: bool,
    min_len: int,
    min_en_len: int,
    pause: float,
) -> None:
    if not settings.tmdb_api_key:
        raise SystemExit("TMDB_API_KEY не задан в .env")

    async with AsyncSessionLocal() as db:
        languages = await get_languages(db)
        rows = await fetch_candidates(
            db,
            limit=limit,
            only_directors=only_directors,
            min_en_len=min_en_len,
        )

    log.info("к обработке: %d (dry_run=%s, min_len=%d)", len(rows), dry_run, min_len)
    if "ru" not in languages:
        raise SystemExit("В БД нет language.code = 'ru'")

    stats = {"updated": 0, "no_bio": 0, "too_short": 0, "errors": 0}

    async with TmdbClient(api_key=settings.tmdb_api_key) as tmdb:
        for i, row in enumerate(rows):
            pid = row["person_id"]
            tid = row["tmdb_id"]
            name = row["name"] or "?"
            try:
                data = await tmdb.person_full(tid, language=TMDB_LANG)
                bio = (data.get("biography") or "").strip()
                if not bio:
                    stats["no_bio"] += 1
                    continue
                if len(bio) < min_len:
                    stats["too_short"] += 1
                    continue
                if dry_run:
                    log.info("[%d] %s — RU bio %d симв.", i, name, len(bio))
                    stats["updated"] += 1
                    continue
                async with AsyncSessionLocal() as db:
                    if await update_bio(
                        db,
                        person_id=pid,
                        language_id=languages["ru"],
                        description=bio,
                        force=False,
                    ):
                        await db.commit()
                        stats["updated"] += 1
                        if stats["updated"] % 100 == 0:
                            log.info("  … обновлено %d", stats["updated"])
            except Exception as exc:
                stats["errors"] += 1
                log.warning("[%d] %s (tmdb=%s): %s", i, name, tid, exc)
            if pause:
                await asyncio.sleep(pause)

    log.info("─── DONE ───")
    log.info("обновлено RU:        %d", stats["updated"])
    log.info("пусто в TMDB:       %d", stats["no_bio"])
    log.info("короткий текст:     %d", stats["too_short"])
    log.info("ошибок:             %d", stats["errors"])
    log.info("дальше (если разрыв остался): backfill_person_bios_wikipedia / translate_en_ru")


def cli() -> None:
    p = argparse.ArgumentParser(description="RU-биографии персон из TMDB (ru-RU)")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--all-persons", action="store_true", help="Не только режиссёры")
    p.add_argument(
        "--min-len",
        type=int,
        default=40,
        help="Минимальная длина biography из TMDB",
    )
    p.add_argument(
        "--min-en-len",
        type=int,
        default=0,
        help="Обрабатывать только если EN description >= N (0 = все с пустым RU)",
    )
    p.add_argument("--pause", type=float, default=PAUSE_SEC)
    args = p.parse_args()
    asyncio.run(
        main(
            limit=args.limit,
            dry_run=args.dry_run,
            only_directors=not args.all_persons,
            min_len=args.min_len,
            min_en_len=args.min_en_len,
            pause=args.pause,
        )
    )


if __name__ == "__main__":
    cli()
