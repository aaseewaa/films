"""
Seed-скрипт: обновление / создание 5 коллекций.

Коллекции:
  1. cinema-for-clip-thinking   — «Кино для клипового мышления» (полностью переделана)
  2. catholic-church-cinema     — «Католическая церковь в кино» (новая)
  3. generation-2000s           — «Кино, на котором выросло поколение 2000-х» (новая)
  4. italy-through-cinema       — «Италия через кино» (урезана до 11 фильмов)
  5. women-directors            — «Женщины-режиссёры» (новая)

Идемпотентность:
  - Существующую коллекцию по slug НЕ пересоздаём — только обновляем items.
  - Все старые items коллекции сначала удаляются, затем вставляются заново.
  - Фильмы ищутся сначала по русскому title, затем по английскому.
  - Ненайденные фильмы пропускаются с WARNING (проверь вручную).

Запуск:
    cd backend
    source venv/bin/activate
    python -m scripts.seed_collections_update
"""
from __future__ import annotations

import asyncio
import json
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)-15s | %(message)s",
)
log = logging.getLogger("seed_update")

EDITORIAL_USER_ID = 5  # id системного пользователя «Редакция»

# Редакторские обложки (статика front/public/articles/)
COLLECTION_COVERS: dict[str, str] = {
    "cinema-for-clip-thinking": "/articles/C1.jpg",
    "catholic-church-cinema": "/articles/C6.jpg",
    "generation-2000s": "/articles/C5.jpg",
    "italy-through-cinema": "/articles/C15.jpg",
    "women-directors": "/articles/C11.jpg",
    "memory-and-forgetting": "/articles/C8.jpg",
    "marvel-cinematic-universe": "/articles/C10.jpg",
}

# ═══════════════════════════════════════════════════════════════
# КОНФИГУРАЦИЯ КОЛЛЕКЦИЙ
# Каждый фильм — dict с ключами:
#   title_ru  — русское название (для поиска в entity_translation)
#   title_en  — английское название (fallback-поиск)
#   note      — редакторский комментарий (отображается в карточке коллекции)
# ═══════════════════════════════════════════════════════════════

COLLECTIONS = [

    # ──────────────────────────────────────────────────────────
    # 1. Кино для клипового мышления (полная замена списка)
    # ──────────────────────────────────────────────────────────
    {
        "slug": "cinema-for-clip-thinking",
        "title_ru": "Кино для клипового мышления",
        "title_en": "Cinema for Clip Thinking",
        "summary_ru": "Быстрый монтаж, дроби, ритм как у клипа — фильмы, которые не дают скучать ни секунды.",
        "summary_en": "Fast cuts, pop references, rhythm like a music video — films that never let you breathe.",
        "description_ru": (
            "Эдгар Райт, Гай Ричи, Уэс Андерсон, Дэни Бойл — режиссёры, выросшие на MTV "
            "и сделавшие монтажный темп основой стиля. Сюда попали фильмы, которые "
            "захватывают с первого кадра и держат до финальных титров — иногда через "
            "визуальный фейерверк, иногда через идеальный тайминг шутки."
        ),
        "tags": ["fast-paced", "stylized", "modern", "comedy"],
        "is_featured": True,
        "cover_image": COLLECTION_COVERS["cinema-for-clip-thinking"],
        "films": [
            {"title_ru": "Джон Уик",                           "title_en": "John Wick",                         "note": "Боевая хореография как искусство"},
            {"title_ru": "Дэдпул",                             "title_en": "Deadpool",                          "note": "Мета-комедия, которая смеётся над собой"},
            {"title_ru": "Скейт-кухня",                        "title_en": "Skate Kitchen",                     "note": "Crystal Moselle: подростки и скейт на Lower East Side"},
            {"title_ru": "Код Da Vinci",                       "title_en": "The Da Vinci Code",                 "note": "Рон Ховард и темп детективного триллера"},
            {"title_ru": "Рок-n-Rolla",                        "title_en": "RocknRolla",                        "note": "Гай Ричи до пика стиля"},
            {"title_ru": "Отель «Гранд Будапешт»",             "title_en": "The Grand Budapest Hotel",          "note": "Уэс Андерсон на максимуме симметрии"},
            {"title_ru": "Нимфоманка",                         "title_en": "Nymphomaniac: Vol. I",              "note": "Ларс фон Триер в режиме энциклопедии"},
            {"title_ru": "Невероятная жизнь Уолтера Митти",    "title_en": "The Secret Life of Walter Mitty",   "note": "Мечта как монтаж реальности"},
            {"title_ru": "Джанго освобождённый",               "title_en": "Django Unchained",                  "note": "Тарантино с максимальным удовольствием от кино"},
            {"title_ru": "Проект X",                           "title_en": "Project X",                         "note": "Вечеринка как документальный хаос"},
            {"title_ru": "Без предела",                        "title_en": "Limitless",                         "note": "Визуальный трип от умной пилюли"},
            {"title_ru": "Простая просьба",                    "title_en": "Easy A",                            "note": "Остроумная переработка «Алой буквы»"},
            {"title_ru": "500 дней лета",                      "title_en": "(500) Days of Summer",              "note": "Нелинейная любовная история"},
            {"title_ru": "Всегда говори «Да»",                 "title_en": "Yes Man",                           "note": "Джим Кэрри и сила импульса"},
            {"title_ru": "Wild Child",                         "title_en": "Wild Child",                        "note": "Подростковая комедия на скорости"},
            {"title_ru": "Маленькая мисс Счастье",             "title_en": "Little Miss Sunshine",              "note": "Роуд-муви про семью на грани"},
            {"title_ru": "Жмурки",                             "title_en": "Dead Man's Bluff",                  "note": "Балабанов в жанре чёрной комедии"},
            {"title_ru": "Васаби",                             "title_en": "Wasabi",                            "note": "Бессон и Рeno — безумный французский экшен"},
            {"title_ru": "Заводной апельсин",                  "title_en": "A Clockwork Orange",                "note": "Кубрик и насилие как эстетика"},
            {"title_ru": "Волк с Уолл-стрит",                  "title_en": "The Wolf of Wall Street",           "note": "Скорсезе на скорости 300 км/ч"},
            {"title_ru": "Начало",                             "title_en": "Inception",                         "note": "Нолан строит лабиринт из времени"},
            {"title_ru": "Интерстеллар",                       "title_en": "Interstellar",                      "note": "Космос через монтаж и Циммера"},
            {"title_ru": "Давай, давай",                       "title_en": "C'mon C'mon",                       "note": "Майк Миллс: медленное кино о том, как слушать"},
            {"title_ru": "Худший человек на свете",             "title_en": "The Worst Person in the World",     "note": "Норвежский клиповый поток сознания"},
            {"title_ru": "Зомби по имени Шон",                 "title_en": "Shaun of the Dead",                 "note": "Эдгар Райт превращает зомби-хоррор в ромком"},
            {"title_ru": "Джокер",                             "title_en": "Joker",                             "note": "Феникс и нью-йоркская декаданс"},
            {"title_ru": "Искусство самообороны",               "title_en": "The Art of Self-Defense",           "note": "Сухой абсурд и маскулинность"},
            {"title_ru": "Борат",                              "title_en": "Borat",                             "note": "Саша Барон Коэн взрывает четвёртую стену"},
            {"title_ru": "Бруно",                              "title_en": "Brüno",                             "note": "Провокация как жанр"},
        ],
    },

    # ──────────────────────────────────────────────────────────
    # 2. Католическая церковь в кино (новая)
    # ──────────────────────────────────────────────────────────
    {
        "slug": "catholic-church-cinema",
        "title_ru": "Католическая церковь в кино",
        "title_en": "The Catholic Church in Cinema",
        "summary_ru": "Грех, искупление, власть и вера — как кинематограф смотрит на Церковь изнутри и снаружи.",
        "summary_en": "Sin, redemption, power and faith — cinema looking at the Church from inside and outside.",
        "description_ru": (
            "Кино давно сделало католическую церковь своим пространством для разговора "
            "о власти, лицемерии, вере и прощении. Одни фильмы смотрят с восхищением, "
            "другие — с обвинением. Все — с серьёзностью."
        ),
        "tags": ["religion", "catholicism", "drama", "european-cinema"],
        "is_featured": True,
        "cover_image": COLLECTION_COVERS["catholic-church-cinema"],
        "films": [
            {"title_ru": "Семь",                             "title_en": "Se7en",                          "note": "Семь смертных грехов как детективный сюжет"},
            {"title_ru": "Конклав",                          "title_en": "Conclave",                       "note": "Закулисье выбора папы римского"},
            {"title_ru": "Хористы",                         "title_en": "The Chorus",                     "note": "Музыка как спасение в церковной школе"},
            {"title_ru": "По благодати Бога",                "title_en": "By the Grace of God",            "note": "Реальное дело о насилии в церкви Лиона"},
            {"title_ru": "Молчание",                         "title_en": "Silence",                        "note": "Скорсезе о цене веры в феодальной Японии"},
            {"title_ru": "Ангелы и демоны",                  "title_en": "Angels & Demons",                "note": "Иллюминаты, Ватикан и наука против религии"},
            {"title_ru": "Константин",                       "title_en": "Constantine",                    "note": "Экзорцизм как нуар"},
            {"title_ru": "Молодой папа",                     "title_en": "The Young Pope",                 "note": "Соррентино деконструирует образ понтифика"},
            {"title_ru": "Голгофа",                          "title_en": "Calvary",                        "note": "Священник, получивший угрозу смерти на исповеди"},
            {"title_ru": "Два папы",                         "title_en": "The Two Popes",                  "note": "Диалог Бенедикта XVI и Франциска"},
            {"title_ru": "Явление",                          "title_en": "The Apparition",                 "note": "Ватиканское расследование чудес"},
            {"title_ru": "Тело Христово",                    "title_en": "Corpus Christi",                 "note": "Польское кино о самозванце-священнике"},
            {"title_ru": "Имя розы",                         "title_en": "The Name of the Rose",           "note": "Умберто Эко и средневековый монастырь-детектив"},
            {"title_ru": "Сёстры Магдалины",                 "title_en": "The Magdalene Sisters",          "note": "Ирландские приюты как инструмент подавления"},
            {"title_ru": "Дурное воспитание",                "title_en": "Bad Education",                  "note": "Альмодовар о насилии в религиозной школе"},
            {"title_ru": "Сладкая жизнь",                    "title_en": "La Dolce Vita",                  "note": "Феллини, Рим и духовная пустота"},
            {"title_ru": "Аминь.",                           "title_en": "Amen.",                          "note": "Молчание Ватикана во время Холокоста"},
            {"title_ru": "Великая красота",                  "title_en": "The Great Beauty",               "note": "Рим, вечность и упадок как мистерия"},
        ],
    },

    # ──────────────────────────────────────────────────────────
    # 3. Кино, на котором выросло поколение 2000-х (новая)
    # ──────────────────────────────────────────────────────────
    {
        "slug": "generation-2000s",
        "title_ru": "Кино, на котором выросло поколение 2000-х",
        "title_en": "Films That Raised Generation 2000s",
        "summary_ru": "Фильмы, которые смотрели на кассетах, DVD и пиратских дисках — и которые сформировали вкус целого поколения.",
        "summary_en": "Films watched on VHS, DVD and pirated discs — that shaped the taste of a whole generation.",
        "description_ru": (
            "Конец 90-х — начало 2000-х: время, когда кино ещё не было в стриминге, "
            "зато было у соседа на диске. Фильмы из этого списка ходили по рукам, "
            "цитировались во дворе и переворачивали представление о том, каким кино вообще бывает."
        ),
        "tags": ["nostalgia", "90s", "2000s", "cult"],
        "is_featured": True,
        "cover_image": COLLECTION_COVERS["generation-2000s"],
        "films": [
            {"title_ru": "Дневник баскетболиста",          "title_en": "The Basketball Diary",       "note": "Ди Каприо на дне — и на подъёме"},
            {"title_ru": "Криминальное чтиво",             "title_en": "Pulp Fiction",               "note": "Тарантино изменил язык кино навсегда"},
            {"title_ru": "Американский пирог",             "title_en": "American Pie",               "note": "Взросление через комедию без стеснения"},
            {"title_ru": "13-й район",                     "title_en": "District 13",                "note": "Паркур как синоним французского экшена"},
            {"title_ru": "Форсаж",                         "title_en": "The Fast and the Furious",   "note": "Стартовая точка главной саги нулевых"},
            {"title_ru": "Гарри Поттер и философский камень", "title_en": "Harry Potter and the Philosopher's Stone", "note": "Хогвартс стал второй реальностью"},
            {"title_ru": "Очень страшное кино",            "title_en": "Scary Movie",                "note": "Пародия, которую знали наизусть"},
            {"title_ru": "На игле",                        "title_en": "Trainspotting",              "note": "Бойл, Макгрегор и выбор не выбирать"},
            {"title_ru": "Аватар",                         "title_en": "Avatar",                     "note": "Первый раз в 3D в кино — событие жизни"},
            {"title_ru": "Большой Лебовски",               "title_en": "The Big Lebowski",           "note": "Коэны создали культ из ковра и боулинга"},
            {"title_ru": "Побег из Шоушенка",              "title_en": "The Shawshank Redemption",   "note": "#1 IMDb — не случайно"},
            {"title_ru": "Бойцовский клуб",                "title_en": "Fight Club",                 "note": "Финчер и первое правило, которое все знают"},
            {"title_ru": "Реквием по мечте",               "title_en": "Requiem for a Dream",        "note": "Аронофски и зависимость как ад"},
            {"title_ru": "Карты, деньги, два ствола",      "title_en": "Lock, Stock and Two Smoking Barrels", "note": "Гай Ричи открыл себя одним фильмом"},
            {"title_ru": "Шрек",                           "title_en": "Shrek",                      "note": "Мультфильм, который был и для взрослых"},
        ],
    },

    # ──────────────────────────────────────────────────────────
    # 4. Италия через кино (урезана до 11 фильмов по заданию)
    # ──────────────────────────────────────────────────────────
    {
        "slug": "italy-through-cinema",
        "title_ru": "Италия через кино",
        "title_en": "Italy Through Cinema",
        "summary_ru": "От Феллини до Соррентино — Италия как состояние души, разлитое в кадре.",
        "summary_en": "From Fellini to Sorrentino — Italy as a state of mind poured into the frame.",
        "description_ru": (
            "Итальянское кино всегда было больше чем кино: способ говорить о смерти, любви, "
            "церкви и истории — одновременно. Жара, время, красота на грани отчаяния."
        ),
        "tags": ["italy", "european-cinema", "auteur", "sorrentino"],
        "is_featured": True,
        "cover_image": COLLECTION_COVERS["italy-through-cinema"],
        "films": [
            {"title_ru": "Великая красота",            "title_en": "The Great Beauty",          "note": "Соррентино и Рим как элегия"},
            {"title_ru": "Партенопе",                  "title_en": "Parthenope",                "note": "Соррентино возвращается к Неаполю"},
            {"title_ru": "Рука Бога",                  "title_en": "The Hand of God",           "note": "Автобиографический Неаполь Соррентино"},
            {"title_ru": "Бассейн",                    "title_en": "La Piscine",                "note": "1969: Делon, Роми Шнайдер и ревность"},
            {"title_ru": "Ускользающая красота",       "title_en": "Stealing Beauty",           "note": "Бертолуччи, Тоскана и взросление"},
            {"title_ru": "Баария",                     "title_en": "Baarìa",                    "note": "Торнаторе: сицилийская сага через XX век"},
            {"title_ru": "Leoni",                      "title_en": "A Holy Venetian Family",    "note": "Parolin: комедия о Veneto (Leoni / «венецианские львы»)"},
            {"title_ru": "Лоро",                       "title_en": "Loro",                      "note": "Соррентино о Берлускони как карнавале"},
            {"title_ru": "Казино «Рояль»",             "title_en": "Casino Royale",             "note": "Венеция как декорация к лучшему Бонду"},
            {"title_ru": "Талантливый мистер Рипли",   "title_en": "The Talented Mr. Ripley",   "note": "Мinghella и Мэтт Дэймон на итальянских озёрах"},
        ],
    },

    # ──────────────────────────────────────────────────────────
    # 5. Женщины-режиссёры (новая)
    # ──────────────────────────────────────────────────────────
    {
        "slug": "women-directors",
        "title_ru": "Женщины-режиссёры",
        "title_en": "Women Directors",
        "summary_ru": "Фильмы, снятые женщинами — про женщин, про мужчин и про всё остальное. Взгляд, которого слишком долго не было в главном кресле.",
        "summary_en": "Films directed by women — about women, men, and everything else.",
        "description_ru": (
            "София Коппола, Хлоя Чжао, Надин Лабаки, Агнес Варда — режиссёры, которые "
            "не просто сняли хорошие фильмы, но и изменили язык кино. В этой подборке "
            "— работы разных эпох, стран и жанров, объединённые одним: за камерой стоит женщина."
        ),
        "tags": ["women", "feminism", "auteur", "world-cinema"],
        "is_featured": True,
        "cover_image": COLLECTION_COVERS["women-directors"],
        "films": [
            {"title_ru": "Девственницы-самоубийцы",     "title_en": "The Virgin Suicides",          "note": "Дебют Копполы — меланхолия как жанр"},
            {"title_ru": "Мария-Антуанетта",             "title_en": "Marie Antoinette",             "note": "Коппола: история как поп-клип"},
            {"title_ru": "Американский психопат",        "title_en": "American Psycho",              "note": "Мэри Харрон превращает сатиру в портрет"},
            {"title_ru": "На гребне волны",              "title_en": "Point Break",                  "note": "Кэтрин Бигелоу до «Повелителя бури»"},
            {"title_ru": "Повелитель бури",              "title_en": "The Hurt Locker",              "note": "Бигелоu: Оскар и война в Багдаде"},
            {"title_ru": "Русалка",                      "title_en": "The Mermaid",                  "note": "Анна Меликян и магический реализм"},
            {"title_ru": "Мустанг",                      "title_en": "Mustang",                      "note": "Эргювен: пять сестёр в ловушке традиций"},
            {"title_ru": "Субстанция",                   "title_en": "The Substance",                "note": "Фаржа — тело как политическое высказывание"},
            {"title_ru": "Земля кочевников",             "title_en": "Nomadland",                    "note": "Чжао и тихая Америка на колёсах"},
            {"title_ru": "Трудности перевода",           "title_en": "Lost in Translation",          "note": "Коппола: одиночество вдвоём в Токио"},
            {"title_ru": "Разжимая кулаки",              "title_en": "Unclenching the Fists",        "note": "Коваленко: Осетия и невидимое насилие"},
            {"title_ru": "Клео от 5 до 7",              "title_en": "Cleo from 5 to 7",             "note": "Варда: два часа реального времени в Париже"},
            {"title_ru": "Пыль во прахе",                "title_en": "Daughters of the Dust",       "note": "Джули Дэш: первый голливудский фильм чёрной режиссёрки"},
            {"title_ru": "Что-то не так с Кевином",     "title_en": "We Need to Talk About Kevin", "note": "Линн Рэмси — любовь матери как кошмар"},
            {"title_ru": "Капернаум",                    "title_en": "Capernaum",                    "note": "Лабаки: ребёнок судит собственных родителей"},
            {"title_ru": "Питер FM",                     "title_en": "Peter FM",                     "note": "Оксана Бычкова: петербургский ромком нулевых"},
        ],
    },
]


# TMDB id для надёжного поиска (названия в БД могут отличаться от title_ru)
FILM_TMDB: dict[str, int] = {
    "John Wick": 245891,
    "Deadpool": 293660,
    "Skate Kitchen": 476600,
    "The Da Vinci Code": 591,
    "RocknRolla": 13851,
    "The Grand Budapest Hotel": 120467,
    "Nymphomaniac: Vol. I": 249397,
    "The Secret Life of Walter Mitty": 116745,
    "Django Unchained": 68718,
    "Project X": 57214,
    "Limitless": 51876,
    "Easy A": 37735,
    "(500) Days of Summer": 19913,
    "Yes Man": 10201,
    "Wild Child": 18377,
    "Little Miss Sunshine": 773,
    "Dead Man's Bluff": 20994,
    "Wasabi": 5951,
    "A Clockwork Orange": 185,
    "The Wolf of Wall Street": 106646,
    "Inception": 27205,
    "Interstellar": 157336,
    "C'mon C'mon": 632617,
    "The Worst Person in the World": 660120,
    "Shaun of the Dead": 747,
    "Joker": 475557,
    "The Art of Self-Defense": 480629,
    "Borat": 496,
    "Brüno": 283562,
    "Se7en": 807,
    "Conclave": 1184918,
    "The Chorus": 14238,
    "By the Grace of God": 537108,
    "Silence": 68726,
    "Angels & Demons": 13475,
    "Constantine": 561,
    "Calvary": 219064,
    "The Two Popes": 581600,
    "The Apparition": 574021,
    "Corpus Christi": 613504,
    "The Name of the Rose": 192,
    "The Magdalene Sisters": 11009,
    "Bad Education": 58,
    "La Dolce Vita": 439,
    "Amen.": 31566,
    "The Great Beauty": 985,
    "The Basketball Diary": 9291,
    "Pulp Fiction": 680,
    "American Pie": 481,
    "District 13": 11685,
    "The Fast and the Furious": 9799,
    "Harry Potter and the Philosopher's Stone": 671,
    "Scary Movie": 4247,
    "Trainspotting": 627,
    "Avatar": 19995,
    "The Big Lebowski": 115,
    "The Shawshank Redemption": 278,
    "Fight Club": 550,
    "Requiem for a Dream": 641,
    "Lock, Stock and Two Smoking Barrels": 100,
    "Shrek": 808,
    "Parthenope": 1143014,
    "The Hand of God": 597890,
    "La Piscine": 39018,
    "Stealing Beauty": 11820,
    "Baarìa": 33487,
    "A Holy Venetian Family": 323664,
    "Loro": 541660,
    "Casino Royale": 36557,
    "The Talented Mr. Ripley": 1213,
    "The Virgin Suicides": 11158,
    "Marie Antoinette": 1887,
    "American Psycho": 1359,
    "Point Break": 1089,
    "The Hurt Locker": 12162,
    "The Mermaid": 73576,
    "Mustang": 333277,
    "The Substance": 933260,
    "Nomadland": 747188,
    "Lost in Translation": 153,
    "Unclenching the Fists": 899827,
    "Cleo from 5 to 7": 960,
    "Daughters of the Dust": 21711,
    "We Need to Talk About Kevin": 64688,
    "Capernaum": 499932,
    "Peter FM": 64736,
}


# ═══════════════════════════════════════════════════════════════
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════════

def _norm_title(s: str) -> str:
    return " ".join(s.lower().replace("«", "").replace("»", "").split())


def titles_match(title_ru: str, title_en: str, actual_ru: str, actual_en: str) -> bool:
    """Проверяет, что найденная в БД сущность — тот же фильм."""
    expected = {_norm_title(t) for t in (title_ru, title_en) if t}
    actual = {_norm_title(t) for t in (actual_ru, actual_en) if t}
    if expected & actual:
        return True
    for exp in expected:
        for act in actual:
            if len(exp) >= 4 and (exp in act or act in exp):
                return True
    return False


async def get_film_titles(db: AsyncSession, entity_id: int) -> tuple[str, str]:
    rows = (await db.execute(text("""
        SELECT l.code, et.title
        FROM entity_translation et
        JOIN language l ON l.id = et.language_id
        WHERE et.entity_id = :eid AND l.code IN ('ru', 'en')
    """), {"eid": entity_id})).mappings().all()
    titles = {r["code"]: r["title"] or "" for r in rows}
    return titles.get("ru", ""), titles.get("en", "")


async def find_film_id(
    db: AsyncSession,
    title_ru: str,
    title_en: str,
    tmdb_id: int | None = None,
) -> int | None:
    """Ищет фильм по TMDB id или title; отвергает неверные совпадения."""
    async def _accept(entity_id: int) -> int | None:
        actual_ru, actual_en = await get_film_titles(db, entity_id)
        if titles_match(title_ru, title_en, actual_ru, actual_en):
            return entity_id
        log.warning(
            "  ⚠️  Отклонён неверный match: ожидали «%s» / «%s», в БД «%s» / «%s» (entity id=%d)",
            title_ru, title_en, actual_ru, actual_en, entity_id,
        )
        return None

    if tmdb_id is not None:
        by_tmdb = (await db.execute(text("""
            SELECT id FROM entity
            WHERE entity_type = 'film'
              AND status = 'published'
              AND external_ids->>'tmdb' = :tid
            LIMIT 1
        """), {"tid": str(tmdb_id)})).scalar_one_or_none()
        if by_tmdb:
            accepted = await _accept(by_tmdb)
            if accepted:
                return accepted

    sql = text("""
        SELECT et.entity_id
        FROM entity_translation et
        JOIN entity e ON e.id = et.entity_id
        WHERE e.entity_type = 'film'
          AND e.status = 'published'
          AND lower(et.title) = lower(:title)
        LIMIT 1
    """)
    for title in (title_ru, title_en):
        if not title:
            continue
        result = (await db.execute(sql, {"title": title})).scalar_one_or_none()
        if result:
            accepted = await _accept(result)
            if accepted:
                return accepted
    return None


async def find_collection_id(db: AsyncSession, slug: str) -> int | None:
    """Ищет коллекцию по slug (ru-перевод)."""
    sql = text("""
        SELECT et.entity_id
        FROM entity_translation et
        JOIN entity e ON e.id = et.entity_id
        WHERE e.entity_type = 'collection'
          AND et.slug = :slug
          AND et.language_id = (SELECT id FROM language WHERE code = 'ru')
        LIMIT 1
    """)
    return (await db.execute(sql, {"slug": slug})).scalar_one_or_none()


async def ensure_taxonomy_term(db: AsyncSession, *, term_type: str, code: str) -> int:
    sql = text("""
        INSERT INTO taxonomy_term (term_type, code, is_system, sort_order)
        VALUES (CAST(:tt AS taxonomy_type), :code, true, 0)
        ON CONFLICT (term_type, code) DO UPDATE SET code = EXCLUDED.code
        RETURNING id
    """)
    return (await db.execute(sql, {"tt": term_type, "code": code})).scalar_one()


async def sync_collection_tags(db: AsyncSession, collection_id: int, tags: list[str]) -> None:
    await db.execute(text("""
        DELETE FROM entity_taxonomy et
        USING taxonomy_term tt
        WHERE et.entity_id = :eid
          AND et.term_id = tt.id
          AND tt.term_type = 'tag'
    """), {"eid": collection_id})
    for tag in tags:
        term_id = await ensure_taxonomy_term(db, term_type="tag", code=tag)
        await db.execute(text("""
            INSERT INTO entity_taxonomy (entity_id, term_id, is_primary)
            VALUES (:eid, :tid, false)
            ON CONFLICT (entity_id, term_id) DO NOTHING
        """), {"eid": collection_id, "tid": term_id})


async def create_entity(db: AsyncSession, entity_type: str) -> int:
    sql = text("""
        INSERT INTO entity (entity_type, status, external_ids, extra_metadata)
        VALUES (CAST(:etype AS entity_type), 'published', '{}'::jsonb, '{}'::jsonb)
        RETURNING id
    """)
    return (await db.execute(sql, {"etype": entity_type})).scalar_one()


async def upsert_translation(db: AsyncSession, entity_id: int, lang_code: str, **fields) -> None:
    sql = text("""
        INSERT INTO entity_translation
            (entity_id, language_id, search_config, slug, title, summary, description)
        VALUES (
            :entity_id,
            (SELECT id FROM language WHERE code = :lang),
            :config,
            :slug, :title, :summary, :description
        )
        ON CONFLICT (entity_id, language_id) DO UPDATE SET
            slug        = EXCLUDED.slug,
            title       = EXCLUDED.title,
            summary     = EXCLUDED.summary,
            description = EXCLUDED.description
    """)
    await db.execute(sql, {
        "entity_id": entity_id,
        "lang": lang_code,
        "config": "russian" if lang_code == "ru" else "english",
        **fields,
    })


# ═══════════════════════════════════════════════════════════════
# ОСНОВНАЯ ЛОГИКА
# ═══════════════════════════════════════════════════════════════

async def seed_collection(db: AsyncSession, conf: dict) -> None:
    slug = conf["slug"]
    is_featured = conf.get("is_featured", False)
    extra_meta = json.dumps({"is_featured": is_featured})
    log.info("▶ Коллекция: %s", conf["title_ru"])

    collection_id = await find_collection_id(db, slug)

    if collection_id is None:
        log.info("  Создаю новую сущность...")
        collection_id = await create_entity(db, "collection")
        await db.execute(text("""
            INSERT INTO collection (
                id, owner_user_id, kind, is_system, cover_entity_id, items_count, extra_metadata
            )
            VALUES (
                :id, :owner, 'editorial', true, NULL, 0, CAST(:meta AS jsonb)
            )
            ON CONFLICT (id) DO NOTHING
        """), {
            "id": collection_id,
            "owner": EDITORIAL_USER_ID,
            "meta": extra_meta,
        })
        await db.execute(text(
            "UPDATE entity SET published_at = now() WHERE id = :id"
        ), {"id": collection_id})
        log.info("  Создана с id=%d", collection_id)
    else:
        await db.execute(text("""
            UPDATE collection
            SET extra_metadata = COALESCE(extra_metadata, '{}'::jsonb)
                || CAST(:meta AS jsonb)
            WHERE id = :id
        """), {"id": collection_id, "meta": extra_meta})
        log.info("  Найдена (id=%d), обновляю...", collection_id)

    await upsert_translation(db, collection_id, "ru",
        slug=slug,
        title=conf["title_ru"],
        summary=conf.get("summary_ru", ""),
        description=conf.get("description_ru", ""),
    )
    if conf.get("title_en"):
        await upsert_translation(db, collection_id, "en",
            slug=slug,
            title=conf["title_en"],
            summary=conf.get("summary_en", ""),
            description=conf.get("description_en", ""),
        )

    await sync_collection_tags(db, collection_id, conf.get("tags", []))

    deleted = (await db.execute(text("""
        DELETE FROM collection_item WHERE collection_id = :id
    """), {"id": collection_id})).rowcount
    if deleted:
        log.info("  Удалено старых items: %d", deleted)

    found = 0
    not_found = []
    first_film_id: int | None = None
    insert_pos = 0
    for film in conf["films"]:
        tmdb_id = film.get("tmdb_id") or FILM_TMDB.get(film.get("title_en", ""))
        film_id = await find_film_id(
            db, film["title_ru"], film.get("title_en", ""), tmdb_id,
        )
        if film_id is None:
            not_found.append(film["title_ru"])
            continue
        insert_pos += 1
        if first_film_id is None:
            first_film_id = film_id

        await db.execute(text("""
            INSERT INTO collection_item
                (collection_id, entity_id, position, note, added_by_user_id)
            VALUES (:cid, :eid, :pos, :note, :uid)
            ON CONFLICT (collection_id, entity_id) DO UPDATE
                SET position = EXCLUDED.position,
                    note = EXCLUDED.note
        """), {
            "cid": collection_id,
            "eid": film_id,
            "pos": insert_pos,
            "note": film.get("note"),
            "uid": EDITORIAL_USER_ID,
        })
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

    cover_image = conf.get("cover_image") or COLLECTION_COVERS.get(slug)
    if cover_image:
        await db.execute(text("""
            UPDATE entity SET primary_image_url = :url WHERE id = :id
        """), {"id": collection_id, "url": cover_image})
    elif first_film_id is not None:
        cover_url = (await db.execute(text(
            "SELECT primary_image_url FROM entity WHERE id = :id"
        ), {"id": first_film_id})).scalar_one_or_none()
        if cover_url:
            await db.execute(text("""
                UPDATE entity SET primary_image_url = :url WHERE id = :id
            """), {"id": collection_id, "url": cover_url})

    await db.commit()
    log.info("  ✅ Добавлено фильмов: %d из %d", found, len(conf["films"]))

    if not_found:
        log.warning("  ⚠️  НЕ НАЙДЕНЫ в БД (%d шт) — нужна ручная проверка:", len(not_found))
        for t in not_found:
            log.warning("       • %s", t)


async def apply_collection_covers(db: AsyncSession) -> None:
    """Обновляет primary_image_url коллекций по slug (в т.ч. Marvel и «Кино о памяти»)."""
    log.info("▶ Обложки коллекций")
    for slug, url in COLLECTION_COVERS.items():
        collection_id = await find_collection_id(db, slug)
        if collection_id is None:
            log.warning("  ⚠️  Коллекция %s не найдена — пропуск", slug)
            continue
        await db.execute(text("""
            UPDATE entity SET primary_image_url = :url WHERE id = :id
        """), {"id": collection_id, "url": url})
        await db.commit()
        log.info("  ✅ %s → %s", slug, url)


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

async def main() -> None:
    log.info("═══════════════════════════════════════════════════════")
    log.info("  Seed: обновление коллекций")
    log.info("═══════════════════════════════════════════════════════")

    async with AsyncSession(engine) as db:
        # Проверка editorial-пользователя
        u = (await db.execute(text("""
            SELECT id, display_name FROM app_user WHERE id = :id
        """), {"id": EDITORIAL_USER_ID})).mappings().first()
        if not u:
            raise SystemExit(
                f"❌ Editorial user id={EDITORIAL_USER_ID} не найден. "
                "Создай его через INSERT INTO app_user."
            )
        log.info("👤 Editorial user: id=%d (%s)", u["id"], u["display_name"])
        log.info("")

        for conf in COLLECTIONS:
            try:
                await seed_collection(db, conf)
            except Exception as exc:
                log.error("  ОШИБКА: %s", exc, exc_info=True)
                await db.rollback()
            log.info("")

        await apply_collection_covers(db)

    log.info("═══════════════════════════════════════════════════════")
    log.info("  Готово. Фильмы, которых нет в БД — загрузи через TMDB-скрипт.")
    log.info("═══════════════════════════════════════════════════════")


if __name__ == "__main__":
    asyncio.run(main())
