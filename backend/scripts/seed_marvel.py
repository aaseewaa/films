"""
Загрузка фильмов MCU и заполнение коллекции Marvel: Кинематографическая Вселенная.

Порядок — рекомендованный порядок просмотра MCU (release order с поправкой
на Captain Marvel и Captain America: First Avenger для нарратива).

Запуск (два шага):

  Шаг 1: загрузить фильмы которых нет в БД
    cd backend
    source venv/bin/activate
    python -m scripts.seed_marvel --load-films

  Шаг 2: заполнить коллекцию (фильмы уже есть в БД)
    python -m scripts.seed_marvel --fill-collection

  Или сразу всё:
    python -m scripts.seed_marvel --load-films --fill-collection
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import httpx
from slugify import slugify
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
)
log = logging.getLogger("marvel-seed")

TMDB_BASE = "https://api.themoviedb.org/3"
POSTER_BASE = "https://image.tmdb.org/t/p/w500"
EDITORIAL_USER_ID = 5

# ═══════════════════════════════════════════════════════════════
# MCU — порядок просмотра + TMDB id + позиция + редакторская заметка
# Порядок: рекомендованный watch order (не хронологический, а нарративный)
# ═══════════════════════════════════════════════════════════════

MCU_FILMS = [
    # pos  tmdb_id   title_ru (для поиска в БД / лога)         note
    (1,   1726,    "Железный человек",                         "С чего всё началось — Тони Старк и его первый костюм"),
    (2,   1724,    "Невероятный Халк",                         "Брюс Бэннер бежит от своей силы"),
    (3,   10138,   "Железный человек 2",                       "Тони против правительства и Уиппа"),
    (4,   8669,    "Тор",                                      "Асгардийский принц падает на Землю"),
    (5,   24428,   "Мстители",                                 "Команда собирается впервые — Тесеракт и Локи"),
    (6,   68721,   "Железный человек 3",                       "Тони без брони — личный кризис героя"),
    (7,   76338,   "Тор 2: Царство тьмы",                     "Тёмные эльфы и Эфир — второй камень бесконечности"),
    (8,   100402,  "Первый мститель: Другая война",            "Щ.И.Т. скомпрометирован, Зимний Солдат"),
    (9,   118340,  "Стражи Галактики",                         "Преступники становятся героями — и смешными"),
    (10,  283995,  "Стражи Галактики 2",                       "Отец Питера Квилла и семья как выбор"),
    (11,  99861,   "Мстители: Эра Альтрона",                   "Альтрон, Вижн, Алое Ведьма — раскол команды"),
    (12,  102899,  "Человек-муравей",                          "Воровство технологии и маленький герой"),
    (13,  271110,  "Первый мститель: Противостояние",          "Мстители делятся на два лагеря — Тони против Роджерса"),
    (14,  284053,  "Доктор Стрэндж",                           "Маг и мультивселенная — впервые"),
    (15,  315635,  "Человек-паук: Возвращение домой",          "Питер Паркер в старшей школе и Коршун"),
    (16,  284054,  "Тор: Рагнарёк",                            "Асгард уничтожен, Халк на арене — лучший Тор"),
    (17,  284052,  "Чёрная Пантера",                           "Ваканда и вибраниум — новый король"),
    (18,  299536,  "Мстители: Война бесконечности",            "Танос собирает камни — самая тёмная точка"),
    (19,  363088,  "Человек-муравей и Оса",                    "Квантовое царство и последствия Войны бесконечности"),
    (20,  299537,  "Капитан Марвел",                           "Кэрол Денверс в 90-х — мощнейший герой MCU"),
    (21,  299534,  "Мстители: Финал",                          "Финал — все нити сходятся, пять лет спустя"),
    (22,  429617,  "Человек-паук: Вдали от дома",              "Питер после Финала — Мистерио и мультивселенная"),
    (23,  566525,  "Шан-Чи и легенда десяти колец",            "Новый герой и организация Мандарина"),
    (24,  524434,  "Вечные",                                   "Древние существа и история Земли иначе"),
    (25,  458156,  "Человек-паук: Нет пути домой",             "Мультивселенная открыта — все Человеки-пауки вместе"),
    (26,  616037,  "Тор: Любовь и гром",                       "Горр-убийца богов и возвращение Джейн"),
    (27,  774752,  "Доктор Стрэндж: В мультивселенной безумия", "Мультивселенная взрывается — Скарлет Ведьма"),
    (28,  634649,  "Человек-паук: Нет пути домой",             "Дубль — если предыдущий не нашёлся"),
    (29,  505642,  "Чёрная Пантера: Ваканда навсегда",         "Памяти Чедвика Бозмана — Намор и Талокан"),
    (30,  640146,  "Муравей и Оса: Квантомания",               "Квантовое царство и Канг Завоеватель"),
    (31,  848326,  "Стражи Галактики 3",                       "Финал Стражей — история Ракеты"),
    (32,  986056,  "Чудо-женщины",                             "Команда Моники, Мисс Марвел и Капитана Марвел"),
    (33,  822119,  "Капитан Америка: Дивный новый мир",        "Сэм Уилсон как Капитан Америка — 2025"),
    (34,  986057,  "Громовержцы",                              "Команда антигероев MCU — 2025"),
]

# Убираем дубль (позиция 28 — страховка)
MCU_FILMS_DEDUPED = []
seen_ids = set()
for entry in MCU_FILMS:
    pos, tmdb_id, title_ru, note = entry
    if tmdb_id not in seen_ids:
        seen_ids.add(tmdb_id)
        MCU_FILMS_DEDUPED.append(entry)


# ═══════════════════════════════════════════════════════════════
# TMDB helpers
# ═══════════════════════════════════════════════════════════════

async def tmdb_get(client: httpx.AsyncClient, path: str, params: dict = {}) -> dict:
    p = {"api_key": settings.tmdb_api_key, **params}
    r = await client.get(f"{TMDB_BASE}{path}", params=p, timeout=15)
    r.raise_for_status()
    return r.json()


async def get_movie(client: httpx.AsyncClient, tmdb_id: int, lang: str) -> dict:
    return await tmdb_get(client, f"/movie/{tmdb_id}", {"language": lang, "append_to_response": "credits"})


# ═══════════════════════════════════════════════════════════════
# БД helpers
# ═══════════════════════════════════════════════════════════════

async def get_lang_ids(db: AsyncSession) -> dict[str, int]:
    rows = (await db.execute(text(
        "SELECT id, code FROM language WHERE code IN ('ru','en')"
    ))).mappings().all()
    return {r["code"]: r["id"] for r in rows}


async def find_by_tmdb(db: AsyncSession, entity_type: str, tmdb_id: int) -> int | None:
    return (await db.execute(text("""
        SELECT id FROM entity
        WHERE entity_type = CAST(:t AS entity_type)
          AND external_ids->>'tmdb' = :tid
        LIMIT 1
    """), {"t": entity_type, "tid": str(tmdb_id)})).scalar_one_or_none()


async def find_collection_id(db: AsyncSession, slug: str) -> int | None:
    return (await db.execute(text("""
        SELECT et.entity_id FROM entity_translation et
        JOIN entity e ON e.id = et.entity_id
        WHERE e.entity_type = 'collection' AND et.slug = :slug
        LIMIT 1
    """), {"slug": slug})).scalar_one_or_none()


async def find_orphan_collection_entity(db: AsyncSession) -> int | None:
    """entity collection без строки в collection — после прерванного seed."""
    return (await db.execute(text("""
        SELECT e.id FROM entity e
        LEFT JOIN collection c ON c.id = e.id
        WHERE e.entity_type = 'collection' AND c.id IS NULL
        ORDER BY e.id DESC
        LIMIT 1
    """))).scalar_one_or_none()


async def upsert_genre(db: AsyncSession, tmdb_genre_id: int, name_en: str, name_ru: str, lang_ids: dict) -> int:
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
        """), {"tid": term_id, "lid": lang_ids[lc], "slug": slugify(name)[:255], "name": name})
    await db.commit()
    return term_id


async def upsert_person(db: AsyncSession, *, tmdb_id: int, name_en: str, name_ru: str | None,
                         profile_path: str | None, is_director: bool, is_actor: bool,
                         lang_ids: dict) -> int:
    existing = await find_by_tmdb(db, "person", tmdb_id)
    if existing:
        await db.execute(text("""
            UPDATE person SET
                is_director = is_director OR :isd,
                is_actor    = is_actor    OR :isa
            WHERE id = :id
        """), {"id": existing, "isd": is_director, "isa": is_actor})
        await db.commit()
        return existing

    person_id = (await db.execute(text("""
        INSERT INTO entity (entity_type, status, primary_image_url, external_ids, extra_metadata)
        VALUES ('person', 'published', :img,
                jsonb_build_object('tmdb', CAST(:tid AS text)), '{}'::jsonb)
        RETURNING id
    """), {"img": f"{POSTER_BASE}{profile_path}" if profile_path else None, "tid": str(tmdb_id)})).scalar_one()

    await db.execute(text("""
        INSERT INTO person (id, is_director, is_actor)
        VALUES (:id, :isd, :isa)
    """), {"id": person_id, "isd": is_director, "isa": is_actor})

    for lc, name in [("ru", name_ru or name_en), ("en", name_en)]:
        await db.execute(text("""
            INSERT INTO entity_translation (entity_id, language_id, search_config, slug, title)
            VALUES (:eid, :lid, :cfg, :slug, :title)
            ON CONFLICT (entity_id, language_id) DO UPDATE SET title = EXCLUDED.title
        """), {"eid": person_id, "lid": lang_ids[lc],
               "cfg": "russian" if lc == "ru" else "english",
               "slug": slugify(name_en)[:200] + f"-{tmdb_id}", "title": name})

    await db.commit()
    return person_id


# ═══════════════════════════════════════════════════════════════
# ШАГ 1: Загрузка фильмов
# ═══════════════════════════════════════════════════════════════

async def load_mcu_films(db: AsyncSession, client: httpx.AsyncClient) -> None:
    log.info("── Шаг 1: загрузка фильмов MCU ──────────────────────")
    lang_ids = await get_lang_ids(db)

    for pos, tmdb_id, title_log, note in MCU_FILMS_DEDUPED:
        existing = await find_by_tmdb(db, "film", tmdb_id)
        if existing:
            log.info("  [%2d] ✓ уже в БД: %s", pos, title_log)
            continue

        log.info("  [%2d] Загружаю: %s (tmdb=%d)...", pos, title_log, tmdb_id)
        try:
            ru = await get_movie(client, tmdb_id, "ru-RU")
            en = await get_movie(client, tmdb_id, "en-US")
        except httpx.HTTPStatusError as e:
            log.warning("       TMDB %d для id=%d — пропускаю", e.response.status_code, tmdb_id)
            continue

        title_ru = ru.get("title") or en.get("title") or title_log
        title_en = en.get("title") or title_ru
        overview_ru = ru.get("overview") or ""
        overview_en = en.get("overview") or ""
        tagline = en.get("tagline") or ""
        release_str = (ru.get("release_date") or en.get("release_date") or "")
        release_year = int(release_str[:4]) if release_str else None
        poster = ru.get("poster_path") or en.get("poster_path")
        backdrop = ru.get("backdrop_path") or en.get("backdrop_path")
        runtime = en.get("runtime")
        vote_avg = en.get("vote_average")
        vote_cnt = en.get("vote_count")
        budget = en.get("budget")
        revenue = en.get("revenue")

        release_date = None
        if release_str:
            try:
                release_date = date.fromisoformat(release_str)
            except ValueError:
                pass

        extra_metadata = {
            "vote_average": vote_avg,
            "vote_count": vote_cnt,
            "budget": budget,
            "revenue": revenue,
            "tagline": tagline or None,
        }

        # entity
        film_id = (await db.execute(text("""
            INSERT INTO entity
                (entity_type, status, primary_image_url, primary_backdrop_url,
                 external_ids, published_at, extra_metadata)
            VALUES ('film', 'published', :poster, :backdrop,
                    jsonb_build_object('tmdb', CAST(:tid AS text)),
                    now(), CAST(:meta AS jsonb))
            RETURNING id
        """), {
            "poster": f"{POSTER_BASE}{poster}" if poster else None,
            "backdrop": f"https://image.tmdb.org/t/p/w1280{backdrop}" if backdrop else None,
            "tid": str(tmdb_id),
            "meta": json.dumps(extra_metadata),
        })).scalar_one()

        # film
        await db.execute(text("""
            INSERT INTO film (id, release_date, release_year, runtime_min, sort_title)
            VALUES (:id, :rd, :ry, :rt, :sort_title)
        """), {
            "id": film_id, "rd": release_date, "ry": release_year,
            "rt": runtime, "sort_title": title_en,
        })

        # переводы
        slug_base = slugify(title_en)[:200] + f"-{tmdb_id}"
        for lc, title, overview in [("ru", title_ru, overview_ru), ("en", title_en, overview_en)]:
            await db.execute(text("""
                INSERT INTO entity_translation
                    (entity_id, language_id, search_config, slug, title, summary, description)
                VALUES (:eid, :lid, :cfg, :slug, :title, :summary, :desc)
                ON CONFLICT (entity_id, language_id) DO UPDATE SET
                    title = EXCLUDED.title, summary = EXCLUDED.summary, description = EXCLUDED.description
            """), {
                "eid": film_id, "lid": lang_ids[lc],
                "cfg": "russian" if lc == "ru" else "english",
                "slug": slug_base, "title": title,
                "summary": tagline or overview[:300] if overview else None,
                "desc": overview,
            })

        await db.commit()

        # жанры
        genres_ru_map = {g["id"]: g["name"] for g in ru.get("genres", [])}
        for g in en.get("genres", []):
            gid = await upsert_genre(db, g["id"], g["name"], genres_ru_map.get(g["id"], g["name"]), lang_ids)
            await db.execute(text("""
                INSERT INTO entity_taxonomy (entity_id, term_id, is_primary)
                VALUES (:eid, :tid, false)
                ON CONFLICT (entity_id, term_id) DO NOTHING
            """), {"eid": film_id, "tid": gid})
        await db.commit()

        # режиссёры + топ-8 актёров
        credits_ru_map = {c["id"]: c for c in ru.get("credits", {}).get("crew", [])}
        credits_ru_cast = {c["id"]: c for c in ru.get("credits", {}).get("cast", [])}
        for crew in en.get("credits", {}).get("crew", []):
            if crew.get("job") != "Director":
                continue
            ru_crew = credits_ru_map.get(crew["id"], crew)
            pid = await upsert_person(db, tmdb_id=crew["id"],
                name_en=crew["name"], name_ru=ru_crew.get("name"),
                profile_path=crew.get("profile_path"),
                is_director=True, is_actor=False, lang_ids=lang_ids)
            await db.execute(text("""
                INSERT INTO film_person (film_id, person_id, role_type, billing_order)
                VALUES (:fid, :pid, 'director', 0)
                ON CONFLICT (film_id, person_id, role_type) DO NOTHING
            """), {"fid": film_id, "pid": pid})

        for idx, actor in enumerate(en.get("credits", {}).get("cast", [])[:8]):
            ru_actor = credits_ru_cast.get(actor["id"], actor)
            pid = await upsert_person(db, tmdb_id=actor["id"],
                name_en=actor["name"], name_ru=ru_actor.get("name"),
                profile_path=actor.get("profile_path"),
                is_director=False, is_actor=True, lang_ids=lang_ids)
            await db.execute(text("""
                INSERT INTO film_person (film_id, person_id, role_type, character_name, billing_order)
                VALUES (:fid, :pid, 'actor', :char, :order)
                ON CONFLICT (film_id, person_id, role_type) DO NOTHING
            """), {"fid": film_id, "pid": pid, "char": actor.get("character"), "order": idx + 1})

        await db.commit()
        log.info("       ✅ Загружен: «%s» (entity id=%d)", title_ru, film_id)

        # Небольшая пауза — не флудим TMDB
        await asyncio.sleep(0.3)

    log.info("  ✅ Загрузка фильмов завершена")


# ═══════════════════════════════════════════════════════════════
# ШАГ 2: Заполнить коллекцию
# ═══════════════════════════════════════════════════════════════

async def fill_marvel_collection(db: AsyncSession) -> None:
    log.info("")
    log.info("── Шаг 2: заполнение коллекции ─────────────────────")

    slug = "marvel-cinematic-universe"
    collection_id = await find_collection_id(db, slug)

    # Старый interim-slug от первых версий seed — сливаем в канонический
    if collection_id is None:
        legacy_id = await find_collection_id(db, "marvel-mcu")
        if legacy_id:
            log.info("  Найдена коллекция marvel-mcu (id=%d) — переношу на %s", legacy_id, slug)
            collection_id = legacy_id
            for lc in ("ru", "en"):
                lang_id = (await db.execute(text(
                    "SELECT id FROM language WHERE code = :c"), {"c": lc}
                )).scalar_one()
                await db.execute(text("""
                    UPDATE entity_translation SET slug = :slug
                    WHERE entity_id = :eid AND language_id = :lid
                """), {"slug": slug, "eid": collection_id, "lid": lang_id})
            await db.commit()

    if collection_id is None:
        collection_id = await find_orphan_collection_entity(db)
        if collection_id:
            log.info("  Продолжаю незавершённую коллекцию (entity id=%d)...", collection_id)
        else:
            log.info("  Создаю коллекцию...")
            collection_id = (await db.execute(text("""
                INSERT INTO entity (entity_type, status, external_ids, extra_metadata)
                VALUES ('collection', 'published', '{}'::jsonb, '{}'::jsonb)
                RETURNING id
            """))).scalar_one()

        await db.execute(text("""
            INSERT INTO collection (
                id, owner_user_id, kind, is_system, cover_entity_id, items_count, extra_metadata
            )
            VALUES (
                :id, :owner, 'editorial', true, NULL, 0,
                CAST(:meta AS jsonb)
            )
            ON CONFLICT (id) DO NOTHING
        """), {
            "id": collection_id,
            "owner": EDITORIAL_USER_ID,
            "meta": json.dumps({"is_featured": True}),
        })

        # переводы
        for lc, title, summary, desc in [
            ("ru",
             "Marvel: Кинематографическая Вселенная",
             "Один из самых амбициозных кинопроектов в истории — 30+ фильмов одной истории",
             "MCU — взаимосвязанная вселенная супергероев Marvel Studios. "
             "Этот список — рекомендованный порядок просмотра: "
             "каждый следующий фильм опирается на события предыдущего."),
            ("en",
             "Marvel Cinematic Universe",
             "One of the most ambitious film projects in history — 30+ films, one story",
             "The MCU — an interconnected universe by Marvel Studios. "
             "Watch order: each film builds on the events of the previous one."),
        ]:
            lang_id = (await db.execute(text(
                "SELECT id FROM language WHERE code = :c"), {"c": lc}
            )).scalar_one()
            await db.execute(text("""
                INSERT INTO entity_translation
                    (entity_id, language_id, search_config, slug, title, summary, description)
                VALUES (:eid, :lid, :cfg, :slug, :title, :summary, :desc)
                ON CONFLICT (entity_id, language_id) DO UPDATE SET
                    title = EXCLUDED.title, summary = EXCLUDED.summary
            """), {
                "eid": collection_id, "lid": lang_id,
                "cfg": "russian" if lc == "ru" else "english",
                "slug": slug, "title": title, "summary": summary, "desc": desc,
            })

        await db.execute(text(
            "UPDATE entity SET published_at = now() WHERE id = :id"
        ), {"id": collection_id})
        await db.commit()
        log.info("  Коллекция создана (id=%d)", collection_id)
    else:
        log.info("  Коллекция найдена (id=%d)", collection_id)
        # Удалить дубль marvel-mcu, если обе коллекции существуют
        legacy_id = await find_collection_id(db, "marvel-mcu")
        if legacy_id and legacy_id != collection_id:
            await db.execute(text(
                "DELETE FROM entity WHERE id = :id AND entity_type = 'collection'"
            ), {"id": legacy_id})
            await db.commit()
            log.info("  Удалён дубль marvel-mcu (id=%d)", legacy_id)

    # Удаляем старые items
    deleted = (await db.execute(text("""
        DELETE FROM collection_item WHERE collection_id = :id
    """), {"id": collection_id})).rowcount
    if deleted:
        log.info("  Удалено старых items: %d", deleted)

    # Заполняем в правильном порядке
    found = 0
    not_found = []

    for pos, tmdb_id, title_log, note in MCU_FILMS_DEDUPED:
        film_id = await find_by_tmdb(db, "film", tmdb_id)
        if film_id is None:
            not_found.append(f"[{pos}] {title_log} (tmdb={tmdb_id})")
            continue

        await db.execute(text("""
            INSERT INTO collection_item (collection_id, entity_id, position, note, added_by_user_id)
            VALUES (:cid, :eid, :pos, :note, :uid)
            ON CONFLICT (collection_id, entity_id) DO UPDATE
                SET position = EXCLUDED.position, note = EXCLUDED.note
        """), {"cid": collection_id, "eid": film_id, "pos": pos, "note": note, "uid": EDITORIAL_USER_ID})
        found += 1

    await db.execute(text("""
        UPDATE collection SET
            items_count = (SELECT count(*) FROM collection_item WHERE collection_id = :id),
            cover_entity_id = (
                SELECT entity_id FROM collection_item
                WHERE collection_id = :id
                ORDER BY position
                LIMIT 1
            )
        WHERE id = :id
    """), {"id": collection_id})
    await db.execute(text("""
        UPDATE entity SET primary_image_url = :url WHERE id = :id
    """), {"id": collection_id, "url": "/articles/C10.jpg"})
    await db.commit()
    log.info("  ✅ Добавлено: %d фильмов в правильном порядке", found)

    if not_found:
        log.warning("  ⚠️  Не найдены в БД — запусти сначала --load-films:")
        for t in not_found:
            log.warning("     • %s", t)


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed MCU коллекции")
    parser.add_argument("--load-films", action="store_true",
                        help="Загрузить фильмы MCU которых нет в БД")
    parser.add_argument("--fill-collection", action="store_true",
                        help="Заполнить коллекцию Marvel в правильном порядке")
    args = parser.parse_args()

    if not args.load_films and not args.fill_collection:
        parser.print_help()
        return

    if args.load_films and not settings.tmdb_api_key:
        raise SystemExit("❌ TMDB_API_KEY не задан в .env")

    log.info("═══════════════════════════════════════════════════════")
    log.info("  Marvel MCU seed")
    log.info("═══════════════════════════════════════════════════════")

    async with AsyncSession(engine) as db:
        if args.load_films:
            async with httpx.AsyncClient() as client:
                await load_mcu_films(db, client)

        if args.fill_collection:
            await fill_marvel_collection(db)

    log.info("")
    log.info("  Готово.")


if __name__ == "__main__":
    asyncio.run(main())
