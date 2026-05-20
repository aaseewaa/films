"""
Wikidata Influences loader v3.

Догружает связи через дополнительные свойства Wikidata:
  - P802 ("student") — кто был учеником данного человека
  - P184 ("doctoral advisor") — научный руководитель / наставник
  - P1066 ("student of") — обратное к P802
  - P2099 ("notable student") — известные ученики

Это РЕДКИЕ свойства — в Wikidata их заполнено меньше чем P737, но 
они дают качественные связи учитель→ученик, которые часто не 
помечены через "influenced by".

Пример: Хичкок→Линч может не быть в P737, но Линч в магистратуре
помечен как ученик Хичкока через P802.

ВАЖНО: семантика остаётся та же, что в твоей БД:
  source_director_id — кто ВДОХНОВИЛ / ПОВЛИЯЛ
  target_director_id — НА КОГО повлиял

Поэтому:
  - P802 ("X has student Y") → source=X, target=Y
  - P184 ("X has advisor Y") → source=Y, target=X
  - P1066 ("X is student of Y") → source=Y, target=X
  - P2099 ("X has notable student Y") → source=X, target=Y

Требует IMDb id у режиссёров (как v2). Если их нет:
    python -m scripts.backfill_imdb_from_tmdb

Запуск:
    cd backend
    source venv/bin/activate
    python -m scripts.load_wikidata_influences_v3
    python -m scripts.load_wikidata_influences_v3 --misses-file scripts/cache/wikidata_v3_miss.txt
    python -m scripts.load_wikidata_influences_v3 --autoload-missing
"""
from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from scripts.load_wikidata_influences_v2 import (
    find_person_by_imdb,
    get_directors_imdb_ids,
    get_languages,
    load_person_via_tmdb,
)
from scripts.tmdb_client import TmdbClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
log = logging.getLogger("wikidata-v3")
logging.getLogger("httpx").setLevel(logging.WARNING)


WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
USER_AGENT = "FilmCine/1.0 (educational; aaseewaa@diploma.local)"
BATCH_SIZE = 15
BATCH_PAUSE_SEC = 5


async def sparql_query(client: httpx.AsyncClient, query: str) -> list[dict]:
    """Один запрос к Wikidata SPARQL endpoint."""
    headers = {
        "Accept": "application/sparql-results+json",
        "User-Agent": USER_AGENT,
    }
    r = await client.get(
        WIKIDATA_SPARQL_URL,
        params={"query": query, "format": "json"},
        headers=headers,
        timeout=30.0,
    )
    r.raise_for_status()
    data = r.json()
    return data.get("results", {}).get("bindings", [])


async def insert_influence(
    db: AsyncSession,
    *,
    source_id: int,
    target_id: int,
    relation_note: str,
) -> bool:
    """Создаёт связь. Возвращает True если новая."""
    if source_id == target_id:
        return False
    try:
        result = await db.execute(text("""
            INSERT INTO director_influence (
                source_director_id, target_director_id,
                weight, confidence, relation_note, inferred_by_system
            ) VALUES (
                :src, :tgt, 1.0, 0.9, :note, false
            )
            ON CONFLICT (source_director_id, target_director_id) DO NOTHING
            RETURNING source_director_id
        """), {"src": source_id, "tgt": target_id, "note": relation_note})
        return result.first() is not None
    except Exception as exc:
        log.warning("    fail insert %d→%d: %s", source_id, target_id, exc)
        return False


# SPARQL по IMDb (P345), как в v2 — в БД хранятся tmdb/imdb, не wikidata QID.
SPARQL_TEMPLATES = {
    # P802 + P2099: master имеет ученика student → master влиял на student
    "P802_or_P2099_outgoing": """
SELECT ?masterImdb ?studentImdb WHERE {{
  VALUES ?masterImdb {{ {imdb_ids} }}
  ?master wdt:P345 ?masterImdb .
  {{ ?master wdt:P802 ?student . }}
  UNION
  {{ ?master wdt:P2099 ?student . }}
  ?student wdt:P345 ?studentImdb .
  FILTER(STRSTARTS(?studentImdb, "nm"))
}}
""",
    # P184 + P1066: student имеет учителя master → master влиял на student
    "P184_or_P1066_incoming": """
SELECT ?studentImdb ?masterImdb WHERE {{
  VALUES ?studentImdb {{ {imdb_ids} }}
  ?student wdt:P345 ?studentImdb .
  {{ ?student wdt:P184 ?master . }}
  UNION
  {{ ?student wdt:P1066 ?master . }}
  ?master wdt:P345 ?masterImdb .
  FILTER(STRSTARTS(?masterImdb, "nm"))
}}
""",
}


async def autoload_missing_imdbs(
    miss_imdbs: set[str],
    imdb_to_pid: dict[str, int],
) -> dict[str, int]:
    """Догружает персон из TMDB по IMDb и помечает is_director."""
    if not miss_imdbs:
        return imdb_to_pid
    if not settings.tmdb_api_key:
        raise SystemExit("TMDB_API_KEY не задан (--autoload-missing)")

    log.info("догрузка %d IMDb через TMDB…", len(miss_imdbs))
    stats = {"loaded": 0, "existed": 0, "miss": 0}

    async with AsyncSessionLocal() as db:
        languages = await get_languages(db)

    async with TmdbClient(api_key=settings.tmdb_api_key) as tmdb:
        for imdb in sorted(miss_imdbs):
            if imdb in imdb_to_pid:
                stats["existed"] += 1
                continue
            async with AsyncSessionLocal() as db:
                existing = await find_person_by_imdb(db, imdb)
                if existing:
                    await db.execute(text("""
                        UPDATE person SET is_director = true WHERE id = :id
                    """), {"id": existing})
                    await db.commit()
                    imdb_to_pid[imdb] = existing
                    stats["existed"] += 1
                    continue
                pid = await load_person_via_tmdb(
                    db, tmdb, imdb, fallback_name=imdb, languages=languages,
                )
                if pid:
                    await db.commit()
                    imdb_to_pid[imdb] = pid
                    stats["loaded"] += 1
                else:
                    stats["miss"] += 1

    log.info(
        "догрузка: новых=%d, уже были=%d, TMDB miss=%d",
        stats["loaded"], stats["existed"], stats["miss"],
    )
    return imdb_to_pid


async def process_property_v2(
    client: httpx.AsyncClient,
    imdb_to_pid: dict[str, int],
    miss_imdbs: set[str],
    *,
    query_key: str,
    direction: str,  # "outgoing" — этот человек влиял на других; "incoming" — на него влияли
) -> dict:
    """
    Обрабатывает запрос. Возвращает статистику и сразу пишет в БД.
    """
    template = SPARQL_TEMPLATES[query_key]
    stats = {"created": 0, "skipped": 0, "errors": 0, "queries": 0, "raw_pairs": 0}

    imdb_ids_in_db = list(imdb_to_pid.keys())
    log.info("─── %s [%s] ─── (режиссёров с IMDb: %d)",
             query_key, direction, len(imdb_ids_in_db))

    for batch_start in range(0, len(imdb_ids_in_db), BATCH_SIZE):
        batch = imdb_ids_in_db[batch_start : batch_start + BATCH_SIZE]
        imdb_str = " ".join(f'"{imdb}"' for imdb in batch)
        query = template.format(imdb_ids=imdb_str)

        try:
            results = await sparql_query(client, query)
            stats["queries"] += 1
        except Exception as exc:
            log.warning("  batch %d failed: %s", batch_start, exc)
            stats["errors"] += 1
            await asyncio.sleep(BATCH_PAUSE_SEC * 2)
            continue

        if results:
            log.info("  batch %d: получено %d сырых пар", batch_start, len(results))

        # Парсим и пишем в БД
        async with AsyncSessionLocal() as db:
            for r in results:
                stats["raw_pairs"] += 1
                src_imdb = r.get("masterImdb", {}).get("value")
                tgt_imdb = r.get("studentImdb", {}).get("value")
                if not src_imdb or not tgt_imdb:
                    continue

                src_pid = imdb_to_pid.get(src_imdb)
                tgt_pid = imdb_to_pid.get(tgt_imdb)

                if not src_pid or not tgt_pid:
                    stats["skipped"] += 1
                    if not src_pid:
                        miss_imdbs.add(src_imdb)
                    if not tgt_pid:
                        miss_imdbs.add(tgt_imdb)
                    continue

                # Создаём связь
                note = (
                    f"Wikidata {'P802/P2099 (student)' if direction == 'outgoing' else 'P184/P1066 (advisor)'}"
                )
                created = await insert_influence(
                    db,
                    source_id=src_pid,
                    target_id=tgt_pid,
                    relation_note=note,
                )
                if created:
                    stats["created"] += 1

            await db.commit()

        await asyncio.sleep(BATCH_PAUSE_SEC)

    return stats


async def run_sparql_pass(
    imdb_to_pid: dict[str, int],
    miss_imdbs: set[str],
) -> dict[str, int]:
    total = {"created": 0, "skipped": 0, "errors": 0, "queries": 0}

    async with httpx.AsyncClient() as client:
        stats1 = await process_property_v2(
            client, imdb_to_pid, miss_imdbs,
            query_key="P802_or_P2099_outgoing",
            direction="outgoing",
        )
        for k in total:
            total[k] += stats1.get(k, 0)
        log.info("  P802/P2099: создано связей %d (skipped: %d)",
                 stats1["created"], stats1["skipped"])

        stats2 = await process_property_v2(
            client, imdb_to_pid, miss_imdbs,
            query_key="P184_or_P1066_incoming",
            direction="incoming",
        )
        for k in total:
            total[k] += stats2.get(k, 0)
        log.info("  P184/P1066: создано связей %d (skipped: %d)",
                 stats2["created"], stats2["skipped"])

    return total


async def main(
    *,
    misses_file: str | None,
    autoload_missing: bool,
    second_pass: bool,
) -> None:
    log.info("═══════════════════════════════════════════════════")
    log.info(" Wikidata Influences v3 — P802 + P184 + P1066 + P2099")
    log.info("═══════════════════════════════════════════════════")

    async with AsyncSessionLocal() as db:
        directors = await get_directors_imdb_ids(db)
    imdb_to_pid = {imdb: pid for pid, imdb in directors}
    log.info("режиссёров с IMDb id в БД: %d", len(imdb_to_pid))

    if not imdb_to_pid:
        log.warning(
            "Нет режиссёров с IMDb id — сначала: "
            "python -m scripts.backfill_imdb_from_tmdb"
        )
        return

    miss_imdbs: set[str] = set()
    total = await run_sparql_pass(imdb_to_pid, miss_imdbs)

    if autoload_missing and miss_imdbs:
        imdb_to_pid = await autoload_missing_imdbs(miss_imdbs, imdb_to_pid)
        if second_pass:
            log.info("─── повторный прогон SPARQL после догрузки ───")
            miss_before = len(miss_imdbs)
            miss_imdbs.clear()
            pass_total = await run_sparql_pass(imdb_to_pid, miss_imdbs)
            for k in total:
                total[k] += pass_total.get(k, 0)
            log.info(
                "после догрузки: +%d связей, пропусков ещё %d (было уник. imdb: %d)",
                pass_total["created"], pass_total["skipped"], miss_before,
            )

    log.info("")
    log.info("═══════════════════════════════════════════════════")
    log.info("✅ Готово")
    log.info("   новых связей создано: %d", total["created"])
    log.info("   пропущено (нет в БД): %d", total["skipped"])
    log.info("   уникальных IMDb без пары в БД: %d", len(miss_imdbs))
    log.info("   ошибок:               %d", total["errors"])
    log.info("   SPARQL запросов:      %d", total["queries"])
    log.info("═══════════════════════════════════════════════════")

    if misses_file and miss_imdbs:
        path = Path(misses_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(sorted(miss_imdbs)) + "\n", encoding="utf-8")
        log.info("список IMDb → %s (%d шт.)", path, len(miss_imdbs))
        log.info("  python -m scripts.retry_imdb_persons --file %s", path)
        log.info("  python -m scripts.load_wikidata_influences_v3 --autoload-missing")

    async with AsyncSessionLocal() as db:
        cnt = (await db.execute(text("SELECT count(*) FROM director_influence"))).scalar_one()
        log.info("Всего связей в БД: %d", cnt)


def cli() -> None:
    p = argparse.ArgumentParser(
        description="Wikidata P802/P184/P1066/P2099 → director_influence",
    )
    p.add_argument(
        "--misses-file",
        type=str,
        default="scripts/cache/wikidata_v3_miss_imdb.txt",
        help="Сохранить IMDb, которых не было в БД (пустая строка = не писать)",
    )
    p.add_argument(
        "--autoload-missing",
        action="store_true",
        help="После SPARQL догрузить пропущенных через TMDB",
    )
    p.add_argument(
        "--no-second-pass",
        action="store_true",
        help="С --autoload-missing: не повторять SPARQL (только догрузка)",
    )
    args = p.parse_args()
    misses = args.misses_file.strip() or None
    asyncio.run(main(
        misses_file=misses,
        autoload_missing=args.autoload_missing,
        second_pass=not args.no_second_pass,
    ))


if __name__ == "__main__":
    cli()
