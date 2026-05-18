"""
Новый метод GraphService для радиальной карточки.

Возвращает центрального режиссёра и его N САМЫХ СИЛЬНЫХ связей
(по полю director_influence.weight). Глубина строго 1 — это
для радиального layout на фронте, где визуально показываем
только ближайших соседей.

Использование на фронте:
    GET /api/graph/director/3243/radial?top_n=4&lang=ru
    -> возвращает Спилберга + его топ-4 значимых связей
"""
from __future__ import annotations

import logging
from typing import Optional

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
        lang: str = "ru",
    ) -> Optional[dict]:
        """
        Возвращает центр + топ-N соседей по силе связи.

        Связь = объединение направлений (на кого повлиял + кто повлиял на него).
        Вес связи — сумма weight по обеим направлениям если есть.
        Сортировка по убыванию веса, потом по числу фильмов в БД (тай-брейк).
        """

        # 1) Проверка что центр существует и это режиссёр
        check_sql = text("""
            SELECT p.id, COALESCE(et.title, p.sort_name) AS name,
                   e.primary_image_url AS image
            FROM person p
            JOIN entity e ON e.id = p.id
            LEFT JOIN entity_translation et
                ON et.entity_id = p.id
                AND et.language_id = (SELECT id FROM language WHERE code = :lang)
            WHERE p.id = :cid AND p.is_director = true
        """)
        center = (await self.db.execute(check_sql, {
            "cid": center_id, "lang": lang,
        })).mappings().first()

        if not center:
            return None

        # 2) Берём топ-N связей по объединённой силе
        # Связь объединяется по парам (least, greatest) чтобы (A,B) и (B,A) считались одной
        neighbors_sql = text("""
            WITH pairs AS (
                -- Все рёбра в обе стороны где участвует наш центр
                SELECT
                    CASE
                        WHEN di.source_director_id = :cid THEN di.target_director_id
                        ELSE di.source_director_id
                    END AS neighbor_id,
                    COALESCE(di.weight, 1.0) AS w
                FROM director_influence di
                WHERE di.source_director_id = :cid
                   OR di.target_director_id = :cid
            ),
            ranked AS (
                SELECT
                    neighbor_id,
                    SUM(w) AS total_weight,
                    COUNT(*) AS link_count
                FROM pairs
                GROUP BY neighbor_id
            )
            SELECT
                r.neighbor_id AS id,
                r.total_weight,
                r.link_count,
                COALESCE(et.title, p.sort_name) AS name,
                e.primary_image_url AS image,
                COALESCE((
                    SELECT count(*) FROM film_person fp
                    WHERE fp.person_id = r.neighbor_id
                      AND fp.role_type = 'director'
                ), 0) AS films_count
            FROM ranked r
            JOIN person p ON p.id = r.neighbor_id
            JOIN entity e ON e.id = r.neighbor_id
            LEFT JOIN entity_translation et
                ON et.entity_id = r.neighbor_id
                AND et.language_id = (SELECT id FROM language WHERE code = :lang)
            WHERE p.is_director = true
              AND e.status = 'published'
            ORDER BY r.total_weight DESC, films_count DESC
            LIMIT :n
        """)
        rows = (await self.db.execute(neighbors_sql, {
            "cid": center_id, "lang": lang, "n": top_n,
        })).mappings().all()

        return {
            "center": {
                "id": center["id"],
                "name": center["name"] or "Без имени",
                "image": center["image"],
            },
            "neighbors": [
                {
                    "id": r["id"],
                    "name": r["name"] or "Без имени",
                    "image": r["image"],
                    "weight": float(r["total_weight"]),
                    "films_count": int(r["films_count"] or 0),
                }
                for r in rows
            ],
            "total_neighbors_in_db": len(rows),
            "top_n_requested": top_n,
        }
