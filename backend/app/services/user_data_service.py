"""
Сервис пользовательских данных: избранное, оценки, история.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class UserDataService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ─── Избранное (user_watchlist) ─────────────────────────────
    async def add_to_favorites(
        self,
        user_id: int,
        entity_id: int,
        *,
        status: str = "want_to_watch",
        note: str | None = None,
    ) -> None:
        """Добавить в избранное. Если уже есть — обновляет статус."""
        await self.db.execute(text("""
            INSERT INTO user_watchlist (user_id, entity_id, status, note)
            VALUES (:uid, :eid, CAST(:status AS watchlist_status), :note)
            ON CONFLICT (user_id, entity_id) DO UPDATE
                SET status = EXCLUDED.status,
                    note = EXCLUDED.note,
                    updated_at = now()
        """), {"uid": user_id, "eid": entity_id, "status": status, "note": note})
        await self.db.commit()

    async def remove_from_favorites(self, user_id: int, entity_id: int) -> bool:
        """Удалить из избранного. Возвращает True если что-то удалили."""
        result = await self.db.execute(text("""
            DELETE FROM user_watchlist WHERE user_id = :uid AND entity_id = :eid
        """), {"uid": user_id, "eid": entity_id})
        await self.db.commit()
        return (result.rowcount or 0) > 0

    async def list_favorites(
        self,
        user_id: int,
        *,
        lang: str = "ru",
        entity_type: str | None = None,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        """Список избранного с переводами."""
        where = ["w.user_id = :uid"]
        params: dict = {"uid": user_id, "lang": lang}

        if entity_type:
            where.append("e.entity_type = CAST(:etype AS entity_type)")
            params["etype"] = entity_type
        if status:
            where.append("w.status = CAST(:status AS watchlist_status)")
            params["status"] = status

        where_sql = " AND ".join(where)

        total = (await self.db.execute(
            text(f"""
                SELECT count(*) FROM user_watchlist w
                JOIN entity e ON e.id = w.entity_id
                WHERE {where_sql}
            """), params,
        )).scalar_one()

        params["limit"] = limit
        params["offset"] = offset

        rows = (await self.db.execute(
            text(f"""
                SELECT
                    e.id AS entity_id,
                    e.entity_type::text AS entity_type,
                    COALESCE(et_lang.title, et_en.title, 'Untitled') AS title,
                    COALESCE(et_lang.summary, et_en.summary) AS summary,
                    e.primary_image_url AS img_primary,
                    e.thumbnail_url AS img_thumb,
                    f.release_year,
                    w.status::text AS status,
                    w.note,
                    w.added_at,
                    w.watched_at
                FROM user_watchlist w
                JOIN entity e ON e.id = w.entity_id
                LEFT JOIN film f ON f.id = e.id AND e.entity_type = 'film'
                LEFT JOIN entity_translation et_lang
                    ON et_lang.entity_id = e.id
                    AND et_lang.language_id = (SELECT id FROM language WHERE code = :lang)
                LEFT JOIN entity_translation et_en
                    ON et_en.entity_id = e.id
                    AND et_en.language_id = (SELECT id FROM language WHERE code = 'en')
                WHERE {where_sql}
                ORDER BY w.added_at DESC
                LIMIT :limit OFFSET :offset
            """), params,
        )).mappings().all()

        items = [
            {
                "entity_id": r["entity_id"],
                "entity_type": r["entity_type"],
                "title": r["title"],
                "summary": r["summary"],
                "images": {"primary": r["img_primary"], "thumbnail": r["img_thumb"]},
                "release_year": r["release_year"],
                "status": r["status"],
                "note": r["note"],
                "added_at": r["added_at"],
                "watched_at": r["watched_at"],
            }
            for r in rows
        ]

        return {"items": items, "total": total, "limit": limit, "offset": offset}

    async def check_favorite(self, user_id: int, entity_id: int) -> dict:
        """Быстрая проверка для иконки на карточке."""
        row = (await self.db.execute(
            text("""
                SELECT status::text AS status FROM user_watchlist
                WHERE user_id = :uid AND entity_id = :eid
            """),
            {"uid": user_id, "eid": entity_id},
        )).mappings().first()
        return {
            "is_favorite": row is not None,
            "status": row["status"] if row else None,
        }

    # ─── Оценки (user_rating) ───────────────────────────────────
    async def rate_entity(
        self,
        user_id: int,
        entity_id: int,
        *,
        rating: int,
        would_recommend: bool | None = None,
    ) -> None:
        """Поставить или обновить оценку."""
        await self.db.execute(text("""
            INSERT INTO user_rating (user_id, entity_id, rating, would_recommend)
            VALUES (:uid, :eid, :rating, :rec)
            ON CONFLICT (user_id, entity_id) DO UPDATE
                SET rating = EXCLUDED.rating,
                    would_recommend = EXCLUDED.would_recommend,
                    updated_at = now()
        """), {
            "uid": user_id, "eid": entity_id,
            "rating": rating, "rec": would_recommend,
        })
        await self.db.commit()

    async def remove_rating(self, user_id: int, entity_id: int) -> bool:
        result = await self.db.execute(
            text("DELETE FROM user_rating WHERE user_id = :uid AND entity_id = :eid"),
            {"uid": user_id, "eid": entity_id},
        )
        await self.db.commit()
        return (result.rowcount or 0) > 0

    async def get_my_rating(
        self, user_id: int, entity_id: int
    ) -> dict | None:
        """Получить мою оценку конкретного фильма."""
        row = (await self.db.execute(text("""
            SELECT entity_id, rating, would_recommend, rated_at, updated_at
            FROM user_rating
            WHERE user_id = :uid AND entity_id = :eid
        """), {"uid": user_id, "eid": entity_id})).mappings().first()
        return dict(row) if row else None

    async def list_my_ratings(
        self,
        user_id: int,
        *,
        lang: str = "ru",
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        """Список оценок пользователя с переводами сущностей."""
        total = (await self.db.execute(
            text("SELECT count(*) FROM user_rating WHERE user_id = :uid"),
            {"uid": user_id},
        )).scalar_one()

        params = {"uid": user_id, "lang": lang, "limit": limit, "offset": offset}
        rows = (await self.db.execute(
            text("""
                SELECT
                    e.id AS entity_id,
                    e.entity_type::text AS entity_type,
                    COALESCE(et_lang.title, et_en.title, 'Untitled') AS title,
                    e.primary_image_url AS img_primary,
                    e.thumbnail_url AS img_thumb,
                    f.release_year,
                    ur.rating,
                    ur.would_recommend,
                    ur.rated_at,
                    ur.updated_at
                FROM user_rating ur
                JOIN entity e ON e.id = ur.entity_id
                LEFT JOIN film f ON f.id = e.id AND e.entity_type = 'film'
                LEFT JOIN entity_translation et_lang
                    ON et_lang.entity_id = e.id
                    AND et_lang.language_id = (SELECT id FROM language WHERE code = :lang)
                LEFT JOIN entity_translation et_en
                    ON et_en.entity_id = e.id
                    AND et_en.language_id = (SELECT id FROM language WHERE code = 'en')
                WHERE ur.user_id = :uid
                ORDER BY ur.updated_at DESC
                LIMIT :limit OFFSET :offset
            """),
            params,
        )).mappings().all()

        items = [
            {
                "entity_id": r["entity_id"],
                "entity_type": r["entity_type"],
                "title": r["title"],
                "images": {"primary": r["img_primary"], "thumbnail": r["img_thumb"]},
                "release_year": r["release_year"],
                "rating": r["rating"],
                "would_recommend": r["would_recommend"],
                "rated_at": r["rated_at"],
                "updated_at": r["updated_at"],
            }
            for r in rows
        ]
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    async def get_rating_distribution(self, user_id: int) -> dict:
        """Гистограмма оценок 1–10 для графика в профиле."""
        rows = (await self.db.execute(
            text("""
                SELECT rating, count(*)::int AS cnt
                FROM user_rating
                WHERE user_id = :uid
                GROUP BY rating
                ORDER BY rating
            """),
            {"uid": user_id},
        )).mappings().all()
        counts = {r["rating"]: r["cnt"] for r in rows}
        buckets = [{"rating": i, "count": counts.get(i, 0)} for i in range(1, 11)]
        total = sum(b["count"] for b in buckets)
        avg_row = (await self.db.execute(
            text("SELECT avg(rating)::float AS avg FROM user_rating WHERE user_id = :uid"),
            {"uid": user_id},
        )).mappings().first()
        avg = avg_row["avg"] if avg_row and avg_row["avg"] is not None else None
        return {
            "buckets": buckets,
            "total": total,
            "average": round(avg, 2) if avg is not None else None,
        }

    async def get_profile_stats(self, user_id: int) -> dict:
        """Счётчики для блоков профиля."""
        row = (await self.db.execute(
            text("""
                SELECT
                    (SELECT count(*) FROM user_rating WHERE user_id = :uid) AS ratings_count,
                    (SELECT count(*) FROM user_watchlist WHERE user_id = :uid) AS favorites_count,
                    (SELECT count(*) FROM user_watchlist
                     WHERE user_id = :uid AND status = 'watched') AS watched_count,
                    (SELECT count(*) FROM user_watchlist
                     WHERE user_id = :uid AND status = 'want_to_watch') AS want_to_watch_count,
                    (SELECT count(*) FROM view_history WHERE user_id = :uid) AS views_count,
                    (SELECT count(*) FROM search_history WHERE user_id = :uid) AS searches_count
            """),
            {"uid": user_id},
        )).mappings().first()
        return dict(row) if row else {
            "ratings_count": 0,
            "favorites_count": 0,
            "watched_count": 0,
            "want_to_watch_count": 0,
            "views_count": 0,
            "searches_count": 0,
        }

    async def get_entity_rating_stats(self, entity_id: int) -> dict:
        """
        Сводная статистика оценок по сущности от всех пользователей.
        Полезно показывать на карточке: 'средняя пользовательская оценка 8.4'.
        """
        row = (await self.db.execute(text("""
            SELECT
                avg(rating)::float AS avg_rating,
                count(*) AS total_ratings,
                (count(*) FILTER (WHERE would_recommend IS TRUE)::float /
                 NULLIF(count(*) FILTER (WHERE would_recommend IS NOT NULL), 0) * 100
                ) AS recommend_percent
            FROM user_rating
            WHERE entity_id = :eid
        """), {"eid": entity_id})).mappings().first()
        return {
            "avg_rating": round(row["avg_rating"], 2) if row["avg_rating"] else None,
            "total_ratings": row["total_ratings"] or 0,
            "recommend_percent": round(row["recommend_percent"], 1) if row["recommend_percent"] else None,
        }

    # ─── История поисков и просмотров ───────────────────────────
    async def get_search_history(
        self, user_id: int, *, limit: int = 50
    ) -> list[dict]:
        """Недавние поиски пользователя (только авторизованные)."""
        rows = (await self.db.execute(text("""
            SELECT sh.query_text, sh.results_count, sh.searched_at,
                   l.code AS language_code
            FROM search_history sh
            LEFT JOIN language l ON l.id = sh.language_id
            WHERE sh.user_id = :uid
            ORDER BY sh.searched_at DESC
            LIMIT :limit
        """), {"uid": user_id, "limit": limit})).mappings().all()
        return [dict(r) for r in rows]

    async def get_view_history(
        self, user_id: int, *, lang: str = "ru", limit: int = 50
    ) -> list[dict]:
        """Недавно просмотренные сущности."""
        rows = (await self.db.execute(text("""
            SELECT
                vh.entity_id,
                e.entity_type::text AS entity_type,
                COALESCE(et_lang.title, et_en.title, 'Untitled') AS title,
                e.primary_image_url AS img_primary,
                e.thumbnail_url AS img_thumb,
                vh.viewed_at,
                vh.duration_seconds
            FROM view_history vh
            JOIN entity e ON e.id = vh.entity_id
            LEFT JOIN entity_translation et_lang
                ON et_lang.entity_id = e.id
                AND et_lang.language_id = (SELECT id FROM language WHERE code = :lang)
            LEFT JOIN entity_translation et_en
                ON et_en.entity_id = e.id
                AND et_en.language_id = (SELECT id FROM language WHERE code = 'en')
            WHERE vh.user_id = :uid
            ORDER BY vh.viewed_at DESC
            LIMIT :limit
        """), {"uid": user_id, "lang": lang, "limit": limit})).mappings().all()
        return [
            {
                "entity_id": r["entity_id"],
                "entity_type": r["entity_type"],
                "title": r["title"],
                "images": {"primary": r["img_primary"], "thumbnail": r["img_thumb"]},
                "viewed_at": r["viewed_at"],
                "duration_seconds": r["duration_seconds"],
            }
            for r in rows
        ]
