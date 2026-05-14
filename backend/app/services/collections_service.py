"""
Сервис для работы с коллекциями.

Коллекции - сущности entity с entity_type='collection'.
- title/description: в entity_translation
- содержимое: collection_item (collection_id, entity_id, position, note)
- обложка: entity.primary_image_url ИЛИ collection.cover_entity_id
- теги: entity_taxonomy (для редакторских коллекций можно ставить теги)
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


class CollectionsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_collections(
        self,
        *,
        kind: Optional[str] = None,  # 'editorial' / 'custom' / 'auto'
        lang: str = "ru",
        only_featured: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        """Список коллекций с обложками и тегами."""

        # Базовый WHERE
        where_parts = ["e.status = 'published'", "c.kind = CAST(:kind AS collection_kind)"] if kind else ["e.status = 'published'"]
        params: dict = {
            "lang": lang,
            "lim": limit,
            "off": offset,
        }
        if kind:
            params["kind"] = kind

        if only_featured:
            where_parts.append("COALESCE((c.extra_metadata->>'is_featured')::boolean, false) = true")

        where_sql = " AND ".join(where_parts)

        # Считаем total
        count_sql = text(f"""
            SELECT count(*) FROM collection c
            JOIN entity e ON e.id = c.id
            WHERE {where_sql}
        """)
        total = (await self.db.execute(count_sql, params)).scalar_one()

        # Берём список
        sql = text(f"""
            SELECT
                c.id,
                c.kind::text AS kind,
                c.items_count,
                c.extra_metadata,
                COALESCE(et_lang.title, et_en.title) AS title,
                COALESCE(et_lang.summary, et_en.summary) AS summary,
                COALESCE(
                    cov.primary_image_url,
                    e.primary_image_url
                ) AS cover_image,
                COALESCE(
                    array_agg(DISTINCT tt.code) FILTER (WHERE tt.code IS NOT NULL),
                    ARRAY[]::text[]
                ) AS tags
            FROM collection c
            JOIN entity e ON e.id = c.id
            LEFT JOIN entity_translation et_lang
                ON et_lang.entity_id = c.id
                AND et_lang.language_id = (SELECT id FROM language WHERE code = :lang)
            LEFT JOIN entity_translation et_en
                ON et_en.entity_id = c.id
                AND et_en.language_id = (SELECT id FROM language WHERE code = 'en')
            LEFT JOIN entity cov ON cov.id = c.cover_entity_id
            LEFT JOIN entity_taxonomy ex ON ex.entity_id = c.id
            LEFT JOIN taxonomy_term tt ON tt.id = ex.term_id
            WHERE {where_sql}
            GROUP BY c.id, c.kind, c.items_count, c.extra_metadata,
                     et_lang.title, et_en.title, et_lang.summary, et_en.summary,
                     cov.primary_image_url, e.primary_image_url
            ORDER BY c.items_count DESC, c.id
            LIMIT :lim OFFSET :off
        """)

        rows = (await self.db.execute(sql, params)).mappings().all()

        items = [
            {
                "id": r["id"],
                "kind": r["kind"],
                "title": r["title"] or "Без названия",
                "summary": r["summary"],
                "cover_image": r["cover_image"],
                "items_count": r["items_count"] or 0,
                "is_featured": bool((r["extra_metadata"] or {}).get("is_featured", False)),
                "tags": list(r["tags"] or []),
            }
            for r in rows
        ]

        return {
            "items": items,
            "total": int(total),
            "limit": limit,
            "offset": offset,
        }

    async def get_collection(
        self,
        collection_id: int,
        *,
        lang: str = "ru",
    ) -> Optional[dict]:
        """Полная коллекция с содержимым."""

        # Базовая инфа
        head_sql = text("""
            SELECT
                c.id,
                c.kind::text AS kind,
                c.items_count,
                c.extra_metadata,
                COALESCE(et_lang.title, et_en.title) AS title,
                COALESCE(et_lang.summary, et_en.summary) AS summary,
                COALESCE(et_lang.description, et_en.description) AS description,
                COALESCE(cov.primary_image_url, e.primary_image_url) AS cover_image,
                COALESCE(
                    array_agg(DISTINCT tt.code) FILTER (WHERE tt.code IS NOT NULL),
                    ARRAY[]::text[]
                ) AS tags
            FROM collection c
            JOIN entity e ON e.id = c.id
            LEFT JOIN entity_translation et_lang
                ON et_lang.entity_id = c.id
                AND et_lang.language_id = (SELECT id FROM language WHERE code = :lang)
            LEFT JOIN entity_translation et_en
                ON et_en.entity_id = c.id
                AND et_en.language_id = (SELECT id FROM language WHERE code = 'en')
            LEFT JOIN entity cov ON cov.id = c.cover_entity_id
            LEFT JOIN entity_taxonomy ex ON ex.entity_id = c.id
            LEFT JOIN taxonomy_term tt ON tt.id = ex.term_id
            WHERE c.id = :cid AND e.status = 'published'
            GROUP BY c.id, c.kind, c.items_count, c.extra_metadata,
                     et_lang.title, et_en.title,
                     et_lang.summary, et_en.summary,
                     et_lang.description, et_en.description,
                     cov.primary_image_url, e.primary_image_url
        """)
        head = (await self.db.execute(head_sql, {
            "cid": collection_id, "lang": lang,
        })).mappings().first()

        if not head:
            return None

        # Содержимое
        items_sql = text("""
            SELECT
                ci.entity_id,
                e.entity_type::text AS entity_type,
                ci.position,
                ci.note,
                COALESCE(et_lang.title, et_en.title) AS title,
                COALESCE(et_lang.summary, et_en.summary) AS summary,
                e.primary_image_url,
                e.thumbnail_url,
                f.release_year
            FROM collection_item ci
            JOIN entity e ON e.id = ci.entity_id
            LEFT JOIN film f ON f.id = ci.entity_id
            LEFT JOIN entity_translation et_lang
                ON et_lang.entity_id = ci.entity_id
                AND et_lang.language_id = (SELECT id FROM language WHERE code = :lang)
            LEFT JOIN entity_translation et_en
                ON et_en.entity_id = ci.entity_id
                AND et_en.language_id = (SELECT id FROM language WHERE code = 'en')
            WHERE ci.collection_id = :cid
              AND e.status = 'published'
            ORDER BY ci.position, ci.added_at
        """)
        rows = (await self.db.execute(items_sql, {
            "cid": collection_id, "lang": lang,
        })).mappings().all()

        items = [
            {
                "entity_id": r["entity_id"],
                "entity_type": r["entity_type"],
                "title": r["title"] or "Без названия",
                "summary": r["summary"],
                "images": {
                    "primary": r["primary_image_url"],
                    "thumbnail": r["thumbnail_url"],
                },
                "release_year": r["release_year"],
                "position": r["position"],
                "note": r["note"],
            }
            for r in rows
        ]

        return {
            "id": head["id"],
            "kind": head["kind"],
            "title": head["title"] or "Без названия",
            "summary": head["summary"],
            "description": head["description"],
            "cover_image": head["cover_image"],
            "items_count": head["items_count"] or len(items),
            "tags": list(head["tags"] or []),
            "items": items,
        }
