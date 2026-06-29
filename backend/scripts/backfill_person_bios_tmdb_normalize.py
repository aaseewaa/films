"""
Нормализация биографий режиссёров из TMDB.

Исправляет типичные проблемы:
  - дубли на странице (summary больше не обрезается до 500 символов description)
  - эмодзи и markdown TMDB (**жирный**)
  - короткие wiki-интро вместо полной биографии TMDB
  - отсутствие блока наград (берётся из TMDB biography или award_nomination)

Запуск (из backend/, venv):
    python -m scripts.backfill_person_bios_tmdb_normalize --dry-run --limit 5
    python -m scripts.backfill_person_bios_tmdb_normalize --person-id 2160 2172
    python -m scripts.backfill_person_bios_tmdb_normalize --force --lang ru
    python -m scripts.backfill_person_bios_tmdb_normalize --all-persons --force
"""
from __future__ import annotations

import argparse
import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from scripts.backfill_person_bios_wikipedia import get_languages
from scripts.person_bio_text import LangCode, build_person_bio_fields
from scripts.tmdb_client import TmdbClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
log = logging.getLogger("backfill-tmdb-bio-normalize")

TMDB_LANG = {"ru": "ru-RU", "en": "en-US"}
PAUSE_SEC = 0.25


async def fetch_person_awards(
    db: AsyncSession,
    person_id: int,
    *,
    lang: LangCode,
) -> list[dict]:
    rows = (
        await db.execute(
            text("""
                SELECT
                    n.status::text AS status,
                    c.year,
                    COALESCE(at_lang.name, at_en.name, a.code) AS award_name,
                    COALESCE(et_lang.title, et_en.title) AS film_title
                FROM award_nomination n
                JOIN award_ceremony c ON c.id = n.ceremony_id
                JOIN award a ON a.id = c.award_id
                LEFT JOIN award_translation at_lang
                    ON at_lang.award_id = a.id
                   AND at_lang.language_id = (SELECT id FROM language WHERE code = :lang)
                LEFT JOIN award_translation at_en
                    ON at_en.award_id = a.id
                   AND at_en.language_id = (SELECT id FROM language WHERE code = 'en')
                LEFT JOIN entity_translation et_lang
                    ON et_lang.entity_id = n.entity_id
                   AND et_lang.language_id = (SELECT id FROM language WHERE code = :lang)
                LEFT JOIN entity_translation et_en
                    ON et_en.entity_id = n.entity_id
                   AND et_en.language_id = (SELECT id FROM language WHERE code = 'en')
                WHERE n.person_id = :pid
                ORDER BY c.year DESC, (n.status = 'won') DESC
                LIMIT 20
            """),
            {"pid": person_id, "lang": lang},
        )
    ).mappings().all()
    return [dict(r) for r in rows]


async def fetch_candidates(
    db: AsyncSession,
    *,
    limit: int | None,
    only_directors: bool,
    person_ids: list[int] | None,
) -> list[dict]:
    role_filter = "p.is_director = true" if only_directors else "true"
    id_filter = ""
    params: dict = {}
    if person_ids:
        id_filter = "AND p.id = ANY(:ids)"
        params["ids"] = person_ids

    sql = f"""
        SELECT
            p.id AS person_id,
            (e.external_ids->>'tmdb')::int AS tmdb_id,
            COALESCE(et_ru.title, et_en.title, p.sort_name) AS name,
            length(coalesce(trim(et_ru.description), '')) AS ru_desc_len,
            length(coalesce(trim(et_en.description), '')) AS en_desc_len
        FROM person p
        JOIN entity e ON e.id = p.id
        LEFT JOIN entity_translation et_ru
            ON et_ru.entity_id = p.id
           AND et_ru.language_id = (SELECT id FROM language WHERE code = 'ru' LIMIT 1)
        LEFT JOIN entity_translation et_en
            ON et_en.entity_id = p.id
           AND et_en.language_id = (SELECT id FROM language WHERE code = 'en' LIMIT 1)
        WHERE e.entity_type = 'person'
          AND e.status = 'published'
          AND {role_filter}
          AND e.external_ids ? 'tmdb'
          {id_filter}
        ORDER BY p.id
    """
    if limit:
        sql += f" LIMIT {int(limit)}"
    rows = (await db.execute(text(sql), params)).mappings().all()
    return [dict(r) for r in rows]


async def upsert_bio_fields(
    db: AsyncSession,
    *,
    person_id: int,
    language_id: int,
    summary: str | None,
    description: str | None,
    force: bool,
) -> bool:
    if not summary and not description:
        return False

    if force:
        sql = """
            UPDATE entity_translation
            SET summary = :sum, description = :desc
            WHERE entity_id = :id AND language_id = :lid
        """
    else:
        sql = """
            UPDATE entity_translation
            SET summary = :sum, description = :desc
            WHERE entity_id = :id AND language_id = :lid
              AND (
                coalesce(trim(description), '') = ''
                OR coalesce(trim(summary), '') = coalesce(trim(description), '')
                OR length(coalesce(trim(description), '')) < 280
              )
        """
    r = await db.execute(
        text(sql),
        {"id": person_id, "lid": language_id, "sum": summary, "desc": description},
    )
    return (r.rowcount or 0) > 0


async def process_lang(
    *,
    tmdb: TmdbClient,
    db: AsyncSession,
    row: dict,
    lang: LangCode,
    languages: dict[str, int],
    force: bool,
    min_len: int,
    dry_run: bool,
) -> str:
    """Возвращает статус: updated | skipped | no_bio | too_short | error."""
    pid = row["person_id"]
    tid = row["tmdb_id"]
    name = row["name"] or "?"

    if lang not in languages:
        return "skipped"

    try:
        data = await tmdb.person_full(tid, language=TMDB_LANG[lang])
        raw_bio = (data.get("biography") or "").strip()
        if not raw_bio:
            if lang == "ru":
                data_en = await tmdb.person_full(tid, language=TMDB_LANG["en"])
                raw_bio = (data_en.get("biography") or "").strip()
            if not raw_bio:
                log.info("  %s [%s]: пустая biography в TMDB", name, lang)
                return "no_bio"

        db_awards = await fetch_person_awards(db, pid, lang=lang)
        summary, description = build_person_bio_fields(
            raw_bio,
            lang=lang,
            db_awards=db_awards,
        )
        total_len = len(summary or "") + len(description or "")
        if total_len < min_len:
            log.info("  %s [%s]: слишком коротко (%d симв.)", name, lang, total_len)
            return "too_short"

        if dry_run:
            log.info(
                "  %s [%s]: summary=%d desc=%d симв. | %s…",
                name,
                lang,
                len(summary or ""),
                len(description or ""),
                (summary or description or "")[:80],
            )
            return "updated"

        changed = await upsert_bio_fields(
            db,
            person_id=pid,
            language_id=languages[lang],
            summary=summary,
            description=description,
            force=force,
        )
        if changed:
            await db.commit()
            return "updated"
        log.info("  %s [%s]: пропуск (уже нормальная bio, без --force)", name, lang)
        return "skipped"
    except Exception as exc:
        log.warning("  %s [%s]: %s", name, lang, exc)
        return "error"


async def main(
    *,
    limit: int | None,
    dry_run: bool,
    only_directors: bool,
    person_ids: list[int] | None,
    langs: list[LangCode],
    force: bool,
    min_len: int,
    pause: float,
) -> None:
    if not settings.tmdb_api_key:
        raise SystemExit("TMDB_API_KEY не задан в .env")

    async with AsyncSessionLocal() as db:
        languages = await get_languages(db)
        rows = await fetch_candidates(
            db,
            limit=limit,
            only_directors=only_directors,
            person_ids=person_ids,
        )

    log.info(
        "к обработке: %d режиссёров (dry_run=%s, force=%s, langs=%s)",
        len(rows),
        dry_run,
        force,
        ",".join(langs),
    )

    stats = {k: 0 for k in ("updated", "skipped", "no_bio", "too_short", "errors")}

    async with TmdbClient(api_key=settings.tmdb_api_key) as tmdb:
        for i, row in enumerate(rows):
            log.info("[%d] %s (id=%s, tmdb=%s)", i, row["name"], row["person_id"], row["tmdb_id"])
            async with AsyncSessionLocal() as db:
                for lang in langs:
                    status = await process_lang(
                        tmdb=tmdb,
                        db=db,
                        row=row,
                        lang=lang,
                        languages=languages,
                        force=force,
                        min_len=min_len,
                        dry_run=dry_run,
                    )
                    if status == "error":
                        stats["errors"] += 1
                    else:
                        stats[status] += 1
            if pause:
                await asyncio.sleep(pause)

    log.info("─── DONE ───")
    log.info("обновлено:     %d", stats["updated"])
    log.info("пропущено:     %d", stats["skipped"])
    log.info("пусто TMDB:    %d", stats["no_bio"])
    log.info("слишком коротко:%d", stats["too_short"])
    log.info("ошибок:        %d", stats["errors"])


def cli() -> None:
    p = argparse.ArgumentParser(
        description="Нормализация биографий персон из TMDB (без эмодзи и дублей, с наградами)",
    )
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--force", action="store_true", help="Перезаписать все существующие bio")
    p.add_argument("--all-persons", action="store_true", help="Не только режиссёры")
    p.add_argument(
        "--person-id",
        type=int,
        nargs="+",
        default=None,
        help="Конкретные entity id (например 2160 2172)",
    )
    p.add_argument(
        "--lang",
        choices=("ru", "en", "both"),
        default="ru",
        help="Язык биографии (по умолчанию ru)",
    )
    p.add_argument("--min-len", type=int, default=80, help="Мин. длина итогового текста")
    p.add_argument("--pause", type=float, default=PAUSE_SEC)
    args = p.parse_args()

    langs: list[LangCode]
    if args.lang == "both":
        langs = ["ru", "en"]
    else:
        langs = [args.lang]  # type: ignore[list-item]

    asyncio.run(
        main(
            limit=args.limit,
            dry_run=args.dry_run,
            only_directors=not args.all_persons,
            person_ids=args.person_id,
            langs=langs,
            force=args.force,
            min_len=args.min_len,
            pause=args.pause,
        )
    )


if __name__ == "__main__":
    cli()
