"""
Спрятать фильмы с сайта (status=draft), не удаляя из БД.

По умолчанию — всё с жанром «Анимация» (tmdb-16): мультики из load_tmdb_extra.

Запуск:
    cd backend && source venv/bin/activate
    python -m scripts.hide_films_by_genre              # только показать
    python -m scripts.hide_films_by_genre --apply      # спрятать
    python -m scripts.hide_films_by_genre --apply --genre family  # семейное (10751)
"""
from __future__ import annotations

import argparse
import asyncio
import logging

from sqlalchemy import text

from app.database import AsyncSessionLocal

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("hide-genre")

GENRE_CODES = {
    "animation": "tmdb-16",
    "family": "tmdb-10751",
}


async def run(*, genre_key: str, apply: bool) -> None:
    code = GENRE_CODES.get(genre_key)
    if not code:
        raise SystemExit(f"Неизвестный жанр: {genre_key}. Варианты: {list(GENRE_CODES)}")

    async with AsyncSessionLocal() as db:
        preview = (await db.execute(text("""
            SELECT e.id, et.title, f.release_year
            FROM entity e
            JOIN film f ON f.id = e.id
            LEFT JOIN entity_translation et
                ON et.entity_id = e.id
               AND et.language_id = (SELECT id FROM language WHERE code = 'ru')
            WHERE e.entity_type = 'film'
              AND e.status = 'published'
              AND EXISTS (
                SELECT 1 FROM entity_taxonomy ext
                JOIN taxonomy_term tt ON tt.id = ext.term_id
                WHERE ext.entity_id = e.id AND tt.code = :code
              )
            ORDER BY et.title
            LIMIT 200
        """), {"code": code})).mappings().all()

        total = (await db.execute(text("""
            SELECT count(*) AS n
            FROM entity e
            WHERE e.entity_type = 'film'
              AND e.status = 'published'
              AND EXISTS (
                SELECT 1 FROM entity_taxonomy ext
                JOIN taxonomy_term tt ON tt.id = ext.term_id
                WHERE ext.entity_id = e.id AND tt.code = :code
              )
        """), {"code": code})).scalar()

        log.info("Жанр %s (%s): %d опубликованных фильмов", genre_key, code, total)
        for r in preview[:30]:
            log.info("  • %s (%s)", r["title"] or "?", r["release_year"])
        if total > 30:
            log.info("  … и ещё %d", total - 30)

        if not apply:
            log.info("")
            log.info("Пробный прогон. Чтобы спрятать: --apply")
            return

        n = (await db.execute(text("""
            UPDATE entity e
            SET status = 'draft'
            WHERE e.entity_type = 'film'
              AND e.status = 'published'
              AND EXISTS (
                SELECT 1 FROM entity_taxonomy ext
                JOIN taxonomy_term tt ON tt.id = ext.term_id
                WHERE ext.entity_id = e.id AND tt.code = :code
              )
        """), {"code": code})).rowcount
        await db.commit()
        log.info("Скрыто (draft): %d фильмов. На сайте их не будет.", n)
        log.info("Эмбеддинги не трогали. Вернуть: UPDATE entity SET status='published' WHERE id=…")


def cli() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true", help="Реально перевести в draft")
    p.add_argument(
        "--genre", choices=list(GENRE_CODES), default="animation",
        help="Какой жанр спрятать (по умолчанию animation)",
    )
    args = p.parse_args()
    asyncio.run(run(genre_key=args.genre, apply=args.apply))


if __name__ == "__main__":
    cli()
