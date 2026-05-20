"""
Сервис «Новинки»: афиша в городе (парсинг Кинопоиска) + обогащение из БД и TMDB.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.integrations.city_ref import CityRef, default_city, resolve_city
from app.integrations.kinopoisk_afisha import KinopoiskAfishaFilm, KinopoiskAfishaParser
from app.integrations.tmdb_client import TMDB_IMAGE_BASE, TmdbClient

log = logging.getLogger(__name__)


def _norm_title(value: str) -> str:
    text = (value or "").lower().replace("ё", "е")
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def _item_dedup_key(item: dict) -> str:
    if item.get("kinopoisk_id"):
        return f"kp:{item['kinopoisk_id']}"
    if item.get("tmdb_id"):
        return f"tmdb:{item['tmdb_id']}"
    return f"title:{_norm_title(item.get('title') or '')}"


class NewsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_worldwide(
        self,
        *,
        lang: str = "ru",
        limit: int = 20,
    ) -> dict:
        """Фильмы в мировом прокате (TMDB now_playing, без привязки к городу)."""
        city = default_city()
        kp_films = await self._tmdb_rows_to_films(
            await self._tmdb_list_now_playing(lang=lang, pages=3),
            city=city,
            ticket_mode="world",
        )
        return await self._pack_items(
            kp_films,
            city_label="В мировом прокате",
            city_kp_id="",
            source="tmdb_world",
            lang=lang,
            limit=limit,
        )

    async def get_upcoming(
        self,
        *,
        lang: str = "ru",
        limit: int = 12,
    ) -> dict:
        """Скоро в прокате — для карусели на вкладке «Новинки»."""
        city = default_city()
        if not settings.tmdb_api_key:
            return self._empty_response("Скоро в прокате", "", "tmdb_upcoming", limit)
        language = "ru-RU" if lang == "ru" else "en-US"
        async with TmdbClient(api_key=settings.tmdb_api_key) as tmdb:
            rows = await tmdb.upcoming(region="RU", pages=2, language=language)
        kp_films = await self._tmdb_rows_to_films(rows, city=city, ticket_mode="world")
        return await self._pack_items(
            kp_films,
            city_label="Скоро в прокате",
            city_kp_id="",
            source="tmdb_upcoming",
            lang=lang,
            limit=limit,
            tmdb_rows=rows,
        )

    async def get_film_afisha(
        self,
        *,
        entity_id: int,
        city_raw: str | None,
        lang: str = "ru",
    ) -> dict | None:
        """Афиша одного фильма в городе пользователя (для сайдбара на карточке фильма)."""
        city = resolve_city(city_raw) or default_city()
        row = await self._entity_row(entity_id, lang=lang)
        if not row:
            return None

        news = await self.get_news(city_raw=city.name, lang=lang, limit=50)
        for item in news["items"]:
            if item.get("entity_id") == entity_id:
                return {**item, "city": city.name}

        title = row["title"] or ""
        ticket_url = (
            f"https://www.kinopoisk.ru/film/{row['kinopoisk_id']}/afisha/city/{city.kp_city_id}/"
            if row.get("kinopoisk_id")
            else f"https://www.kinopoisk.ru/index.php?kp_query={quote(title)}"
        )
        return {
            "kinopoisk_id": row.get("kinopoisk_id"),
            "title": title,
            "entity_id": entity_id,
            "release_year": row.get("release_year"),
            "summary": row.get("summary"),
            "images": {
                "primary": row.get("img_primary"),
                "thumbnail": row.get("img_thumb"),
            },
            "ticket_url": ticket_url,
            "ticket_provider": "kinopoisk",
            "cinemas": [],
            "in_database": True,
            "tmdb_id": row.get("tmdb_id"),
            "city": city.name,
        }

    async def get_news(
        self,
        *,
        city_raw: str | None,
        lang: str = "ru",
        limit: int = 20,
    ) -> dict:
        city = resolve_city(city_raw) or default_city()
        kp_films = await self._fetch_kinopoisk(city)

        source = "kinopoisk_afisha"
        if not kp_films:
            log.warning("kinopoisk afisha empty for %s, fallback TMDB", city.name)
            kp_films = await self._tmdb_as_kp_fallback(city)
            source = "tmdb_fallback"

        return await self._pack_items(
            kp_films,
            city_label=city.name,
            city_kp_id=city.kp_city_id,
            source=source,
            lang=lang,
            limit=limit,
            city=city,
        )

    async def _pack_items(
        self,
        kp_films: list[KinopoiskAfishaFilm],
        *,
        city_label: str,
        city_kp_id: str,
        source: str,
        lang: str,
        limit: int,
        city: CityRef | None = None,
        tmdb_rows: list[dict] | None = None,
    ) -> dict:
        city = city or default_city()
        if tmdb_rows is not None:
            tmdb_by_id = {
                int(r["id"]): r for r in tmdb_rows if r.get("id") is not None
            }
        else:
            tmdb_by_id = await self._tmdb_now_playing_map(lang=lang)
        titles = [f.title for f in kp_films]
        db_by_kp, db_by_title = await self._load_entity_maps(
            [f.kinopoisk_id for f in kp_films],
            titles=titles,
            lang=lang,
        )

        items: list[dict] = []
        for kp in kp_films:
            item = self._build_item(
                kp,
                city=city,
                db_by_kp=db_by_kp,
                db_by_title=db_by_title,
                tmdb_by_id=tmdb_by_id,
            )
            if item:
                items.append(item)

        seen: set[str] = set()
        unique: list[dict] = []
        for it in items:
            key = _item_dedup_key(it)
            if key in seen:
                continue
            seen.add(key)
            unique.append(it)
            if len(unique) >= limit:
                break

        return {
            "city": city_label,
            "city_kp_id": city_kp_id,
            "source": source,
            "fetched_at": datetime.now(timezone.utc),
            "items": unique,
            "total": len(unique),
            "limit": limit,
        }

    def _empty_response(
        self, city_label: str, city_kp_id: str, source: str, limit: int
    ) -> dict:
        return {
            "city": city_label,
            "city_kp_id": city_kp_id,
            "source": source,
            "fetched_at": datetime.now(timezone.utc),
            "items": [],
            "total": 0,
            "limit": limit,
        }

    async def _tmdb_list_now_playing(self, *, lang: str, pages: int) -> list[dict]:
        if not settings.tmdb_api_key:
            return []
        language = "ru-RU" if lang == "ru" else "en-US"
        async with TmdbClient(api_key=settings.tmdb_api_key) as tmdb:
            return await tmdb.now_playing(region="RU", pages=pages, language=language)

    async def _tmdb_rows_to_films(
        self,
        rows: list[dict],
        *,
        city: CityRef,
        ticket_mode: str = "city",
    ) -> list[KinopoiskAfishaFilm]:
        out: list[KinopoiskAfishaFilm] = []
        for row in rows:
            tmdb_id = row.get("id")
            if not tmdb_id:
                continue
            title = row.get("title") or row.get("original_title") or f"Фильм {tmdb_id}"
            if ticket_mode == "world":
                ticket_url = f"https://www.kinopoisk.ru/index.php?kp_query={quote(title)}"
            else:
                ticket_url = (
                    f"https://www.kinopoisk.ru/afisha/city/{city.kp_city_id}/"
                    f"?kp_query={quote(title)}"
                )
            out.append(
                KinopoiskAfishaFilm(
                    kinopoisk_id=0,
                    title=title,
                    ticket_url=ticket_url,
                    tmdb_id=int(tmdb_id),
                ),
            )
        return out

    async def _entity_row(self, entity_id: int, *, lang: str) -> dict | None:
        sql = text("""
            SELECT
                e.id,
                e.primary_image_url AS img_primary,
                e.thumbnail_url AS img_thumb,
                e.external_ids,
                f.release_year,
                COALESCE(et_lang.title, et_en.title, f.sort_title) AS title,
                COALESCE(et_lang.summary, et_en.summary) AS summary,
                (e.external_ids->>'kinopoisk')::bigint AS kinopoisk_id,
                (e.external_ids->>'tmdb')::int AS tmdb_id
            FROM entity e
            JOIN film f ON f.id = e.id
            LEFT JOIN entity_translation et_lang
                ON et_lang.entity_id = e.id
                AND et_lang.language_id = (SELECT id FROM language WHERE code = :lang)
            LEFT JOIN entity_translation et_en
                ON et_en.entity_id = e.id
                AND et_en.language_id = (SELECT id FROM language WHERE code = 'en')
            WHERE e.id = :id AND e.entity_type = 'film' AND e.status = 'published'
        """)
        row = (
            await self.db.execute(sql, {"id": entity_id, "lang": lang})
        ).mappings().first()
        return dict(row) if row else None

    async def _fetch_kinopoisk(self, city: CityRef) -> list[KinopoiskAfishaFilm]:
        async with KinopoiskAfishaParser() as parser:
            return await parser.fetch_city_afisha(city)

    async def _tmdb_as_kp_fallback(self, city: CityRef) -> list[KinopoiskAfishaFilm]:
        if not settings.tmdb_api_key:
            return []
        async with TmdbClient(api_key=settings.tmdb_api_key) as tmdb:
            rows = await tmdb.now_playing(region="RU", pages=3, language="ru-RU")
        out: list[KinopoiskAfishaFilm] = []
        for row in rows:
            tmdb_id = row.get("id")
            if not tmdb_id:
                continue
            title = row.get("title") or row.get("original_title") or f"Фильм {tmdb_id}"
            out.append(
                KinopoiskAfishaFilm(
                    kinopoisk_id=0,
                    title=title,
                    ticket_url=(
                        f"https://www.kinopoisk.ru/index.php?kp_query={quote(title)}"
                    ),
                    tmdb_id=int(tmdb_id),
                ),
            )
        return out

    async def _tmdb_now_playing_map(self, *, lang: str) -> dict[int, dict]:
        if not settings.tmdb_api_key:
            return {}
        language = "ru-RU" if lang == "ru" else "en-US"
        async with TmdbClient(api_key=settings.tmdb_api_key) as tmdb:
            rows = await tmdb.now_playing(region="RU", pages=3, language=language)
        return {int(r["id"]): r for r in rows if r.get("id")}

    async def _load_entity_maps(
        self,
        kp_ids: list[int],
        *,
        titles: list[str],
        lang: str,
    ) -> tuple[dict[int, dict], dict[str, dict]]:
        by_kp: dict[int, dict] = {}
        by_title: dict[str, dict] = {}

        real_kp = [kid for kid in kp_ids if kid > 0]
        if real_kp:
            sql = text("""
                SELECT
                    e.id,
                    e.primary_image_url AS img_primary,
                    e.thumbnail_url AS img_thumb,
                    e.external_ids,
                    f.release_year,
                    COALESCE(et_lang.title, et_en.title, f.sort_title) AS title,
                    COALESCE(et_lang.summary, et_en.summary) AS summary,
                    (e.external_ids->>'kinopoisk')::bigint AS kinopoisk_id,
                    (e.external_ids->>'tmdb')::int AS tmdb_id
                FROM entity e
                JOIN film f ON f.id = e.id
                LEFT JOIN entity_translation et_lang
                    ON et_lang.entity_id = e.id
                    AND et_lang.language_id = (SELECT id FROM language WHERE code = :lang)
                LEFT JOIN entity_translation et_en
                    ON et_en.entity_id = e.id
                    AND et_en.language_id = (SELECT id FROM language WHERE code = 'en')
                WHERE e.entity_type = 'film'
                  AND e.status = 'published'
                  AND e.external_ids ? 'kinopoisk'
                  AND (e.external_ids->>'kinopoisk')::bigint = ANY(:kp_ids)
            """)
            rows = (
                await self.db.execute(sql, {"kp_ids": real_kp, "lang": lang})
            ).mappings().all()
            for r in rows:
                rec = dict(r)
                if r["kinopoisk_id"]:
                    by_kp[int(r["kinopoisk_id"])] = rec
                key = _norm_title(r["title"] or "")
                if key:
                    by_title[key] = rec

        await self._fill_title_matches(titles, by_title, lang=lang)
        return by_kp, by_title

    async def _fill_title_matches(
        self,
        titles: list[str],
        by_title: dict[str, dict],
        *,
        lang: str,
    ) -> None:
        """Подтягивает entity по названиям (для TMDB-fallback и парсера без kp id в БД)."""
        wanted = {_norm_title(t) for t in titles if t}
        missing = [t for t in wanted if t and t not in by_title]
        if not missing:
            return

        sql = text("""
            SELECT
                e.id,
                e.primary_image_url AS img_primary,
                e.thumbnail_url AS img_thumb,
                e.external_ids,
                f.release_year,
                COALESCE(et_lang.title, et_en.title, f.sort_title) AS title,
                COALESCE(et_lang.summary, et_en.summary) AS summary,
                (e.external_ids->>'tmdb')::int AS tmdb_id
            FROM entity e
            JOIN film f ON f.id = e.id
            LEFT JOIN entity_translation et_lang
                ON et_lang.entity_id = e.id
                AND et_lang.language_id = (SELECT id FROM language WHERE code = :lang)
            LEFT JOIN entity_translation et_en
                ON et_en.entity_id = e.id
                AND et_en.language_id = (SELECT id FROM language WHERE code = 'en')
            WHERE e.entity_type = 'film'
              AND e.status = 'published'
            ORDER BY (e.extra_metadata->>'popularity')::float DESC NULLS LAST
            LIMIT 5000
        """)
        rows = (await self.db.execute(sql, {"lang": lang})).mappings().all()
        for r in rows:
            key = _norm_title(r["title"] or "")
            if key and key not in by_title:
                by_title[key] = dict(r)

    def _build_item(
        self,
        kp: KinopoiskAfishaFilm,
        *,
        city: CityRef,
        db_by_kp: dict[int, dict],
        db_by_title: dict[str, dict],
        tmdb_by_id: dict[int, dict],
    ) -> dict | None:
        db_row: dict[str, Any] | None = None
        if kp.kinopoisk_id > 0:
            db_row = db_by_kp.get(kp.kinopoisk_id)
        if db_row is None:
            db_row = db_by_title.get(_norm_title(kp.title))

        tmdb_id: int | None = kp.tmdb_id
        if db_row:
            tmdb_id = db_row.get("tmdb_id")
            if isinstance(db_row.get("external_ids"), dict):
                raw = db_row["external_ids"].get("tmdb")
                if raw:
                    try:
                        tmdb_id = int(raw)
                    except (TypeError, ValueError):
                        pass

        tmdb_row = tmdb_by_id.get(tmdb_id) if tmdb_id else None
        if tmdb_row is None:
            for row in tmdb_by_id.values():
                if _norm_title(row.get("title") or "") == _norm_title(kp.title):
                    tmdb_row = row
                    tmdb_id = int(row["id"])
                    break

        title = kp.title
        summary = None
        release_year = None
        img_primary = None
        img_thumb = None
        entity_id = None

        if db_row:
            entity_id = db_row["id"]
            title = db_row["title"] or title
            summary = db_row.get("summary")
            release_year = db_row.get("release_year")
            img_primary = db_row.get("img_primary")
            img_thumb = db_row.get("img_thumb")

        if tmdb_row:
            if not img_primary and tmdb_row.get("poster_path"):
                img_primary = f"{TMDB_IMAGE_BASE}/w500{tmdb_row['poster_path']}"
            if release_year is None and tmdb_row.get("release_date"):
                try:
                    release_year = int(str(tmdb_row["release_date"])[:4])
                except ValueError:
                    pass
            if not summary and tmdb_row.get("overview"):
                summary = tmdb_row["overview"]
            if not title or title.startswith("Фильм "):
                title = tmdb_row.get("title") or title

        ticket_url = kp.ticket_url
        if kp.kinopoisk_id <= 0 and tmdb_id:
            ticket_url = (
                f"https://www.kinopoisk.ru/afisha/city/{city.kp_city_id}/"
                f"?kp_query={quote(title)}"
            )

        return {
            "kinopoisk_id": kp.kinopoisk_id if kp.kinopoisk_id > 0 else None,
            "title": title,
            "entity_id": entity_id,
            "release_year": release_year,
            "summary": summary,
            "images": {"primary": img_primary, "thumbnail": img_thumb},
            "ticket_url": ticket_url,
            "ticket_provider": "kinopoisk",
            "cinemas": kp.cinemas[:8],
            "in_database": entity_id is not None,
            "tmdb_id": tmdb_id,
        }
