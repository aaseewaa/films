"""
Сервис рекомендаций.

Поддерживает два режима:

1. **content** (по умолчанию) — взвешенный score по совпадениям атрибутов:
   - +3 за общего режиссёра
   - +2 за общего топ-10 актёра
   - +1 за общий жанр (кап 3)
   - +1.5 за общий keyword/атмосферный тег (кап 6) — НОВОЕ через TMDB keywords
   - +0.5 за близкий год (±5)

   Это улучшенный «Кинопоиск-стиль»: тегов больше, но логика та же.

2. **semantic** — близость по смыслу через эмбеддинги pgvector:
   - находит фильмы где описание семантически близко
   - использует косинусное сходство векторов
   - даёт совершенно другую выдачу — по атмосфере и смыслу

Для персон (режиссёров):
- content: +5 за связь в графе влияний + общие жанры режиссуры
- semantic: близость векторов биографий

На защите можно сравнить выдачу content vs semantic — это
ключевое сравнение «Кинопоиск vs Letterboxd-стиль».
"""
from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


class RecommendationsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ─── Рекомендации для фильма ────────────────────────────────
    async def for_film(
        self,
        film_id: int,
        *,
        lang: str = "ru",
        limit: int = 10,
        mode: str = "content",
    ) -> dict | None:
        """
        Похожие фильмы.

        mode='content' — взвешенный score по атрибутам (режиссёр/актёр/жанр/keyword)
        mode='semantic' — близость векторов описаний через pgvector
        """
        check = await self.db.execute(text("""
            SELECT 1 FROM film WHERE id = :id
        """), {"id": film_id})
        if not check.first():
            return None

        if mode == "semantic":
            return await self._for_film_semantic(film_id, lang=lang, limit=limit)
        else:
            return await self._for_film_content(film_id, lang=lang, limit=limit)

    async def _for_film_content(
        self, film_id: int, *, lang: str, limit: int,
    ) -> dict:
        """Content-based: общие режиссёры, актёры, жанры, keywords, близкий год."""

        sql = text("""
            WITH
            source_genres AS (
                SELECT term_id FROM entity_taxonomy ex
                JOIN taxonomy_term tt ON tt.id = ex.term_id
                WHERE ex.entity_id = :fid AND tt.term_type = 'genre'
            ),
            source_keywords AS (
                SELECT term_id FROM entity_taxonomy ex
                JOIN taxonomy_term tt ON tt.id = ex.term_id
                WHERE ex.entity_id = :fid AND tt.term_type = 'keyword'
            ),
            source_directors AS (
                SELECT person_id FROM film_person
                WHERE film_id = :fid AND role_type = 'director'
            ),
            source_actors AS (
                SELECT person_id FROM film_person
                WHERE film_id = :fid AND role_type = 'actor'
                ORDER BY billing_order NULLS LAST
                LIMIT 5
            ),
            source_year AS (
                SELECT release_year FROM film WHERE id = :fid
            ),
            scored AS (
                SELECT
                    f.id,
                    -- Жанры: 1 за каждый, кап 3
                    LEAST(3, (
                        SELECT count(*) FROM entity_taxonomy ex
                        JOIN taxonomy_term tt ON tt.id = ex.term_id
                        WHERE ex.entity_id = f.id AND tt.term_type = 'genre'
                          AND ex.term_id IN (SELECT term_id FROM source_genres)
                    )) AS genre_score,
                    -- Keywords: 1.5 за каждый, кап 6 (макс 4 общих атмосферных)
                    LEAST(6, 1.5 * (
                        SELECT count(*) FROM entity_taxonomy ex
                        JOIN taxonomy_term tt ON tt.id = ex.term_id
                        WHERE ex.entity_id = f.id AND tt.term_type = 'keyword'
                          AND ex.term_id IN (SELECT term_id FROM source_keywords)
                    )) AS keyword_score,
                    -- Режиссёр: 3
                    3 * (
                        SELECT count(*) FROM film_person fp
                        WHERE fp.film_id = f.id AND fp.role_type = 'director'
                          AND fp.person_id IN (SELECT person_id FROM source_directors)
                    ) AS director_score,
                    -- Актёр: 2, кап 6
                    LEAST(6, 2 * (
                        SELECT count(*) FROM film_person fp
                        WHERE fp.film_id = f.id AND fp.role_type = 'actor'
                          AND fp.person_id IN (SELECT person_id FROM source_actors)
                    )) AS actor_score,
                    -- Год: 0.5 за близкий
                    CASE
                        WHEN abs(f.release_year - (SELECT release_year FROM source_year)) <= 5
                        THEN 0.5 ELSE 0
                    END AS year_score
                FROM film f
                WHERE f.id != :fid
                  AND EXISTS (
                      SELECT 1 FROM entity_taxonomy ex
                      WHERE ex.entity_id = f.id
                        AND ex.term_id IN (
                            SELECT term_id FROM source_genres
                            UNION SELECT term_id FROM source_keywords
                        )
                      UNION
                      SELECT 1 FROM film_person fp
                      WHERE fp.film_id = f.id
                        AND fp.role_type IN ('director', 'actor')
                        AND fp.person_id IN (
                            SELECT person_id FROM source_directors
                            UNION SELECT person_id FROM source_actors
                        )
                  )
            )
            SELECT
                scored.id,
                (scored.genre_score + scored.keyword_score
                 + scored.director_score + scored.actor_score
                 + scored.year_score) AS total_score,
                scored.genre_score, scored.keyword_score,
                scored.director_score, scored.actor_score, scored.year_score,
                e.primary_image_url AS img_primary,
                e.thumbnail_url AS img_thumb,
                f.release_year,
                COALESCE(et_lang.title, et_en.title, f.sort_title) AS title,
                COALESCE(et_lang.summary, et_en.summary) AS summary
            FROM scored
            JOIN film f ON f.id = scored.id
            JOIN entity e ON e.id = scored.id
            LEFT JOIN entity_translation et_lang
                ON et_lang.entity_id = scored.id
                AND et_lang.language_id = (SELECT id FROM language WHERE code = :lang)
            LEFT JOIN entity_translation et_en
                ON et_en.entity_id = scored.id
                AND et_en.language_id = (SELECT id FROM language WHERE code = 'en')
            WHERE (scored.genre_score + scored.keyword_score
                   + scored.director_score + scored.actor_score) > 0
            ORDER BY total_score DESC
            LIMIT :lim
        """)
        rows = (await self.db.execute(sql, {
            "fid": film_id, "lang": lang, "lim": limit,
        })).mappings().all()

        max_score = max((r["total_score"] for r in rows), default=1.0) or 1.0

        items = []
        for r in rows:
            reasons = []
            if r["director_score"] > 0:
                reasons.append("общий режиссёр")
            if r["actor_score"] > 0:
                reasons.append("общий актёр")
            if r["keyword_score"] > 0:
                reasons.append("общая атмосфера")
            if r["genre_score"] > 0:
                reasons.append("общий жанр")
            if r["year_score"] > 0:
                reasons.append("близкий год")

            items.append({
                "entity_id": r["id"],
                "entity_type": "film",
                "title": r["title"] or "Untitled",
                "summary": r["summary"],
                "images": {
                    "primary": r["img_primary"],
                    "thumbnail": r["img_thumb"],
                },
                "release_year": r["release_year"],
                "score": round(float(r["total_score"]) / float(max_score), 3),
                "reasons": reasons,
            })

        return {
            "items": items,
            "source_entity_id": film_id,
            "source_entity_type": "film",
            "algorithm": "content_based",
        }

    async def _for_film_semantic(
        self, film_id: int, *, lang: str, limit: int,
    ) -> dict:
        """
        Семантические рекомендации: близость векторов описаний.
        Использует pgvector с HNSW-индексом, время <50ms даже на 10000+ векторов.
        """
        sql = text("""
            WITH source_emb AS (
                SELECT embedding FROM entity_translation
                WHERE entity_id = :fid AND embedding IS NOT NULL
                ORDER BY
                    CASE WHEN language_id = (SELECT id FROM language WHERE code = :lang)
                         THEN 0 ELSE 1 END
                LIMIT 1
            )
            SELECT DISTINCT ON (et.entity_id)
                et.entity_id,
                COALESCE(et_lang.title, et.title) AS title,
                COALESCE(et_lang.summary, et.summary) AS summary,
                e.primary_image_url AS img_primary,
                e.thumbnail_url AS img_thumb,
                f.release_year,
                1 - (et.embedding <=> (SELECT embedding FROM source_emb)) AS similarity
            FROM entity_translation et
            JOIN entity e ON e.id = et.entity_id
            JOIN film f ON f.id = et.entity_id
            LEFT JOIN entity_translation et_lang
                ON et_lang.entity_id = e.id
                AND et_lang.language_id = (SELECT id FROM language WHERE code = :lang)
            WHERE et.embedding IS NOT NULL
              AND et.entity_id != :fid
              AND e.entity_type = 'film'
              AND e.status = 'published'
            ORDER BY et.entity_id, et.embedding <=> (SELECT embedding FROM source_emb)
            LIMIT 200
        """)
        rows = (await self.db.execute(sql, {
            "fid": film_id, "lang": lang,
        })).mappings().all()

        items = sorted(
            (
                {
                    "entity_id": r["entity_id"],
                    "entity_type": "film",
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
            "source_entity_id": film_id,
            "source_entity_type": "film",
            "algorithm": "semantic",
        }

    # ─── Рекомендации для персоны ───────────────────────────────
    async def for_person(
        self,
        person_id: int,
        *,
        lang: str = "ru",
        limit: int = 10,
        mode: str = "content",
    ) -> dict | None:
        """Похожие режиссёры. mode='content' или 'semantic'."""
        check = await self.db.execute(text("""
            SELECT 1 FROM person WHERE id = :id AND is_director = true
        """), {"id": person_id})
        if not check.first():
            return None

        if mode == "semantic":
            return await self._for_person_semantic(person_id, lang=lang, limit=limit)
        else:
            return await self._for_person_content(person_id, lang=lang, limit=limit)

    async def _for_person_content(
        self, person_id: int, *, lang: str, limit: int,
    ) -> dict:
        """Content-based: связи в графе + общие жанры режиссуры."""
        sql = text("""
            WITH
            source_genres AS (
                SELECT DISTINCT ex.term_id
                FROM film_person fp
                JOIN entity_taxonomy ex ON ex.entity_id = fp.film_id
                JOIN taxonomy_term tt ON tt.id = ex.term_id
                WHERE fp.person_id = :pid AND fp.role_type = 'director'
                  AND tt.term_type = 'genre'
            ),
            scored AS (
                SELECT
                    p.id,
                    5 * (
                        SELECT count(*) FROM director_influence di
                        WHERE (di.source_director_id = :pid
                                AND di.target_director_id = p.id)
                           OR (di.target_director_id = :pid
                                AND di.source_director_id = p.id)
                    ) AS graph_score,
                    LEAST(3, (
                        SELECT count(DISTINCT ex.term_id)
                        FROM film_person fp
                        JOIN entity_taxonomy ex ON ex.entity_id = fp.film_id
                        WHERE fp.person_id = p.id AND fp.role_type = 'director'
                          AND ex.term_id IN (SELECT term_id FROM source_genres)
                    )) AS genre_score
                FROM person p
                WHERE p.id != :pid AND p.is_director = true
            )
            SELECT
                scored.id,
                (scored.graph_score + scored.genre_score) AS total_score,
                scored.graph_score, scored.genre_score,
                e.primary_image_url AS img_primary,
                e.thumbnail_url AS img_thumb,
                COALESCE(et_lang.title, et_en.title, p.sort_name) AS title,
                COALESCE(et_lang.summary, et_en.summary) AS summary
            FROM scored
            JOIN person p ON p.id = scored.id
            JOIN entity e ON e.id = scored.id
            LEFT JOIN entity_translation et_lang
                ON et_lang.entity_id = scored.id
                AND et_lang.language_id = (SELECT id FROM language WHERE code = :lang)
            LEFT JOIN entity_translation et_en
                ON et_en.entity_id = scored.id
                AND et_en.language_id = (SELECT id FROM language WHERE code = 'en')
            WHERE (scored.graph_score + scored.genre_score) > 0
            ORDER BY total_score DESC
            LIMIT :lim
        """)
        rows = (await self.db.execute(sql, {
            "pid": person_id, "lang": lang, "lim": limit,
        })).mappings().all()

        max_score = max((r["total_score"] for r in rows), default=1.0) or 1.0

        items = []
        for r in rows:
            reasons = []
            if r["graph_score"] > 0:
                reasons.append("связь в графе влияний")
            if r["genre_score"] > 0:
                reasons.append("общий жанр режиссуры")

            items.append({
                "entity_id": r["id"],
                "entity_type": "person",
                "title": r["title"] or "Unknown",
                "summary": r["summary"],
                "images": {
                    "primary": r["img_primary"],
                    "thumbnail": r["img_thumb"],
                },
                "release_year": None,
                "score": round(float(r["total_score"]) / float(max_score), 3),
                "reasons": reasons,
            })

        return {
            "items": items,
            "source_entity_id": person_id,
            "source_entity_type": "person",
            "algorithm": "content_based",
        }

    async def _for_person_semantic(
        self, person_id: int, *, lang: str, limit: int,
    ) -> dict:
        """Семантические рекомендации для режиссёров через биографии."""
        sql = text("""
            WITH source_emb AS (
                SELECT embedding FROM entity_translation
                WHERE entity_id = :pid AND embedding IS NOT NULL
                ORDER BY
                    CASE WHEN language_id = (SELECT id FROM language WHERE code = :lang)
                         THEN 0 ELSE 1 END
                LIMIT 1
            )
            SELECT DISTINCT ON (et.entity_id)
                et.entity_id,
                COALESCE(et_lang.title, et.title) AS title,
                COALESCE(et_lang.summary, et.summary) AS summary,
                e.primary_image_url AS img_primary,
                e.thumbnail_url AS img_thumb,
                1 - (et.embedding <=> (SELECT embedding FROM source_emb)) AS similarity
            FROM entity_translation et
            JOIN entity e ON e.id = et.entity_id
            JOIN person p ON p.id = et.entity_id
            LEFT JOIN entity_translation et_lang
                ON et_lang.entity_id = e.id
                AND et_lang.language_id = (SELECT id FROM language WHERE code = :lang)
            WHERE et.embedding IS NOT NULL
              AND et.entity_id != :pid
              AND e.entity_type = 'person'
              AND p.is_director = true
              AND e.status = 'published'
            ORDER BY et.entity_id, et.embedding <=> (SELECT embedding FROM source_emb)
            LIMIT 200
        """)
        rows = (await self.db.execute(sql, {
            "pid": person_id, "lang": lang,
        })).mappings().all()

        items = sorted(
            (
                {
                    "entity_id": r["entity_id"],
                    "entity_type": "person",
                    "title": r["title"] or "Unknown",
                    "summary": r["summary"],
                    "images": {
                        "primary": r["img_primary"],
                        "thumbnail": r["img_thumb"],
                    },
                    "release_year": None,
                    "score": round(float(r["similarity"]), 4),
                    "reasons": [
                        f"семантическая близость биографий {round(float(r['similarity']) * 100)}%"
                    ],
                }
                for r in rows
            ),
            key=lambda x: -x["score"],
        )[:limit]

        return {
            "items": items,
            "source_entity_id": person_id,
            "source_entity_type": "person",
            "algorithm": "semantic",
        }
