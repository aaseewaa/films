"""
Удаление устаревших дублей коллекций (оставляем новые версии).

Удаляет:
  - marvel-mcu                   (старый interim-slug)
  - cinema-of-2000s-generation   (старая, v3)

Оставляет:
  - marvel-cinematic-universe    (seed_marvel.py, 33 фильма MCU)
  - generation-2000s             (seed_collections_update.py, 14 фильмов)

Фильмы из БД не удаляются — только entity коллекций и их items.

Запуск:
    cd backend
    source venv/bin/activate
    python -m scripts.prune_duplicate_collections          # dry-run
    python -m scripts.prune_duplicate_collections --apply  # удалить
"""
from __future__ import annotations

import argparse
import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
)
log = logging.getLogger("prune-collections")

SLUGS_TO_DELETE = [
    "marvel-mcu",
    "cinema-of-2000s-generation",
]

SLUGS_TO_KEEP = [
    "marvel-cinematic-universe",
    "generation-2000s",
]


async def fetch_by_slugs(db: AsyncSession, slugs: list[str]) -> list[dict]:
    rows = (await db.execute(text("""
        SELECT c.id, et.slug, et.title, c.items_count
        FROM collection c
        JOIN entity e ON e.id = c.id
        JOIN entity_translation et ON et.entity_id = c.id
          AND et.language_id = (SELECT id FROM language WHERE code = 'ru')
        WHERE et.slug = ANY(:slugs)
        ORDER BY et.slug
    """), {"slugs": slugs})).mappings().all()
    return [dict(r) for r in rows]


async def main() -> None:
    parser = argparse.ArgumentParser(description="Удалить дубли коллекций Marvel и 2000-х")
    parser.add_argument("--apply", action="store_true", help="Выполнить удаление (без флага — только просмотр)")
    args = parser.parse_args()

    async with AsyncSession(engine) as db:
        to_delete = await fetch_by_slugs(db, SLUGS_TO_DELETE)
        to_keep = await fetch_by_slugs(db, SLUGS_TO_KEEP)

        log.info("═══ Оставляем (новые) ═══")
        if not to_keep:
            log.warning("  ⚠️  Не найдены — проверь, что seed_marvel и seed_collections_update уже запускались")
        for row in to_keep:
            log.info("  ✓ id=%d | %d films | %s | %s", row["id"], row["items_count"], row["slug"], row["title"])

        log.info("")
        log.info("═══ К удалению (старые дубли) ═══")
        if not to_delete:
            log.info("  (ничего не найдено — дублей уже нет)")
            return

        for row in to_delete:
            log.info("  ✗ id=%d | %d films | %s | %s", row["id"], row["items_count"], row["slug"], row["title"])

        if not args.apply:
            log.info("")
            log.info("Dry-run. Для удаления запусти с --apply")
            return

        ids = [row["id"] for row in to_delete]
        result = await db.execute(text("""
            DELETE FROM entity
            WHERE id = ANY(:ids)
              AND entity_type = 'collection'
            RETURNING id
        """), {"ids": ids})
        deleted_ids = [r[0] for r in result.all()]
        await db.commit()

        log.info("")
        log.info("✅ Удалено коллекций: %d (entity ids: %s)", len(deleted_ids), deleted_ids)


if __name__ == "__main__":
    asyncio.run(main())
