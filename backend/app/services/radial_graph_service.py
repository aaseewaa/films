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
                text("""
                    SELECT p.id,
                           COALESCE(et.title, p.sort_name) AS name,
                           e.primary_image_url AS image
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
                text("""
                    SELECT
                        di.source_director_id AS id,
                        COALESCE(di.weight, 3) AS weight,
                        COALESCE(et.title, p.sort_name) AS name,
                        e.primary_image_url AS image,
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
                text("""
                    SELECT parent_id, id, weight, name, image, films_count
                    FROM (
                        SELECT
                            di.target_director_id AS parent_id,
                            di.source_director_id AS id,
                            COALESCE(di.weight, 3) AS weight,
                            COALESCE(et.title, p.sort_name) AS name,
                            e.primary_image_url AS image,
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
