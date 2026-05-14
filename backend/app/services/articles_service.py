"""
Сервис для работы со статьями (журнальные эссе).

Статьи - сущности entity с entity_type='article'.
- title/summary/body: в entity_translation
- метаданные: в article (article_type, reading_time_min, is_featured, author_user_id)
- связи с режиссёрами/фильмами: article_entity_link (link_type: about/mentions/...)
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


class ArticlesService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_articles(
        self,
        *,
        lang: str = "ru",
        only_featured: bool = False,
        article_type: Optional[str] = None,
        for_entity_id: Optional[int] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        """Список статей с обложками и главными субъектами."""

        where_parts = ["e.status = 'published'"]
        params: dict = {"lang": lang, "lim": limit, "off": offset}

        if only_featured:
            where_parts.append("a.is_featured = true")
        if article_type:
            where_parts.append("a.article_type = :atype")
            params["atype"] = article_type
        if for_entity_id is not None:
            # только статьи которые ссылаются на эту сущность
            where_parts.append("""
                EXISTS (
                    SELECT 1 FROM article_entity_link ael
                    WHERE ael.article_id = a.id AND ael.entity_id = :ent_id
                )
            """)
            params["ent_id"] = for_entity_id

        where_sql = " AND ".join(where_parts)

        # total
        count_sql = text(f"""
            SELECT count(*) FROM article a
            JOIN entity e ON e.id = a.id
            WHERE {where_sql}
        """)
        total = (await self.db.execute(count_sql, params)).scalar_one()

        # Список
        sql = text(f"""
            SELECT
                a.id,
                a.article_type,
                a.reading_time_min,
                a.is_featured,
                e.published_at,
                e.primary_image_url AS cover_image,
                COALESCE(et_lang.slug, et_en.slug) AS slug,
                COALESCE(et_lang.title, et_en.title) AS title,
                COALESCE(et_lang.summary, et_en.summary) AS summary
            FROM article a
            JOIN entity e ON e.id = a.id
            LEFT JOIN entity_translation et_lang
                ON et_lang.entity_id = a.id
                AND et_lang.language_id = (SELECT id FROM language WHERE code = :lang)
            LEFT JOIN entity_translation et_en
                ON et_en.entity_id = a.id
                AND et_en.language_id = (SELECT id FROM language WHERE code = 'en')
            WHERE {where_sql}
            ORDER BY a.is_featured DESC, e.published_at DESC NULLS LAST, a.id DESC
            LIMIT :lim OFFSET :off
        """)
        rows = (await self.db.execute(sql, params)).mappings().all()
        article_ids = [r["id"] for r in rows]

        # Главные субъекты (link_type='about') для всех статей разом
        subjects_by_article: dict[int, dict] = {}
        if article_ids:
            subj_sql = text("""
                SELECT DISTINCT ON (ael.article_id)
                    ael.article_id,
                    ael.entity_id,
                    e.entity_type::text AS entity_type,
                    COALESCE(et_lang.title, et_en.title) AS title,
                    e.primary_image_url,
                    e.thumbnail_url
                FROM article_entity_link ael
                JOIN entity e ON e.id = ael.entity_id
                LEFT JOIN entity_translation et_lang
                    ON et_lang.entity_id = ael.entity_id
                    AND et_lang.language_id = (SELECT id FROM language WHERE code = :lang)
                LEFT JOIN entity_translation et_en
                    ON et_en.entity_id = ael.entity_id
                    AND et_en.language_id = (SELECT id FROM language WHERE code = 'en')
                WHERE ael.article_id = ANY(:ids)
                  AND ael.link_type = 'about'
                ORDER BY ael.article_id, ael.link_weight DESC
            """)
            subj_rows = (await self.db.execute(subj_sql, {
                "ids": article_ids, "lang": lang,
            })).mappings().all()
            for r in subj_rows:
                subjects_by_article[r["article_id"]] = {
                    "entity_id": r["entity_id"],
                    "entity_type": r["entity_type"],
                    "title": r["title"] or "Untitled",
                    "link_type": "about",
                    "images": {
                        "primary": r["primary_image_url"],
                        "thumbnail": r["thumbnail_url"],
                    },
                }

        items = [
            {
                "id": r["id"],
                "slug": r["slug"] or f"article-{r['id']}",
                "article_type": r["article_type"],
                "title": r["title"] or "Без названия",
                "summary": r["summary"],
                "cover_image": r["cover_image"],
                "reading_time_min": r["reading_time_min"],
                "is_featured": bool(r["is_featured"]),
                "published_at": r["published_at"].isoformat() if r["published_at"] else None,
                "main_subject": subjects_by_article.get(r["id"]),
            }
            for r in rows
        ]

        return {
            "items": items,
            "total": int(total),
            "limit": limit,
            "offset": offset,
        }

    async def get_article_by_slug(
        self,
        slug: str,
        *,
        lang: str = "ru",
    ) -> Optional[dict]:
        """Статья по slug. Slug уникален в рамках языка."""

        # Сначала найдём entity_id по slug
        find_sql = text("""
            SELECT et.entity_id
            FROM entity_translation et
            JOIN entity e ON e.id = et.entity_id
            WHERE et.slug = :slug
              AND e.entity_type = 'article'
              AND e.status = 'published'
            ORDER BY
                CASE WHEN et.language_id = (SELECT id FROM language WHERE code = :lang)
                     THEN 0 ELSE 1 END
            LIMIT 1
        """)
        article_id = (await self.db.execute(find_sql, {
            "slug": slug, "lang": lang,
        })).scalar_one_or_none()

        if not article_id:
            return None

        return await self.get_article_by_id(article_id, lang=lang)

    async def get_article_by_id(
        self,
        article_id: int,
        *,
        lang: str = "ru",
    ) -> Optional[dict]:
        """Статья по ID с телом и связанными сущностями."""

        head_sql = text("""
            SELECT
                a.id,
                a.article_type,
                a.reading_time_min,
                a.is_featured,
                e.published_at,
                e.primary_image_url AS cover_image,
                COALESCE(et_lang.slug, et_en.slug) AS slug,
                COALESCE(et_lang.title, et_en.title) AS title,
                COALESCE(et_lang.summary, et_en.summary) AS summary,
                COALESCE(et_lang.body, et_en.body) AS body,
                au.display_name AS author_name
            FROM article a
            JOIN entity e ON e.id = a.id
            LEFT JOIN entity_translation et_lang
                ON et_lang.entity_id = a.id
                AND et_lang.language_id = (SELECT id FROM language WHERE code = :lang)
            LEFT JOIN entity_translation et_en
                ON et_en.entity_id = a.id
                AND et_en.language_id = (SELECT id FROM language WHERE code = 'en')
            LEFT JOIN app_user au ON au.id = a.author_user_id
            WHERE a.id = :aid AND e.status = 'published'
        """)
        head = (await self.db.execute(head_sql, {
            "aid": article_id, "lang": lang,
        })).mappings().first()

        if not head:
            return None

        # Связанные сущности
        rel_sql = text("""
            SELECT
                ael.entity_id,
                e.entity_type::text AS entity_type,
                ael.link_type::text AS link_type,
                ael.link_weight,
                COALESCE(et_lang.title, et_en.title) AS title,
                e.primary_image_url,
                e.thumbnail_url
            FROM article_entity_link ael
            JOIN entity e ON e.id = ael.entity_id
            LEFT JOIN entity_translation et_lang
                ON et_lang.entity_id = ael.entity_id
                AND et_lang.language_id = (SELECT id FROM language WHERE code = :lang)
            LEFT JOIN entity_translation et_en
                ON et_en.entity_id = ael.entity_id
                AND et_en.language_id = (SELECT id FROM language WHERE code = 'en')
            WHERE ael.article_id = :aid
              AND e.status = 'published'
            ORDER BY
                CASE ael.link_type::text
                    WHEN 'about' THEN 0
                    WHEN 'analyzes' THEN 1
                    WHEN 'reviews' THEN 2
                    WHEN 'cites' THEN 3
                    WHEN 'mentions' THEN 4
                    WHEN 'interview' THEN 5
                    ELSE 6
                END,
                ael.link_weight DESC
        """)
        rel_rows = (await self.db.execute(rel_sql, {
            "aid": article_id, "lang": lang,
        })).mappings().all()

        related = [
            {
                "entity_id": r["entity_id"],
                "entity_type": r["entity_type"],
                "title": r["title"] or "Untitled",
                "link_type": r["link_type"],
                "images": {
                    "primary": r["primary_image_url"],
                    "thumbnail": r["thumbnail_url"],
                },
            }
            for r in rel_rows
        ]

        return {
            "id": head["id"],
            "slug": head["slug"] or f"article-{head['id']}",
            "article_type": head["article_type"],
            "title": head["title"] or "Без названия",
            "summary": head["summary"],
            "body": head["body"],
            "cover_image": head["cover_image"],
            "reading_time_min": head["reading_time_min"],
            "is_featured": bool(head["is_featured"]),
            "published_at": head["published_at"].isoformat() if head["published_at"] else None,
            "author_name": head["author_name"] or "Редакция",
            "related_entities": related,
        }
