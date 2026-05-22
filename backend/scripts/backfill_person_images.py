"""
Дозагрузка фото режиссёров из TMDB (+ запасные источники) в entity.primary_image_url.

Этапы для каждой персоны без фото:
  1. TMDB person profile_path (/person/{id})
  2. TMDB /person/{id}/images → profiles[]
  3. TMDB /find/{imdb} → person_results[].profile_path
  4. TMDB /search/person по имени (если нет tmdb id) + сохранение tmdb в external_ids
  5. Постер последнего фильма режиссёра из нашей БД (--film-fallback, по умолчанию вкл.)

Запуск:
    python -m scripts.backfill_person_images --graph-only
    python -m scripts.backfill_person_images --graph-only --no-search-names
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import re
import unicodedata

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from scripts.tmdb_client import TmdbClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
log = logging.getLogger("backfill-person-images")

LANG = "en-US"


def _missing_image_clause() -> str:
    return """(
        e.primary_image_url IS NULL
        OR trim(e.primary_image_url) = ''
    )"""


def norm_name(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^\w\s]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def paths_to_urls(path: str | None) -> tuple[str | None, str | None]:
    return (
        TmdbClient.image_url(path, "w500"),
        TmdbClient.image_url(path, "w185"),
    )


async def set_images(
    db: AsyncSession,
    person_id: int,
    *,
    primary: str | None,
    thumb: str | None,
) -> bool:
    if not primary:
        return False
    await db.execute(
        text("""
            UPDATE entity
            SET primary_image_url = :p,
                thumbnail_url = COALESCE(:t, :p)
            WHERE id = :id
        """),
        {"id": person_id, "p": primary, "t": thumb},
    )
    return True


async def save_tmdb_id(db: AsyncSession, person_id: int, tmdb_id: int) -> None:
    await db.execute(
        text("""
            UPDATE entity
            SET external_ids = COALESCE(external_ids, '{}'::jsonb)
                || jsonb_build_object('tmdb', CAST(:tid AS text))
            WHERE id = :id
              AND NOT (COALESCE(external_ids, '{}'::jsonb) ? 'tmdb')
        """),
        {"id": person_id, "tid": str(tmdb_id)},
    )


async def film_poster_from_db(db: AsyncSession, person_id: int) -> str | None:
    return (
        await db.execute(
            text("""
                SELECT fe.primary_image_url
                FROM film_person fp
                JOIN entity fe ON fe.id = fp.film_id
                JOIN film f ON f.id = fp.film_id
                WHERE fp.person_id = :pid
                  AND fp.role_type = 'director'
                  AND fe.primary_image_url IS NOT NULL
                  AND trim(fe.primary_image_url) <> ''
                ORDER BY f.release_year DESC NULLS LAST
                LIMIT 1
            """),
            {"pid": person_id},
        )
    ).scalar_one_or_none()


async def resolve_tmdb_id(
    tmdb: TmdbClient,
    *,
    tmdb_id: int | None,
    imdb_id: str | None,
    search_name: str | None,
    allow_search: bool,
) -> tuple[int | None, str | None]:
    """
    Возвращает (tmdb_person_id, profile_path из find/search если есть).
    """
    find_path: str | None = None

    if tmdb_id:
        return tmdb_id, None

    if imdb_id and imdb_id.startswith("nm"):
        found = await tmdb.find_by_imdb(imdb_id, language=LANG)
        people = (found or {}).get("person_results") or []
        if people:
            p0 = people[0]
            find_path = p0.get("profile_path")
            return int(p0["id"]), find_path

    if allow_search and search_name and len(search_name.strip()) >= 3:
        results = await tmdb.search_person(search_name.strip(), language=LANG)
        picked = pick_search_result(search_name, results)
        if picked:
            return int(picked["id"]), picked.get("profile_path")

    return None, find_path


def pick_search_result(query: str, results: list[dict]) -> dict | None:
    if not results:
        return None
    q = norm_name(query)
    exact = [r for r in results if norm_name(r.get("name") or "") == q]
    pool = exact or results
    with_photo = [r for r in pool if r.get("profile_path")]
    directors = [
        r for r in pool
        if (r.get("known_for_department") or "").lower() == "directing"
    ]
    if directors:
        return directors[0]
    if with_photo:
        return with_photo[0]
    return pool[0]


async def fetch_tmdb_photo_urls(
    tmdb: TmdbClient,
    tmdb_person_id: int,
    *,
    hint_path: str | None = None,
) -> tuple[str | None, str | None, str]:
    """Возвращает (primary, thumb, source_label)."""
    if hint_path:
        p, t = paths_to_urls(hint_path)
        if p:
            return p, t, "find/search"

    data = await tmdb.person_full(tmdb_person_id, language=LANG)
    p, t = paths_to_urls(data.get("profile_path"))
    if p:
        return p, t, "person"

    images = await tmdb.person_images(tmdb_person_id)
    profiles = images.get("profiles") or []
    if profiles:
        best = max(
            profiles,
            key=lambda x: float(x.get("vote_average") or 0),
        )
        p, t = paths_to_urls(best.get("file_path"))
        if p:
            return p, t, "person_images"

    return None, None, ""


async def main(
    *,
    limit: int | None,
    dry_run: bool,
    graph_only: bool,
    only_directors: bool,
    search_names: bool,
    film_fallback: bool,
) -> None:
    if not settings.tmdb_api_key:
        raise SystemExit("TMDB_API_KEY не задан в .env")

    graph_filter = ""
    if graph_only:
        graph_filter = """
            AND EXISTS (
                SELECT 1 FROM director_influence di
                WHERE di.source_director_id = p.id
                   OR di.target_director_id = p.id
            )
        """

    role_filter = "p.is_director = true" if only_directors else "true"

    id_clause = """
          AND (
              e.external_ids ? 'tmdb'
              OR (
                  e.external_ids ? 'imdb'
                  AND e.external_ids->>'imdb' LIKE 'nm%'
              )
          )
    """
    if search_names:
        id_clause = """
          AND (
              e.external_ids ? 'tmdb'
              OR (
                  e.external_ids ? 'imdb'
                  AND e.external_ids->>'imdb' LIKE 'nm%'
              )
              OR COALESCE(et.title, p.sort_name) IS NOT NULL
          )
        """

    sql = f"""
        SELECT
            p.id AS person_id,
            NULLIF(e.external_ids->>'tmdb', '')::int AS tmdb_id,
            e.external_ids->>'imdb' AS imdb_id,
            COALESCE(et.title, p.sort_name) AS name_en,
            COALESCE(et_ru.title, p.sort_name) AS name_ru
        FROM person p
        JOIN entity e ON e.id = p.id
        LEFT JOIN entity_translation et
            ON et.entity_id = p.id
           AND et.language_id = (
               SELECT id FROM language WHERE code = 'en' LIMIT 1
           )
        LEFT JOIN entity_translation et_ru
            ON et_ru.entity_id = p.id
           AND et_ru.language_id = (
               SELECT id FROM language WHERE code = 'ru' LIMIT 1
           )
        WHERE {role_filter}
          AND e.status = 'published'
          AND {_missing_image_clause()}
          {id_clause}
          {graph_filter}
        ORDER BY p.id
    """
    if limit:
        sql += f" LIMIT {int(limit)}"

    async with AsyncSessionLocal() as db:
        rows = [dict(r) for r in (await db.execute(text(sql))).mappings().all()]

    log.info(
        "к обработке: %d (dry_run=%s, graph_only=%s, search=%s, film_fb=%s)",
        len(rows),
        dry_run,
        graph_only,
        search_names,
        film_fallback,
    )

    stats = {
        "updated": 0,
        "from_film_db": 0,
        "linked_tmdb": 0,
        "no_photo_anywhere": 0,
        "no_tmdb_resolved": 0,
        "errors": 0,
    }
    by_source: dict[str, int] = {}

    async with TmdbClient(api_key=settings.tmdb_api_key) as tmdb:
        for i, row in enumerate(rows):
            pid = row["person_id"]
            name = row["name_en"] or row["name_ru"] or "?"
            search_query = row["name_en"] or row["name_ru"]
            try:
                tid, hint_path = await resolve_tmdb_id(
                    tmdb,
                    tmdb_id=row["tmdb_id"],
                    imdb_id=row["imdb_id"],
                    search_name=search_query,
                    allow_search=search_names,
                )

                primary: str | None = None
                thumb: str | None = None
                source = ""

                if tid:
                    primary, thumb, source = await fetch_tmdb_photo_urls(
                        tmdb, tid, hint_path=hint_path,
                    )
                    if not row["tmdb_id"] and not dry_run:
                        async with AsyncSessionLocal() as db:
                            await save_tmdb_id(db, pid, tid)
                            await db.commit()
                        stats["linked_tmdb"] += 1
                else:
                    stats["no_tmdb_resolved"] += 1

                if not primary and film_fallback:
                    async with AsyncSessionLocal() as db:
                        poster = await film_poster_from_db(db, pid)
                    if poster:
                        primary = poster
                        thumb = poster
                        source = "film_poster_db"
                        stats["from_film_db"] += 1

                if not primary:
                    stats["no_photo_anywhere"] += 1
                    log.debug("[%d] без фото: %s", i, name)
                    continue

                by_source[source] = by_source.get(source, 0) + 1

                if dry_run:
                    log.info("[%d] would %s → %s (%s)", i, name, primary[:55], source)
                    stats["updated"] += 1
                    continue

                async with AsyncSessionLocal() as db:
                    if await set_images(db, pid, primary=primary, thumb=thumb):
                        await db.commit()
                        stats["updated"] += 1

                if stats["updated"] % 25 == 0:
                    log.info("  … обновлено %d", stats["updated"])
            except Exception as exc:
                stats["errors"] += 1
                log.warning("[%d] %s: %s", i, name, exc)

    log.info("─── DONE ───")
    log.info("фото проставлено:        %d", stats["updated"])
    log.info("  из них постер фильма:  %d", stats["from_film_db"])
    log.info("привязан tmdb (search):  %d", stats["linked_tmdb"])
    log.info("не нашли tmdb id:        %d", stats["no_tmdb_resolved"])
    log.info("совсем без картинки:     %d", stats["no_photo_anywhere"])
    log.info("ошибок:                  %d", stats["errors"])
    if by_source:
        log.info("источники: %s", by_source)


def cli() -> None:
    p = argparse.ArgumentParser(description="Фото персон: TMDB + постер фильма")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--graph-only", action="store_true")
    p.add_argument("--all-persons", action="store_true")
    p.add_argument(
        "--no-search-names",
        action="store_true",
        help="Не искать в TMDB по имени, если нет tmdb/imdb",
    )
    p.add_argument(
        "--no-film-fallback",
        action="store_true",
        help="Не брать постер последнего фильма из БД",
    )
    args = p.parse_args()
    asyncio.run(
        main(
            limit=args.limit,
            dry_run=args.dry_run,
            graph_only=args.graph_only,
            only_directors=not args.all_persons,
            search_names=not args.no_search_names,
            film_fallback=not args.no_film_fallback,
        )
    )


if __name__ == "__main__":
    cli()
