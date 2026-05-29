"""
Генератор эмбеддингов для семантического поиска.

Модель: intfloat/multilingual-e5-small (384 dim, query:/passage: префиксы).
Персоны: имя + роли + био + до 8 фильмов из фильмографии.

Запуск:
    cd backend && source venv/bin/activate
    python -m scripts.generate_embeddings              # только без эмбеддинга
    python -m scripts.generate_embeddings --force      # пересчитать ВСЁ (после смены модели)

После смены модели в embedding_config.py всегда нужен --force.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import time

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import engine
from app.embedding_config import (
    MODEL_NAME,
    build_film_passage_text,
    build_person_passage_text,
    wrap_passage,
)
from app.embedding_person_context import load_person_context_for_batch

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)-12s | %(message)s",
)
log = logging.getLogger("embeddings")

BATCH_SIZE = 32


async def _texts_for_batch(
    db: AsyncSession,
    batch: list,
) -> list[str]:
    """Собирает passage-тексты для батча переводов."""
    person_ids = [
        int(r["entity_id"])
        for r in batch
        if r.get("entity_type") == "person"
    ]
    lang_by_person: dict[int, str] = {}
    for r in batch:
        if r.get("entity_type") == "person":
            lang_by_person[int(r["entity_id"])] = r.get("lang_code") or "ru"

    person_ctx_by_lang: dict[str, dict[int, dict]] = {}
    for lang in set(lang_by_person.values()):
        ids = [pid for pid, lc in lang_by_person.items() if lc == lang]
        person_ctx_by_lang[lang] = await load_person_context_for_batch(db, ids, lang)

    texts: list[str] = []
    for r in batch:
        lang = r.get("lang_code") or "ru"
        if r.get("entity_type") == "person":
            ctx = person_ctx_by_lang.get(lang, {}).get(int(r["entity_id"]), {})
            raw = build_person_passage_text(
                title=r["title"],
                summary=r["summary"],
                description=r["description"],
                is_director=ctx.get("is_director", False),
                is_actor=ctx.get("is_actor", False),
                birth_place=ctx.get("birth_place"),
                filmography_lines=ctx.get("filmography_lines"),
            )
        else:
            raw = build_film_passage_text(
                r["title"], r["summary"], r["description"],
            )
        texts.append(wrap_passage(raw))
    return texts


async def generate_embeddings(
    *,
    limit: int | None,
    force: bool,
    batch_size: int = BATCH_SIZE,
) -> None:
    log.info("Модель: %s", MODEL_NAME)
    if force:
        log.info("--force: пересчитываем все переводы (включая уже с эмбеддингом)")

    from sentence_transformers import SentenceTransformer

    t0 = time.time()
    model = SentenceTransformer(MODEL_NAME)
    log.info("Модель загружена за %.1f сек, dim=%d", time.time() - t0,
             model.get_sentence_embedding_dimension())

    async with AsyncSession(engine) as db:
        where_clause = "" if force else "WHERE et.embedding IS NULL"
        limit_clause = f"LIMIT {int(limit)}" if limit else ""

        sql = f"""
            SELECT et.entity_id, et.language_id, et.title, et.summary, et.description,
                   l.code AS lang_code, e.entity_type::text AS entity_type
            FROM entity_translation et
            JOIN entity e ON e.id = et.entity_id
            LEFT JOIN language l ON l.id = et.language_id
            {where_clause}
            ORDER BY et.entity_id, et.language_id
            {limit_clause}
        """
        rows = (await db.execute(text(sql))).mappings().all()
        log.info("Переводов к обработке: %d", len(rows))

        if not rows:
            log.info("Нечего обрабатывать.")
            return

        total = len(rows)
        processed = 0
        errors = 0
        t_start = time.time()

        for batch_start in range(0, total, batch_size):
            batch = rows[batch_start:batch_start + batch_size]
            texts = await _texts_for_batch(db, batch)

            non_empty_indices = [i for i, t in enumerate(texts) if t.strip()]
            non_empty_texts = [texts[i] for i in non_empty_indices]

            if not non_empty_texts:
                processed += len(batch)
                continue

            try:
                embeddings = model.encode(
                    non_empty_texts,
                    batch_size=batch_size,
                    show_progress_bar=False,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                )
            except Exception as exc:
                log.warning("Ошибка модели на батче %d: %s", batch_start, exc)
                errors += len(batch)
                continue

            for idx_in_filtered, idx_in_batch in enumerate(non_empty_indices):
                row = batch[idx_in_batch]
                vec = embeddings[idx_in_filtered]
                vec_str = "[" + ",".join(f"{x:.6f}" for x in vec) + "]"

                try:
                    await db.execute(text("""
                        UPDATE entity_translation
                        SET embedding = CAST(:vec AS vector),
                            embedding_updated_at = now()
                        WHERE entity_id = :eid AND language_id = :lid
                    """), {
                        "vec": vec_str,
                        "eid": row["entity_id"],
                        "lid": row["language_id"],
                    })
                except Exception as exc:
                    log.warning(
                        "UPDATE failed entity_id=%d lang_id=%d: %s",
                        row["entity_id"], row["language_id"], exc,
                    )
                    errors += 1

            await db.commit()
            processed += len(batch)

            if (batch_start // batch_size) % 10 == 0 or batch_start + batch_size >= total:
                elapsed = time.time() - t_start
                speed = processed / elapsed if elapsed > 0 else 0
                eta = (total - processed) / speed if speed > 0 else 0
                log.info(
                    "[%d/%d] %.1f%% | %.1f/сек | ETA %.0f с",
                    processed, total, 100 * processed / total, speed, eta,
                )

        elapsed = time.time() - t_start
        log.info("─── DONE ─── обработано=%d ошибок=%d время=%.1f с",
                 processed, errors, elapsed)

        stats = (await db.execute(text("""
            SELECT count(*) AS total, count(embedding) AS with_emb
            FROM entity_translation
        """))).mappings().first()
        log.info("Переводов с эмбеддингом: %d / %d",
                 stats["with_emb"], stats["total"])


def cli() -> None:
    parser = argparse.ArgumentParser(description="Генерация эмбеддингов (e5-small)")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--force", action="store_true",
        help="Пересчитать все эмбеддинги (обязательно после смены модели)",
    )
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    args = parser.parse_args()
    asyncio.run(generate_embeddings(
        limit=args.limit,
        force=args.force,
        batch_size=args.batch_size,
    ))


if __name__ == "__main__":
    cli()
