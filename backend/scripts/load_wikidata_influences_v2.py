"""
Точечный загрузчик связей влияния — версия 2 (с отладочными логами).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from scripts.tmdb_client import TmdbClient
from scripts.wikidata_client import WikidataClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
log = logging.getLogger("wikidata-v2")
logging.getLogger("httpx").setLevel(logging.WARNING)


LANG_EN = "en-US"
LANG_RU = "ru-RU"
BATCH_SIZE = 30


def build_sparql(imdb_ids: list[str]) -> str:
    values_block = " ".join(f'"{imdb}"' for imdb in imdb_ids)
    return f"""
    SELECT DISTINCT ?source ?sourceLabel ?sourceImdb
                    ?target ?targetLabel ?targetImdb
    WHERE {{
      VALUES ?ourImdb {{ {values_block} }}

      {{
        ?target wdt:P345 ?ourImdb .
        ?target wdt:P737 ?source .
      }} UNION {{
        ?source wdt:P345 ?ourImdb .
        ?target wdt:P737 ?source .
      }}

      ?source wdt:P345 ?sourceImdb .
      ?target wdt:P345 ?targetImdb .
      ?source wdt:P106 wd:Q2526255 .
      ?target wdt:P106 wd:Q2526255 .

      FILTER(STRSTARTS(?sourceImdb, "nm"))
      FILTER(STRSTARTS(?targetImdb, "nm"))

      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    LIMIT 5000
    """


async def get_languages(db: AsyncSession) -> dict[str, int]:
    result = await db.execute(text("SELECT id, code FROM language"))
    return {r["code"]: r["id"] for r in result.mappings().all()}


async def get_directors_imdb_ids(db: AsyncSession) -> list[tuple[int, str]]:
    sql = text("""
        SELECT p.id, e.external_ids->>'imdb' AS imdb
        FROM person p
        JOIN entity e ON e.id = p.id
        WHERE p.is_director = true
          AND e.external_ids ? 'imdb'
          AND e.external_ids->>'imdb' LIKE 'nm%'
    """)
    rows = (await db.execute(sql)).mappings().all()
    return [(r["id"], r["imdb"]) for r in rows]


async def find_person_by_imdb(db: AsyncSession, imdb_id: str) -> int | None:
    sql = text("""
        SELECT p.id FROM person p
        JOIN entity e ON e.id = p.id
        WHERE e.external_ids->>'imdb' = :imdb
        LIMIT 1
    """)
    row = (await db.execute(sql, {"imdb": imdb_id})).mappings().first()
    return row["id"] if row else None


async def upsert_influence_raw(
    db: AsyncSession,
    *,
    source_id: int,
    target_id: int,
    source_label: str,
    target_label: str,
    source_qid: str,
) -> bool:
    if source_id == target_id:
        return False

    check = await db.execute(text("""
        SELECT 1 FROM director_influence
        WHERE source_director_id = :s AND target_director_id = :t
    """), {"s": source_id, "t": target_id})
    if check.first():
        return False

    note = (
        f"Источник: Wikidata (P737 'influenced by'). "
        f"{source_label} → {target_label}. Wikidata QID: {source_qid}"
    )

    await db.execute(text("""
        INSERT INTO director_influence
            (source_director_id, target_director_id, weight, confidence,
             relation_note, inferred_by_system)
        VALUES (:s, :t, 3, 0.70, :note, true)
    """), {"s": source_id, "t": target_id, "note": note})
    return True


async def find_person_by_tmdb_id(db: AsyncSession, tmdb_id: int) -> int | None:
    """Ищет персону по TMDB id."""
    sql = text("""
        SELECT p.id FROM person p
        JOIN entity e ON e.id = p.id
        WHERE e.external_ids->>'tmdb' = :tid
        LIMIT 1
    """)
    row = (await db.execute(sql, {"tid": str(tmdb_id)})).mappings().first()
    return row["id"] if row else None


async def add_imdb_to_existing_person(
    db: AsyncSession, person_id: int, imdb_id: str
) -> None:
    """Добавляет IMDb id в external_ids существующей персоны.

    Используем CAST(:imdb AS text) — без явного каста asyncpg не может
    определить тип параметра в jsonb_build_object и падает с
    IndeterminateDatatypeError.
    """
    await db.execute(text("""
        UPDATE entity
        SET external_ids = external_ids || jsonb_build_object('imdb', CAST(:imdb AS text))
        WHERE id = :id
    """), {"id": person_id, "imdb": imdb_id})

async def find_person_by_slug(
    db: AsyncSession, slug: str, language_id: int
) -> int | None:
    """Ищет персону по уникальному slug в переводе."""
    sql = text("""
        SELECT et.entity_id FROM entity_translation et
        JOIN entity e ON e.id = et.entity_id
        WHERE et.slug = :slug
          AND et.language_id = :lid
          AND e.entity_type = 'person'
        LIMIT 1
    """)
    row = (await db.execute(sql, {"slug": slug, "lid": language_id})).mappings().first()
    return row["entity_id"] if row else None


async def load_person_via_tmdb(
    db: AsyncSession,
    tmdb: TmdbClient,
    imdb_id: str,
    fallback_name: str,
    languages: dict[str, int],
) -> int | None:
    found = await tmdb._get(f"/find/{imdb_id}", {"external_source": "imdb_id"})
    person_results = (found or {}).get("person_results", [])
    if not person_results:
        return None

    tmdb_person = person_results[0]
    tmdb_id = tmdb_person["id"]

    # Проверка 1: ищем по TMDB id в external_ids
    existing_id = await find_person_by_tmdb_id(db, tmdb_id)
    if existing_id:
        await add_imdb_to_existing_person(db, existing_id, imdb_id)
        log.info("  ✓ существующая (по tmdb): %s", fallback_name)
        return existing_id

    p_en = await tmdb.person_full(tmdb_id, language=LANG_EN)
    p_ru = await tmdb.person_full(tmdb_id, language=LANG_RU)
    name_en = p_en.get("name") or fallback_name
    name_ru = p_ru.get("name") if p_ru else None

    # Проверка 2: ищем по будущему slug (тут ловим случай "person есть, но без TMDB id")
    en_slug = f"{name_en.lower().replace(' ', '-')}-{tmdb_id}"[:255]
    existing_by_slug = await find_person_by_slug(db, en_slug, languages["en"])
    if existing_by_slug:
        await add_imdb_to_existing_person(db, existing_by_slug, imdb_id)
        # Также обновим tmdb id если его не было
        await db.execute(text("""
            UPDATE entity
            SET external_ids = external_ids || jsonb_build_object('tmdb', CAST(:tid AS text))
            WHERE id = :id AND NOT external_ids ? 'tmdb'
        """), {"id": existing_by_slug, "tid": str(tmdb_id)})
        
        log.info("  ✓ существующая (по slug): %s", fallback_name)
        return existing_by_slug

    # Создаём новую персону
    er = await db.execute(text("""
        INSERT INTO entity (entity_type, status, primary_image_url, thumbnail_url, external_ids)
        VALUES ('person', 'published', :img_p, :img_t, CAST(:ext AS jsonb))
        RETURNING id
    """), {
        "img_p": TmdbClient.image_url(p_en.get("profile_path"), "w500"),
        "img_t": TmdbClient.image_url(p_en.get("profile_path"), "w185"),
        "ext": json.dumps({"tmdb": str(tmdb_id), "imdb": imdb_id}),
    })
    new_id = er.scalar_one()

    birth = p_en.get("birthday")
    death = p_en.get("deathday")
    await db.execute(text("""
        INSERT INTO person (id, birth_date, death_date, birth_place, is_director,
                            primary_profession, sort_name)
        VALUES (:id, :bd, :dd, :bp, true, 'director', :sn)
    """), {
        "id": new_id,
        "bd": date.fromisoformat(birth) if birth else None,
        "dd": date.fromisoformat(death) if death else None,
        "bp": p_en.get("place_of_birth"),
        "sn": name_en,
    })

    await db.execute(text("""
        INSERT INTO entity_translation
            (entity_id, language_id, search_config, slug, title, summary, description)
        VALUES (:id, :lid, 'english', :slug, :title, :sum, :desc)
    """), {
        "id": new_id, "lid": languages["en"],
        "slug": en_slug,
        "title": name_en,
        "sum": (p_en.get("biography") or "")[:500] or None,
        "desc": p_en.get("biography") or None,
    })
    if name_ru:
        try:
            await db.execute(text("""
                INSERT INTO entity_translation
                    (entity_id, language_id, search_config, slug, title, summary, description)
                VALUES (:id, :lid, 'russian', :slug, :title, :sum, :desc)
            """), {
                "id": new_id, "lid": languages["ru"],
                "slug": f"{name_ru.lower().replace(' ', '-')}-{tmdb_id}"[:255],
                "title": name_ru,
                "sum": (p_ru.get("biography") or "")[:500] or None,
                "desc": p_ru.get("biography") or None,
            })
        except Exception:
            pass

    log.info("  ✓ догружен: %s (imdb=%s)", name_en, imdb_id)
    return new_id


async def main(*, max_directors: int | None) -> None:
    if not settings.tmdb_api_key:
        raise SystemExit("TMDB_API_KEY не задан")

    log.info("─── Wikidata Influences Loader v2 (DEBUG) ───")

    async with AsyncSessionLocal() as db:
        languages = await get_languages(db)
        directors = await get_directors_imdb_ids(db)
    log.info("режиссёров с IMDb id в БД: %d", len(directors))

    if max_directors:
        directors = directors[:max_directors]
        log.info("ограничиваем до %d (--max-directors)", max_directors)

    stats = {
        "batches": 0,
        "pairs_total": 0,
        "created": 0,
        "skipped_existing": 0,
        "loaded_new": 0,
        "errors": 0,
        "src_not_found": 0,
        "tgt_not_found": 0,
    }

    async with WikidataClient() as wd:
        async with TmdbClient(api_key=settings.tmdb_api_key) as tmdb:
            for i in range(0, len(directors), BATCH_SIZE):
                batch = directors[i : i + BATCH_SIZE]
                imdb_ids = [imdb for _, imdb in batch]
                stats["batches"] += 1

                log.info("batch %d (директоров: %d)", stats["batches"], len(batch))

                try:
                    sparql = build_sparql(imdb_ids)
                    pairs = await wd._query(sparql)
                except Exception as exc:
                    log.exception("SPARQL для батча упал: %s", exc)
                    continue

                clean_pairs = []
                for p in pairs:
                    try:
                        clean_pairs.append({
                            "source_qid": p["source"]["value"].rsplit("/", 1)[-1],
                            "source_label": p["sourceLabel"]["value"],
                            "source_imdb": p["sourceImdb"]["value"],
                            "target_label": p["targetLabel"]["value"],
                            "target_imdb": p["targetImdb"]["value"],
                        })
                    except KeyError:
                        continue

                stats["pairs_total"] += len(clean_pairs)
                log.info("  получено %d пар из Wikidata", len(clean_pairs))

                async with AsyncSessionLocal() as db:
                    for idx, pair in enumerate(clean_pairs):
                        try:
                            src_id = await find_person_by_imdb(db, pair["source_imdb"])
                            if not src_id:
                                log.info(
                                    "  [%d] src NOT in DB: %s (%s) — try TMDB",
                                    idx, pair["source_label"], pair["source_imdb"],
                                )
                                src_id = await load_person_via_tmdb(
                                    db, tmdb, pair["source_imdb"],
                                    pair["source_label"], languages,
                                )
                                if src_id:
                                    stats["loaded_new"] += 1
                                else:
                                    stats["src_not_found"] += 1
                                    log.info("  [%d] src TMDB miss", idx)
                                    continue

                            tgt_id = await find_person_by_imdb(db, pair["target_imdb"])
                            if not tgt_id:
                                log.info(
                                    "  [%d] tgt NOT in DB: %s (%s) — try TMDB",
                                    idx, pair["target_label"], pair["target_imdb"],
                                )
                                tgt_id = await load_person_via_tmdb(
                                    db, tmdb, pair["target_imdb"],
                                    pair["target_label"], languages,
                                )
                                if tgt_id:
                                    stats["loaded_new"] += 1
                                else:
                                    stats["tgt_not_found"] += 1
                                    log.info("  [%d] tgt TMDB miss", idx)
                                    continue

                            await db.execute(text("""
                                UPDATE person SET is_director = true
                                WHERE id IN (:s, :t)
                            """), {"s": src_id, "t": tgt_id})

                            created = await upsert_influence_raw(
                                db,
                                source_id=src_id, target_id=tgt_id,
                                source_label=pair["source_label"],
                                target_label=pair["target_label"],
                                source_qid=pair["source_qid"],
                            )
                            if created:
                                stats["created"] += 1
                                log.info(
                                    "  [%d] ✓ CREATED: %s → %s",
                                    idx, pair["source_label"], pair["target_label"],
                                )
                            else:
                                stats["skipped_existing"] += 1

                            await db.commit()
                        except Exception as exc:
                            stats["errors"] += 1
                            await db.rollback()
                            log.exception(
                                "  [%d] FAILED %s → %s",
                                idx, pair["source_label"], pair["target_label"],
                            )

                log.info(
                    "  стат: создано=%d, существ=%d, новых=%d, src_miss=%d, tgt_miss=%d, ошибок=%d",
                    stats["created"], stats["skipped_existing"],
                    stats["loaded_new"], stats["src_not_found"],
                    stats["tgt_not_found"], stats["errors"],
                )

    log.info("─── DONE ───")
    log.info("батчей:                  %(batches)d", stats)
    log.info("пар получено всего:      %(pairs_total)d", stats)
    log.info(" • создано связей:        %(created)d", stats)
    log.info(" • уже существовали:      %(skipped_existing)d", stats)
    log.info(" • новых персон:          %(loaded_new)d", stats)
    log.info(" • src не найден:         %(src_not_found)d", stats)
    log.info(" • tgt не найден:         %(tgt_not_found)d", stats)
    log.info(" • ошибок:                %(errors)d", stats)


def cli() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-directors", type=int, default=None)
    args = parser.parse_args()
    asyncio.run(main(max_directors=args.max_directors))


if __name__ == "__main__":
    cli()
