"""
Проставляет search_config (russian/english) и пересобирает search_tsv.

Запуск:
    cd backend && python -m scripts.backfill_search_config
"""
from __future__ import annotations

import asyncio

from sqlalchemy import text

from app.database import AsyncSessionLocal


async def main() -> None:
    async with AsyncSessionLocal() as db:
        r = await db.execute(text("""
            UPDATE entity_translation et
            SET search_config = CASE l.code
                WHEN 'ru' THEN 'russian'::regconfig
                WHEN 'en' THEN 'english'::regconfig
                ELSE 'simple'::regconfig
            END,
            search_tsv = to_tsvector(
                CASE l.code
                    WHEN 'ru' THEN 'russian'::regconfig
                    WHEN 'en' THEN 'english'::regconfig
                    ELSE 'simple'::regconfig
                END,
                coalesce(title, '') || ' ' ||
                coalesce(summary, '') || ' ' ||
                coalesce(description, '') || ' ' ||
                coalesce(body, '')
            )
            FROM language l
            WHERE l.id = et.language_id
              AND et.search_config::text = 'simple'
        """))
        await db.commit()
        print(f"updated rows: {r.rowcount}")


if __name__ == "__main__":
    asyncio.run(main())
