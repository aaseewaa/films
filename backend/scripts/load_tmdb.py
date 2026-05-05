"""
Загрузчик данных из TMDB в твою БД.

Что делает:
  1. Читает топ N популярных фильмов TMDB
  2. Для каждого: full info на ru и en (название, описание, год, постер, режиссёр, актёры, жанры)
  3. Записывает в БД через ORM:
       - Entity + Film + EntityTranslation (ru/en)
       - Entity + Person + EntityTranslation (ru/en)  для всех режиссёров и top-10 актёров
       - FilmPerson — связи фильм-персона
       - EntityTaxonomy — жанры (TaxonomyTerm уже должны быть, см. seed_genres.py)
  4. Идемпотентно: по external_ids->>'tmdb' определяет уже загруженные сущности

Запуск:
    cd backend
    source venv/bin/activate
    python -m scripts.load_tmdb --pages 10 --top-actors 10

    # для пробного запуска:
    python -m scripts.load_tmdb --pages 1 --top-actors 5
"""
from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import date
from typing import Any

from slugify import slugify
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import (
    Entity,
    EntityTaxonomy,
    EntityTranslation,
    Film,
    FilmPerson,
    Language,
    Person,
    TaxonomyTerm,
    TaxonomyTermTranslation,
)
from scripts.tmdb_client import TmdbClient

# ─── Логгирование ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
log = logging.getLogger("loader")
logging.getLogger("httpx").setLevel(logging.WARNING)


# ─── Маппинг языков TMDB → наш формат ──────────────────────────────
LANG_RU = "ru-RU"
LANG_EN = "en-US"


# ─── Утилиты ───────────────────────────────────────────────────────
def make_slug(text: str, suffix: str | int = "") -> str:
    """slug из заголовка + опциональный суффикс (год или TMDB id)."""
    base = slugify(text or "untitled", lowercase=True, max_length=200)
    if suffix:
        base = f"{base}-{suffix}"
    return base[:255]


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


# ─── Получение языков из БД ────────────────────────────────────────
async def get_languages(db: AsyncSession) -> dict[str, int]:
    """Возвращает dict 'ru' -> language_id, 'en' -> language_id."""
    rows = (await db.execute(select(Language))).scalars().all()
    by_code = {lang.code: lang.id for lang in rows}
    if "ru" not in by_code or "en" not in by_code:
        raise RuntimeError(
            "В таблице language должны быть строки с code='ru' и code='en'. "
            "Прогони seed.sql прежде чем запускать загрузчик."
        )
    return by_code


# ─── Поиск/создание Entity по external_ids ─────────────────────────
async def find_entity_by_tmdb(
    db: AsyncSession, *, entity_type: str, tmdb_id: int
) -> Entity | None:
    """Возвращает существующую сущность по TMDB id или None."""
    stmt = select(Entity).where(
        Entity.entity_type == entity_type,
        Entity.external_ids["tmdb"].astext == str(tmdb_id),
    )
    return (await db.execute(stmt)).scalar_one_or_none()


# ─── Загрузка/обновление жанров ─────────────────────────────────────
async def upsert_genre(
    db: AsyncSession,
    *,
    tmdb_genre_id: int,
    name_en: str,
    name_ru: str | None,
    languages: dict[str, int],
) -> TaxonomyTerm:
    """Находит/создаёт жанр в taxonomy_term + переводы."""
    code = f"tmdb-{tmdb_genre_id}"

    stmt = select(TaxonomyTerm).where(
        TaxonomyTerm.term_type == "genre", TaxonomyTerm.code == code
    )
    term = (await db.execute(stmt)).scalar_one_or_none()
    if term is None:
        term = TaxonomyTerm(
            term_type="genre",
            code=code,
            is_system=True,
            extra_metadata={"tmdb_genre_id": tmdb_genre_id},
        )
        db.add(term)
        await db.flush()

        # Переводы
        db.add(
            TaxonomyTermTranslation(
                term_id=term.id,
                language_id=languages["en"],
                slug=slugify(name_en),
                name=name_en,
            )
        )
        if name_ru:
            db.add(
                TaxonomyTermTranslation(
                    term_id=term.id,
                    language_id=languages["ru"],
                    slug=slugify(name_ru),
                    name=name_ru,
                )
            )
    return term


# ─── Загрузка персоны ──────────────────────────────────────────────
async def upsert_person(
    db: AsyncSession,
    *,
    tmdb_id: int,
    name_en: str,
    name_ru: str | None,
    biography_en: str | None,
    biography_ru: str | None,
    birthday: str | None,
    deathday: str | None,
    place_of_birth: str | None,
    profile_path: str | None,
    is_director: bool = False,
    is_actor: bool = False,
    languages: dict[str, int],
) -> Person:
    """Создаёт или обновляет персону."""
    existing = await find_entity_by_tmdb(db, entity_type="person", tmdb_id=tmdb_id)
    if existing:
        # Обновим флаги ролей если стало больше известно
        person = (
            await db.execute(select(Person).where(Person.id == existing.id))
        ).scalar_one()
        if is_director:
            person.is_director = True
        if is_actor:
            person.is_actor = True
        return person

    # Новая персона: сначала Entity, потом Person с тем же id, потом переводы
    entity = Entity(
        entity_type="person",
        status="published",
        primary_image_url=TmdbClient.image_url(profile_path, "w500"),
        thumbnail_url=TmdbClient.image_url(profile_path, "w185"),
        external_ids={"tmdb": str(tmdb_id)},
    )
    db.add(entity)
    await db.flush()

    person = Person(
        id=entity.id,
        birth_date=parse_date(birthday),
        death_date=parse_date(deathday),
        birth_place=place_of_birth,
        is_director=is_director,
        is_actor=is_actor,
        primary_profession="director" if is_director else ("actor" if is_actor else None),
        sort_name=name_en,
    )
    db.add(person)

    # Переводы (английский — обязательно, русский — если есть)
    db.add(
        EntityTranslation(
            entity_id=entity.id,
            language_id=languages["en"],
            search_config="english",
            slug=make_slug(name_en, tmdb_id),
            title=name_en,
            summary=biography_en[:500] if biography_en else None,
            description=biography_en,
        )
    )
    if name_ru:
        db.add(
            EntityTranslation(
                entity_id=entity.id,
                language_id=languages["ru"],
                search_config="russian",
                slug=make_slug(name_ru, tmdb_id),
                title=name_ru,
                summary=biography_ru[:500] if biography_ru else None,
                description=biography_ru,
            )
        )

    await db.flush()
    return person


# ─── Загрузка фильма ───────────────────────────────────────────────
async def load_film(
    db: AsyncSession,
    tmdb: TmdbClient,
    *,
    tmdb_id: int,
    languages: dict[str, int],
    top_actors_count: int,
) -> bool:
    """
    Загружает один фильм со всеми связанными персонами и жанрами.
    Возвращает True если фильм был создан, False если уже существовал.
    """
    if await find_entity_by_tmdb(db, entity_type="film", tmdb_id=tmdb_id):
        log.debug("film tmdb=%s already loaded, skip", tmdb_id)
        return False

    # ─ полные данные фильма на двух языках ─
    en = await tmdb.movie_full(tmdb_id, language=LANG_EN)
    ru = await tmdb.movie_full(tmdb_id, language=LANG_RU)
    if not en:
        log.warning("film tmdb=%s not found", tmdb_id)
        return False

    title_en = en.get("title") or en.get("original_title") or "Untitled"
    title_ru = ru.get("title") if ru else None
    overview_en = en.get("overview") or None
    overview_ru = ru.get("overview") if ru else None

    # ─ Entity ─
    entity = Entity(
        entity_type="film",
        status="published",
        primary_image_url=TmdbClient.image_url(en.get("poster_path"), "w500"),
        thumbnail_url=TmdbClient.image_url(en.get("poster_path"), "w185"),
        external_ids={
            "tmdb": str(tmdb_id),
            "imdb": en.get("imdb_id") or en.get("external_ids", {}).get("imdb_id") or "",
        },
        extra_metadata={
            "vote_average": en.get("vote_average"),
            "vote_count": en.get("vote_count"),
            "popularity": en.get("popularity"),
            "budget": en.get("budget"),
            "revenue": en.get("revenue"),
            "tagline": en.get("tagline"),
        },
    )
    db.add(entity)
    await db.flush()

    # ─ Film ─
    release_date = parse_date(en.get("release_date"))
    film = Film(
        id=entity.id,
        release_year=release_date.year if release_date else None,
        release_date=release_date,
        runtime_min=en.get("runtime"),
        sort_title=title_en,
    )
    db.add(film)

    # ─ Переводы ─
    db.add(
        EntityTranslation(
            entity_id=entity.id,
            language_id=languages["en"],
            search_config="english",
            slug=make_slug(title_en, tmdb_id),
            title=title_en,
            summary=overview_en[:500] if overview_en else None,
            description=overview_en,
        )
    )
    if title_ru:
        db.add(
            EntityTranslation(
                entity_id=entity.id,
                language_id=languages["ru"],
                search_config="russian",
                slug=make_slug(title_ru, tmdb_id),
                title=title_ru,
                summary=overview_ru[:500] if overview_ru else None,
                description=overview_ru,
            )
        )

    # ─ Жанры ─
    for g in en.get("genres", []):
        # Найти соответствие в ru-данных
        ru_name = None
        for g_ru in (ru.get("genres", []) if ru else []):
            if g_ru.get("id") == g.get("id"):
                ru_name = g_ru.get("name")
                break
        term = await upsert_genre(
            db,
            tmdb_genre_id=g["id"],
            name_en=g["name"],
            name_ru=ru_name,
            languages=languages,
        )
        db.add(EntityTaxonomy(entity_id=entity.id, term_id=term.id, is_primary=False))

    # ─ Режиссёры ─
    crew = en.get("credits", {}).get("crew", [])
    directors = [c for c in crew if c.get("job") == "Director"]
    for d in directors:
        person_full_en = await tmdb.person_full(d["id"], language=LANG_EN)
        person_full_ru = await tmdb.person_full(d["id"], language=LANG_RU)
        person = await upsert_person(
            db,
            tmdb_id=d["id"],
            name_en=person_full_en.get("name") or d.get("name", "Unknown"),
            name_ru=person_full_ru.get("name") if person_full_ru else None,
            biography_en=person_full_en.get("biography") or None,
            biography_ru=(person_full_ru.get("biography") if person_full_ru else None),
            birthday=person_full_en.get("birthday"),
            deathday=person_full_en.get("deathday"),
            place_of_birth=person_full_en.get("place_of_birth"),
            profile_path=person_full_en.get("profile_path"),
            is_director=True,
            languages=languages,
        )
        db.add(
            FilmPerson(
                film_id=film.id,
                person_id=person.id,
                role_type="director",
                is_primary=True,
            )
        )

    # ─ Актёры (top N по billing) ─
    cast = en.get("credits", {}).get("cast", [])
    cast_sorted = sorted(cast, key=lambda c: c.get("order", 9999))
    for c in cast_sorted[:top_actors_count]:
        person_full_en = await tmdb.person_full(c["id"], language=LANG_EN)
        person_full_ru = await tmdb.person_full(c["id"], language=LANG_RU)
        person = await upsert_person(
            db,
            tmdb_id=c["id"],
            name_en=person_full_en.get("name") or c.get("name", "Unknown"),
            name_ru=person_full_ru.get("name") if person_full_ru else None,
            biography_en=person_full_en.get("biography") or None,
            biography_ru=(person_full_ru.get("biography") if person_full_ru else None),
            birthday=person_full_en.get("birthday"),
            deathday=person_full_en.get("deathday"),
            place_of_birth=person_full_en.get("place_of_birth"),
            profile_path=person_full_en.get("profile_path"),
            is_actor=True,
            languages=languages,
        )
        db.add(
            FilmPerson(
                film_id=film.id,
                person_id=person.id,
                role_type="actor",
                character_name=c.get("character"),
                billing_order=c.get("order"),
                is_primary=c.get("order", 999) <= 2,
            )
        )

    await db.flush()
    log.info("✓ film loaded: '%s' (%s)", title_en, release_date.year if release_date else "?")
    return True


# ─── main ──────────────────────────────────────────────────────────
async def main(*, pages: int, top_actors: int) -> None:
    if not settings.tmdb_api_key:
        raise SystemExit("TMDB_API_KEY не задан в .env")

    log.info("─── TMDB loader ───")
    log.info("pages=%d, top-actors-per-film=%d", pages, top_actors)

    async with TmdbClient(api_key=settings.tmdb_api_key) as tmdb:
        # 1) Получаем список популярных фильмов (на английском, для устойчивости)
        popular = await tmdb.popular_movies(pages=pages, language=LANG_EN)
        log.info("got %d popular film ids from TMDB", len(popular))

        # 2) Загружаем каждый фильм в БД
        async with AsyncSessionLocal() as db:
            languages = await get_languages(db)
            await db.commit()  # отдельная транзакция для чтения языков

            created = 0
            skipped = 0
            errors = 0

            for i, p in enumerate(popular, start=1):
                tmdb_id = p["id"]
                title_preview = p.get("title", "?")
                log.info("[%d/%d] processing tmdb=%s '%s'", i, len(popular), tmdb_id, title_preview)

                # Каждый фильм — отдельная транзакция, чтобы ошибка
                # на одном фильме не уносила весь батч.
                try:
                    async with AsyncSessionLocal() as film_db:
                        was_created = await load_film(
                            film_db,
                            tmdb,
                            tmdb_id=tmdb_id,
                            languages=languages,
                            top_actors_count=top_actors,
                        )
                        await film_db.commit()
                        if was_created:
                            created += 1
                        else:
                            skipped += 1
                except Exception as exc:
                    errors += 1
                    log.exception("film tmdb=%s failed: %s", tmdb_id, exc)

            log.info("─── DONE ───")
            log.info("created=%d, skipped(already loaded)=%d, errors=%d", created, skipped, errors)


def cli() -> None:
    parser = argparse.ArgumentParser(description="Загрузчик TMDB → БД")
    parser.add_argument(
        "--pages", type=int, default=10,
        help="Сколько страниц популярных фильмов TMDB загрузить (1 страница = 20 фильмов)",
    )
    parser.add_argument(
        "--top-actors", type=int, default=10,
        help="Сколько актёров (по billing order) брать на каждый фильм",
    )
    args = parser.parse_args()
    asyncio.run(main(pages=args.pages, top_actors=args.top_actors))


if __name__ == "__main__":
    cli()
