"""
Загрузчик TMDB keywords для всех фильмов в БД.

Что делает:
  1. Берёт все фильмы из БД, у которых есть external_ids.tmdb
  2. Для каждого дёргает /movie/{tmdb_id}/keywords у TMDB
  3. Для каждого keyword:
     - создаёт taxonomy_term (term_type='keyword') если ещё нет (по code)
     - создаёт перевод taxonomy_term_translation на английском
     - связывает фильм с keyword через entity_taxonomy

Идемпотентность:
  - ON CONFLICT DO NOTHING на уникальных ключах
  - Можно запускать сколько угодно раз, дубли не создаст
  - Если keyword уже существует — переиспользует, не плодит копии

Запуск:
    python -m scripts.load_tmdb_keywords
    python -m scripts.load_tmdb_keywords --limit 50   # для теста
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import re

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import engine
from sqlalchemy.ext.asyncio import AsyncSession
from scripts.tmdb_client import TmdbClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)-12s | %(message)s",
)
log = logging.getLogger("keywords-loader")


def normalize_code(name: str) -> str:
    """
    Нормализует имя keyword в безопасный slug для taxonomy_term.code (varchar 64).

    Примеры:
      'Sci-Fi'          -> 'sci-fi'
      'Time Travel'     -> 'time-travel'
      'Mind-Bending'    -> 'mind-bending'
      'Based on novel'  -> 'based-on-novel'
    """
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s)
    s = s.strip("-")
    return s[:64]


async def load_keywords_for_film(
    db: AsyncSession,
    tmdb: TmdbClient,
    *,
    film_id: int,
    tmdb_id: int,
    en_lang_id: int,
) -> int:
    """Загружает keywords для одного фильма. Возвращает число новых связей.

    Каждый keyword обрабатывается в отдельной транзакции — если один упал,
    остальные сохраняются. Это особенно важно при идемпотентном перезапуске
    скрипта (на втором прогоне INSERT может встретить дубли).
    """
    data = await tmdb._get(f"/movie/{tmdb_id}/keywords", {})
    keywords = (data or {}).get("keywords", [])
    if not keywords:
        return 0

    new_links = 0

    for kw in keywords:
        name = kw.get("name", "").strip()
        if not name:
            continue

        code = normalize_code(name)
        if not code:
            continue

        try:
            term_id = (await db.execute(text("""
                INSERT INTO taxonomy_term (term_type, code, is_system, sort_order)
                VALUES ('keyword', :code, true, 0)
                ON CONFLICT (term_type, code) DO UPDATE
                    SET code = EXCLUDED.code
                RETURNING id
            """), {"code": code})).scalar_one()

            await db.execute(text("""
                INSERT INTO taxonomy_term_translation (term_id, language_id, name)
                VALUES (:tid, :lid, :name)
                ON CONFLICT (term_id, language_id) DO NOTHING
            """), {"tid": term_id, "lid": en_lang_id, "name": name})

            result = await db.execute(text("""
                INSERT INTO entity_taxonomy (entity_id, term_id, is_primary)
                VALUES (:eid, :tid, false)
                ON CONFLICT (entity_id, term_id) DO NOTHING
            """), {"eid": film_id, "tid": term_id})

            if (result.rowcount or 0) > 0:
                new_links += 1

            await db.commit()
        except Exception as exc:
            await db.rollback()
            log.warning(
                "    keyword=%r FAILED (film=%d): %s", code, film_id, exc,
            )

    return new_links


async def main(*, limit: int | None) -> None:
    if not settings.tmdb_api_key:
        raise SystemExit("TMDB_API_KEY не задан в .env")

    log.info("─── TMDB Keywords Loader ───")

    async with AsyncSession(engine) as db:
        en_lang_id = (await db.execute(
            text("SELECT id FROM language WHERE code = 'en'")
        )).scalar_one_or_none()
        if en_lang_id is None:
            raise SystemExit("Язык 'en' не найден в таблице language")

        sql = """
            SELECT f.id AS film_id, (e.external_ids->>'tmdb')::int AS tmdb_id
            FROM film f
            JOIN entity e ON e.id = f.id
            WHERE e.external_ids ? 'tmdb'
            ORDER BY f.id
        """
        if limit:
            sql += f" LIMIT {int(limit)}"

        rows = (await db.execute(text(sql))).mappings().all()
        log.info("фильмов для обработки: %d", len(rows))

        if not rows:
            log.warning("Нет фильмов с TMDB id — нечего загружать")
            return

        async with TmdbClient(api_key=settings.tmdb_api_key) as tmdb:
            total_new_links = 0
            total_with_keywords = 0
            errors = 0

            for i, row in enumerate(rows, 1):
                film_id = row["film_id"]
                tmdb_id = row["tmdb_id"]

                try:
                    new_links = await load_keywords_for_film(
                        db, tmdb,
                        film_id=film_id, tmdb_id=tmdb_id,
                        en_lang_id=en_lang_id,
                    )
                    if new_links > 0:
                        total_with_keywords += 1
                    total_new_links += new_links

                    if i % 50 == 0 or i == len(rows):
                        log.info(
                            "[%d/%d] обработано, новых связей: %d, фильмов с keywords: %d",
                            i, len(rows), total_new_links, total_with_keywords,
                        )

                except Exception as exc:
                    errors += 1
                    log.warning(
                        "[%d/%d] film_id=%d tmdb=%d FAILED: %s",
                        i, len(rows), film_id, tmdb_id, exc,
                    )
                    # На всякий случай откатываем транзакцию, чтобы не залипла
                    try:
                        await db.rollback()
                    except Exception:
                        pass

        log.info("─── DONE ───")
        log.info("обработано фильмов:       %d", len(rows))
        log.info(" • получили keywords:     %d", total_with_keywords)
        log.info(" • создано новых связей:  %d", total_new_links)
        log.info(" • ошибок:                %d", errors)

        stats = (await db.execute(text("""
            SELECT count(*) FROM taxonomy_term WHERE term_type = 'keyword'
        """))).scalar_one()
        log.info(" • всего keywords в БД:   %d", stats)

        top = (await db.execute(text("""
            SELECT tt.code, count(ex.entity_id) AS film_count
            FROM taxonomy_term tt
            JOIN entity_taxonomy ex ON ex.term_id = tt.id
            WHERE tt.term_type = 'keyword'
            GROUP BY tt.id, tt.code
            ORDER BY film_count DESC
            LIMIT 10
        """))).mappings().all()
        log.info("Топ-10 keywords:")
        for r in top:
            log.info("    %-30s %d фильмов", r["code"], r["film_count"])


def cli() -> None:
    parser = argparse.ArgumentParser(description="Загрузчик TMDB keywords")
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Ограничить число фильмов (для теста)",
    )
    args = parser.parse_args()
    asyncio.run(main(limit=args.limit))


if __name__ == "__main__":
    cli()
