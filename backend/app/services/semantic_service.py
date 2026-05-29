"""
Сервис семантического поиска и рекомендаций через pgvector.

Этот сервис добавляет возможность находить сущности **по смыслу описания**,
а не по совпадению ключевых слов. Это решает классическую проблему:
запрос "медленный нуар с одиночеством" должен находить Drive и Blade Runner,
даже если этих слов нет в их описании.

Технология:
  1. При загрузке скрипт generate_embeddings посчитал вектор 384 измерений
     для каждого перевода через многоязычную модель
     paraphrase-multilingual-MiniLM-L12-v2.
  2. Эти векторы хранятся в entity_translation.embedding (тип pgvector).
  3. Для поиска: запрос пользователя проходит через ту же модель,
     получаем вектор. Затем PostgreSQL находит N ближайших по
     косинусному расстоянию через HNSW-индекс.
  4. Время: <50ms на запрос даже на десятках тысяч векторов.

Многоязычность:
  Модель учит русский и английский в **одном векторном пространстве**.
  Это значит: русский запрос находит английские описания и наоборот.
  Не нужны переводы запроса.

Использование:
    service = SemanticService(db)
    results = await service.semantic_search("медленный нуар", limit=10)
"""
from __future__ import annotations

import logging
from typing import ClassVar

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.embedding_config import (
    MIN_SEMANTIC_SIMILARITY,
    MODEL_NAME as EMBEDDING_MODEL_NAME,
    wrap_query,
)

log = logging.getLogger(__name__)


class SemanticService:
    """Семантический поиск и рекомендации через pgvector."""

    # Кешируем модель на уровне класса — загрузка дорогая (~3 сек),
    # держим её в памяти процесса между запросами.
    # Загружается лениво при первом обращении.
    _model: ClassVar[object | None] = None

    MODEL_NAME: ClassVar[str] = EMBEDDING_MODEL_NAME

    def __init__(self, db: AsyncSession):
        self.db = db

    @classmethod
    def _get_model(cls):
        """Ленивая загрузка модели sentence-transformers."""
        if cls._model is None:
            log.info("Загружаю модель %s (первый раз — ~470 МБ)", cls.MODEL_NAME)
            from sentence_transformers import SentenceTransformer
            cls._model = SentenceTransformer(cls.MODEL_NAME)
            log.info("Модель загружена. Размер вектора: %d",
                     cls._model.get_sentence_embedding_dimension())
        return cls._model

    def _encode_query(self, query: str) -> str:
        """Кодирует запрос в вектор и возвращает строку для PostgreSQL."""
        model = self._get_model()
        vec = model.encode(
            wrap_query(query),
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"

    # ─── Семантический поиск ───────────────────────────────────
    async def semantic_search(
        self,
        query: str,
        *,
        lang: str | None = None,
        entity_type: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict]:
        """
        Находит сущности по семантическому сходству описания с запросом.

        Возвращает список с similarity score (0-1, где 1 = идеальное совпадение).

        Параметр lang: если задан — ищем только по переводам на этом языке.
        Если None — ищем в любом языке (благодаря многоязычной модели,
        русский запрос найдёт английское описание тоже).
        """
        vec_str = self._encode_query(query)

        # Берём с запасом, потом отсекаем по MIN_SEMANTIC_SIMILARITY
        fetch_limit = min(200, max(60, (limit + offset) * 4))
        where_parts = ["et.embedding IS NOT NULL"]
        params: dict = {"vec": vec_str, "lim": fetch_limit, "off": 0}

        if lang:
            where_parts.append("l.code = :lang")
            params["lang"] = lang
        if entity_type:
            where_parts.append("e.entity_type = CAST(:etype AS entity_type)")
            params["etype"] = entity_type

        where_parts.append("e.status = 'published'")
        where_sql = " AND ".join(where_parts)

        # 1) MIN distance на сущность  2) глобальный ORDER BY distance  3) текст ближайшего перевода
        # Раньше LIMIT резал по entity_id до сортировки по similarity — одни и те же хиты.
        pref_lang = lang or "ru"
        params["pref_lang"] = pref_lang

        sql = f"""
            WITH per_entity AS (
                SELECT
                    et.entity_id,
                    MIN(et.embedding <=> CAST(:vec AS vector)) AS distance
                FROM entity_translation et
                JOIN entity e ON e.id = et.entity_id
                LEFT JOIN language l ON l.id = et.language_id
                WHERE {where_sql}
                GROUP BY et.entity_id
                ORDER BY distance
                LIMIT :lim OFFSET :off
            )
            SELECT DISTINCT ON (pe.entity_id)
                pe.entity_id,
                e.entity_type::text AS entity_type,
                COALESCE(et_pref.title, et.title) AS title,
                COALESCE(et_pref.summary, et.summary) AS summary,
                l.code AS language_code,
                e.primary_image_url AS img_primary,
                e.thumbnail_url AS img_thumb,
                1 - pe.distance AS similarity
            FROM per_entity pe
            JOIN entity e ON e.id = pe.entity_id
            JOIN entity_translation et
                ON et.entity_id = pe.entity_id
               AND et.embedding IS NOT NULL
            LEFT JOIN language l ON l.id = et.language_id
            LEFT JOIN entity_translation et_pref
                ON et_pref.entity_id = pe.entity_id
               AND et_pref.language_id = (SELECT id FROM language WHERE code = :pref_lang)
            ORDER BY pe.entity_id, et.embedding <=> CAST(:vec AS vector)
        """

        rows = (await self.db.execute(text(sql), params)).mappings().all()
        rows = sorted(rows, key=lambda r: -float(r["similarity"]))
        rows = [
            r for r in rows
            if float(r["similarity"]) >= MIN_SEMANTIC_SIMILARITY
        ]
        rows = rows[offset : offset + limit]

        return [
            {
                "entity_id": r["entity_id"],
                "entity_type": r["entity_type"],
                "title": r["title"],
                "summary": r["summary"],
                "language_code": r["language_code"],
                "images": {
                    "primary": r["img_primary"],
                    "thumbnail": r["img_thumb"],
                },
                "similarity": round(float(r["similarity"]), 4),
            }
            for r in rows
        ]

    # ─── Семантические рекомендации ────────────────────────────
    async def similar_to_entity(
        self,
        entity_id: int,
        *,
        lang: str = "ru",
        limit: int = 10,
    ) -> dict | None:
        """
        Похожие сущности по семантике описания.

        Алгоритм:
          1. Берём эмбеддинг описания исходной сущности (на выбранном языке)
          2. Ищем N ближайших по косинусу
          3. Исключаем саму исходную сущность

        Это даёт **смысловое сходство** — Inception + Memento будут рядом,
        потому что описания обоих про память/время/идентичность, хотя
        у них разные жанры, актёры, и режиссёры.
        """
        # Берём эмбеддинг исходной сущности
        source_emb_sql = text("""
            SELECT et.embedding, e.entity_type::text AS entity_type
            FROM entity_translation et
            JOIN entity e ON e.id = et.entity_id
            WHERE et.entity_id = :eid
              AND et.embedding IS NOT NULL
            ORDER BY
              CASE WHEN et.language_id = (SELECT id FROM language WHERE code = :lang)
                   THEN 0 ELSE 1 END
            LIMIT 1
        """)
        row = (await self.db.execute(source_emb_sql, {
            "eid": entity_id, "lang": lang,
        })).mappings().first()

        if not row or row["embedding"] is None:
            return None

        source_entity_type = row["entity_type"]

        # Ищем похожие. Ограничиваем тем же типом сущности (фильмы похожи на фильмы)
        sql = text("""
            SELECT DISTINCT ON (et.entity_id)
                et.entity_id,
                e.entity_type::text AS entity_type,
                COALESCE(et_lang.title, et.title) AS title,
                COALESCE(et_lang.summary, et.summary) AS summary,
                e.primary_image_url AS img_primary,
                e.thumbnail_url AS img_thumb,
                f.release_year,
                1 - (et.embedding <=> :source_vec) AS similarity
            FROM entity_translation et
            JOIN entity e ON e.id = et.entity_id
            LEFT JOIN film f ON f.id = e.id
            LEFT JOIN entity_translation et_lang
                ON et_lang.entity_id = e.id
                AND et_lang.language_id = (SELECT id FROM language WHERE code = :lang)
            WHERE et.embedding IS NOT NULL
              AND et.entity_id != :eid
              AND e.entity_type = CAST(:etype AS entity_type)
              AND e.status = 'published'
            ORDER BY et.entity_id, et.embedding <=> :source_vec
            LIMIT 200
        """)
        rows = (await self.db.execute(sql, {
            "source_vec": row["embedding"],
            "eid": entity_id,
            "etype": source_entity_type,
            "lang": lang,
        })).mappings().all()

        # Сортируем по similarity и обрезаем до limit
        items = sorted(
            (
                {
                    "entity_id": r["entity_id"],
                    "entity_type": r["entity_type"],
                    "title": r["title"] or "Untitled",
                    "summary": r["summary"],
                    "images": {
                        "primary": r["img_primary"],
                        "thumbnail": r["img_thumb"],
                    },
                    "release_year": r["release_year"],
                    "score": round(float(r["similarity"]), 4),
                    "reasons": [
                        f"семантическая близость {round(float(r['similarity']) * 100)}%"
                    ],
                }
                for r in rows
            ),
            key=lambda x: -x["score"],
        )[:limit]

        return {
            "items": items,
            "source_entity_id": entity_id,
            "source_entity_type": source_entity_type,
            "algorithm": "semantic",
        }
