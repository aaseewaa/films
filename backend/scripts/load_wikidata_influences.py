"""
Загрузчик графа влияний между режиссёрами из Wikidata.

Что делает:
  1. SPARQL-запрос к Wikidata: все пары "режиссёр A повлиял на режиссёра B"
     (свойство P737), у которых есть IMDb id у обоих
  2. Для каждой пары проверяет: есть ли оба режиссёра в нашей БД
     (через external_ids->>'imdb')
  3. Если есть оба — пишет связь в director_influence
  4. Если режиссёра нет — пытается догрузить через TMDB API по IMDb id
     (TMDB поддерживает поиск по imdb_id через /find endpoint)
  5. Создаёт source-запись в таблице source с указанием Wikidata как источник

Запуск:
    cd backend
    source venv/bin/activate
    python -m scripts.load_wikidata_influences

    # с параметрами:
    python -m scripts.load_wikidata_influences --autoload-missing
"""
from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import (
    DirectorInfluence,
    Entity,
    EntityTranslation,
    Language,
    Person,
)
from scripts.tmdb_client import TmdbClient
from scripts.wikidata_client import WikidataClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
log = logging.getLogger("wikidata-loader")
logging.getLogger("httpx").setLevel(logging.WARNING)


# ─── helpers ──────────────────────────────────────────────────────
LANG_RU = "ru-RU"
LANG_EN = "en-US"


async def get_languages(db: AsyncSession) -> dict[str, int]:
    rows = (await db.execute(select(Language))).scalars().all()
    return {lang.code: lang.id for lang in rows}


async def find_person_by_imdb(db: AsyncSession, imdb_id: str) -> Person | None:
    """Ищет персону в БД по IMDb id (поле entity.external_ids->>'imdb')."""
    stmt = (
        select(Person)
        .join(Entity, Entity.id == Person.id)
        .where(Entity.external_ids["imdb"].astext == imdb_id)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def find_or_load_person_via_tmdb(
    db: AsyncSession,
    tmdb: TmdbClient,
    imdb_id: str,
    fallback_name: str,
    languages: dict[str, int],
) -> Person | None:
    """
    Если персона есть в БД — вернуть её.
    Если нет — попытаться найти в TMDB по IMDb id и загрузить.
    Возвращает None если ничего не получилось.
    """
    existing = await find_person_by_imdb(db, imdb_id)
    if existing:
        return existing

    # TMDB endpoint /find умеет искать сущности по внешним ID
    found = await tmdb._get(f"/find/{imdb_id}", {"external_source": "imdb_id"})
    person_results = (found or {}).get("person_results", [])
    if not person_results:
        log.debug("tmdb /find: no person for imdb=%s (%s)", imdb_id, fallback_name)
        return None

    tmdb_person = person_results[0]
    tmdb_id = tmdb_person["id"]

    # Получаем подробную инфу
    person_full_en = await tmdb.person_full(tmdb_id, language=LANG_EN)
    person_full_ru = await tmdb.person_full(tmdb_id, language=LANG_RU)

    name_en = person_full_en.get("name") or fallback_name
    name_ru = person_full_ru.get("name") if person_full_ru else None

    # Создаём Entity + Person + переводы (как в load_tmdb)
    entity = Entity(
        entity_type="person",
        status="published",
        external_ids={"tmdb": str(tmdb_id), "imdb": imdb_id},
        primary_image_url=TmdbClient.image_url(person_full_en.get("profile_path"), "w500"),
        thumbnail_url=TmdbClient.image_url(person_full_en.get("profile_path"), "w185"),
    )
    db.add(entity)
    await db.flush()

    birth = person_full_en.get("birthday")
    death = person_full_en.get("deathday")

    person = Person(
        id=entity.id,
        birth_date=date.fromisoformat(birth) if birth else None,
        death_date=date.fromisoformat(death) if death else None,
        birth_place=person_full_en.get("place_of_birth"),
        is_director=True,
        primary_profession="director",
        sort_name=name_en,
    )
    db.add(person)

    # Переводы: английский — обязательно, русский — если есть
    db.add(EntityTranslation(
        entity_id=entity.id,
        language_id=languages["en"],
        search_config="english",
        slug=f"{name_en.lower().replace(' ', '-')}-{tmdb_id}"[:255],
        title=name_en,
        summary=(person_full_en.get("biography") or "")[:500] or None,
        description=person_full_en.get("biography") or None,
    ))
    if name_ru:
        db.add(EntityTranslation(
            entity_id=entity.id,
            language_id=languages["ru"],
            search_config="russian",
            slug=f"{name_ru.lower().replace(' ', '-')}-{tmdb_id}"[:255],
            title=name_ru,
            summary=(person_full_ru.get("biography") or "")[:500] or None,
            description=person_full_ru.get("biography") or None,
        ))

    await db.flush()
    log.info("✓ догружен режиссёр: %s (imdb=%s)", name_en, imdb_id)
    return person


async def upsert_influence(
    db: AsyncSession,
    *,
    source_id: int,
    target_id: int,
    source_label: str,
    target_label: str,
    source_qid: str,
) -> bool:
    """Создаёт связь, если ещё нет. Возвращает True если создал."""
    if source_id == target_id:
        return False  # самовлияние запрещено CHECK-constraint'ом

    existing = await db.execute(
        select(DirectorInfluence).where(
            DirectorInfluence.source_director_id == source_id,
            DirectorInfluence.target_director_id == target_id,
        )
    )
    if existing.scalar_one_or_none():
        return False

    db.add(DirectorInfluence(
        source_director_id=source_id,
        target_director_id=target_id,
        weight=3,
        confidence=0.70,  # средне-высокое доверие к Wikidata
        relation_note=(
            f"Источник: Wikidata (P737 'influenced by'). "
            f"{source_label} → {target_label}. "
            f"Wikidata QID: {source_qid}"
        ),
        inferred_by_system=True,
    ))
    return True


# ─── main ─────────────────────────────────────────────────────────
async def main(*, autoload_missing: bool, max_pairs: int | None) -> None:
    if not settings.tmdb_api_key:
        log.warning("TMDB_API_KEY не задан — отключаю --autoload-missing")
        autoload_missing = False

    log.info("─── Wikidata Influences Loader ───")

    # 1) Получаем пары из Wikidata
    async with WikidataClient() as wd:
        pairs = await wd.director_influences()
    log.info("получено %d пар из Wikidata", len(pairs))

    if max_pairs:
        pairs = pairs[:max_pairs]
        log.info("ограничиваем до %d пар (--max)", max_pairs)

    # 2) Загружаем в БД
    stats = {
        "processed": 0,
        "created": 0,
        "skipped_existing": 0,
        "skipped_no_persons": 0,
        "loaded_new_persons": 0,
        "errors": 0,
    }

    async with TmdbClient(api_key=settings.tmdb_api_key or "dummy") as tmdb:
        async with AsyncSessionLocal() as db:
            languages = await get_languages(db)
            await db.commit()

            for i, pair in enumerate(pairs, start=1):
                stats["processed"] += 1
                src_imdb = pair["source_imdb"]
                tgt_imdb = pair["target_imdb"]
                src_label = pair["source_label"]
                tgt_label = pair["target_label"]

                if i % 50 == 0:
                    log.info("progress: %d/%d", i, len(pairs))

                try:
                    async with AsyncSessionLocal() as pair_db:
                        # Ищем источника
                        source_person = await find_person_by_imdb(pair_db, src_imdb)
                        if not source_person and autoload_missing:
                            source_person = await find_or_load_person_via_tmdb(
                                pair_db, tmdb, src_imdb, src_label, languages
                            )
                            if source_person:
                                stats["loaded_new_persons"] += 1

                        # Ищем целевого
                        target_person = await find_person_by_imdb(pair_db, tgt_imdb)
                        if not target_person and autoload_missing:
                            target_person = await find_or_load_person_via_tmdb(
                                pair_db, tmdb, tgt_imdb, tgt_label, languages
                            )
                            if target_person:
                                stats["loaded_new_persons"] += 1

                        if not source_person or not target_person:
                            stats["skipped_no_persons"] += 1
                            await pair_db.rollback()
                            continue

                        # Помечаем что персона стала режиссёром
                        source_person.is_director = True
                        target_person.is_director = True

                        # Создаём связь
                        was_created = await upsert_influence(
                            pair_db,
                            source_id=source_person.id,
                            target_id=target_person.id,
                            source_label=src_label,
                            target_label=tgt_label,
                            source_qid=pair["source_qid"],
                        )

                        if was_created:
                            stats["created"] += 1
                            log.debug("✓ %s → %s", src_label, tgt_label)
                        else:
                            stats["skipped_existing"] += 1

                        await pair_db.commit()
                except Exception as exc:
                    stats["errors"] += 1
                    log.exception("pair %s → %s failed: %s", src_label, tgt_label, exc)

    log.info("─── DONE ───")
    log.info("processed=%(processed)d", stats)
    log.info(" • созданы новые связи:        %(created)d", stats)
    log.info(" • уже существовали:           %(skipped_existing)d", stats)
    log.info(" • нет одного из режиссёров:   %(skipped_no_persons)d", stats)
    log.info(" • догружено режиссёров:       %(loaded_new_persons)d", stats)
    log.info(" • ошибок:                     %(errors)d", stats)


def cli() -> None:
    parser = argparse.ArgumentParser(
        description="Загрузчик графа влияний между режиссёрами из Wikidata"
    )
    parser.add_argument(
        "--autoload-missing",
        action="store_true",
        help="Если режиссёра нет в БД, попытаться загрузить через TMDB по IMDb id",
    )
    parser.add_argument(
        "--max", type=int, default=None,
        help="Максимум пар для обработки (для отладки), напр. --max 50",
    )
    args = parser.parse_args()

    asyncio.run(main(autoload_missing=args.autoload_missing, max_pairs=args.max))


if __name__ == "__main__":
    cli()
