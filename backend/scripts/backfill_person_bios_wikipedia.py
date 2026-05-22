"""
Дозагрузка биографий режиссёров из Wikipedia (через Wikidata по IMDb id).

TMDB часто отдаёт пустой biography; у нас тексты лежат в entity_translation
(summary + description). Скрипт заполняет только пустые поля (если не --force).

Цепочка:
  1. IMDb id из entity.external_ids
  2. Wikidata SPARQL: imdb → Q-id
  3. wbgetentities: Q-id → enwiki / ruwiki заголовки
  4. Wikipedia API: intro extract
  5. UPDATE entity_translation (и опционально wikipedia_* в external_ids)

Запуск (из backend/):
    python -m scripts.backfill_person_bios_wikipedia --dry-run --limit 20
    python -m scripts.backfill_person_bios_wikipedia --graph-only
    python -m scripts.backfill_person_bios_wikipedia --lang ru

Требуется: IMDb id (python -m scripts.backfill_imdb_from_tmdb для догрузки).
Лицензия Wikipedia: CC BY-SA 3.0 — при публикации на сайте нужна атрибуция.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
from typing import Literal

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from scripts.wikidata_client import WikidataClient
from scripts.wikipedia_client import WikipediaClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
log = logging.getLogger("backfill-wiki-bios")

IMDB_BATCH = 40
WD_ENTITIES_URL = "https://www.wikidata.org/w/api.php"
WD_USER_AGENT = "FilmsDB-Diploma/0.1 (educational; student project)"

LangMode = Literal["both", "en", "ru"]


def _missing_bio_clause(lang: str) -> str:
    col = "et" if lang == "en" else "et_ru"
    return f"coalesce(trim({col}.description), '') = ''"


def build_imdb_to_qid_sparql(imdb_ids: list[str]) -> str:
    values = " ".join(f'"{i}"' for i in imdb_ids)
    return f"""
    SELECT ?imdb ?item WHERE {{
      VALUES ?imdb {{ {values} }}
      ?item wdt:P345 ?imdb .
      FILTER(STRSTARTS(STR(?imdb), "nm"))
    }}
    """


def binding_val(row: dict, key: str) -> str | None:
    cell = row.get(key)
    if not cell:
        return None
    return cell.get("value")


async def imdb_to_qids(wd: WikidataClient, imdb_ids: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for i in range(0, len(imdb_ids), IMDB_BATCH):
        batch = imdb_ids[i : i + IMDB_BATCH]
        rows = await wd._query(build_imdb_to_qid_sparql(batch))
        for row in rows:
            imdb = binding_val(row, "imdb")
            item_uri = binding_val(row, "item")
            if imdb and item_uri:
                qid = item_uri.rsplit("/", 1)[-1]
                out[imdb] = qid
        if i + IMDB_BATCH < len(imdb_ids):
            await asyncio.sleep(3)
    return out


async def qids_to_sitelinks(qids: list[str]) -> dict[str, dict[str, str]]:
    """Q-id → {'en': title, 'ru': title}."""
    result: dict[str, dict[str, str]] = {}
    if not qids:
        return result

    async with httpx.AsyncClient(
        timeout=60.0,
        headers={"User-Agent": WD_USER_AGENT},
    ) as client:
        for i in range(0, len(qids), 50):
            chunk = qids[i : i + 50]
            resp = await client.get(
                WD_ENTITIES_URL,
                params={
                    "action": "wbgetentities",
                    "format": "json",
                    "props": "sitelinks",
                    "ids": "|".join(chunk),
                },
            )
            if resp.status_code != 200:
                log.warning("wbgetentities HTTP %s", resp.status_code)
                continue
            entities = (resp.json().get("entities") or {})
            for qid, ent in entities.items():
                if ent.get("missing"):
                    continue
                links = ent.get("sitelinks") or {}
                titles: dict[str, str] = {}
                if "enwiki" in links:
                    titles["en"] = links["enwiki"]["title"]
                if "ruwiki" in links:
                    titles["ru"] = links["ruwiki"]["title"]
                if titles:
                    result[qid] = titles
            await asyncio.sleep(0.5)
    return result


def clean_wiki_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    # Убираем хвост «(born …)» если слишком длинный intro — оставляем как есть
    return text


async def get_languages(db: AsyncSession) -> dict[str, int]:
    rows = await db.execute(text("SELECT id, code FROM language"))
    return {r["code"]: r["id"] for r in rows.mappings().all()}


async def update_bio(
    db: AsyncSession,
    *,
    person_id: int,
    language_id: int,
    description: str,
    force: bool,
) -> bool:
    summary = description[:500] if len(description) > 500 else description
    if force:
        sql = """
            UPDATE entity_translation
            SET description = :desc, summary = :sum
            WHERE entity_id = :id AND language_id = :lid
        """
    else:
        sql = """
            UPDATE entity_translation
            SET description = :desc, summary = :sum
            WHERE entity_id = :id AND language_id = :lid
              AND coalesce(trim(description), '') = ''
        """
    r = await db.execute(
        text(sql),
        {"id": person_id, "lid": language_id, "desc": description, "sum": summary},
    )
    return (r.rowcount or 0) > 0


async def save_wiki_refs(
    db: AsyncSession,
    person_id: int,
    refs: dict[str, str],
) -> None:
    if not refs:
        return
    payload = json.dumps(refs)
    await db.execute(
        text("""
            UPDATE entity
            SET external_ids = COALESCE(external_ids, '{}'::jsonb) || CAST(:refs AS jsonb)
            WHERE id = :id
        """),
        {"id": person_id, "refs": payload},
    )


async def apply_person_updates(
    *,
    dry_run: bool,
    languages: dict[str, int],
    force: bool,
    pid: int,
    updates: dict[str, str],
    wiki_refs: dict[str, str],
    stats: dict[str, int],
) -> None:
    if dry_run:
        stats["updated_en"] += int("en" in updates)
        stats["updated_ru"] += int("ru" in updates)
        return

    async with AsyncSessionLocal() as db:
        changed = False
        if "en" in updates and "en" in languages:
            if await update_bio(
                db,
                person_id=pid,
                language_id=languages["en"],
                description=updates["en"],
                force=force,
            ):
                stats["updated_en"] += 1
                changed = True
        if "ru" in updates and "ru" in languages:
            if await update_bio(
                db,
                person_id=pid,
                language_id=languages["ru"],
                description=updates["ru"],
                force=force,
            ):
                stats["updated_ru"] += 1
                changed = True
        if changed and wiki_refs:
            await save_wiki_refs(db, pid, wiki_refs)
        if changed:
            await db.commit()


async def main(
    *,
    limit: int | None,
    dry_run: bool,
    graph_only: bool,
    only_directors: bool,
    lang_mode: LangMode,
    force: bool,
    search_fallback: bool,
    imdb_batch_pause: float,
    wiki_pause: float,
) -> None:
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

    need_en = lang_mode in ("both", "en")
    need_ru = lang_mode in ("both", "ru")
    bio_missing = []
    if need_en:
        bio_missing.append(_missing_bio_clause("en"))
    if need_ru:
        bio_missing.append(_missing_bio_clause("ru"))
    bio_clause = " AND ".join(f"({c})" for c in bio_missing) if bio_missing else "true"

    sql = f"""
        SELECT
            p.id AS person_id,
            e.external_ids->>'imdb' AS imdb_id,
            COALESCE(et.title, p.sort_name) AS name_en,
            COALESCE(et_ru.title, p.sort_name) AS name_ru,
            coalesce(trim(et.description), '') = '' AS missing_en,
            coalesce(trim(et_ru.description), '') = '' AS missing_ru
        FROM person p
        JOIN entity e ON e.id = p.id
        LEFT JOIN entity_translation et
            ON et.entity_id = p.id
           AND et.language_id = (SELECT id FROM language WHERE code = 'en' LIMIT 1)
        LEFT JOIN entity_translation et_ru
            ON et_ru.entity_id = p.id
           AND et_ru.language_id = (
               SELECT id FROM language WHERE code = 'ru' LIMIT 1
           )
        WHERE {role_filter}
          AND e.status = 'published'
          AND ({bio_clause})
          AND e.external_ids ? 'imdb'
          AND e.external_ids->>'imdb' LIKE 'nm%'
          {graph_filter}
        ORDER BY p.id
    """
    if limit:
        sql += f" LIMIT {int(limit)}"

    async with AsyncSessionLocal() as db:
        rows = [dict(r) for r in (await db.execute(text(sql))).mappings().all()]
        languages = await get_languages(db)

    log.info(
        "к обработке: %d (dry_run=%s, lang=%s, force=%s, search=%s)",
        len(rows),
        dry_run,
        lang_mode,
        force,
        search_fallback,
    )

    imdb_ids = [r["imdb_id"] for r in rows if r.get("imdb_id")]

    stats = {
        "updated_en": 0,
        "updated_ru": 0,
        "no_wikidata": 0,
        "no_sitelink": 0,
        "no_extract": 0,
        "no_imdb": 0,
        "errors": 0,
    }

    async with WikidataClient() as wd, WikipediaClient(pause_sec=wiki_pause) as wiki:
        imdb_to_qid = await imdb_to_qids(wd, imdb_ids)
        log.info("Wikidata Q-id: %d / %d imdb", len(imdb_to_qid), len(imdb_ids))

        qid_to_sitelinks = await qids_to_sitelinks(list(imdb_to_qid.values()))
        log.info("статьи Wikipedia (sitelinks): %d Q-id", len(qid_to_sitelinks))

        # person_id → {lang: title} для batch-загрузки
        pending: dict[int, dict[str, str]] = {}
        row_by_pid = {r["person_id"]: r for r in rows}

        for row in rows:
            imdb = row.get("imdb_id")
            if not imdb:
                stats["no_imdb"] += 1
                continue

            pid = row["person_id"]
            qid = imdb_to_qid.get(imdb)
            sitelinks = qid_to_sitelinks.get(qid, {}) if qid else {}
            if not qid:
                stats["no_wikidata"] += 1

            titles: dict[str, str] = {}
            for lang in ("en", "ru"):
                if lang == "en" and (not need_en or not row["missing_en"]):
                    continue
                if lang == "ru" and (not need_ru or not row["missing_ru"]):
                    continue
                if sitelinks.get(lang):
                    titles[lang] = sitelinks[lang]

            if titles:
                pending[pid] = titles
            elif not search_fallback:
                stats["no_sitelink"] += 1

        # Пакетная загрузка intro (меньше запросов → меньше 429)
        for lang in ("en", "ru"):
            if lang == "en" and not need_en:
                continue
            if lang == "ru" and not need_ru:
                continue

            jobs = [
                (pid, titles[lang])
                for pid, titles in pending.items()
                if lang in titles
            ]
            if not jobs:
                continue

            log.info("Wikipedia batch %s: %d статей", lang, len(jobs))
            titles_only = [t for _, t in jobs]
            extracts: dict[str, str] = {}
            for i in range(0, len(titles_only), 15):
                chunk = titles_only[i : i + 15]
                part = await wiki.fetch_intros_batch(lang, chunk)
                extracts.update(part)

            for pid, title in jobs:
                row = row_by_pid[pid]
                name = row["name_en"] or row["name_ru"] or "?"
                key = title.replace(" ", "_")
                raw = extracts.get(key) or extracts.get(title)
                if not raw:
                    stats["no_extract"] += 1
                    continue
                text_clean = clean_wiki_text(raw)
                if len(text_clean) < 40:
                    stats["no_extract"] += 1
                    continue

                updates = {lang: text_clean}
                wiki_refs = {f"wikipedia_{lang}": title}
                try:
                    await apply_person_updates(
                        dry_run=dry_run,
                        languages=languages,
                        force=force,
                        pid=pid,
                        updates=updates,
                        wiki_refs=wiki_refs,
                        stats=stats,
                    )
                except Exception as exc:
                    stats["errors"] += 1
                    log.warning("%s: %s", name, exc)

        # Опционально: opensearch только для языков без sitelink
        if search_fallback:
            log.info("opensearch fallback…")
            for row in rows:
                imdb = row.get("imdb_id")
                if not imdb:
                    continue
                pid = row["person_id"]
                known = pending.get(pid, {})
                name = row["name_en"] or row["name_ru"] or "?"
                updates: dict[str, str] = {}
                wiki_refs: dict[str, str] = {}
                try:
                    for lang in ("en", "ru"):
                        if lang == "en" and (not need_en or not row["missing_en"]):
                            continue
                        if lang == "ru" and (not need_ru or not row["missing_ru"]):
                            continue
                        if known.get(lang):
                            continue
                        q = row["name_en"] if lang == "en" else (row["name_ru"] or row["name_en"])
                        if not q:
                            stats["no_sitelink"] += 1
                            continue
                        title = await wiki.search_title(lang, q)
                        if not title:
                            stats["no_sitelink"] += 1
                            continue
                        raw = await wiki.fetch_intro(lang, title)
                        if not raw or len(clean_wiki_text(raw)) < 40:
                            stats["no_extract"] += 1
                            continue
                        updates[lang] = clean_wiki_text(raw)
                        wiki_refs[f"wikipedia_{lang}"] = title
                    if updates:
                        await apply_person_updates(
                            dry_run=dry_run,
                            languages=languages,
                            force=force,
                            pid=pid,
                            updates=updates,
                            wiki_refs=wiki_refs,
                            stats=stats,
                        )
                except Exception as exc:
                    stats["errors"] += 1
                    log.warning("%s: %s", name, exc)

            if imdb_batch_pause:
                await asyncio.sleep(imdb_batch_pause)

    log.info("─── DONE ───")
    log.info("обновлено EN:           %d", stats["updated_en"])
    log.info("обновлено RU:           %d", stats["updated_ru"])
    log.info("без Wikidata Q-id:      %d", stats["no_wikidata"])
    log.info("без sitelink:           %d", stats["no_sitelink"])
    log.info("статья без текста:      %d", stats["no_extract"])
    if wiki_pause:
        log.info("(wiki_pause=%.1fs)", wiki_pause)
    log.info("ошибок:                 %d", stats["errors"])


def cli() -> None:
    p = argparse.ArgumentParser(
        description="Биографии режиссёров из Wikipedia (Wikidata → sitelinks → intro)",
    )
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--graph-only", action="store_true", help="Только режиссёры из director_influence")
    p.add_argument("--all-persons", action="store_true")
    p.add_argument("--force", action="store_true", help="Перезаписать непустые description")
    p.add_argument(
        "--lang",
        choices=["both", "en", "ru"],
        default="both",
        help="Какие переводы заполнять",
    )
    p.add_argument(
        "--search-fallback",
        action="store_true",
        help="Если нет sitelink — opensearch Wikipedia по имени",
    )
    p.add_argument(
        "--wiki-pause",
        type=float,
        default=1.2,
        help="Пауза между запросами к Wikipedia (сек), по умолчанию 1.2",
    )
    args = p.parse_args()
    asyncio.run(
        main(
            limit=args.limit,
            dry_run=args.dry_run,
            graph_only=args.graph_only,
            only_directors=not args.all_persons,
            lang_mode=args.lang,
            force=args.force,
            search_fallback=args.search_fallback,
            imdb_batch_pause=0.0,
            wiki_pause=args.wiki_pause,
        )
    )


if __name__ == "__main__":
    cli()
