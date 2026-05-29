"""
Связи статей с упомянутыми режиссёрами (article_entity_link, link_type=mentions).

Совпадение: целое слово с заглавной, не внутри «кавычек», не из deny-листа.

Запуск (из backend/):
    python -m scripts.backfill_article_entity_links --dry-run
    python -m scripts.backfill_article_entity_links --replace
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import re

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from scripts.article_link_rules import (
    guillemet_ranges,
    is_valid_match,
    person_title_denied,
    surname_from_title,
    starts_with_capital,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
)
log = logging.getLogger("backfill-article-links")

MIN_FULL_NAME_LENGTH = 4

INSERT_SQL = text("""
    INSERT INTO article_entity_link
        (article_id, entity_id, link_type, link_weight, confidence, note)
    VALUES (:aid, :eid, 'mentions', 0.8, 0.9, 'auto: name in body')
    ON CONFLICT (article_id, entity_id, link_type) DO NOTHING
""")

DELETE_AUTO_SQL = text("""
    DELETE FROM article_entity_link
    WHERE note = 'auto: name in body'
""")


def regex_for_name(name: str) -> re.Pattern[str] | None:
    term = name.strip()
    if len(term) < MIN_FULL_NAME_LENGTH or not starts_with_capital(term):
        return None
    return re.compile(re.escape(term))


def patterns_for_title(title: str, slug: str | None) -> list[re.Pattern[str]]:
    full = title.strip()
    if not full or person_title_denied(slug, full):
        return []
    out: list[re.Pattern[str]] = []
    full_re = regex_for_name(full)
    if full_re:
        out.append(full_re)
    surname = surname_from_title(full)
    if surname:
        surname_re = regex_for_name(surname)
        if surname_re:
            out.append(surname_re)
    return out


def mentioned_in_body(
    body: str,
    slug: str | None,
    compiled: list[re.Pattern[str]],
) -> bool:
    if not body or not compiled:
        return False
    quote_ranges = guillemet_ranges(body)
    for pattern in compiled:
        for m in pattern.finditer(body):
            if is_valid_match(body, m, quote_ranges):
                return True
    return False


async def fetch_articles(db: AsyncSession) -> list[dict]:
    rows = (
        await db.execute(
            text("""
            SELECT a.id AS article_id, et.slug, et.body
            FROM article a
            JOIN entity e ON e.id = a.id
            JOIN entity_translation et ON et.entity_id = a.id
            JOIN language l ON l.id = et.language_id AND l.code = 'ru'
            WHERE e.status = 'published'
              AND coalesce(trim(et.body), '') <> ''
        """)
        )
    ).mappings().all()
    return [dict(r) for r in rows]


async def fetch_directors(db: AsyncSession) -> list[dict]:
    rows = (
        await db.execute(
            text("""
            SELECT e.id AS entity_id, COALESCE(et_ru.title, et_en.title) AS title
            FROM entity e
            JOIN person p ON p.id = e.id
            LEFT JOIN entity_translation et_ru
                ON et_ru.entity_id = e.id
                AND et_ru.language_id = (SELECT id FROM language WHERE code = 'ru')
            LEFT JOIN entity_translation et_en
                ON et_en.entity_id = e.id
                AND et_en.language_id = (SELECT id FROM language WHERE code = 'en')
            WHERE e.entity_type = 'person'
              AND e.status = 'published'
              AND p.is_director = true
              AND COALESCE(et_ru.title, et_en.title) IS NOT NULL
        """)
        )
    ).mappings().all()
    return [dict(r) for r in rows]


async def run(*, dry_run: bool, replace: bool) -> None:
    async with AsyncSessionLocal() as db:
        articles = await fetch_articles(db)
        directors = await fetch_directors(db)
        log.info("Статей с body: %d, режиссёров: %d", len(articles), len(directors))

        director_patterns = [
            (d["entity_id"], d["title"] or "")
            for d in directors
        ]

        pending: list[dict] = []
        articles_touched: set[int] = set()

        for art in articles:
            body = art["body"] or ""
            slug = art.get("slug")
            article_id = art["article_id"]

            for entity_id, title in director_patterns:
                compiled = patterns_for_title(title, slug)
                if not mentioned_in_body(body, slug, compiled):
                    continue
                pending.append({"aid": article_id, "eid": entity_id})
                articles_touched.add(article_id)

        log.info(
            "Найдено совпадений: %d (статей: %d)",
            len(pending),
            len(articles_touched),
        )

        if dry_run:
            log.info("Dry-run — изменений в БД нет.")
            return

        if replace:
            deleted = await db.execute(DELETE_AUTO_SQL)
            log.info("Удалено старых auto-связей: %s", deleted.rowcount)

        if pending:
            await db.execute(INSERT_SQL, pending)
            await db.commit()
            log.info("Сохранено.")
        else:
            if replace:
                await db.commit()
            log.info("Нечего вставлять.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Только лог, без INSERT",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Сначала удалить auto-связи, затем вставить заново",
    )
    args = parser.parse_args()
    asyncio.run(run(dry_run=args.dry_run, replace=args.replace))


if __name__ == "__main__":
    main()
