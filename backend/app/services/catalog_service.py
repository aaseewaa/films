"""
Сервис каталогов: списки фильмов, персон, жанров, popular.

Принципы:
  - Все запросы возвращают переводы на запрошенном языке с fallback на английский
  - Пагинация через limit/offset
  - Фильтры опциональные, безопасные (через параметры, без склейки строк)
  - Сортировка через белый список колонок (защита от SQL-инъекций)
"""
from __future__ import annotations

from typing import Literal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


# Белые списки сортировки — защита от SQL-инъекций.
# Любые значения вне списка автоматически отбрасываются.
FILM_SORT_COLUMNS = {
    "popularity": "(e.extra_metadata->>'popularity')::float DESC NULLS LAST",
    "vote_average": "(e.extra_metadata->>'vote_average')::float DESC NULLS LAST",
    "year": "f.release_year DESC NULLS LAST",
    "year_asc": "f.release_year ASC NULLS LAST",
    "title": "COALESCE(et_lang.title, et_en.title) ASC NULLS LAST",
}

PERSON_SORT_COLUMNS = {
    "influences": "influences_count",
    "name": "et.title",
    "birth_year": "EXTRACT(YEAR FROM p.birth_date)",
}


class CatalogService:
    """Каталоги: фильмы, персоны, жанры, popular."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ─── Фильмы с фильтрами ─────────────────────────────────────
    async def list_films(
        self,
        *,
        lang: str = "ru",
        genre: str | None = None,
        country: str | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
        sort_by: str = "popularity",
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        """Каталог фильмов с фильтрами по жанру, году, сортировкой."""

        # Безопасная сортировка через белый список
        sort_col = FILM_SORT_COLUMNS.get(sort_by, FILM_SORT_COLUMNS["popularity"])

        # Базовый WHERE одинаков для COUNT и SELECT — выносим в переменную
        where_parts = ["e.entity_type = 'film'", "e.status = 'published'"]
        params: dict = {"lang": lang}

        if year_from is not None:
            where_parts.append("f.release_year >= :year_from")
            params["year_from"] = year_from
        if year_to is not None:
            where_parts.append("f.release_year <= :year_to")
            params["year_to"] = year_to
        if genre:
            where_parts.append("""
                EXISTS (
                    SELECT 1 FROM entity_taxonomy ex
                    JOIN taxonomy_term tt ON tt.id = ex.term_id
                    WHERE ex.entity_id = e.id AND tt.code = :genre
                      AND tt.term_type = 'genre'
                )
            """)
            params["genre"] = genre
        if country:
            where_parts.append("""
                EXISTS (
                    SELECT 1
                    FROM jsonb_array_elements(
                        COALESCE(e.extra_metadata->'production_countries', '[]'::jsonb)
                    ) pc
                    WHERE pc->>'code' = :country
                )
            """)
            params["country"] = country

        where_sql = " AND ".join(where_parts)

        # COUNT для пагинации
        count_sql = f"""
            SELECT count(DISTINCT e.id)
            FROM entity e
            JOIN film f ON f.id = e.id
            WHERE {where_sql}
        """
        total = (await self.db.execute(text(count_sql), params)).scalar_one()

        # Основной запрос с переводами и жанрами
        # Жанры собираем через array_agg в подзапросе чтобы не дублировать строки
        params["limit"] = limit
        params["offset"] = offset

        list_sql = f"""
            SELECT
                e.id,
                COALESCE(et_lang.title, et_en.title, f.sort_title) AS title,
                et_en.title AS original_title,
                COALESCE(et_lang.summary, et_en.summary) AS summary,
                f.release_year,
                f.runtime_min,
                e.primary_image_url AS img_primary,
                e.thumbnail_url AS img_thumb,
                (e.extra_metadata->>'vote_average')::float AS vote_average,
                (e.extra_metadata->>'popularity')::float AS popularity,
                COALESCE(
                    (SELECT array_agg(
                        COALESCE(ttt.name, ttt_en.name)
                        ORDER BY ex.is_primary DESC
                     )
                     FROM entity_taxonomy ex
                     JOIN taxonomy_term tt ON tt.id = ex.term_id
                     LEFT JOIN taxonomy_term_translation ttt
                         ON ttt.term_id = tt.id
                         AND ttt.language_id = (SELECT id FROM language WHERE code = :lang)
                     LEFT JOIN taxonomy_term_translation ttt_en
                         ON ttt_en.term_id = tt.id
                         AND ttt_en.language_id = (SELECT id FROM language WHERE code = 'en')
                     WHERE ex.entity_id = e.id AND tt.term_type = 'genre'
                    ),
                    ARRAY[]::text[]
                ) AS genres,
                (
                    SELECT COALESCE(et_d.title, et_d_en.title)
                    FROM film_person fp_d
                    JOIN person p_d ON p_d.id = fp_d.person_id
                    LEFT JOIN entity_translation et_d
                        ON et_d.entity_id = p_d.id
                        AND et_d.language_id = (SELECT id FROM language WHERE code = :lang)
                    LEFT JOIN entity_translation et_d_en
                        ON et_d_en.entity_id = p_d.id
                        AND et_d_en.language_id = (SELECT id FROM language WHERE code = 'en')
                    WHERE fp_d.film_id = f.id AND fp_d.role_type = 'director'
                    ORDER BY fp_d.is_primary DESC NULLS LAST
                    LIMIT 1
                ) AS director,
                COALESCE(
                    (SELECT array_agg(names.n ORDER BY names.bo NULLS LAST)
                     FROM (
                         SELECT COALESCE(et_a.title, et_a_en.title) AS n,
                                fp_a.billing_order AS bo
                         FROM film_person fp_a
                         JOIN person p_a ON p_a.id = fp_a.person_id
                         LEFT JOIN entity_translation et_a
                             ON et_a.entity_id = p_a.id
                             AND et_a.language_id = (SELECT id FROM language WHERE code = :lang)
                         LEFT JOIN entity_translation et_a_en
                             ON et_a_en.entity_id = p_a.id
                             AND et_a_en.language_id = (SELECT id FROM language WHERE code = 'en')
                         WHERE fp_a.film_id = f.id AND fp_a.role_type = 'actor'
                         ORDER BY fp_a.billing_order NULLS LAST, et_a.title
                         LIMIT 3
                     ) names),
                    ARRAY[]::text[]
                ) AS actors,
                (
                    SELECT string_agg(DISTINCT names.n, ', ')
                    FROM (
                        SELECT CASE
                            WHEN :lang = 'ru' THEN COALESCE(pc->>'name_ru', pc->>'name_en')
                            ELSE COALESCE(pc->>'name_en', pc->>'name_ru')
                        END AS n
                        FROM jsonb_array_elements(
                            COALESCE(e.extra_metadata->'production_countries', '[]'::jsonb)
                        ) pc
                    ) names
                    WHERE names.n IS NOT NULL AND names.n <> ''
                ) AS country
            FROM entity e
            JOIN film f ON f.id = e.id
            LEFT JOIN entity_translation et_lang
                ON et_lang.entity_id = e.id
                AND et_lang.language_id = (SELECT id FROM language WHERE code = :lang)
            LEFT JOIN entity_translation et_en
                ON et_en.entity_id = e.id
                AND et_en.language_id = (SELECT id FROM language WHERE code = 'en')
            WHERE {where_sql}
            ORDER BY {sort_col}
            LIMIT :limit OFFSET :offset
        """

        rows = (await self.db.execute(text(list_sql), params)).mappings().all()

        items = [self._row_to_film_card(r) for r in rows]

        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    @staticmethod
    def _row_to_film_card(row) -> dict:
        return {
            "id": row["id"],
            "title": row["title"] or "Untitled",
            "original_title": row["original_title"],
            "summary": row["summary"],
            "release_year": row["release_year"],
            "runtime_min": row["runtime_min"],
            "images": {
                "primary": row["img_primary"],
                "thumbnail": row["img_thumb"],
            },
            "genres": list(row["genres"]) if row["genres"] else [],
            "director": row["director"],
            "actors": list(row["actors"]) if row["actors"] else [],
            "country": row["country"],
            "vote_average": row["vote_average"],
            "popularity": row["popularity"],
        }

    # ─── Персоны с фильтрами ────────────────────────────────────
    async def list_persons(
        self,
        *,
        lang: str = "ru",
        is_director: bool | None = None,
        is_actor: bool | None = None,
        sort_by: str = "influences",
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        """Каталог персон с фильтрами."""

        sort_col = PERSON_SORT_COLUMNS.get(sort_by, PERSON_SORT_COLUMNS["influences"])

        where_parts = ["e.entity_type = 'person'", "e.status = 'published'"]
        params: dict = {"lang": lang}

        if is_director is not None:
            where_parts.append("p.is_director = :is_director")
            params["is_director"] = is_director
        if is_actor is not None:
            where_parts.append("p.is_actor = :is_actor")
            params["is_actor"] = is_actor

        where_sql = " AND ".join(where_parts)

        count_sql = f"""
            SELECT count(DISTINCT e.id)
            FROM entity e
            JOIN person p ON p.id = e.id
            WHERE {where_sql}
        """
        total = (await self.db.execute(text(count_sql), params)).scalar_one()

        params["limit"] = limit
        params["offset"] = offset

        list_sql = f"""
            SELECT
                e.id,
                COALESCE(et_lang.title, et_en.title, p.sort_name) AS title,
                COALESCE(et_lang.summary, et_en.summary) AS summary,
                e.primary_image_url AS img_primary,
                e.thumbnail_url AS img_thumb,
                p.is_director,
                p.is_actor,
                p.primary_profession::text AS primary_profession,
                EXTRACT(YEAR FROM p.birth_date)::int AS birth_year,
                COALESCE((
                    SELECT count(*) FROM director_influence di
                    WHERE di.source_director_id = e.id
                ), 0) AS influences_count
            FROM entity e
            JOIN person p ON p.id = e.id
            LEFT JOIN entity_translation et_lang
                ON et_lang.entity_id = e.id
                AND et_lang.language_id = (SELECT id FROM language WHERE code = :lang)
            LEFT JOIN entity_translation et_en
                ON et_en.entity_id = e.id
                AND et_en.language_id = (SELECT id FROM language WHERE code = 'en')
            WHERE {where_sql}
            ORDER BY {sort_col} DESC NULLS LAST
            LIMIT :limit OFFSET :offset
        """

        rows = (await self.db.execute(text(list_sql), params)).mappings().all()

        items = [
            {
                "id": r["id"],
                "title": r["title"] or "Unknown",
                "summary": r["summary"],
                "images": {"primary": r["img_primary"], "thumbnail": r["img_thumb"]},
                "is_director": r["is_director"],
                "is_actor": r["is_actor"],
                "primary_profession": r["primary_profession"],
                "birth_year": r["birth_year"],
                "influences_count": r["influences_count"],
            }
            for r in rows
        ]

        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    # ─── Страны производства (из extra_metadata фильмов) ─────────
    async def list_production_countries(self, lang: str = "ru") -> list[dict]:
        """Страны, встречающиеся в production_countries, с числом фильмов."""

        name_col = "name_ru" if lang == "ru" else "name_en"
        sql = f"""
            SELECT
                pc->>'code' AS code,
                COALESCE(max(pc->>'{name_col}'), max(pc->>'name_en'), pc->>'code') AS name,
                count(DISTINCT e.id)::int AS films_count
            FROM entity e
            JOIN film f ON f.id = e.id
            CROSS JOIN LATERAL jsonb_array_elements(
                COALESCE(e.extra_metadata->'production_countries', '[]'::jsonb)
            ) pc
            WHERE e.entity_type = 'film'
              AND e.status = 'published'
              AND pc->>'code' IS NOT NULL
            GROUP BY pc->>'code'
            HAVING count(DISTINCT e.id) > 0
            ORDER BY films_count DESC, name
        """
        rows = (await self.db.execute(text(sql))).mappings().all()
        return [
            {"id": i + 1, "code": r["code"], "name": r["name"], "films_count": r["films_count"]}
            for i, r in enumerate(rows)
        ]

    # ─── Жанры ──────────────────────────────────────────────────
    async def list_genres(self, lang: str = "ru") -> list[dict]:
        """Все жанры с переводом и количеством фильмов."""

        sql = """
            SELECT
                tt.id,
                tt.code,
                COALESCE(ttt.name, ttt_en.name, tt.code) AS name,
                count(ex.entity_id)::int AS films_count
            FROM taxonomy_term tt
            LEFT JOIN taxonomy_term_translation ttt
                ON ttt.term_id = tt.id
                AND ttt.language_id = (SELECT id FROM language WHERE code = :lang)
            LEFT JOIN taxonomy_term_translation ttt_en
                ON ttt_en.term_id = tt.id
                AND ttt_en.language_id = (SELECT id FROM language WHERE code = 'en')
            LEFT JOIN entity_taxonomy ex ON ex.term_id = tt.id
            WHERE tt.term_type = 'genre'
            GROUP BY tt.id, tt.code, ttt.name, ttt_en.name
            ORDER BY films_count DESC
        """
        rows = (await self.db.execute(text(sql), {"lang": lang})).mappings().all()
        return [
            {
                "id": r["id"],
                "code": r["code"],
                "name": r["name"],
                "films_count": r["films_count"],
            }
            for r in rows
        ]

    # ─── Главная страница (popular) ─────────────────────────────
    async def popular(self, lang: str = "ru", limit: int = 12) -> dict:
        """
        Подборки для главной страницы:
          - топ по рейтингу TMDB (классика)
          - топ по популярности (хиты)
          - топ влиятельных режиссёров (по числу связей в графе)
        """
        # Используем уже готовые методы для согласованности форматов
        top_rated = await self.list_films(
            lang=lang, sort_by="vote_average", limit=limit, offset=0
        )
        popular = await self.list_films(
            lang=lang, sort_by="popularity", limit=limit, offset=0
        )
        directors = await self.list_persons(
            lang=lang, is_director=True, sort_by="influences", limit=limit, offset=0
        )

        return {
            "top_rated_films": top_rated["items"],
            "popular_films": popular["items"],
            "influential_directors": directors["items"],
        }
