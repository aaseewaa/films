from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class EntityService:
    """Получение карточек сущностей с переводами и связями."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_entity(self, entity_id: int, lang: str = "ru") -> dict | None:
        """
        Возвращает полные данные сущности по id или None.
        Автоматически определяет тип (film/person) и подгружает связи.
        """
        # 1. Базовая информация: тип и есть ли вообще такая сущность
        # ─── ИЗМЕНЕНИЕ: добавлен primary_backdrop_url ───
        base_sql = """
            SELECT e.id, e.entity_type::text AS entity_type, e.status,
                   e.primary_image_url, e.thumbnail_url,
                   e.primary_backdrop_url,
                   e.external_ids, e.extra_metadata
            FROM entity e
            WHERE e.id = :eid AND e.status = 'published'
        """
        base = (await self.db.execute(text(base_sql), {"eid": entity_id})).mappings().first()
        if not base:
            return None

        # 2. Перевод на запрошенном языке (с fallback на английский)
        translation = await self._get_translation(entity_id, lang)

        # 3. В зависимости от типа — добираем спец-данные
        if base["entity_type"] == "film":
            return await self._build_film(base, translation, lang)
        elif base["entity_type"] == "person":
            return await self._build_person(base, translation, lang)
        else:
            # studio / article / collection — пока не делаем
            return {
                "id": entity_id,
                "entity_type": base["entity_type"],
                "title": translation.get("title", "Untitled"),
                "summary": translation.get("summary"),
            }

    # ─── Перевод ────────────────────────────────────────────────
    async def _get_title_in_lang(self, entity_id: int, lang: str) -> str | None:
        sql = """
            SELECT et.title
            FROM entity_translation et
            JOIN language l ON l.id = et.language_id
            WHERE et.entity_id = :eid AND l.code = :lang
            LIMIT 1
        """
        row = (await self.db.execute(text(sql), {"eid": entity_id, "lang": lang})).first()
        return row[0] if row else None

    async def _get_translation(self, entity_id: int, lang: str) -> dict:
        """Перевод на нужном языке + fallback на любой имеющийся."""
        sql = """
            SELECT et.title, et.summary, et.description, l.code AS lang
            FROM entity_translation et
            JOIN language l ON l.id = et.language_id
            WHERE et.entity_id = :eid
            ORDER BY (l.code = :lang) DESC, (l.code = 'en') DESC
            LIMIT 1
        """
        row = (await self.db.execute(text(sql), {"eid": entity_id, "lang": lang})).mappings().first()
        return dict(row) if row else {}

    # ─── Жанры ──────────────────────────────────────────────────
    async def _get_genres(self, entity_id: int, lang: str) -> list[dict]:
        sql = """
            SELECT tt.id, tt.code, tt.term_type::text AS term_type,
                   COALESCE(ttt.name, ttt_en.name) AS name
            FROM entity_taxonomy ex
            JOIN taxonomy_term tt ON tt.id = ex.term_id
            LEFT JOIN taxonomy_term_translation ttt
                ON ttt.term_id = tt.id
                AND ttt.language_id = (SELECT id FROM language WHERE code = :lang)
            LEFT JOIN taxonomy_term_translation ttt_en
                ON ttt_en.term_id = tt.id
                AND ttt_en.language_id = (SELECT id FROM language WHERE code = 'en')
            WHERE ex.entity_id = :eid AND tt.term_type = 'genre'
            ORDER BY ex.is_primary DESC, name
        """
        result = await self.db.execute(text(sql), {"eid": entity_id, "lang": lang})
        return [dict(r) for r in result.mappings().all()]

    # ─── Кадры из фильма (галерея) ──────────────────────────────
    # ─── НОВЫЙ МЕТОД ───
    async def _get_stills(self, entity_id: int, limit: int = 10) -> list[str]:
        """
        Возвращает до N URL-ов кадров из фильма (entity_media role='still').
        Отсортированы по position (порядку как пришли из TMDB).
        """
        sql = """
            SELECT ma.url
            FROM entity_media em
            JOIN media_asset ma ON ma.id = em.media_id
            WHERE em.entity_id = :eid
              AND em.role = 'still'
            ORDER BY em.position
            LIMIT :lim
        """
        rows = (await self.db.execute(
            text(sql), {"eid": entity_id, "lim": limit}
        )).all()
        return [row[0] for row in rows]

    # ─── Карточка фильма ────────────────────────────────────────
    async def _build_film(self, base: dict, tr: dict, lang: str) -> dict:
        # Спец-поля фильма
        film_sql = """
            SELECT release_year, release_date, runtime_min, age_rating, sort_title
            FROM film WHERE id = :eid
        """
        film_row = (await self.db.execute(text(film_sql), {"eid": base["id"]})).mappings().first()
        film_data = dict(film_row) if film_row else {}

        # Крю фильма с переводами имён
        crew_sql = """
            SELECT
                p.id AS person_id,
                COALESCE(et_lang.title, et_en.title, p.sort_name) AS title,
                e.primary_image_url AS img_primary,
                e.thumbnail_url AS img_thumb,
                fp.role_type::text AS role_type,
                fp.character_name,
                fp.billing_order
            FROM film_person fp
            JOIN person p ON p.id = fp.person_id
            JOIN entity e ON e.id = p.id
            LEFT JOIN entity_translation et_lang
                ON et_lang.entity_id = p.id
                AND et_lang.language_id = (SELECT id FROM language WHERE code = :lang)
            LEFT JOIN entity_translation et_en
                ON et_en.entity_id = p.id
                AND et_en.language_id = (SELECT id FROM language WHERE code = 'en')
            WHERE fp.film_id = :eid
            ORDER BY
                CASE WHEN fp.role_type = 'director' THEN 0 ELSE 1 END,
                fp.billing_order NULLS LAST,
                fp.role_type
            LIMIT 50
        """
        crew_rows = (await self.db.execute(text(crew_sql), {"eid": base["id"], "lang": lang})).mappings().all()

        directors = []
        cast = []
        for r in crew_rows:
            person_ref = {
                "id": r["person_id"],
                "title": r["title"],
                "images": {"primary": r["img_primary"], "thumbnail": r["img_thumb"]},
                "role_type": r["role_type"],
                "character_name": r["character_name"],
                "billing_order": r["billing_order"],
            }
            if r["role_type"] == "director":
                directors.append(person_ref)
            elif r["role_type"] == "actor":
                cast.append(person_ref)

        genres = await self._get_genres(base["id"], lang)
        stills_urls = await self._get_stills(base["id"], limit=10)
        original_title = await self._get_title_in_lang(base["id"], "en")
        if original_title and original_title == tr.get("title"):
            original_title = None

        meta = base["extra_metadata"] or {}
        pc_list = meta.get("production_countries") or []
        if lang == "ru":
            country_str = ", ".join(
                c.get("name_ru") or c.get("name_en") or c.get("code", "")
                for c in pc_list if isinstance(c, dict)
            )
        else:
            country_str = ", ".join(
                c.get("name_en") or c.get("code", "")
                for c in pc_list if isinstance(c, dict)
            )
        production_countries = country_str or None

        return {
            "id": base["id"],
            "entity_type": "film",
            "title": tr.get("title", film_data.get("sort_title", "Untitled")),
            "original_title": original_title,
            "summary": tr.get("summary"),
            "description": tr.get("description"),
            "release_year": film_data.get("release_year"),
            "release_date": film_data.get("release_date"),
            "runtime_min": film_data.get("runtime_min"),
            "age_rating": film_data.get("age_rating"),
            "images": {
                "primary": base["primary_image_url"],
                "thumbnail": base["thumbnail_url"],
            },
            # ─── НОВЫЕ ПОЛЯ ───
            "backdrop_url": base["primary_backdrop_url"],
            "stills_urls": stills_urls,
            # ──────────────────
            "genres": genres,
            "production_countries": production_countries,
            "directors": directors,
            "cast": cast,
            "extra_metadata": base["extra_metadata"] or {},
            "external_ids": base["external_ids"] or {},
        }

    # ─── Карточка персоны ───────────────────────────────────────
    async def _build_person(self, base: dict, tr: dict, lang: str) -> dict:
        person_sql = """
            SELECT birth_date, death_date, birth_place, primary_profession,
                   is_director, is_actor, sort_name
            FROM person WHERE id = :eid
        """
        p_row = (await self.db.execute(text(person_sql), {"eid": base["id"]})).mappings().first()
        p_data = dict(p_row) if p_row else {}

        # Фильмография
        filmo_sql = """
            SELECT
                f.id AS film_id,
                COALESCE(et_lang.title, et_en.title, f.sort_title) AS title,
                f.release_year,
                e.primary_image_url AS img_primary,
                e.thumbnail_url AS img_thumb,
                fp.role_type::text AS role_type
            FROM film_person fp
            JOIN film f ON f.id = fp.film_id
            JOIN entity e ON e.id = f.id
            LEFT JOIN entity_translation et_lang
                ON et_lang.entity_id = f.id
                AND et_lang.language_id = (SELECT id FROM language WHERE code = :lang)
            LEFT JOIN entity_translation et_en
                ON et_en.entity_id = f.id
                AND et_en.language_id = (SELECT id FROM language WHERE code = 'en')
            WHERE fp.person_id = :eid
            ORDER BY f.release_year DESC NULLS LAST
            LIMIT 50
        """
        filmo_rows = (await self.db.execute(text(filmo_sql), {"eid": base["id"], "lang": lang})).mappings().all()
        filmography = [
            {
                "id": r["film_id"],
                "title": r["title"],
                "release_year": r["release_year"],
                "images": {"primary": r["img_primary"], "thumbnail": r["img_thumb"]},
                "role_type": r["role_type"],
            }
            for r in filmo_rows
        ]

        # Граф влияний — для всех персон, но обычно заполнено только у режиссёров
        influenced_by = await self._get_influences(base["id"], direction="incoming", lang=lang)
        influenced = await self._get_influences(base["id"], direction="outgoing", lang=lang)

        return {
            "id": base["id"],
            "entity_type": "person",
            "title": tr.get("title", p_data.get("sort_name", "Unknown")),
            "summary": tr.get("summary"),
            "description": tr.get("description"),
            "birth_date": p_data.get("birth_date"),
            "death_date": p_data.get("death_date"),
            "birth_place": p_data.get("birth_place"),
            "primary_profession": p_data.get("primary_profession"),
            "is_director": p_data.get("is_director", False),
            "is_actor": p_data.get("is_actor", False),
            "images": {
                "primary": base["primary_image_url"],
                "thumbnail": base["thumbnail_url"],
            },
            "filmography": filmography,
            "influenced_by": influenced_by,
            "influenced": influenced,
            "external_ids": base["external_ids"] or {},
        }

    # ─── Граф влияний ───────────────────────────────────────────
    async def _get_influences(
        self, person_id: int, *, direction: str, lang: str
    ) -> list[dict]:
        """
        direction='incoming' — кто повлиял на person_id (target = person_id)
        direction='outgoing' — на кого повлиял person_id (source = person_id)
        """
        if direction == "incoming":
            where_clause = "di.target_director_id = :pid"
            select_id = "di.source_director_id"
        else:
            where_clause = "di.source_director_id = :pid"
            select_id = "di.target_director_id"

        sql = f"""
            SELECT
                {select_id} AS person_id,
                COALESCE(et_lang.title, et_en.title, p.sort_name) AS title,
                e.primary_image_url AS img_primary,
                e.thumbnail_url AS img_thumb,
                di.weight,
                di.confidence,
                di.relation_note
            FROM director_influence di
            JOIN person p ON p.id = {select_id}
            JOIN entity e ON e.id = p.id
            LEFT JOIN entity_translation et_lang
                ON et_lang.entity_id = p.id
                AND et_lang.language_id = (SELECT id FROM language WHERE code = :lang)
            LEFT JOIN entity_translation et_en
                ON et_en.entity_id = p.id
                AND et_en.language_id = (SELECT id FROM language WHERE code = 'en')
            WHERE {where_clause}
            ORDER BY di.confidence DESC, di.weight DESC
            LIMIT 50
        """
        rows = (await self.db.execute(text(sql), {"pid": person_id, "lang": lang})).mappings().all()
        return [
            {
                "person_id": r["person_id"],
                "title": r["title"],
                "images": {"primary": r["img_primary"], "thumbnail": r["img_thumb"]},
                "weight": r["weight"],
                "confidence": float(r["confidence"]),
                "relation_note": r["relation_note"],
            }
            for r in rows
        ]
