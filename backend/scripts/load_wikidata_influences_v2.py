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
BATCH_SIZE = 10
BATCH_PAUSE_SEC = 8
PROP_PAUSE_SEC = 5
WD_PROPS = ("P737", "P941")


def build_sparql(imdb_ids: list[str], prop: str) -> str:
    """
    Один Wikidata-property за запрос (легче для WDQS, чем 4 UNION сразу).
    P737 — influenced by; P941 — inspired by.
    """
    values_block = " ".join(f'"{imdb}"' for imdb in imdb_ids)
    return f"""
    SELECT DISTINCT ?source ?sourceLabel ?sourceImdb
                    ?target ?targetLabel ?targetImdb
    WHERE {{
      VALUES ?ourImdb {{ {values_block} }}

      {{
        ?target wdt:P345 ?ourImdb .
        ?target wdt:{prop} ?source .
      }} UNION {{
        ?source wdt:P345 ?ourImdb .
        ?target wdt:{prop} ?source .
      }}

      ?source wdt:P345 ?sourceImdb .
      ?target wdt:P345 ?targetImdb .
      ?source wdt:P106 wd:Q2526255 .
      ?target wdt:P106 wd:Q2526255 .
      FILTER(STRSTARTS(?sourceImdb, "nm"))
      FILTER(STRSTARTS(?targetImdb, "nm"))

      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    LIMIT 2000
    """


async def fetch_batch_from_wikidata(
    wd: WikidataClient,
    imdb_ids: list[str],
    *,
    props: tuple[str, ...] = WD_PROPS,
) -> list[dict]:
    """P737 и P941 — отдельными лёгкими запросами с паузой."""
    all_rows: list[dict] = []
    for prop in props:
        log.info("  Wikidata %s (%d imdb)...", prop, len(imdb_ids))
        try:
            rows = await wd._query(build_sparql(imdb_ids, prop))
            for row in rows:
                row["_prop"] = prop
            all_rows.extend(rows)
            log.info("  %s → %d пар", prop, len(rows))
        except Exception as exc:
            log.warning("  %s пропущен: %s", prop, exc)
        if prop != props[-1]:
            await asyncio.sleep(PROP_PAUSE_SEC)
    return all_rows


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


_WD_PROP_META = {
    "P737": ("influenced by", 3, 0.70),
    "P941": ("inspired by", 2, 0.60),
}


async def upsert_influence_raw(
    db: AsyncSession,
    *,
    source_id: int,
    target_id: int,
    source_label: str,
    target_label: str,
    source_qid: str,
    wikidata_prop: str = "P737",
) -> bool:
    if source_id == target_id:
        return False

    check = await db.execute(text("""
        SELECT 1 FROM director_influence
        WHERE source_director_id = :s AND target_director_id = :t
    """), {"s": source_id, "t": target_id})
    if check.first():
        return False

    label, weight, confidence = _WD_PROP_META.get(
        wikidata_prop, ("influence", 3, 0.65),
    )
    note = (
        f"Источник: Wikidata ({wikidata_prop} '{label}'). "
        f"{source_label} → {target_label}. Wikidata QID: {source_qid}"
    )

    await db.execute(text("""
        INSERT INTO director_influence
            (source_director_id, target_director_id, weight, confidence,
             relation_note, inferred_by_system)
        VALUES (:s, :t, :w, :c, :note, true)
    """), {
        "s": source_id, "t": target_id, "w": weight, "c": confidence, "note": note,
    })
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


async def main(
    *,
    max_directors: int | None,
    batch_size: int = BATCH_SIZE,
    batch_pause: float = BATCH_PAUSE_SEC,
    props: tuple[str, ...] = WD_PROPS,
    misses_file: str | None = None,
) -> None:
    if not settings.tmdb_api_key:
        raise SystemExit("TMDB_API_KEY не задан")

    log.info("─── Wikidata Influences Loader v2 (%s) ───", " + ".join(props))

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
        "created_p737": 0,
        "created_p941": 0,
        "skipped_existing": 0,
        "loaded_new": 0,
        "errors": 0,
        "src_not_found": 0,
        "tgt_not_found": 0,
        "sparql_failures": 0,
    }
    tgt_miss_imdbs: set[str] = set()

    total_batches = (len(directors) + batch_size - 1) // batch_size
    log.info("батчей: %d по %d режиссёров, пауза %ss", total_batches, batch_size, batch_pause)

    async with WikidataClient() as wd:
        async with TmdbClient(api_key=settings.tmdb_api_key) as tmdb:
            for i in range(0, len(directors), batch_size):
                batch = directors[i : i + batch_size]
                imdb_ids = [imdb for _, imdb in batch]
                stats["batches"] += 1

                log.info(
                    "batch %d/%d (режиссёров: %d)",
                    stats["batches"], total_batches, len(batch),
                )

                try:
                    pairs = await fetch_batch_from_wikidata(wd, imdb_ids, props=props)
                except Exception as exc:
                    stats["sparql_failures"] += 1
                    log.exception("SPARQL батч полностью упал: %s", exc)
                    await asyncio.sleep(batch_pause)
                    continue

                clean_pairs = []
                for p in pairs:
                    try:
                        prop = p.get("_prop", "P737")
                        clean_pairs.append({
                            "source_qid": p["source"]["value"].rsplit("/", 1)[-1],
                            "source_label": p["sourceLabel"]["value"],
                            "source_imdb": p["sourceImdb"]["value"],
                            "target_label": p["targetLabel"]["value"],
                            "target_imdb": p["targetImdb"]["value"],
                            "wikidata_prop": prop,
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
                                    tgt_miss_imdbs.add(pair["target_imdb"])
                                    log.info(
                                        "  [%d] tgt TMDB miss: %s (%s)",
                                        idx, pair["target_label"], pair["target_imdb"],
                                    )
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
                                wikidata_prop=pair.get("wikidata_prop", "P737"),
                            )
                            if created:
                                stats["created"] += 1
                                prop = pair.get("wikidata_prop", "P737")
                                if prop == "P941":
                                    stats["created_p941"] += 1
                                else:
                                    stats["created_p737"] += 1
                                log.info(
                                    "  [%d] ✓ CREATED (%s): %s → %s",
                                    idx, prop,
                                    pair["source_label"], pair["target_label"],
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

                if stats["batches"] < total_batches:
                    log.info("  пауза %ss перед следующим батчем...", batch_pause)
                    await asyncio.sleep(batch_pause)

    log.info("─── DONE ───")
    log.info("батчей:                  %(batches)d", stats)
    log.info("пар получено всего:      %(pairs_total)d", stats)
    log.info(" • создано связей:        %(created)d", stats)
    log.info("   — P737 influenced by:  %(created_p737)d", stats)
    log.info("   — P941 inspired by:    %(created_p941)d", stats)
    log.info(" • уже существовали:      %(skipped_existing)d", stats)
    log.info(" • новых персон:          %(loaded_new)d", stats)
    log.info(" • src не найден:         %(src_not_found)d", stats)
    log.info(" • tgt не найден:         %(tgt_not_found)d", stats)
    log.info(" • ошибок:                %(errors)d", stats)

    if misses_file and tgt_miss_imdbs:
        from pathlib import Path

        path = Path(misses_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(sorted(tgt_miss_imdbs)) + "\n", encoding="utf-8")
        log.info("список tgt_miss (%d imdb) → %s", len(tgt_miss_imdbs), path)
        log.info("  python -m scripts.retry_imdb_persons --file %s", path)


def cli() -> None:
    parser = argparse.ArgumentParser(
        description="Wikidata P737 + P941 → director_influence (лёгкие батчи)",
    )
    parser.add_argument("--max-directors", type=int, default=None)
    parser.add_argument(
        "--batch-size", type=int, default=BATCH_SIZE,
        help="IMDb id за один заход к WDQS (по умолчанию 10)",
    )
    parser.add_argument(
        "--batch-pause", type=float, default=BATCH_PAUSE_SEC,
        help="Секунд между батчами (по умолчанию 8)",
    )
    parser.add_argument(
        "--only-p737", action="store_true",
        help="Только P737, без P941 (быстрее)",
    )
    parser.add_argument(
        "--misses-file",
        type=str,
        default="scripts/cache/wikidata_tgt_miss.txt",
        help="Сохранить IMDb id с tgt_miss (пустая строка = не писать)",
    )
    args = parser.parse_args()
    props: tuple[str, ...] = ("P737",) if args.only_p737 else WD_PROPS
    misses = args.misses_file.strip() or None
    asyncio.run(main(
        max_directors=args.max_directors,
        batch_size=max(1, args.batch_size),
        batch_pause=max(0.0, args.batch_pause),
        props=props,
        misses_file=misses,
    ))


if __name__ == "__main__":
    cli()
