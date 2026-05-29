from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.film_media import film_media_kind
from app.services.catalog_service import ANIMATION_GENRE_CODE


class EntityService:
    """Получение карточек сущностей с переводами и связями."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_entity(self, entity_id: int, lang: str = "ru") -> dict | None:
        """
        Возвращает полные данные сущности по id или None.
        Автоматически определяет тип (film/person) и подгружает связи.
        """
        base_sql = """
            SELECT e.id, e.entity_type::text AS entity_type, e.status,
                   e.primary_image_url, e.thumbnail_url,
                   e.primary_backdrop_url,
                   e.external_ids, e.extra_metadata
            FROM entity e
            WHERE e.id = :eid
              AND (
                e.status = 'published'
                OR (
                  e.status = 'draft'
                  AND e.entity_type = 'film'
                  AND EXISTS (
                    SELECT 1 FROM entity_taxonomy ex_anim
                    JOIN taxonomy_term tt_anim ON tt_anim.id = ex_anim.term_id
                    WHERE ex_anim.entity_id = e.id
                      AND tt_anim.code = :animation_genre
                      AND tt_anim.term_type = 'genre'
                  )
                )
              )
        """
        base = (
            await self.db.execute(
                text(base_sql),
                {"eid": entity_id, "animation_genre": ANIMATION_GENRE_CODE},
            )
        ).mappings().first()
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
    async def _get_person_crew_stats(self, person_ids: list[int]) -> dict[int, dict]:
        """
        Счётчики работ в каталоге (film_person) и имя на EN.
        Сериалы отдельно не ведём — series_count всегда 0.
        """
        if not person_ids:
            return {}

        out: dict[int, dict] = {
            pid: {
                "title_en": None,
                "directed_count": 0,
                "acted_count": 0,
                "series_count": 0,
            }
            for pid in person_ids
        }

        en_rows = (
            await self.db.execute(
                text("""
                    SELECT et.entity_id, et.title
                    FROM entity_translation et
                    JOIN language l ON l.id = et.language_id AND l.code = 'en'
                    WHERE et.entity_id = ANY(:ids)
                """),
                {"ids": person_ids},
            )
        ).mappings().all()
        for r in en_rows:
            out[r["entity_id"]]["title_en"] = r["title"]

        count_rows = (
            await self.db.execute(
                text("""
                    SELECT fp.person_id, fp.role_type::text AS role_type,
                           COUNT(DISTINCT fp.film_id) AS cnt
                    FROM film_person fp
                    JOIN entity e ON e.id = fp.film_id AND e.status = 'published'
                    WHERE fp.person_id = ANY(:ids)
                    GROUP BY fp.person_id, fp.role_type
                """),
                {"ids": person_ids},
            )
        ).mappings().all()
        for r in count_rows:
            pid = r["person_id"]
            if r["role_type"] == "director":
                out[pid]["directed_count"] = int(r["cnt"])
            elif r["role_type"] == "actor":
                out[pid]["acted_count"] = int(r["cnt"])

        return out

    def _apply_person_stats(self, person_ref: dict, stats: dict[int, dict], lang_title: str) -> None:
        s = stats.get(person_ref["id"], {})
        en = (s.get("title_en") or "").strip()
        if en and en != lang_title:
            person_ref["title_en"] = en
        directed = s.get("directed_count") or 0
        acted = s.get("acted_count") or 0
        if directed > 0:
            person_ref["directed_count"] = directed
        if acted > 0:
            person_ref["acted_count"] = acted
        series = s.get("series_count") or 0
        if series > 0:
            person_ref["series_count"] = series

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

        person_ids = list({int(r["person_id"]) for r in crew_rows})
        crew_stats = await self._get_person_crew_stats(person_ids)

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
            self._apply_person_stats(person_ref, crew_stats, r["title"])
            if r["role_type"] == "director":
                directors.append(person_ref)
            elif r["role_type"] == "actor":
                cast.append(person_ref)

        genres = await self._get_genres(base["id"], lang)
        genre_titles = [g["name"] for g in genres]
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
            "backdrop_url": base["primary_backdrop_url"],
            "stills_urls": stills_urls,
            "media_kind": film_media_kind(genre_titles, meta),
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

        work_role = "director" if p_data.get("is_director") else "actor"
        filmography = await self._get_person_filmography(
            base["id"], lang=lang, work_role=work_role,
        )

        # Граф влияний — для всех персон, но обычно заполнено только у режиссёров
        influenced_by = await self._get_influences(base["id"], direction="incoming", lang=lang)
        influenced = await self._get_influences(base["id"], direction="outgoing", lang=lang)
        awards = await self._get_person_awards(base["id"], lang=lang)

        ru_title = tr.get("title", p_data.get("sort_name", "Unknown"))
        stats = await self._get_person_crew_stats([base["id"]])
        s = stats.get(base["id"], {})
        title_en = (s.get("title_en") or "").strip() or (p_data.get("sort_name") or "").strip()
        if title_en and title_en == ru_title:
            title_en = None

        roles_rows = (
            await self.db.execute(
                text("""
                    SELECT fp.role_type::text AS role_type
                    FROM film_person fp
                    JOIN entity e ON e.id = fp.film_id AND e.status = 'published'
                    WHERE fp.person_id = :eid
                    GROUP BY fp.role_type
                """),
                {"eid": base["id"]},
            )
        ).mappings().all()
        crew_roles = [r["role_type"] for r in roles_rows]

        directed = s.get("directed_count") or 0
        acted = s.get("acted_count") or 0

        return {
            "id": base["id"],
            "entity_type": "person",
            "title": ru_title,
            "title_en": title_en,
            "summary": tr.get("summary"),
            "description": tr.get("description"),
            "birth_date": p_data.get("birth_date"),
            "death_date": p_data.get("death_date"),
            "birth_place": p_data.get("birth_place"),
            "primary_profession": p_data.get("primary_profession"),
            "is_director": p_data.get("is_director", False),
            "is_actor": p_data.get("is_actor", False),
            "directed_count": directed if directed > 0 else None,
            "acted_count": acted if acted > 0 else None,
            "series_count": None,
            "crew_roles": crew_roles,
            "images": {
                "primary": base["primary_image_url"],
                "thumbnail": base["thumbnail_url"],
            },
            "filmography": filmography,
            "influenced_by": influenced_by,
            "influenced": influenced,
            "awards": awards,
            "external_ids": base["external_ids"] or {},
        }

    async def _get_person_filmography(
        self,
        person_id: int,
        *,
        lang: str,
        work_role: str,
    ) -> list[dict]:
        """Фильмы персоны в роли режиссёра или актёра (список для страницы)."""
        sql = text("""
            SELECT
                f.id AS film_id,
                COALESCE(et_lang.title, et_en.title, f.sort_title) AS title,
                et_en.title AS original_title,
                f.release_year,
                e.primary_image_url AS img_primary,
                e.thumbnail_url AS img_thumb,
                fp.role_type::text AS role_type,
                e.extra_metadata,
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
                         LIMIT 4
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
            FROM film_person fp
            JOIN film f ON f.id = fp.film_id
            JOIN entity e ON e.id = f.id AND e.status = 'published'
            LEFT JOIN entity_translation et_lang
                ON et_lang.entity_id = f.id
                AND et_lang.language_id = (SELECT id FROM language WHERE code = :lang)
            LEFT JOIN entity_translation et_en
                ON et_en.entity_id = f.id
                AND et_en.language_id = (SELECT id FROM language WHERE code = 'en')
            WHERE fp.person_id = :eid
              AND fp.role_type = CAST(:work_role AS film_person_role)
            ORDER BY f.release_year DESC NULLS LAST, title
            LIMIT 80
        """)
        rows = (
            await self.db.execute(
                sql, {"eid": person_id, "lang": lang, "work_role": work_role},
            )
        ).mappings().all()

        items = []
        for r in rows:
            title = r["title"] or "Untitled"
            orig = (r["original_title"] or "").strip() or None
            if orig and orig.lower() == (title or "").lower():
                orig = None
            genres = list(r["genres"] or [])
            extra = r["extra_metadata"] if isinstance(r["extra_metadata"], dict) else {}
            items.append(
                {
                    "id": r["film_id"],
                    "title": title,
                    "original_title": orig,
                    "release_year": r["release_year"],
                    "images": {
                        "primary": r["img_primary"],
                        "thumbnail": r["img_thumb"],
                    },
                    "role_type": r["role_type"],
                    "media_kind": film_media_kind(genres, extra),
                    "genres": genres,
                    "country": r["country"],
                    "director": r["director"],
                    "actors": list(r["actors"] or []),
                }
            )
        return items

    async def _get_person_awards(self, person_id: int, *, lang: str) -> dict | None:
        """
        Номинации и победы персоны из award_nomination (person_id).
        Возвращает None, если записей нет.
        """
        sql = """
            SELECT
                n.status::text AS status,
                c.year,
                COALESCE(at_lang.name, at_en.name, a.code) AS award_name,
                COALESCE(act_lang.name, act_en.name, ac.code) AS category_name,
                COALESCE(et_lang.title, et_en.title) AS film_title
            FROM award_nomination n
            JOIN award_ceremony c ON c.id = n.ceremony_id
            JOIN award a ON a.id = c.award_id
            JOIN award_category ac ON ac.id = n.category_id
            LEFT JOIN award_translation at_lang
                ON at_lang.award_id = a.id
                AND at_lang.language_id = (SELECT id FROM language WHERE code = :lang)
            LEFT JOIN award_translation at_en
                ON at_en.award_id = a.id
                AND at_en.language_id = (SELECT id FROM language WHERE code = 'en')
            LEFT JOIN award_category_translation act_lang
                ON act_lang.category_id = ac.id
                AND act_lang.language_id = (SELECT id FROM language WHERE code = :lang)
            LEFT JOIN award_category_translation act_en
                ON act_en.category_id = ac.id
                AND act_en.language_id = (SELECT id FROM language WHERE code = 'en')
            LEFT JOIN entity_translation et_lang
                ON et_lang.entity_id = n.entity_id
                AND et_lang.language_id = (SELECT id FROM language WHERE code = :lang)
            LEFT JOIN entity_translation et_en
                ON et_en.entity_id = n.entity_id
                AND et_en.language_id = (SELECT id FROM language WHERE code = 'en')
            WHERE n.person_id = :pid
            ORDER BY c.year DESC, (n.status = 'won') DESC, award_name
            LIMIT 40
        """
        rows = (
            await self.db.execute(text(sql), {"pid": person_id, "lang": lang})
        ).mappings().all()
        if not rows:
            return None

        items = []
        wins = 0
        nominated_only = 0
        for r in rows:
            status = r["status"] if r["status"] in ("won", "nominated") else "nominated"
            if status == "won":
                wins += 1
            else:
                nominated_only += 1
            items.append(
                {
                    "status": status,
                    "year": int(r["year"]),
                    "award_name": r["award_name"] or "—",
                    "category_name": r["category_name"],
                    "film_title": r["film_title"],
                }
            )

        return {
            "wins_count": wins,
            "nominations_count": nominated_only,
            "items": items,
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
