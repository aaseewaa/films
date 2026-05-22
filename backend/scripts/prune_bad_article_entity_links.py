"""
Удаляет ошибочные связи article_entity_link (mentions) по deny-листу.

Запуск (из backend/):
    python -m scripts.prune_bad_article_entity_links --dry-run
    python -m scripts.prune_bad_article_entity_links
"""
from __future__ import annotations

import argparse
import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from scripts.article_link_rules import person_title_denied

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
)
log = logging.getLogger("prune-article-links")


async def prune_with_python(db: AsyncSession, *, dry_run: bool) -> int:
    rows = (
        await db.execute(
            text("""
            SELECT
                ael.article_id,
                ael.entity_id,
                art_et.slug AS article_slug,
                person_et.title AS person_title
            FROM article_entity_link ael
            JOIN entity_translation art_et ON art_et.entity_id = ael.article_id
            JOIN language art_lang ON art_lang.id = art_et.language_id AND art_lang.code = 'ru'
            JOIN entity_translation person_et ON person_et.entity_id = ael.entity_id
            JOIN language person_lang ON person_lang.id = person_et.language_id AND person_lang.code = 'ru'
            WHERE ael.link_type = 'mentions'
        """)
        )
    ).mappings().all()

    to_delete: list[dict] = []
    for r in rows:
        slug = r["article_slug"]
        title = r["person_title"] or ""
        if person_title_denied(slug, title):
            to_delete.append({
                "aid": r["article_id"],
                "eid": r["entity_id"],
                "slug": slug,
                "title": title,
            })

    for item in to_delete:
        log.info(
            "  удалить: %s ← %s",
            item["slug"],
            item["title"],
        )

    if dry_run:
        log.info("Dry-run: к удалению %d связей", len(to_delete))
        return len(to_delete)

    if not to_delete:
        log.info("Нечего удалять.")
        return 0

    await db.execute(
        text("""
            DELETE FROM article_entity_link
            WHERE article_id = :aid AND entity_id = :eid AND link_type = 'mentions'
        """),
        [{"aid": x["aid"], "eid": x["eid"]} for x in to_delete],
    )
    await db.commit()
    log.info("Удалено связей: %d", len(to_delete))
    return len(to_delete)


async def run(*, dry_run: bool) -> None:
    async with AsyncSessionLocal() as db:
        await prune_with_python(db, dry_run=dry_run)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
