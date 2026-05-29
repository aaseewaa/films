"""
Радиальная карточка графа влияний для главной страницы.

Кольцо 1 — «учителя» центра: source → target, где target = центр.
Кольцо 2 — учителя каждого узла кольца 1 (веер вокруг B-узла на фронте).

GET /api/graph/director/{id}/radial?top_n=4&ring2_n=3
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

# Портрет режиссёра или постер его последнего фильма (для графа без headshot в TMDB).
_PERSON_IMAGE_SQL = """
    COALESCE(
        NULLIF(trim(e.primary_image_url), ''),
        (
            SELECT fe.primary_image_url
            FROM film_person fp
            JOIN entity fe ON fe.id = fp.film_id
            JOIN film f ON f.id = fp.film_id
            WHERE fp.person_id = p.id
              AND fp.role_type = 'director'
              AND fe.primary_image_url IS NOT NULL
              AND trim(fe.primary_image_url) <> ''
            ORDER BY f.release_year DESC NULLS LAST
            LIMIT 1
        )
    )
"""


class RadialGraphService:
    """Сервис для радиальной карточки графа влияний."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_radial(
        self,
        center_id: int,
        *,
        top_n: int = 4,
        ring2_n: int = 3,
        lang: str = "ru",
    ) -> Optional[dict]:
        center = await self._get_director(center_id, lang)
        if not center:
            return None

        ring1 = await self._get_influencers(center_id, top_n=top_n, lang=lang)
        ring1_ids = [r["id"] for r in ring1]
        ring2_map = await self._get_influencers_batch(
            ring1_ids, top_n=ring2_n, lang=lang,
        )

        ring1_payload = [
            {
                **node,
                "ring2": ring2_map.get(node["id"], []),
            }
            for node in ring1
        ]

        return {
            "center": center,
            "ring1": ring1_payload,
            # обратная совместимость (без вложенного ring2)
            "neighbors": [
                {k: v for k, v in node.items() if k != "ring2"}
                for node in ring1_payload
            ],
            "ring1_count": len(ring1),
            "ring2_per_node": ring2_n,
            "top_n_requested": top_n,
        }

    async def _get_director(self, person_id: int, lang: str) -> Optional[dict]:
        row = (
            await self.db.execute(
                text(f"""
                    SELECT p.id,
                           COALESCE(et.title, p.sort_name) AS name,
                           {_PERSON_IMAGE_SQL} AS image
                    FROM person p
                    JOIN entity e ON e.id = p.id
                    LEFT JOIN entity_translation et
                        ON et.entity_id = p.id
                        AND et.language_id = (
                            SELECT id FROM language WHERE code = :lang
                        )
                    WHERE p.id = :pid
                      AND p.is_director = true
                      AND e.status = 'published'
                """),
                {"pid": person_id, "lang": lang},
            )
        ).mappings().first()
        if not row:
            return None
        return {
            "id": row["id"],
            "name": row["name"] or "Без имени",
            "image": row["image"],
        }

    async def _get_influencers(
        self, target_id: int, *, top_n: int, lang: str,
    ) -> list[dict[str, Any]]:
        """
        Кто повлиял на target_id (учителя / вдохновители).
        source_director_id → target_director_id.
        """
        rows = (
            await self.db.execute(
                text(f"""
                    SELECT
                        di.source_director_id AS id,
                        COALESCE(di.weight, 3) AS weight,
                        COALESCE(et.title, p.sort_name) AS name,
                        {_PERSON_IMAGE_SQL} AS image,
                        COALESCE((
                            SELECT count(*) FROM film_person fp
                            WHERE fp.person_id = di.source_director_id
                              AND fp.role_type = 'director'
                        ), 0) AS films_count
                    FROM director_influence di
                    JOIN person p ON p.id = di.source_director_id
                    JOIN entity e ON e.id = di.source_director_id
                    LEFT JOIN entity_translation et
                        ON et.entity_id = di.source_director_id
                        AND et.language_id = (
                            SELECT id FROM language WHERE code = :lang
                        )
                    WHERE di.target_director_id = :tid
                      AND p.is_director = true
                      AND e.status = 'published'
                    ORDER BY di.weight DESC,
                        (SELECT count(*) FROM film_person fp
                         WHERE fp.person_id = di.source_director_id
                           AND fp.role_type = 'director') DESC
                    LIMIT :n
                """),
                {"tid": target_id, "lang": lang, "n": top_n},
            )
        ).mappings().all()

        return [
            {
                "id": r["id"],
                "name": r["name"] or "Без имени",
                "image": r["image"],
                "weight": float(r["weight"]),
                "films_count": int(r["films_count"] or 0),
            }
            for r in rows
        ]

    async def _get_influencers_batch(
        self,
        target_ids: list[int],
        *,
        top_n: int,
        lang: str,
    ) -> dict[int, list[dict[str, Any]]]:
        if not target_ids:
            return {}

        rows = (
            await self.db.execute(
                text(f"""
                    SELECT parent_id, id, weight, name, image, films_count
                    FROM (
                        SELECT
                            di.target_director_id AS parent_id,
                            di.source_director_id AS id,
                            COALESCE(di.weight, 3) AS weight,
                            COALESCE(et.title, p.sort_name) AS name,
                            {_PERSON_IMAGE_SQL} AS image,
                            COALESCE((
                                SELECT count(*) FROM film_person fp
                                WHERE fp.person_id = di.source_director_id
                                  AND fp.role_type = 'director'
                            ), 0) AS films_count,
                            ROW_NUMBER() OVER (
                                PARTITION BY di.target_director_id
                                ORDER BY di.weight DESC,
                                    (SELECT count(*) FROM film_person fp
                                     WHERE fp.person_id = di.source_director_id
                                       AND fp.role_type = 'director') DESC
                            ) AS rn
                        FROM director_influence di
                        JOIN person p ON p.id = di.source_director_id
                        JOIN entity e ON e.id = di.source_director_id
                        LEFT JOIN entity_translation et
                            ON et.entity_id = di.source_director_id
                            AND et.language_id = (
                                SELECT id FROM language WHERE code = :lang
                            )
                        WHERE di.target_director_id = ANY(:tids)
                          AND p.is_director = true
                          AND e.status = 'published'
                    ) ranked
                    WHERE rn <= :n
                """),
                {"tids": target_ids, "lang": lang, "n": top_n},
            )
        ).mappings().all()

        result: dict[int, list[dict[str, Any]]] = {tid: [] for tid in target_ids}
        for r in rows:
            parent_id = r["parent_id"]
            result.setdefault(parent_id, []).append({
                "id": r["id"],
                "name": r["name"] or "Без имени",
                "image": r["image"],
                "weight": float(r["weight"]),
                "films_count": int(r["films_count"] or 0),
            })
        return result

    async def get_center_candidates(
        self,
        *,
        limit: int = 80,
        min_incoming: int = 2,
        lang: str = "ru",
    ) -> list[dict[str, Any]]:
        """
        Режиссёры, у которых достаточно «учителей» для кольца 1 на главной.

        Сортировка: входящие связи → ручная разметка (confidence≥0.9) → всего связей.
        """
        rows = (
            await self.db.execute(
                text("""
                    SELECT
                        p.id,
                        COALESCE(et.title, p.sort_name) AS name,
                        COALESCE(inc.cnt, 0) AS incoming_count,
                        COALESCE(out.cnt, 0) AS outgoing_count,
                        COALESCE(inc.manual_cnt, 0) AS manual_incoming_count
                    FROM person p
                    JOIN entity e ON e.id = p.id
                    LEFT JOIN entity_translation et
                        ON et.entity_id = p.id
                        AND et.language_id = (
                            SELECT id FROM language WHERE code = :lang
                        )
                    LEFT JOIN (
                        SELECT
                            target_director_id AS pid,
                            count(*) AS cnt,
                            count(*) FILTER (
                                WHERE confidence >= 0.9
                                  AND inferred_by_system = false
                            ) AS manual_cnt
                        FROM director_influence
                        GROUP BY target_director_id
                    ) inc ON inc.pid = p.id
                    LEFT JOIN (
                        SELECT source_director_id AS pid, count(*) AS cnt
                        FROM director_influence
                        GROUP BY source_director_id
                    ) out ON out.pid = p.id
                    WHERE p.is_director = true
                      AND e.status = 'published'
                      AND COALESCE(inc.cnt, 0) >= :min_incoming
                    ORDER BY inc.cnt DESC,
                        inc.manual_cnt DESC,
                        (COALESCE(inc.cnt, 0) + COALESCE(out.cnt, 0)) DESC,
                        p.id
                    LIMIT :lim
                """),
                {"lang": lang, "min_incoming": min_incoming, "lim": limit},
            )
        ).mappings().all()

        return [
            {
                "id": r["id"],
                "name": r["name"] or "Без имени",
                "incoming_count": int(r["incoming_count"]),
                "outgoing_count": int(r["outgoing_count"]),
                "manual_incoming_count": int(r["manual_incoming_count"]),
            }
            for r in rows
        ]
