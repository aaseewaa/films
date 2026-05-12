"""
Генератор эмбеддингов для семантического поиска.

Что делает:
  1. Загружает многоязычную модель sentence-transformers
     (paraphrase-multilingual-MiniLM-L12-v2 — 384 измерения, 50+ языков)
  2. Берёт переводы entity_translation без эмбеддинга
  3. Считает эмбеддинг от title + summary (или description если summary нет)
  4. Сохраняет в БД пакетами

Идемпотентность:
  - Считает только записи где embedding IS NULL
  - При повторном запуске продолжит с того где закончил
  - Можно прервать (Ctrl+C) и запустить заново — прогресс сохранится

Запуск:
    python -m scripts.generate_embeddings           # обработать все
    python -m scripts.generate_embeddings --limit 100  # тест на 100
    python -m scripts.generate_embeddings --force      # пересчитать всё

Время прогона на mac (CPU):
    ~5300 переводов × ~50ms на эмбеддинг = ~5 минут
    Первый запуск + загрузка модели = +2-5 минут (зависит от интернета)
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import time

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)-12s | %(message)s",
)
log = logging.getLogger("embeddings")


# Модель: многоязычная (русский + английский в одном пространстве)
# 384 измерения, ~470 МБ, скачивается один раз
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Размер батча для модели (CPU): 32 — баланс памяти и скорости
BATCH_SIZE = 32


def build_text_for_embedding(title: str | None, summary: str | None, description: str | None) -> str:
    """
    Готовит текст для эмбеддинга.

    Стратегия:
      - title повторяется (+ выше вес заголовка в семантике)
      - summary предпочтительнее description (короче и точнее)
      - description обрезается до ~1000 символов (модель работает с 256 токенами)

    Это инженерная эвристика — не идеальная, но даёт хорошее качество.
    """
    parts: list[str] = []
    if title:
        parts.append(title.strip())
        parts.append(title.strip())  # title × 2 = повышенный вес

    body = (summary or description or "").strip()
    if body:
        parts.append(body[:1000])

    return " | ".join(parts) if parts else ""


async def generate_embeddings(
    *,
    limit: int | None,
    force: bool,
    batch_size: int = BATCH_SIZE,
) -> None:
    # Импорт здесь чтобы не загружать модель если скрипт упал на чём-то простом
    log.info("Загружаю модель sentence-transformers...")
    log.info("(первый раз качается ~470 МБ, это нормально)")

    from sentence_transformers import SentenceTransformer

    t0 = time.time()
    model = SentenceTransformer(MODEL_NAME)
    log.info("Модель загружена за %.1f сек", time.time() - t0)
    log.info("Embedding size: %d", model.get_sentence_embedding_dimension())

    # Берём переводы для обработки
    async with AsyncSession(engine) as db:
        where_clause = "" if force else "WHERE et.embedding IS NULL"
        if limit:
            limit_clause = f"LIMIT {int(limit)}"
        else:
            limit_clause = ""

        sql = f"""
            SELECT et.entity_id, et.language_id, et.title, et.summary, et.description,
                   l.code AS lang_code
            FROM entity_translation et
            LEFT JOIN language l ON l.id = et.language_id
            {where_clause}
            ORDER BY et.entity_id, et.language_id
            {limit_clause}
        """
        rows = (await db.execute(text(sql))).mappings().all()
        log.info("Переводов к обработке: %d", len(rows))

        if not rows:
            log.info("Нечего обрабатывать. Все эмбеддинги уже посчитаны.")
            return

        # Прогон батчами
        total = len(rows)
        processed = 0
        errors = 0
        t_start = time.time()

        for batch_start in range(0, total, batch_size):
            batch = rows[batch_start:batch_start + batch_size]

            # Готовим тексты для модели
            texts = [
                build_text_for_embedding(r["title"], r["summary"], r["description"])
                for r in batch
            ]

            # Если все тексты пустые — пропускаем (None в embedding)
            non_empty_indices = [i for i, t in enumerate(texts) if t]
            non_empty_texts = [texts[i] for i in non_empty_indices]

            if not non_empty_texts:
                processed += len(batch)
                continue

            # Считаем эмбеддинги одним батчем (быстрее чем по одному)
            try:
                embeddings = model.encode(
                    non_empty_texts,
                    batch_size=batch_size,
                    show_progress_bar=False,
                    convert_to_numpy=True,
                    normalize_embeddings=True,  # для cosine similarity
                )
            except Exception as exc:
                log.warning("Ошибка модели на батче %d: %s", batch_start, exc)
                errors += len(batch)
                continue

            # Сохраняем в БД
            for idx_in_filtered, idx_in_batch in enumerate(non_empty_indices):
                row = batch[idx_in_batch]
                vec = embeddings[idx_in_filtered]
                # pgvector принимает строку вида '[0.1,0.2,...]'
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
                        "UPDATE failed for entity_id=%d lang_id=%d: %s",
                        row["entity_id"], row["language_id"], exc,
                    )
                    errors += 1

            await db.commit()
            processed += len(batch)

            # Прогресс каждые 10 батчей
            if (batch_start // batch_size) % 10 == 0 or batch_start + batch_size >= total:
                elapsed = time.time() - t_start
                speed = processed / elapsed if elapsed > 0 else 0
                eta = (total - processed) / speed if speed > 0 else 0
                log.info(
                    "[%d/%d] %.1f%% | %.1f текстов/сек | ETA: %.0f сек",
                    processed, total, 100 * processed / total, speed, eta,
                )

        # Итоги
        elapsed = time.time() - t_start
        log.info("─── DONE ───")
        log.info("обработано:    %d", processed)
        log.info("ошибок:        %d", errors)
        log.info("время:         %.1f сек (%.1f текстов/сек)",
                 elapsed, processed / elapsed if elapsed > 0 else 0)

        # Финальная статистика
        stats = (await db.execute(text("""
            SELECT
                count(*) AS total,
                count(embedding) AS with_emb
            FROM entity_translation
        """))).mappings().first()
        log.info("Всего переводов:    %d", stats["total"])
        log.info("С эмбеддингами:     %d (%.1f%%)",
                 stats["with_emb"],
                 100 * stats["with_emb"] / stats["total"] if stats["total"] else 0)


def cli() -> None:
    parser = argparse.ArgumentParser(description="Генерация эмбеддингов")
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Обработать только N переводов (для теста)",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Пересчитать ВСЕ эмбеддинги, даже уже существующие",
    )
    parser.add_argument(
        "--batch-size", type=int, default=BATCH_SIZE,
        help=f"Размер батча для модели (по умолчанию {BATCH_SIZE})",
    )
    args = parser.parse_args()
    asyncio.run(generate_embeddings(
        limit=args.limit,
        force=args.force,
        batch_size=args.batch_size,
    ))


if __name__ == "__main__":
    cli()
