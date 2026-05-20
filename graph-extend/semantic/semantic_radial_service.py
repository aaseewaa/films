"""
Сервис гибридного радиального графа.

Объединяет ДВА типа связей:
  1. Эксплицитные ("учителя") — из director_influence (Wikidata + manual)
  2. Семантические ("близкие по духу") — через косинусное расстояние эмбеддингов биографий

ВАЖНО — логика заполнения:
  - Сначала тянем РЕАЛЬНЫХ учителей через director_influence
  - Если их МЕНЬШЕ 4 — добираем семантически похожими режиссёрами
  - Если 4 и более — семантические НЕ добавляем

Каждый узел в ответе имеет поле `link_kind`:
  - "explicit" — реальная связь из БД
  - "semantic" — семантическая близость

На фронте рисуем по-разному:
  - explicit: золотая обводка, "учитель"
  - semantic: серая пунктирная обводка, "близкий по духу"

Это сохраняет ТОЧНОСТЬ данных и при этом даёт плотный граф для любого центра.

Архитектурно это паттерн "Knowledge Graph Embedding" — стандартная практика
в современных KG (Google KG, Wikidata Embeddings, ConceptNet).
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


class SemanticRadialService:
    """Гибридный радиальный граф: explicit + semantic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_radial(
        self,
        center_id: int,
        *,
        top_n: int = 4,
        lang: str = "ru",
    ) -> Optional[dict]:
        """
        Возвращает центр + top_n соседей.

        Логика:
          1. Тянем эксплицитных учителей (top_n штук максимум) по weight DESC
          2. Если их = top_n → возвращаем только их
          3. Если меньше → добираем семантически похожими до top_n
        """
        # 1) Центральный режиссёр
        center = await self._fetch_person(center_id, lang=lang)
        if not center:
            return None

        # 2) Эксплицитные учителя
        explicit = await self._fetch_explicit_teachers(
            center_id, top_n=top_n, lang=lang,
        )

        # 3) Если хватает — возвращаем как есть
        if len(explicit) >= top_n:
            neighbors = explicit[:top_n]
            return {
                "center": center,
                "neighbors": neighbors,
                "explicit_count": len(explicit),
                "semantic_count": 0,
                "top_n_requested": top_n,
            }

        # 4) Добираем семантически похожими
        # Исключаем уже найденных явных учителей чтобы не было дублей
        exclude_ids = {n["id"] for n in explicit}
        exclude_ids.add(center_id)
        n_needed = top_n - len(explicit)

        semantic = await self._fetch_semantic_neighbors(
            center_id,
            n_needed=n_needed,
            exclude_ids=exclude_ids,
            lang=lang,
        )

        neighbors = explicit + semantic
        return {
            "center": center,
            "neighbors": neighbors,
            "explicit_count": len(explicit),
            "semantic_count": len(semantic),
            "top_n_requested": top_n,
        }

    # ─────────────────────────────────────────────
    async def _fetch_person(self, person_id: int, *, lang: str) -> Optional[dict]:
        sql = text("""
            SELECT
                p.id,
                COALESCE(et.title, p.sort_name) AS name,
                e.primary_image_url AS image
            FROM person p
            JOIN entity e ON e.id = p.id
            LEFT JOIN entity_translation et
                ON et.entity_id = p.id
                AND et.language_id = (SELECT id FROM language WHERE code = :lang)
            WHERE p.id = :pid AND p.is_director = true
        """)
        row = (await self.db.execute(sql, {"pid": person_id, "lang": lang})).mappings().first()
        if not row:
            return None
        return {
            "id": row["id"],
            "name": row["name"] or "Без имени",
            "image": row["image"],
        }

    # ─────────────────────────────────────────────
    async def _fetch_explicit_teachers(
        self,
        person_id: int,
        *,
        top_n: int,
        lang: str,
    ) -> list[dict]:
        """
        Учителя из director_influence:
          source повлиял на target,
          target = наш центральный,
          source = его учителя.
        """
        sql = text("""
            SELECT
                p.id,
                COALESCE(et.title, p.sort_name) AS name,
                e.primary_image_url AS image,
                COALESCE(di.weight, 1.0) AS weight,
                COALESCE((
                    SELECT count(*) FROM film_person fp
                    WHERE fp.person_id = p.id
                      AND fp.role_type = 'director'
                ), 0) AS films_count
            FROM director_influence di
            JOIN person p ON p.id = di.source_director_id
            JOIN entity e ON e.id = p.id
            LEFT JOIN entity_translation et
                ON et.entity_id = p.id
                AND et.language_id = (SELECT id FROM language WHERE code = :lang)
            WHERE di.target_director_id = :pid
              AND p.is_director = true
              AND e.status = 'published'
            ORDER BY COALESCE(di.weight, 1.0) DESC, films_count DESC
            LIMIT :n
        """)
        rows = (await self.db.execute(sql, {
            "pid": person_id, "lang": lang, "n": top_n,
        })).mappings().all()

        return [
            {
                "id": r["id"],
                "name": r["name"] or "Без имени",
                "image": r["image"],
                "weight": float(r["weight"]),
                "films_count": int(r["films_count"] or 0),
                "link_kind": "explicit",
                "link_label": "вдохновитель",
            }
            for r in rows
        ]

    # ─────────────────────────────────────────────
    async def _fetch_semantic_neighbors(
        self,
        center_id: int,
        *,
        n_needed: int,
        exclude_ids: set[int],
        lang: str,
    ) -> list[dict]:
        """
        Семантически близкие режиссёры через cosine distance эмбеддингов биографий.

        Использует pgvector:
          centerEmb.embedding <=> otherEmb.embedding

        Возвращает только режиссёров, у которых есть эмбеддинг биографии.
        """
        if n_needed <= 0:
            return []

        # Берём эмбеддинг центра (биография на запрошенном языке, fallback на EN)
        center_emb_sql = text("""
            SELECT et.embedding
            FROM entity_translation et
            JOIN language l ON l.id = et.language_id
            WHERE et.entity_id = :cid
              AND et.embedding IS NOT NULL
            ORDER BY (l.code = :lang) DESC, (l.code = 'en') DESC
            LIMIT 1
        """)
        center_row = (await self.db.execute(center_emb_sql, {
            "cid": center_id, "lang": lang,
        })).first()

        if not center_row or center_row[0] is None:
            # У центра нет эмбеддинга — семантический поиск невозможен
            log.info("Center %d has no embedding — skipping semantic neighbors", center_id)
            return []

        # exclude_ids нужно превратить в массив для PostgreSQL
        exclude_array = list(exclude_ids) if exclude_ids else [0]

        # Главный запрос: ближайшие режиссёры по cosine distance
        # Используем pgvector оператор <=>
        sql = text("""
            WITH center_emb AS (
                SELECT et.embedding AS emb
                FROM entity_translation et
                JOIN language l ON l.id = et.language_id
                WHERE et.entity_id = :cid
                  AND et.embedding IS NOT NULL
                ORDER BY (l.code = :lang) DESC, (l.code = 'en') DESC
                LIMIT 1
            )
            SELECT DISTINCT ON (p.id)
                p.id,
                COALESCE(et.title, p.sort_name) AS name,
                e.primary_image_url AS image,
                (et.embedding <=> (SELECT emb FROM center_emb)) AS distance,
                COALESCE((
                    SELECT count(*) FROM film_person fp
                    WHERE fp.person_id = p.id
                      AND fp.role_type = 'director'
                ), 0) AS films_count
            FROM person p
            JOIN entity e ON e.id = p.id
            JOIN entity_translation et ON et.entity_id = p.id
            JOIN language l ON l.id = et.language_id
            WHERE p.is_director = true
              AND e.status = 'published'
              AND et.embedding IS NOT NULL
              AND p.id != ALL(:exclude)
              AND films_count_filter(p.id) > 0  -- режиссёр должен иметь хотя бы один фильм
            ORDER BY p.id, (l.code = :lang) DESC, (l.code = 'en') DESC
            -- но нам нужно сортировать по distance...
        """)
        # Выше слишком сложно с DISTINCT ON + ORDER BY distance.
        # Упрощаю — отдельно вытащим лучший перевод для каждой персоны.

        # Упрощённый запрос: фильтр + сортировка по distance, без DISTINCT
        sql = text("""
            WITH center_emb AS (
                SELECT et.embedding AS emb
                FROM entity_translation et
                JOIN language l ON l.id = et.language_id
                WHERE et.entity_id = :cid
                  AND et.embedding IS NOT NULL
                ORDER BY (l.code = :lang) DESC, (l.code = 'en') DESC
                LIMIT 1
            ),
            candidates AS (
                SELECT
                    p.id AS pid,
                    MIN(et.embedding <=> (SELECT emb FROM center_emb)) AS min_distance
                FROM person p
                JOIN entity e ON e.id = p.id
                JOIN entity_translation et ON et.entity_id = p.id
                WHERE p.is_director = true
                  AND e.status = 'published'
                  AND et.embedding IS NOT NULL
                  AND p.id != ALL(:exclude)
                GROUP BY p.id
            ),
            -- Только режиссёры с хотя бы одним фильмом, чтобы не показывать
            -- одно-роль персон с is_director=true но без фильмов
            with_films AS (
                SELECT c.pid, c.min_distance
                FROM candidates c
                WHERE EXISTS (
                    SELECT 1 FROM film_person fp
                    WHERE fp.person_id = c.pid AND fp.role_type = 'director'
                )
                ORDER BY c.min_distance
                LIMIT :n
            )
            SELECT
                wf.pid AS id,
                wf.min_distance AS distance,
                COALESCE(et_lang.title, et_en.title, p.sort_name) AS name,
                e.primary_image_url AS image,
                (SELECT count(*) FROM film_person fp
                 WHERE fp.person_id = wf.pid AND fp.role_type = 'director') AS films_count
            FROM with_films wf
            JOIN person p ON p.id = wf.pid
            JOIN entity e ON e.id = wf.pid
            LEFT JOIN entity_translation et_lang
                ON et_lang.entity_id = wf.pid
                AND et_lang.language_id = (SELECT id FROM language WHERE code = :lang)
            LEFT JOIN entity_translation et_en
                ON et_en.entity_id = wf.pid
                AND et_en.language_id = (SELECT id FROM language WHERE code = 'en')
            ORDER BY wf.min_distance
        """)

        try:
            rows = (await self.db.execute(sql, {
                "cid": center_id,
                "lang": lang,
                "exclude": exclude_array,
                "n": n_needed,
            })).mappings().all()
        except Exception as exc:
            log.error("Semantic query failed: %s", exc)
            return []

        return [
            {
                "id": r["id"],
                "name": r["name"] or "Без имени",
                "image": r["image"],
                # distance — от 0 (идентично) до 2 (противоположно)
                # similarity = 1 - distance/2, чтобы 0..1
                "similarity": round(1.0 - float(r["distance"]) / 2.0, 3),
                "films_count": int(r["films_count"] or 0),
                "link_kind": "semantic",
                "link_label": "близкий по духу",
            }
            for r in rows
        ]
