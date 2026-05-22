"""Фильмография и метаданные персон для эмбеддингов."""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def load_person_context_for_batch(
    db: AsyncSession,
    person_ids: list[int],
    lang_code: str,
) -> dict[int, dict]:
    """
    Возвращает {person_id: {is_director, is_actor, birth_place, filmography_lines}}.
    """
    if not person_ids:
        return {}

    meta_rows = (
        await db.execute(
            text("""
                SELECT p.id, p.is_director, p.is_actor, p.birth_place
                FROM person p
                WHERE p.id = ANY(:ids)
            """),
            {"ids": person_ids},
        )
    ).mappings().all()

    film_rows = (
        await db.execute(
            text("""
                SELECT person_id, role_type, film_title, release_year, genres
                FROM (
                    SELECT
                        fp.person_id,
                        fp.role_type::text AS role_type,
                        et.title AS film_title,
                        f.release_year,
                        COALESCE((
                            SELECT string_agg(ttt.name, ', ' ORDER BY ttt.name)
                            FROM entity_taxonomy ext
                            JOIN taxonomy_term_translation ttt ON ttt.term_id = ext.term_id
                            JOIN language l2 ON l2.id = ttt.language_id AND l2.code = :lang
                            WHERE ext.entity_id = fp.film_id
                        ), '') AS genres,
                        ROW_NUMBER() OVER (
                            PARTITION BY fp.person_id
                            ORDER BY f.release_year DESC NULLS LAST, et.title
                        ) AS rn
                    FROM film_person fp
                    JOIN film f ON f.id = fp.film_id
                    JOIN entity e ON e.id = f.id AND e.status = 'published'
                    JOIN entity_translation et ON et.entity_id = f.id
                    JOIN language l ON l.id = et.language_id AND l.code = :lang
                    WHERE fp.person_id = ANY(:ids)
                ) ranked
                WHERE rn <= 8
            """),
            {"ids": person_ids, "lang": lang_code},
        )
    ).mappings().all()

    out: dict[int, dict] = {
        int(r["id"]): {
            "is_director": bool(r["is_director"]),
            "is_actor": bool(r["is_actor"]),
            "birth_place": r["birth_place"],
            "filmography_lines": [],
        }
        for r in meta_rows
    }

    role_ru = {"director": "реж.", "actor": "акт.", "writer": "сцен.", "producer": "прод."}

    for r in film_rows:
        pid = int(r["person_id"])
        if pid not in out:
            continue
        title = (r["film_title"] or "").strip()
        if not title:
            continue
        year = f" ({r['release_year']})" if r["release_year"] else ""
        role = role_ru.get(r["role_type"] or "", r["role_type"] or "")
        genres = (r["genres"] or "").strip()
        line = f"{title}{year}"
        if role:
            line = f"{line} [{role}]"
        if genres:
            line = f"{line} — {genres}"
        out[pid]["filmography_lines"].append(line)

    return out
