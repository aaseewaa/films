"""
Сервис рекомендаций (content-based).

Алгоритм для фильма:
  - +3 балла за общего режиссёра
  - +2 балла за общего актёра
  - +1 балл за общий жанр
  - +0.5 балла за близкий год (±5 лет)
  - сортировка по сумме баллов

Для персоны:
  - +5 баллов за прямую связь в графе влияний
  - +2 балла за общий жанр режиссуры (через film_person + entity_taxonomy)
  - +1 балл за похожий период активности

Это классический content-based подход. Преимущества:
  - не нужны другие пользователи (cold start не страшен)
  - объяснимо: можем сказать "потому что общий режиссёр"
  - быстро: всё считается одним SQL
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


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
    ) -> dict | None:
        """
        Похожие фильмы по контенту.

        Используется в карточке фильма: блок 'Похожее'.
        """
        # Проверка что фильм существует
        check = await self.db.execute(text("""
            SELECT 1 FROM film WHERE id = :id
        """), {"id": film_id})
        if not check.first():
            return None

        # Главный SQL: считаем score через сумму взвешенных совпадений
        # Используем подзапросы вместо JOIN для ясности
        sql = text("""
            WITH
            -- Жанры исходного фильма
            source_genres AS (
                SELECT term_id FROM entity_taxonomy
                WHERE entity_id = :fid
                  AND term_id IN (SELECT id FROM taxonomy_term WHERE term_type = 'genre')
            ),
            -- Режиссёры
            source_directors AS (
                SELECT person_id FROM film_person
                WHERE film_id = :fid AND role_type = 'director'
            ),
            -- Топ-5 актёров
            source_actors AS (
                SELECT person_id FROM film_person
                WHERE film_id = :fid AND role_type = 'actor'
                ORDER BY billing_order NULLS LAST
                LIMIT 5
            ),
            -- Год выпуска исходного
            source_year AS (
                SELECT release_year FROM film WHERE id = :fid
            ),
            -- Кандидаты со score
            scored AS (
                SELECT
                    f.id,
                    -- Общие жанры (по 1 за каждый, но капируем 3)
                    LEAST(3, (
                        SELECT count(*) FROM entity_taxonomy ex
                        WHERE ex.entity_id = f.id
                          AND ex.term_id IN (SELECT term_id FROM source_genres)
                    )) AS genre_score,
                    -- Общие режиссёры (по 3)
                    3 * (
                        SELECT count(*) FROM film_person fp
                        WHERE fp.film_id = f.id AND fp.role_type = 'director'
                          AND fp.person_id IN (SELECT person_id FROM source_directors)
                    ) AS director_score,
                    -- Общие актёры (по 2)
                    LEAST(6, 2 * (
                        SELECT count(*) FROM film_person fp
                        WHERE fp.film_id = f.id AND fp.role_type = 'actor'
                          AND fp.person_id IN (SELECT person_id FROM source_actors)
                    )) AS actor_score,
                    -- Близкий год (±5 = +0.5)
                    CASE
                        WHEN abs(f.release_year - (SELECT release_year FROM source_year)) <= 5
                        THEN 0.5 ELSE 0
                    END AS year_score
                FROM film f
                WHERE f.id != :fid
                  AND EXISTS (
                      -- Должно быть ХОТЯ БЫ ОДНО общее: жанр/режиссёр/актёр
                      SELECT 1 FROM entity_taxonomy ex
                      WHERE ex.entity_id = f.id
                        AND ex.term_id IN (SELECT term_id FROM source_genres)
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
                (scored.genre_score + scored.director_score
                 + scored.actor_score + scored.year_score) AS total_score,
                scored.genre_score, scored.director_score,
                scored.actor_score, scored.year_score,
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
            WHERE (scored.genre_score + scored.director_score
                   + scored.actor_score) > 0
            ORDER BY total_score DESC
            LIMIT :lim
        """)
        rows = (await self.db.execute(sql, {
            "fid": film_id, "lang": lang, "lim": limit,
        })).mappings().all()

        # Максимальный score для нормализации
        max_score = max((r["total_score"] for r in rows), default=1.0) or 1.0

        items = []
        for r in rows:
            reasons = []
            if r["director_score"] > 0:
                reasons.append(f"общий режиссёр")
            if r["actor_score"] > 0:
                reasons.append(f"общий актёр")
            if r["genre_score"] > 0:
                reasons.append(f"общий жанр")
            if r["year_score"] > 0:
                reasons.append(f"близкий год")

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

    # ─── Рекомендации для персоны (режиссёра) ───────────────────
    async def for_person(
        self,
        person_id: int,
        *,
        lang: str = "ru",
        limit: int = 10,
    ) -> dict | None:
        """
        Похожие режиссёры.

        Используется в карточке персоны: блок 'Похожие режиссёры'.
        Учитывает: связи в графе влияний + общие жанры режиссуры.
        """
        check = await self.db.execute(text("""
            SELECT 1 FROM person WHERE id = :id AND is_director = true
        """), {"id": person_id})
        if not check.first():
            return None

        sql = text("""
            WITH
            -- Жанры в которых работал исходный режиссёр
            source_genres AS (
                SELECT DISTINCT ex.term_id
                FROM film_person fp
                JOIN entity_taxonomy ex ON ex.entity_id = fp.film_id
                JOIN taxonomy_term tt ON tt.id = ex.term_id
                WHERE fp.person_id = :pid AND fp.role_type = 'director'
                  AND tt.term_type = 'genre'
            ),
            -- Кандидаты со score
            scored AS (
                SELECT
                    p.id,
                    -- Прямые связи в графе (+5 за каждое направление)
                    5 * (
                        SELECT count(*) FROM director_influence di
                        WHERE (di.source_director_id = :pid
                                AND di.target_director_id = p.id)
                           OR (di.target_director_id = :pid
                                AND di.source_director_id = p.id)
                    ) AS graph_score,
                    -- Общие жанры режиссуры (по 1, кап 3)
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
                scored.graph_score,
                scored.genre_score,
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
            "algorithm": "hybrid" if any(i.get("reasons") and "графе" in i["reasons"][0] for i in items) else "content_based",
        }
