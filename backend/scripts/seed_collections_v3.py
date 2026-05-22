"""
Seed Collections v3 — финальный скрипт коллекций.

Делает 3 вещи:
  1) РАСШИРЯЕТ 7 существующих коллекций недостающими фильмами
     (через ON CONFLICT DO NOTHING — не пересоздаёт)
  2) СОЗДАЁТ 8 новых тематических коллекций
  3) ВЫВОДИТ итоговую статистику: было/добавлено/стало

Идемпотентно. Можно запускать многократно.

Запуск:
    cd backend
    source venv/bin/activate
    python -m scripts.seed_collections_v3              # все 15
    python -m scripts.seed_collections_v3 --new-only   # только 8 новых
"""
from __future__ import annotations

import argparse
import asyncio
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
log = logging.getLogger("collections-v3")

EDITORIAL_USER_ID = 5
MAX_FILMS = 50


# ════════════════════════════════════════════════════════════════
#  ОПРЕДЕЛЕНИЯ 15 КОЛЛЕКЦИЙ
# ════════════════════════════════════════════════════════════════

COLLECTIONS = [
    # ═══════════ СУЩЕСТВУЮЩИЕ 7 — расширяем ═══════════
    {
        "slug": "french-new-wave",
        "title": "Французская новая волна",
        "summary": "Революция 1960-х: разрушение классического кинематографа в Париже",
        "description": (
            "В конце 1950-х группа молодых критиков из Cahiers du Cinéma — "
            "Годар, Трюффо, Шаброль, Риветт, Ромер — взяла камеры и пошла снимать. "
            "Ручная съёмка, импровизация, разрушение четвёртой стены. Без них не было бы "
            "Тарантино, ПТА, Уэса Андерсона."
        ),
        "strategy": "director_names",
        "params": {
            "directors": [
                "Jean-Luc Godard", "Жан-Люк Годар",
                "François Truffaut", "Франсуа Трюффо",
                "Claude Chabrol", "Клод Шаброль",
                "Jacques Rivette", "Жак Риветт",
                "Éric Rohmer", "Эрик Ромер",
                "Alain Resnais", "Ален Рене",
                "Agnès Varda", "Аньес Варда",
                "Louis Malle", "Луи Маль",
                "Jacques Demy", "Жак Деми",
            ],
        },
        "is_new": False,
    },
    {
        "slug": "cinema-for-clip-thinking",
        "title": "Кино для клипового мышления",
        "summary": "Короткое, быстрое, ритмичное — кино для тех кто живёт в TikTok",
        "description": (
            "Если средний план в кино 1970-х был 6 секунд, а в современном — 1.8, "
            "то это кино было сделано для следующего шага. Энергия, ритм, "
            "безостановочный монтаж."
        ),
        "strategy": "rating_genre",
        "params": {"min_rating": 6.5, "genres": [28, 53, 80], "min_year": 2010},
        "is_new": False,
    },
    {
        "slug": "italy-through-cinema",
        "title": "Италия через экран",
        "summary": "От неореализма Росселлини до барокко Соррентино",
        "description": (
            "Италия дала кинематографу больше великих режиссёров на душу населения, "
            "чем любая другая страна. От послевоенного неореализма к карнавалу Феллини, "
            "политическим триллерам Петри, постмодерну Соррентино."
        ),
        "strategy": "country",
        "params": {"country": "IT", "min_rating": 6.8},
        "is_new": False,
    },
    {
        "slug": "kubrick-evolution",
        "title": "Стэнли Кубрик: эволюция мастера",
        "summary": "Все фильмы перфекциониста, который снимал раз в 7 лет — но каждый менял кино",
        "description": (
            "Кубрик за 47 лет снял 13 полнометражных фильмов. Каждый — формальный "
            "эксперимент в новом жанре."
        ),
        "strategy": "director_names",
        "params": {"directors": ["Stanley Kubrick", "Стэнли Кубрик"]},
        "is_new": False,
    },
    {
        "slug": "east-loneliness",
        "title": "Восточный взгляд на одиночество",
        "summary": "Японское, корейское, тайваньское кино о тишине и присутствии",
        "description": (
            "Восточная кинематографическая традиция работает с одиночеством иначе, "
            "чем западная. Не как с проблемой, а как с естественным состоянием. "
            "Озу, Куросава, Хамагути, Ли Чхан Дон, Хоу Сяосянь."
        ),
        "strategy": "country",
        "params": {"country": "JP|KR|TW|HK|CN", "min_rating": 7.0},
        "is_new": False,
    },
    {
        "slug": "memory-and-forgetting",
        "title": "Кино о памяти",
        "summary": "Помнить, забывать, переписывать прошлое — фильмы которые меняют то что мы помним",
        "description": (
            "'Помни', 'Вечное сияние чистого разума', 'Мементо', 'Зеркало' Тарковского, "
            "'Хиросима, моя любовь'. Эти фильмы исследуют главный вопрос: что такое 'я' "
            "если память можно потерять, искажать, заменить."
        ),
        "strategy": "keywords",
        "params": {
            "keywords": [
                "memory", "amnesia", "memory loss", "remembering",
                "flashback", "dementia", "forgetting", "memories",
                "память", "воспоминания",
            ],
            "min_rating": 6.5,
        },
        "is_new": False,
    },
    {
        "slug": "black-and-white-masterpieces",
        "title": "Чёрно-белые шедевры",
        "summary": "Классика до цветного кино — и современные авторы выбирающие монохром",
        "description": (
            "До 1960-х чёрно-белая плёнка была нормой. Сейчас — сознательный выбор. "
            "От 'Касабланки' до 'Зоны интересов' Глейзера, от 'Гражданина Кейна' до 'Артиста'."
        ),
        "strategy": "rating_genre",
        "params": {"min_rating": 7.2, "max_year": 1965},
        "is_new": False,
    },

    # ═══════════ НОВЫЕ 8 ═══════════
    {
        "slug": "marvel-cinematic-universe",
        "title": "Marvel: Кинематографическая Вселенная",
        "summary": "Один из самых амбициозных кинопроектов в истории — 30+ фильмов одной истории",
        "description": (
            "Кевин Файги начал в 2008 году с 'Железного человека', и через одиннадцать лет "
            "'Финал' стал кульминацией одной из самых сложных непрерывных нарративов в "
            "истории кино."
        ),
        "strategy": "marvel",
        "params": {},
        "is_new": True,
    },
    {
        "slug": "cinema-of-2000s-generation",
        "title": "Кино на котором выросло поколение 00-х",
        "summary": "Pulp Fiction, Fight Club, Eternal Sunshine — фильмы которые сформировали миллениалов",
        "description": (
            "Эти фильмы вышли в 1994-2010, когда сегодняшние тридцатилетние были подростками. "
            "Каждый из них меняет жанр или формальный язык. Кино, которое смотрели на DVD "
            "дома и обсуждали в школе."
        ),
        "strategy": "title_exact",
        "params": {
            "titles_with_year": [
                ("Pulp Fiction", 1994), ("Криминальное чтиво", 1994),
                ("Fight Club", 1999), ("Бойцовский клуб", 1999),
                ("The Matrix", 1999), ("Матрица", 1999),
                ("Eternal Sunshine of the Spotless Mind", 2004),
                ("Вечное сияние чистого разума", 2004),
                ("Memento", 2000), ("Помни", 2000),
                ("Inception", 2010), ("Начало", 2010),
                ("The Dark Knight", 2008), ("Тёмный рыцарь", 2008),
                ("American Beauty", 1999), ("Красота по-американски", 1999),
                ("Forrest Gump", 1994), ("Форрест Гамп", 1994),
                ("The Shawshank Redemption", 1994), ("Побег из Шоушенка", 1994),
                ("Trainspotting", 1996), ("На игле", 1996),
                ("Donnie Darko", 2001), ("Донни Дарко", 2001),
                ("The Big Lebowski", 1998), ("Большой Лебовски", 1998),
                ("Lost in Translation", 2003), ("Трудности перевода", 2003),
                ("Requiem for a Dream", 2000), ("Реквием по мечте", 2000),
                ("Léon", 1994), ("Léon: The Professional", 1994), ("Леон", 1994),
                ("Fargo", 1996), ("Фарго", 1996),
                ("Magnolia", 1999), ("Магнолия", 1999),
                ("There Will Be Blood", 2007), ("Нефть", 2007),
                ("No Country for Old Men", 2007), ("Старикам тут не место", 2007),
                ("The Departed", 2006), ("Отступники", 2006),
                ("Snatch", 2000), ("Снэтч", 2000),
                ("Lock, Stock and Two Smoking Barrels", 1998),
                ("Карты, деньги, два ствола", 1998),
                ("Kill Bill: Vol. 1", 2003), ("Убить Билла", 2003),
                ("Sin City", 2005), ("Город грехов", 2005),
                ("V for Vendetta", 2005), ("V — значит вендетта", 2005),
                ("Mr. Nobody", 2009), ("Господин Никто", 2009),
                ("500 Days of Summer", 2009), ("500 дней лета", 2009),
                ("Juno", 2007), ("Джуно", 2007),
            ],
        },
        "is_new": True,
    },
    {
        "slug": "oscar-best-picture",
        "title": "Лауреаты Оскара за лучший фильм",
        "summary": "Главные фильмы по версии Американской киноакадемии за последние 30 лет",
        "description": (
            "Оскар за лучший фильм — индикатор того, что считается профессиональной "
            "вершиной в Голливуде на момент выхода."
        ),
        "strategy": "title_exact",
        "params": {
            "titles_with_year": [
                ("Forrest Gump", 1994), ("Форрест Гамп", 1994),
                ("Braveheart", 1995), ("Храброе сердце", 1995),
                ("The English Patient", 1996),
                ("Titanic", 1997), ("Титаник", 1997),
                ("Shakespeare in Love", 1998),
                ("American Beauty", 1999),
                ("Gladiator", 2000), ("Гладиатор", 2000),
                ("A Beautiful Mind", 2001), ("Игры разума", 2001),
                ("Chicago", 2002), ("Чикаго", 2002),
                ("The Lord of the Rings: The Return of the King", 2003),
                ("Властелин колец: Возвращение короля", 2003),
                ("Million Dollar Baby", 2004),
                ("Crash", 2004),
                ("The Departed", 2006), ("Отступники", 2006),
                ("No Country for Old Men", 2007),
                ("Slumdog Millionaire", 2008), ("Миллионер из трущоб", 2008),
                ("The Hurt Locker", 2008), ("Повелитель бури", 2008),
                ("The King's Speech", 2010), ("Король говорит!", 2010),
                ("The Artist", 2011), ("Артист", 2011),
                ("Argo", 2012), ("Операция «Арго»", 2012),
                ("12 Years a Slave", 2013), ("12 лет рабства", 2013),
                ("Birdman", 2014), ("Бёрдмэн", 2014),
                ("Spotlight", 2015), ("В центре внимания", 2015),
                ("Moonlight", 2016), ("Лунный свет", 2016),
                ("The Shape of Water", 2017), ("Форма воды", 2017),
                ("Green Book", 2018), ("Зелёная книга", 2018),
                ("Parasite", 2019), ("Паразиты", 2019),
                ("Nomadland", 2020), ("Земля кочевников", 2020),
                ("CODA", 2021),
                ("Everything Everywhere All at Once", 2022),
                ("Всё везде и сразу", 2022),
                ("Oppenheimer", 2023), ("Оппенгеймер", 2023),
            ],
        },
        "is_new": True,
    },
    {
        "slug": "elitarno-nishevo-conceptualno",
        "title": "Элитарно-нишево-концептуальное",
        "summary": "Артхаус 2020-х: A24, Neon, Mubi — кино для тех кто читает рецензии до похода",
        "description": (
            "Если вы видели 'Прошлые жизни', 'Аноре', 'Зону интересов' или 'Субстанцию' — "
            "вы знаете о чём это. Студии A24 и Neon стали новым лицом авторского кино. "
            "Это не фильмы для всех. Но те, для кого они — те находят в них себя."
        ),
        "strategy": "rating_genre",
        "params": {
            "min_rating": 7.0, "min_year": 2018,
            "genres": [18], "exclude_genres": [28, 12, 14],
        },
        "is_new": True,
    },
    {
        "slug": "best-documentary",
        "title": "Лучшее документальное кино",
        "summary": "Документалки которые меняют как мы видим реальность",
        "description": (
            "Хороший документальный фильм — это не репортаж. Это авторская интерпретация "
            "фактов. От 'Человека на канате' Маршалла до 'Гражданина Х'."
        ),
        "strategy": "genres",
        "params": {"genres": [99], "min_rating": 7.0},
        "is_new": True,
    },
    {
        "slug": "women-directors",
        "title": "Женщины-режиссёры",
        "summary": "Как женщины снимают кино — отдельный взгляд, отдельная грамматика",
        "description": (
            "Сто лет в Голливуде женщин-режиссёров считали по пальцам одной руки. "
            "С 2010-х это меняется. Гервиг, Хлоя Жао, Сьямма, Кэмпион, Бигелоу, Феннелл, "
            "ДюВерней. Это не 'женское кино'. Это просто кино, которое снимают женщины."
        ),
        "strategy": "women_hybrid",
        "params": {
            "known_directors": [
                "Greta Gerwig", "Грета Гервиг",
                "Sofia Coppola", "София Коппола",
                "Chloé Zhao", "Хлоя Жао",
                "Kathryn Bigelow", "Кэтрин Бигелоу",
                "Céline Sciamma", "Селин Сьямма",
                "Emerald Fennell", "Эмеральд Феннелл",
                "Jane Campion", "Джейн Кэмпион",
                "Lana Wachowski", "Лана Вачовски",
                "Lilly Wachowski", "Лилли Вачовски",
                "Nancy Meyers", "Нэнси Майерс",
                "Nora Ephron", "Нора Эфрон",
                "Sarah Polley", "Сара Полли",
                "Debra Granik", "Дебра Граник",
                "Ava DuVernay", "Ава ДюВерней",
                "Lena Dunham", "Лена Данэм",
                "Julia Ducournau", "Жюли Декурно",
                "Coralie Fargeat", "Корали Фаржа",
                "Lulu Wang", "Лулу Ван",
                "Patty Jenkins", "Патти Дженкинс",
                "Olivia Wilde", "Оливия Уайлд",
                "Andrea Arnold", "Андреа Арнольд",
                "Lynne Ramsay", "Линн Рэмзи",
                "Mira Nair", "Мира Наир",
            ],
            "min_rating_for_gender": 6.5,
        },
        "is_new": True,
    },
    {
        "slug": "catholic-church-cinema",
        "title": "Католическая церковь в кино",
        "summary": "Папы, монахи, святые, экзорцизм — религия как драматический материал",
        "description": (
            "Католичество с его иерархией, ритуалами, грехом и спасением — благодатный "
            "материал для кино. От 'Молчания' Скорсезе до 'Великой красоты' Соррентино, "
            "от 'Имени розы' Анно до 'Молодого папы'."
        ),
        "strategy": "keywords_with_titles",
        "params": {
            "keywords": [
                "pope", "priest", "vatican", "catholic", "nun", "monk",
                "jesuit", "cardinal", "religion", "faith", "church",
                "exorcism", "crusade", "monastery", "confession",
            ],
            "additional_titles": [
                ("Silence", 2016), ("Молчание", 2016),
                ("The Name of the Rose", 1986), ("Имя розы", 1986),
                ("The Young Pope", 2016), ("Молодой папа", 2016),
                ("The New Pope", 2020), ("Новый папа", 2020),
                ("The Great Beauty", 2013), ("Великая красота", 2013),
                ("Doubt", 2008), ("Сомнение", 2008),
                ("Spotlight", 2015), ("В центре внимания", 2015),
                ("The Exorcist", 1973), ("Изгоняющий дьявола", 1973),
                ("The Passion of the Christ", 2004), ("Страсти Христовы", 2004),
                ("The Two Popes", 2019), ("Два папы", 2019),
                ("Of Gods and Men", 2010), ("Люди и боги", 2010),
            ],
        },
        "is_new": True,
    },
    {
        "slug": "great-russian-cinema",
        "title": "Великое русское кино",
        "summary": "Советская классика и российский авторский кинематограф",
        "description": (
            "От 'Андрея Рублёва' Тарковского до 'Левиафана' Звягинцева. Это кино, в котором "
            "соединяются великая литературная традиция, философская глубина и формальный эксперимент."
        ),
        "strategy": "russian_great",
        "params": {
            "known_directors": [
                "Andrei Tarkovsky", "Андрей Тарковский",
                "Alexander Sokurov", "Александр Сокуров",
                "Andrey Zvyagintsev", "Андрей Звягинцев",
                "Andrei Konchalovsky", "Андрей Кончаловский",
                "Nikita Mikhalkov", "Никита Михалков",
                "Eldar Ryazanov", "Эльдар Рязанов",
                "Leonid Gaidai", "Леонид Гайдай",
                "Aleksei Balabanov", "Алексей Балабанов",
                "Aleksei German", "Алексей Герман",
                "Ilya Khrzhanovsky", "Илья Хржановский",
                "Sergei Eisenstein", "Сергей Эйзенштейн",
                "Larisa Shepitko", "Лариса Шепитько",
                "Elem Klimov", "Элем Климов",
                "Vasili Shukshin", "Василий Шукшин",
                "Mikhail Romm", "Михаил Ромм",
                "Sergei Bondarchuk", "Сергей Бондарчук",
                "Stanislav Govorukhin", "Станислав Говорухин",
                "Kira Muratova", "Кира Муратова",
                "Aleksei Popogrebsky", "Алексей Попогребский",
                "Yuri Bykov", "Юрий Быков",
            ],
            "min_rating_fallback": 7.0,
        },
        "is_new": True,
    },
]


# ════════════════════════════════════════════════════════════════
#  СТРАТЕГИИ ПОДБОРА
# ════════════════════════════════════════════════════════════════

async def pick_by_director_names(db, directors, limit=MAX_FILMS):
    sql = text("""
        SELECT DISTINCT f.id, COALESCE((e.extra_metadata->>'vote_average')::float, 0) AS r
        FROM film f
        JOIN entity e ON e.id = f.id
        JOIN film_person fp ON fp.film_id = f.id
        JOIN person p ON p.id = fp.person_id
        LEFT JOIN entity_translation pt ON pt.entity_id = p.id
        WHERE fp.role_type = 'director'
          AND (lower(pt.title) = ANY(:names) OR lower(p.sort_name) = ANY(:names))
          AND e.status = 'published'
        ORDER BY r DESC NULLS LAST
        LIMIT :lim
    """)
    rows = (await db.execute(sql, {"names": [n.lower() for n in directors], "lim": limit})).all()
    return [r[0] for r in rows]


async def pick_by_country(db, country, min_rating=0.0, limit=MAX_FILMS):
    countries = country.split("|")
    sql = text("""
        SELECT f.id, COALESCE((e.extra_metadata->>'vote_average')::float, 0) AS r
        FROM film f
        JOIN entity e ON e.id = f.id
        WHERE e.status = 'published'
          AND (
            e.extra_metadata->'origin_country' ?| :countries
            OR EXISTS (
              SELECT 1 FROM jsonb_array_elements(
                COALESCE(e.extra_metadata->'production_countries', '[]'::jsonb)
              ) pc
              WHERE pc->>'iso_3166_1' = ANY(:countries)
            )
          )
          AND COALESCE((e.extra_metadata->>'vote_average')::float, 0) >= :min_r
        ORDER BY r DESC NULLS LAST
        LIMIT :lim
    """)
    rows = (await db.execute(sql, {"countries": countries, "min_r": min_rating, "lim": limit})).all()
    return [r[0] for r in rows]


async def pick_by_keywords(db, keywords, min_rating=0.0, limit=MAX_FILMS):
    sql = text("""
        SELECT DISTINCT f.id, COALESCE((e.extra_metadata->>'vote_average')::float, 0) AS r
        FROM film f
        JOIN entity e ON e.id = f.id
        JOIN entity_taxonomy et ON et.entity_id = f.id
        JOIN taxonomy_term tt ON tt.id = et.term_id
        LEFT JOIN taxonomy_term_translation ttt ON ttt.term_id = tt.id
        WHERE tt.term_type = 'keyword'
          AND (lower(tt.code) = ANY(:kws) OR lower(ttt.name) = ANY(:kws))
          AND e.status = 'published'
          AND COALESCE((e.extra_metadata->>'vote_average')::float, 0) >= :min_r
        ORDER BY r DESC NULLS LAST
        LIMIT :lim
    """)
    rows = (await db.execute(sql, {"kws": [k.lower() for k in keywords], "min_r": min_rating, "lim": limit})).all()
    return [r[0] for r in rows]


async def pick_by_genres(db, genres, min_rating=0.0, limit=MAX_FILMS):
    codes = [f"tmdb-{g}" for g in genres]
    sql = text("""
        SELECT DISTINCT f.id, COALESCE((e.extra_metadata->>'vote_average')::float, 0) AS r
        FROM film f
        JOIN entity e ON e.id = f.id
        JOIN entity_taxonomy et ON et.entity_id = f.id
        JOIN taxonomy_term tt ON tt.id = et.term_id
        WHERE tt.code = ANY(:codes) AND tt.term_type = 'genre'
          AND e.status = 'published'
          AND COALESCE((e.extra_metadata->>'vote_average')::float, 0) >= :min_r
        ORDER BY r DESC NULLS LAST
        LIMIT :lim
    """)
    rows = (await db.execute(sql, {"codes": codes, "min_r": min_rating, "lim": limit})).all()
    return [r[0] for r in rows]


async def pick_by_rating_genre(db, *, min_rating=0.0, genres=None, exclude_genres=None,
                                min_year=None, max_year=None, limit=MAX_FILMS):
    where_parts = ["e.status = 'published'",
                   "COALESCE((e.extra_metadata->>'vote_average')::float, 0) >= :min_r"]
    params: dict[str, Any] = {"min_r": min_rating, "lim": limit}

    if min_year is not None:
        where_parts.append("f.release_year >= :min_y")
        params["min_y"] = min_year
    if max_year is not None:
        where_parts.append("f.release_year <= :max_y")
        params["max_y"] = max_year
    if genres:
        params["genre_codes"] = [f"tmdb-{g}" for g in genres]
        where_parts.append("""
            EXISTS (SELECT 1 FROM entity_taxonomy et JOIN taxonomy_term tt ON tt.id = et.term_id
                    WHERE et.entity_id = f.id AND tt.code = ANY(:genre_codes))
        """)
    if exclude_genres:
        params["excl_codes"] = [f"tmdb-{g}" for g in exclude_genres]
        where_parts.append("""
            NOT EXISTS (SELECT 1 FROM entity_taxonomy et JOIN taxonomy_term tt ON tt.id = et.term_id
                        WHERE et.entity_id = f.id AND tt.code = ANY(:excl_codes))
        """)

    sql = text(f"""
        SELECT DISTINCT f.id, COALESCE((e.extra_metadata->>'vote_average')::float, 0) AS r
        FROM film f JOIN entity e ON e.id = f.id
        WHERE {' AND '.join(where_parts)}
        ORDER BY r DESC NULLS LAST
        LIMIT :lim
    """)
    rows = (await db.execute(sql, params)).all()
    return [r[0] for r in rows]


async def pick_by_title_exact(db, titles_with_year, limit=MAX_FILMS):
    found: set[int] = set()
    for title, year in titles_with_year:
        if len(found) >= limit:
            break
        sql = text("""
            SELECT f.id FROM film f
            JOIN entity_translation et ON et.entity_id = f.id
            WHERE lower(et.title) = lower(:t)
              AND (f.release_year BETWEEN :y - 1 AND :y + 1)
            LIMIT 1
        """)
        row = (await db.execute(sql, {"t": title, "y": year})).first()
        if row:
            found.add(row[0])
    return list(found)


async def pick_marvel(db, limit=MAX_FILMS):
    sql = text("""
        SELECT DISTINCT f.id, COALESCE((e.extra_metadata->>'vote_average')::float, 0) AS r
        FROM film f
        JOIN entity e ON e.id = f.id
        WHERE e.status = 'published'
          AND (
            EXISTS (
              SELECT 1 FROM jsonb_array_elements(
                COALESCE(e.extra_metadata->'production_companies', '[]'::jsonb)
              ) pc WHERE pc->>'name' ILIKE '%marvel%'
            )
            OR (e.extra_metadata->'belongs_to_collection'->>'name') ILIKE ANY(ARRAY[
              '%Avengers%', '%Iron Man%', '%Captain America%', '%Thor%',
              '%Spider-Man%', '%Guardians of the Galaxy%', '%Black Panther%',
              '%Doctor Strange%', '%Ant-Man%', '%Deadpool%', '%X-Men%',
              '%Wolverine%', '%Fantastic Four%', '%Captain Marvel%'
            ])
          )
        ORDER BY r DESC NULLS LAST
        LIMIT :lim
    """)
    rows = (await db.execute(sql, {"lim": limit})).all()
    return [r[0] for r in rows]


async def pick_women_hybrid(db, *, known_directors, min_rating_for_gender=6.5, limit=MAX_FILMS):
    found: set[int] = set()
    by_names = await pick_by_director_names(db, known_directors, limit=limit)
    found.update(by_names)

    if len(found) < limit:
        need = limit - len(found)
        excluded = list(found) if found else [0]
        sql = text("""
            SELECT DISTINCT f.id, COALESCE((e.extra_metadata->>'vote_average')::float, 0) AS r
            FROM film f
            JOIN entity e ON e.id = f.id
            JOIN film_person fp ON fp.film_id = f.id
            JOIN person p ON p.id = fp.person_id
            WHERE fp.role_type = 'director'
              AND p.gender = 1
              AND e.status = 'published'
              AND f.id != ALL(:excl)
              AND COALESCE((e.extra_metadata->>'vote_average')::float, 0) >= :min_r
            ORDER BY r DESC NULLS LAST
            LIMIT :lim
        """)
        rows = (await db.execute(sql, {"excl": excluded, "min_r": min_rating_for_gender, "lim": need})).all()
        for r in rows:
            found.add(r[0])

    return list(found)[:limit]


async def pick_russian_great(db, *, known_directors, min_rating_fallback=7.0, limit=MAX_FILMS):
    found: set[int] = set()
    by_names = await pick_by_director_names(db, known_directors, limit=limit)
    found.update(by_names)

    if len(found) < limit:
        need = limit - len(found)
        excluded = list(found) if found else [0]
        sql = text("""
            SELECT DISTINCT f.id, COALESCE((e.extra_metadata->>'vote_average')::float, 0) AS r
            FROM film f
            JOIN entity e ON e.id = f.id
            WHERE e.status = 'published'
              AND f.id != ALL(:excl)
              AND (
                e.extra_metadata->'origin_country' ?| ARRAY['RU', 'SU']
                OR EXISTS (
                  SELECT 1 FROM jsonb_array_elements(
                    COALESCE(e.extra_metadata->'production_countries', '[]'::jsonb)
                  ) pc WHERE pc->>'iso_3166_1' IN ('RU', 'SU')
                )
              )
              AND COALESCE((e.extra_metadata->>'vote_average')::float, 0) >= :min_r
            ORDER BY r DESC NULLS LAST
            LIMIT :lim
        """)
        rows = (await db.execute(sql, {"excl": excluded, "min_r": min_rating_fallback, "lim": need})).all()
        for r in rows:
            found.add(r[0])

    return list(found)[:limit]


async def pick_keywords_with_titles(db, *, keywords, additional_titles, limit=MAX_FILMS):
    found: set[int] = set()
    by_titles = await pick_by_title_exact(db, additional_titles, limit=limit)
    found.update(by_titles)

    if len(found) < limit:
        need = limit - len(found)
        by_kw = await pick_by_keywords(db, keywords, limit=need + len(found))
        for fid in by_kw:
            if fid not in found:
                found.add(fid)
                if len(found) >= limit:
                    break

    return list(found)[:limit]


async def pick_films(db, conf):
    s = conf["strategy"]
    p = conf["params"]
    if s == "director_names": return await pick_by_director_names(db, p["directors"])
    if s == "country":        return await pick_by_country(db, p["country"], min_rating=p.get("min_rating", 0))
    if s == "keywords":       return await pick_by_keywords(db, p["keywords"], min_rating=p.get("min_rating", 0))
    if s == "keywords_with_titles": return await pick_keywords_with_titles(db,
                                                                            keywords=p["keywords"],
                                                                            additional_titles=p["additional_titles"])
    if s == "genres":         return await pick_by_genres(db, p["genres"], min_rating=p.get("min_rating", 0))
    if s == "rating_genre":   return await pick_by_rating_genre(db,
                                                                  min_rating=p.get("min_rating", 0),
                                                                  genres=p.get("genres"),
                                                                  exclude_genres=p.get("exclude_genres"),
                                                                  min_year=p.get("min_year"),
                                                                  max_year=p.get("max_year"))
    if s == "title_exact":    return await pick_by_title_exact(db, p["titles_with_year"])
    if s == "marvel":         return await pick_marvel(db)
    if s == "women_hybrid":   return await pick_women_hybrid(db,
                                                              known_directors=p["known_directors"],
                                                              min_rating_for_gender=p.get("min_rating_for_gender", 6.5))
    if s == "russian_great":  return await pick_russian_great(db,
                                                                known_directors=p["known_directors"],
                                                                min_rating_fallback=p.get("min_rating_fallback", 7.0))
    log.warning("Unknown strategy: %s", s)
    return []


# ════════════════════════════════════════════════════════════════
#  СОЗДАНИЕ / ДОПОЛНЕНИЕ
# ════════════════════════════════════════════════════════════════

async def get_collection_id_by_slug(db, slug):
    sql = text("""
        SELECT c.id FROM collection c
        JOIN entity_translation et ON et.entity_id = c.id
        WHERE et.slug = :slug
          AND et.language_id = (SELECT id FROM language WHERE code='ru')
        LIMIT 1
    """)
    return (await db.execute(sql, {"slug": slug})).scalar_one_or_none()


async def count_collection_films(db, col_id):
    return (await db.execute(text("SELECT count(*) FROM collection_item WHERE collection_id = :c"),
                              {"c": col_id})).scalar_one()


async def create_collection_entity(db, conf):
    entity_id = (await db.execute(text("""
        INSERT INTO entity (entity_type, status, external_ids, extra_metadata)
        VALUES (CAST('collection' AS entity_type), 'published', '{}'::jsonb, '{}'::jsonb)
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
    """), {
        "id": entity_id,
        "owner": EDITORIAL_USER_ID,
        "meta": '{"is_featured": true}',
    })

    await db.execute(text("""
        INSERT INTO entity_translation (
            entity_id, language_id, search_config, slug, title, summary, description
        ) VALUES (
            :id, (SELECT id FROM language WHERE code='ru'),
            'russian', :slug, :title, :summary, :desc
        )
    """), {
        "id": entity_id, "slug": conf["slug"],
        "title": conf["title"], "summary": conf["summary"],
        "desc": conf["description"],
    })

    await db.execute(text("UPDATE entity SET published_at = now() WHERE id = :id"),
                     {"id": entity_id})
    await db.commit()
    return entity_id


async def add_films_to_collection(db, col_id, film_ids):
    if not film_ids:
        return 0
    pos_row = await db.execute(
        text("SELECT COALESCE(MAX(position), 0) FROM collection_item WHERE collection_id = :c"),
        {"c": col_id},
    )
    current_max = pos_row.scalar_one()

    added = 0
    for i, fid in enumerate(film_ids, start=1):
        result = await db.execute(text("""
            INSERT INTO collection_item (collection_id, entity_id, position, added_by_user_id)
            VALUES (:c, :e, :p, :u)
            ON CONFLICT (collection_id, entity_id) DO NOTHING
            RETURNING collection_id
        """), {"c": col_id, "e": fid, "p": current_max + i, "u": EDITORIAL_USER_ID})
        if result.first():
            added += 1

    await db.execute(text("""
        UPDATE collection SET items_count = (
            SELECT count(*) FROM collection_item WHERE collection_id = :c
        ) WHERE id = :c
    """), {"c": col_id})
    await db.commit()
    return added


# ════════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════════

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Seed editorial collections v3")
    p.add_argument(
        "--new-only",
        action="store_true",
        help="Создать/наполнить только 8 новых коллекций (без 7 существующих)",
    )
    return p.parse_args()


async def main():
    args = parse_args()
    batch = [c for c in COLLECTIONS if c["is_new"]] if args.new_only else COLLECTIONS

    log.info("═════════════════════════════════════════════════════")
    log.info(" Seed Collections v3 — %d коллекций", len(batch))
    log.info("═════════════════════════════════════════════════════")

    stats: list[dict] = []

    async with AsyncSessionLocal() as db:
        for i, conf in enumerate(batch, start=1):
            slug = conf["slug"]
            title = conf["title"]
            log.info("")
            log.info("[%d/%d] %s", i, len(batch), title)
            log.info("       slug: %s | стратегия: %s", slug, conf["strategy"])

            existing_id = await get_collection_id_by_slug(db, slug)
            if existing_id:
                col_id = existing_id
                before = await count_collection_films(db, col_id)
                log.info("       коллекция существует (id=%d, фильмов: %d)", col_id, before)
            else:
                col_id = await create_collection_entity(db, conf)
                before = 0
                log.info("       создана новая коллекция (id=%d)", col_id)

            try:
                film_ids = await pick_films(db, conf)
            except Exception as exc:
                log.error("       ОШИБКА подбора: %s", exc)
                await db.rollback()
                stats.append({"slug": slug, "title": title, "before": before,
                              "added": 0, "after": before, "is_new": conf["is_new"]})
                continue

            log.info("       подобрано: %d фильмов", len(film_ids))

            try:
                added = await add_films_to_collection(db, col_id, film_ids)
                after = await count_collection_films(db, col_id)
                log.info("       добавлено: %d (было %d → стало %d)", added, before, after)
            except Exception as exc:
                log.error("       ОШИБКА добавления: %s", exc)
                await db.rollback()
                added, after = 0, before

            stats.append({"slug": slug, "title": title, "before": before,
                          "added": added, "after": after, "is_new": conf["is_new"]})

    # Финальный отчёт
    log.info("")
    log.info("═══════════════════════════════════════════════════════════════")
    log.info("  ИТОГОВАЯ СТАТИСТИКА")
    log.info("═══════════════════════════════════════════════════════════════")
    log.info("")
    log.info("%-3s %-40s %5s %10s %6s", "№", "Название", "Было", "Добавлено", "Стало")
    log.info("─" * 75)
    total_added = 0
    for i, s in enumerate(stats, start=1):
        t = s["title"]
        if len(t) > 38:
            t = t[:37] + "…"
        new_mark = " (NEW)" if s["is_new"] and s["before"] == 0 else ""
        log.info("%-3d %-40s %5d %10d %6d%s", i, t, s["before"], s["added"], s["after"], new_mark)
        total_added += s["added"]
    log.info("─" * 75)
    log.info("ИТОГО добавлено фильмов: %d", total_added)
    log.info("ИТОГО коллекций:         %d", len(stats))
    log.info("═══════════════════════════════════════════════════════════════")


if __name__ == "__main__":
    asyncio.run(main())
