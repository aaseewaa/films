"""
Загрузчик одного фильма по названию или TMDB id.

Запуск из папки backend/:
    python -m scripts.load_film_by_title --title "Skate Kitchen" --year 2018
    python -m scripts.load_film_by_title --tmdb-id 476600
    python -m scripts.load_film_by_title --file scripts/films_to_load.txt
    python -m scripts.load_film_by_title --title "Daughters of the Dust" --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
from datetime import date
from pathlib import Path

import httpx
from slugify import slugify
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
)
log = logging.getLogger("film-loader")

TMDB_BASE = "https://api.themoviedb.org/3"
POSTER_BASE = "https://image.tmdb.org/t/p/w500"
TOP_ACTORS = 10


async def tmdb_get(client: httpx.AsyncClient, path: str, params: dict) -> dict:
    params["api_key"] = settings.tmdb_api_key
    r = await client.get(f"{TMDB_BASE}{path}", params=params, timeout=15)
    r.raise_for_status()
    return r.json()


async def search_film(client: httpx.AsyncClient, title: str, year: int | None = None) -> list[dict]:
    params: dict = {"query": title, "language": "ru-RU"}
    if year:
        params["year"] = year
    data = await tmdb_get(client, "/search/movie", params)
    return data.get("results", [])


async def get_movie_details(client: httpx.AsyncClient, tmdb_id: int, lang: str) -> dict:
    return await tmdb_get(client, f"/movie/{tmdb_id}",
                          {"language": lang, "append_to_response": "credits"})


async def get_lang_ids(db: AsyncSession) -> dict[str, int]:
    rows = (await db.execute(text(
        "SELECT id, code FROM language WHERE code IN ('ru','en')"
    ))).mappings().all()
    result = {r["code"]: r["id"] for r in rows}
    if "ru" not in result or "en" not in result:
        raise SystemExit("Языки ru/en не найдены. Прогони seed.sql.")
    return result


async def find_entity_by_tmdb(db: AsyncSession, entity_type: str, tmdb_id: int) -> int | None:
    # FIX: передаём tmdb_id как строку-параметр, без ::text в SQL
    return (await db.execute(text("""
        SELECT id FROM entity
        WHERE entity_type = CAST(:t AS entity_type)
          AND external_ids->>'tmdb' = :tid
        LIMIT 1
    """), {"t": entity_type, "tid": str(tmdb_id)})).scalar_one_or_none()


async def upsert_genre(db: AsyncSession, tmdb_genre_id: int, name_en: str,
                       name_ru: str | None, lang_ids: dict) -> int:
    code = f"tmdb-{tmdb_genre_id}"
    term_id = (await db.execute(text("""
        INSERT INTO taxonomy_term (term_type, code, is_system, sort_order)
        VALUES ('genre', :code, true, 0)
        ON CONFLICT (term_type, code) DO UPDATE SET code = EXCLUDED.code
        RETURNING id
    """), {"code": code})).scalar_one()
    for lc, name in [("en", name_en), ("ru", name_ru or name_en)]:
        await db.execute(text("""
            INSERT INTO taxonomy_term_translation (term_id, language_id, slug, name)
            VALUES (:tid, :lid, :slug, :name)
            ON CONFLICT (term_id, language_id) DO UPDATE SET name = EXCLUDED.name
        """), {"tid": term_id, "lid": lang_ids[lc],
               "slug": slugify(name)[:255], "name": name})
    await db.commit()
    return term_id


async def upsert_person(db: AsyncSession, *, tmdb_id: int, name_en: str,
                         name_ru: str | None, profile_path: str | None,
                         biography_ru: str | None, biography_en: str | None,
                         birthday: str | None, deathday: str | None,
                         place_of_birth: str | None,
                         is_director: bool, is_actor: bool,
                         lang_ids: dict) -> int:
    existing_id = await find_entity_by_tmdb(db, "person", tmdb_id)
    if existing_id:
        await db.execute(text("""
            UPDATE person SET
                is_director = is_director OR :is_dir,
                is_actor    = is_actor    OR :is_act
            WHERE id = :id
        """), {"id": existing_id, "is_dir": is_director, "is_act": is_actor})
        await db.commit()
        return existing_id

    person_id = (await db.execute(text("""
        INSERT INTO entity (entity_type, status, primary_image_url, external_ids, extra_metadata)
        VALUES ('person', 'published', :img,
                jsonb_build_object('tmdb', CAST(:tid AS text)),
                '{}'::jsonb)
        RETURNING id
    """), {
        "img": f"{POSTER_BASE}{profile_path}" if profile_path else None,
        "tid": str(tmdb_id),
    })).scalar_one()

    bday = None
    if birthday:
        try: bday = date.fromisoformat(birthday)
        except ValueError: pass
    dday = None
    if deathday:
        try: dday = date.fromisoformat(deathday)
        except ValueError: pass

    await db.execute(text("""
        INSERT INTO person (id, is_director, is_actor, birth_date, death_date, birth_place)
        VALUES (:id, :is_dir, :is_act, :bday, :dday, :bplace)
    """), {"id": person_id, "is_dir": is_director, "is_act": is_actor,
           "bday": bday, "dday": dday, "bplace": place_of_birth})

    for lc, name, bio in [("ru", name_ru or name_en, biography_ru),
                            ("en", name_en, biography_en)]:
        slug_val = slugify(name_en)[:200] + f"-{tmdb_id}"
        await db.execute(text("""
            INSERT INTO entity_translation
                (entity_id, language_id, search_config, slug, title, description)
            VALUES (:eid, :lid, :cfg, :slug, :title, :desc)
            ON CONFLICT (entity_id, language_id) DO UPDATE SET
                title = EXCLUDED.title,
                description = COALESCE(EXCLUDED.description, entity_translation.description)
        """), {"eid": person_id, "lid": lang_ids[lc],
               "cfg": "russian" if lc == "ru" else "english",
               "slug": slug_val, "title": name, "desc": bio})

    await db.commit()
    return person_id


async def ensure_film_row(db: AsyncSession, *, film_id: int, release_date: date | None,
                          release_year: int | None, runtime: int | None,
                          sort_title: str) -> None:
    exists = (await db.execute(text(
        "SELECT 1 FROM film WHERE id = :id"
    ), {"id": film_id})).scalar_one_or_none()
    if exists:
        return
    await db.execute(text("""
        INSERT INTO film (id, release_date, release_year, runtime_min, sort_title)
        VALUES (:id, :rdate, :ryear, :runtime, :sort_title)
    """), {"id": film_id, "rdate": release_date, "ryear": release_year,
           "runtime": runtime, "sort_title": sort_title})


async def load_film(db: AsyncSession, client: httpx.AsyncClient,
                    tmdb_id: int, dry_run: bool = False) -> bool:
    log.info("Загружаю детали с TMDB (id=%d)...", tmdb_id)
    try:
        ru = await get_movie_details(client, tmdb_id, "ru-RU")
        en = await get_movie_details(client, tmdb_id, "en-US")
    except httpx.HTTPStatusError as e:
        log.error("TMDB вернул %d для id=%d", e.response.status_code, tmdb_id)
        return False

    title_ru    = ru.get("title") or en.get("title") or f"Film {tmdb_id}"
    title_en    = en.get("title") or title_ru
    overview_ru = ru.get("overview") or ""
    overview_en = en.get("overview") or ""
    tagline_ru  = ru.get("tagline") or ""
    tagline_en  = en.get("tagline") or ""
    release_str = ru.get("release_date") or en.get("release_date") or ""
    release_year = int(release_str[:4]) if release_str else None
    runtime      = ru.get("runtime") or en.get("runtime")
    poster_path  = ru.get("poster_path") or en.get("poster_path")
    vote_average = ru.get("vote_average")
    vote_count   = ru.get("vote_count")
    budget       = en.get("budget")
    revenue      = en.get("revenue")
    genres_ru    = ru.get("genres", [])
    genres_en    = en.get("genres", [])
    credits_ru   = ru.get("credits", {})
    credits_en   = en.get("credits", {})
    crew_ru      = {c["id"]: c for c in credits_ru.get("crew", [])}
    directors_en = [c for c in credits_en.get("crew", []) if c.get("job") == "Director"]
    cast_ru      = {c["id"]: c for c in credits_ru.get("cast", [])}
    cast_en      = credits_en.get("cast", [])[:TOP_ACTORS]

    log.info("─── %s / %s (%s) ───", title_ru, title_en, release_year or "?")
    log.info("  Режиссёры: %s", ", ".join(d["name"] for d in directors_en) or "нет")
    log.info("  Жанры: %s", ", ".join(g["name"] for g in genres_en))
    log.info("  Рейтинг TMDB: %.1f (%s голосов)", vote_average or 0, vote_count or 0)

    if dry_run:
        log.info("  [DRY RUN] — в БД не записываю.")
        return True

    lang_ids = await get_lang_ids(db)
    existing = await find_entity_by_tmdb(db, "film", tmdb_id)

    release_date = None
    if release_str:
        try: release_date = date.fromisoformat(release_str)
        except ValueError: pass

    extra_metadata = {
        "vote_average": vote_average,
        "vote_count": vote_count,
        "budget": budget,
        "revenue": revenue,
        "tagline": tagline_en or None,
    }

    if existing:
        log.info("  Фильм уже в БД (id=%d), обновляю...", existing)
        film_id = existing
        await ensure_film_row(
            db, film_id=film_id, release_date=release_date,
            release_year=release_year, runtime=runtime, sort_title=title_en,
        )
    else:
        film_id = (await db.execute(text("""
            INSERT INTO entity
                (entity_type, status, primary_image_url, external_ids,
                 published_at, extra_metadata)
            VALUES (
                'film', 'published', :poster,
                jsonb_build_object('tmdb', CAST(:tmdb_id AS text)),
                now(), CAST(:meta AS jsonb)
            )
            RETURNING id
        """), {
            "poster": f"{POSTER_BASE}{poster_path}" if poster_path else None,
            "tmdb_id": str(tmdb_id),
            "meta": json.dumps(extra_metadata),
        })).scalar_one()

        await ensure_film_row(
            db, film_id=film_id, release_date=release_date,
            release_year=release_year, runtime=runtime, sort_title=title_en,
        )
        log.info("  Создан с id=%d", film_id)

    for lc, title, overview, tagline in [
        ("ru", title_ru, overview_ru, tagline_ru),
        ("en", title_en, overview_en, tagline_en),
    ]:
        slug_val = slugify(title_en)[:200] + f"-{tmdb_id}"
        await db.execute(text("""
            INSERT INTO entity_translation
                (entity_id, language_id, search_config, slug, title, summary, description)
            VALUES (:eid, :lid, :cfg, :slug, :title, :summary, :desc)
            ON CONFLICT (entity_id, language_id) DO UPDATE SET
                title = EXCLUDED.title, summary = EXCLUDED.summary,
                description = EXCLUDED.description
        """), {"eid": film_id, "lid": lang_ids[lc],
               "cfg": "russian" if lc == "ru" else "english",
               "slug": slug_val, "title": title,
               "summary": tagline or overview[:300] if overview else None,
               "desc": overview})
    await db.commit()

    genre_map_ru = {g["id"]: g["name"] for g in genres_ru}
    for g in genres_en:
        gid = await upsert_genre(db, g["id"], g["name"],
                                  genre_map_ru.get(g["id"]), lang_ids)
        await db.execute(text("""
            INSERT INTO entity_taxonomy (entity_id, term_id, is_primary)
            VALUES (:eid, :tid, false)
            ON CONFLICT (entity_id, term_id) DO NOTHING
        """), {"eid": film_id, "tid": gid})
    await db.commit()
    log.info("  Жанры: OK")

    for dir_en in directors_en:
        pid = dir_en["id"]
        dir_ru = crew_ru.get(pid, dir_en)
        person_id = await upsert_person(
            db, tmdb_id=pid, name_en=dir_en["name"], name_ru=dir_ru.get("name"),
            profile_path=dir_en.get("profile_path"),
            biography_ru=None, biography_en=None,
            birthday=None, deathday=None, place_of_birth=None,
            is_director=True, is_actor=False, lang_ids=lang_ids)
        await db.execute(text("""
            INSERT INTO film_person (film_id, person_id, role_type, billing_order)
            VALUES (:fid, :pid, 'director', 0)
            ON CONFLICT (film_id, person_id, role_type) DO NOTHING
        """), {"fid": film_id, "pid": person_id})
    await db.commit()
    log.info("  Режиссёры: OK (%d)", len(directors_en))

    for idx, actor_en in enumerate(cast_en):
        pid = actor_en["id"]
        actor_ru = cast_ru.get(pid, actor_en)
        person_id = await upsert_person(
            db, tmdb_id=pid, name_en=actor_en["name"], name_ru=actor_ru.get("name"),
            profile_path=actor_en.get("profile_path"),
            biography_ru=None, biography_en=None,
            birthday=None, deathday=None, place_of_birth=None,
            is_director=False, is_actor=True, lang_ids=lang_ids)
        await db.execute(text("""
            INSERT INTO film_person (film_id, person_id, role_type, character_name, billing_order)
            VALUES (:fid, :pid, 'actor', :char, :order)
            ON CONFLICT (film_id, person_id, role_type) DO NOTHING
        """), {"fid": film_id, "pid": person_id,
               "char": actor_en.get("character"), "order": idx + 1})
    await db.commit()
    log.info("  Актёры: OK (%d)", len(cast_en))
    log.info("  ✅ Загружен: «%s» (entity id=%d)", title_ru, film_id)
    return True


def parse_entry(raw: str) -> tuple[str | None, int | None, int | None]:
    raw = raw.strip()
    if "#" in raw:
        raw = raw.split("#", 1)[0].strip()
    if not raw:
        return None, None, None
    if raw.isdigit():
        return None, None, int(raw)
    m = re.match(r"^(.+?)\s*\(?(\d{4})\)?$", raw)
    if m:
        return m.group(1).strip(), int(m.group(2)), None
    return raw, None, None


async def resolve_tmdb_id(client: httpx.AsyncClient,
                           title: str, year: int | None) -> int | None:
    results = await search_film(client, title, year)
    if not results:
        log.warning("  ⚠️  TMDB: ничего не найдено по «%s»%s",
                    title, f" ({year})" if year else "")
        return None
    if len(results) > 1:
        log.info("  Найдено %d результатов, беру первый:", len(results))
        for i, r in enumerate(results[:3]):
            log.info("    [%d] %s / %s (%s) — tmdb_id=%d",
                     i+1, r.get("title","?"), r.get("original_title","?"),
                     (r.get("release_date") or "")[:4] or "?", r["id"])
        log.info("  Если нужен другой — используй --tmdb-id <id>")
    first = results[0]
    log.info("  Выбран: «%s» (%s), tmdb_id=%d",
             first.get("title","?"), (first.get("release_date") or "")[:4] or "?", first["id"])
    return first["id"]


async def main() -> None:
    parser = argparse.ArgumentParser(description="Загрузить фильм(ы) в БД")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--title", "-t")
    group.add_argument("--tmdb-id", type=int)
    group.add_argument("--file", "-f")
    parser.add_argument("--year", "-y", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not settings.tmdb_api_key:
        raise SystemExit("❌ TMDB_API_KEY не задан в .env")

    queue: list[tuple] = []
    if args.title:
        queue.append((args.title, args.year, None))
    elif args.tmdb_id:
        queue.append((None, None, args.tmdb_id))
    elif args.file:
        path = Path(args.file)
        if not path.exists():
            raise SystemExit(f"❌ Файл не найден: {args.file}")
        for line in path.read_text(encoding="utf-8").splitlines():
            entry = parse_entry(line)
            if entry[0] or entry[2]:
                queue.append(entry)

    if not queue:
        raise SystemExit("❌ Очередь пуста")

    log.info("═══════════════════════════════════════")
    log.info("  Загрузка: %d фильм(ов)", len(queue))
    log.info("═══════════════════════════════════════")

    ok = fail = 0
    async with httpx.AsyncClient() as client:
        async with AsyncSession(engine) as db:
            for title, year, tmdb_id in queue:
                log.info("")
                if tmdb_id is None:
                    log.info("Ищу в TMDB: «%s»%s", title, f" ({year})" if year else "")
                    tmdb_id = await resolve_tmdb_id(client, title, year)
                    if tmdb_id is None:
                        fail += 1
                        continue
                success = await load_film(db, client, tmdb_id, dry_run=args.dry_run)
                if success: ok += 1
                else: fail += 1

    log.info("")
    log.info("═══════════════════════════════════════")
    log.info("  Готово: загружено %d, ошибок %d", ok, fail)
    log.info("═══════════════════════════════════════")


if __name__ == "__main__":
    asyncio.run(main())
