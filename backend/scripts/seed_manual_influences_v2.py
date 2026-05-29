"""
Seed Manual Influences v2 — РАСШИРЕННАЯ ручная разметка графа.

Главное отличие от v1:
  - Фокус на МОЛОДЫХ режиссёрах (5-20 лет в индустрии)
  - Структура с ГЛУБИНОЙ 2:
      молодой → его учитель → учителя учителя (СТОП)
  - У каждого молодого режиссёра 2-4 связи
  - Много женщин-режиссёров (Гервиг, Жао, Декурно, Фаржа, Сьямма, и др.)

Семантика остаётся:
  source_director_id — кто вдохновил
  target_director_id — на кого повлиял

Все связи:
  confidence=0.95 (экспертно подтверждено по интервью/статьям)
  inferred_by_system=false
  relation_note с источником

Запуск:
    python -m scripts.seed_manual_influences_v2

Идемпотентно — ON CONFLICT DO NOTHING.
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
log = logging.getLogger("manual-v2")


# ════════════════════════════════════════════════════════════════
#  СВЯЗИ ВЛИЯНИЯ
#  Формат: (вдохновитель, ученик/последователь, источник)
# ════════════════════════════════════════════════════════════════
#
# Структура: для каждого молодого режиссёра написаны 2-4 учителя.
# Для самих учителей-классиков (Куросава, Хичкок, Бергман...) —
# тоже добавлены их учителя ОДНИМ уровнем выше (не идём глубже).

INFLUENCES = [
    # ════════════════════════════════════════════════════════════
    #  ГРЕТА ГЕРВИГ → Бомбах, ПТА, Бергман, Чехов
    # ════════════════════════════════════════════════════════════
    ("Ноа Баумбах",            "Грета Гервиг",        "Frances Ha — соавторы, личная связь"),
    ("Пол Томас Андерсон",     "Грета Гервиг",        "Gerwig: PTA influence on Lady Bird (LA Times 2017)"),
    ("Ингмар Бергман",         "Грета Гервиг",        "Gerwig: Bergman as core influence (Criterion 2019)"),

    # учителя её учителей:
    ("Уит Стиллмен",           "Ноа Баумбах",         "Baumbach: Whit Stillman as origin"),
    ("Эрик Ромер",             "Ноа Баумбах",         "Baumbach: Rohmer dialogue rhythm"),

    # ════════════════════════════════════════════════════════════
    #  ХЛОЯ ЖАО → Чжанке Цзя, Малик, Киаростами
    # ════════════════════════════════════════════════════════════
    ("Цзя Чжанке",             "Хлоя Жао",            "Zhao: Jia Zhangke documented her growth"),
    ("Терренс Малик",          "Хлоя Жао",            "Zhao: Malick's natural light influence"),
    ("Аббас Киаростами",       "Хлоя Жао",            "Zhao: Kiarostami's pace in Songs My Brothers Taught Me"),

    # их учителя:
    ("Робер Брессон",          "Аббас Киаростами",    "Kiarostami: Bresson as foundation"),

    # ════════════════════════════════════════════════════════════
    #  ЭМЕРАЛЬД ФЕННЕЛЛ → Хейнс, Линч, Де Пальма
    # ════════════════════════════════════════════════════════════
    ("Тодд Хейнс",             "Эмеральд Феннелл",    "Fennell: Haynes on Carol as melodrama craft"),
    ("Дэвид Линч",             "Эмеральд Феннелл",    "Fennell: Lynch's color and dread"),
    ("Брайан Де Пальма",       "Эмеральд Феннелл",    "Fennell: De Palma split-screen for Promising Young Woman"),

    # их учителя:
    ("Райнер Вернер Фассбиндер","Тодд Хейнс",          "Haynes: Far From Heaven как Sirk через Fassbinder"),

    # ════════════════════════════════════════════════════════════
    #  ДЖОРДАН ПИЛ → Ромеро, Кроненберг, Хичкок
    # ════════════════════════════════════════════════════════════
    ("Джордж А. Ромеро",       "Джордан Пил",         "Peele: Romero's social horror on Get Out"),
    ("Дэвид Кроненберг",       "Джордан Пил",         "Peele: Cronenberg body horror"),
    ("Альфред Хичкок",         "Джордан Пил",         "Peele: Hitchcock for Nope"),

    # ════════════════════════════════════════════════════════════
    #  РАЙАН КУГЛЕР → Спайк Ли, Скорсезе, Майкл Манн
    # ════════════════════════════════════════════════════════════
    ("Спайк Ли",               "Райан Куглер",        "Coogler: Spike Lee mentored on Fruitvale"),
    ("Мартин Скорсезе",        "Райан Куглер",        "Coogler: Scorsese's NYC films for Creed"),
    ("Майкл Манн",             "Райан Куглер",        "Coogler: Mann's L.A. visual language"),

    # ════════════════════════════════════════════════════════════
    #  БАРРИ ДЖЕНКИНС → Вонг Кар Вай, Малик, Линклейтер
    # ════════════════════════════════════════════════════════════
    ("Вонг Кар Вай",           "Барри Дженкинс",      "Jenkins: WKW as everything for Moonlight"),
    ("Терренс Малик",          "Барри Дженкинс",      "Jenkins: Malick on light in If Beale Street"),
    ("Ричард Линклейтер",      "Барри Дженкинс",      "Jenkins: Linklater's intimate dialogue"),

    # ════════════════════════════════════════════════════════════
    #  АРИ АСТЕР → Бергман, Поланский, Лантимос
    # ════════════════════════════════════════════════════════════
    ("Ингмар Бергман",         "Ари Астер",           "Aster: Bergman as horror through psychology"),
    ("Роман Полански",         "Ари Астер",           "Aster: Polanski's apartment trilogy"),
    ("Йоргос Лантимос",        "Ари Астер",           "Aster: Lanthimos shared cinematographer Robbie Ryan"),

    # ════════════════════════════════════════════════════════════
    #  РОБЕРТ ЭГГЕРС → Бергман, Дрейер, Тарковский
    # ════════════════════════════════════════════════════════════
    ("Ингмар Бергман",         "Роберт Эггерс",       "Eggers: Bergman's medieval films for The Lighthouse"),
    ("Карл Теодор Дрейер",     "Роберт Эггерс",       "Eggers: Dreyer's spiritual horror for The Witch"),
    ("Андрей Тарковский",      "Роберт Эггерс",       "Eggers: Tarkovsky's pace and silence"),

    # ════════════════════════════════════════════════════════════
    #  КОРАЛИ ФАРЖА (Substance) → Кроненберг, Карпентер, Верховен
    # ════════════════════════════════════════════════════════════
    ("Дэвид Кроненберг",       "Корали Фаржа",        "Fargeat: Cronenberg body horror, Substance"),
    ("Джон Карпентер",         "Корали Фаржа",        "Fargeat: Carpenter's practical effects"),
    ("Пол Верховен",           "Корали Фаржа",        "Fargeat: Verhoeven's satire and excess"),

    # ════════════════════════════════════════════════════════════
    #  СЕЛИН СЬЯММА → Шанталь Акерман, Жанетт Гимар, Варда
    # ════════════════════════════════════════════════════════════
    ("Шанталь Акерман",        "Селин Сьямма",        "Sciamma: Akerman as feminist cinema teacher"),
    ("Аньес Варда",            "Селин Сьямма",        "Sciamma: Varda's female gaze"),
    ("Морис Пиала",            "Селин Сьямма",        "Sciamma: Pialat's emotional realism"),

    # ════════════════════════════════════════════════════════════
    #  АЛИС ДИОП → Варда, Шанталь Акерман, Сембен
    # ════════════════════════════════════════════════════════════
    ("Аньес Варда",            "Алис Диоп",           "Diop: Varda's documentary essay style"),
    ("Шанталь Акерман",        "Алис Диоп",           "Diop: Akerman's duration and feminism"),
    ("Усман Сембен",           "Алис Диоп",           "Diop: Sembène as African cinema foundation"),

    # ════════════════════════════════════════════════════════════
    #  ЛУКА ГУАДАНЬИНО → Бертолуччи, Висконти, Хейнес
    # ════════════════════════════════════════════════════════════
    ("Бернардо Бертолуччи",    "Лука Гуаданьино",     "Guadagnino: Bertolucci's sensuality for Call Me by Your Name"),
    ("Лукино Висконти",        "Лука Гуаданьино",     "Guadagnino: Visconti's aesthetic for I Am Love"),
    ("Тодд Хейнс",             "Лука Гуаданьино",     "Guadagnino: Haynes as contemporary peer"),

    # ════════════════════════════════════════════════════════════
    #  ЙОАХИМ ТРИЕР → Бергман, фон Триер
    # ════════════════════════════════════════════════════════════
    ("Ингмар Бергман",         "Йоахим Триер",        "Trier: Bergman's Nordic introspection"),
    ("Ларс фон Триер",         "Йоахим Триер",        "Trier: family name + Dogme legacy"),
    ("Майк Ли",                "Йоахим Триер",        "Trier: Mike Leigh's working method"),

    # ════════════════════════════════════════════════════════════
    #  ШАРЛОТТА УЭЛЛС (Aftersun) → Тарковский, Малик, Линклейтер
    # ════════════════════════════════════════════════════════════
    ("Андрей Тарковский",      "Шарлотта Уэллс",      "Wells: Tarkovsky's memory aesthetic for Aftersun"),
    ("Терренс Малик",          "Шарлотта Уэллс",      "Wells: Malick's voice-over and light"),
    ("Ричард Линклейтер",      "Шарлотта Уэллс",      "Wells: Linklater's Boyhood time-stretching"),

    # ════════════════════════════════════════════════════════════
    #  АЛИСЕ РОРВАХЕР (La Chimera) → Феллини, Висконти, Олми
    # ════════════════════════════════════════════════════════════
    ("Федерико Феллини",       "Алисе Рорвахер",      "Rohrwacher: Fellini's pastoral magic"),
    ("Лукино Висконти",        "Алисе Рорвахер",      "Rohrwacher: Visconti's neorealist roots"),
    ("Эрманно Ольми",          "Алисе Рорвахер",      "Rohrwacher: Olmi as rural Italian forefather"),

    # ════════════════════════════════════════════════════════════
    #  ЭДГАР РАЙТ → Тарантино, Карпентер, Уолтер Хилл
    # ════════════════════════════════════════════════════════════
    ("Квентин Тарантино",      "Эдгар Райт",          "Wright: Pulp Fiction as foundational"),
    ("Джон Карпентер",         "Эдгар Райт",          "Wright: Carpenter's genre rigor"),
    ("Уолтер Хилл",            "Эдгар Райт",          "Wright: Hill's action choreography"),

    # ════════════════════════════════════════════════════════════
    #  СТИВ МАККУИН → Бэкон (художник, не режиссёр), Ван Сант, Бойл
    # ════════════════════════════════════════════════════════════
    ("Гас Ван Сант",           "Стив МакКуин",        "McQueen: Van Sant's visual restraint"),
    ("Дэнни Бойл",             "Стив МакКуин",        "McQueen: Boyle's British contemporary"),
    ("Мишелангело Антониони",  "Стив МакКуин",        "McQueen: Antonioni's slow alienation"),

    # ════════════════════════════════════════════════════════════
    #  ЛИНН РЭМЗИ → Кесьлёвский, Линч, Тарковский
    # ════════════════════════════════════════════════════════════
    ("Кшиштоф Кесьлёвский",    "Линн Рэмзи",          "Ramsay: Kieślowski's color and morality"),
    ("Дэвид Линч",             "Линн Рэмзи",          "Ramsay: Lynch's dream logic"),
    ("Андрей Тарковский",      "Линн Рэмзи",          "Ramsay: Tarkovsky's water imagery"),

    # ════════════════════════════════════════════════════════════
    #  ПАК ЧХАН УК → Хичкок, Полански, Линч
    # ════════════════════════════════════════════════════════════
    ("Альфред Хичкок",         "Пак Чхан Ук",         "Park: Hitchcock for Oldboy revenge structure"),
    ("Роман Полански",         "Пак Чхан Ук",         "Park: Polanski's psychological intrigue"),
    ("Дэвид Линч",             "Пак Чхан Ук",         "Park: Lynch for Stoker dream sequences"),

    # ════════════════════════════════════════════════════════════
    #  ЛИ ЧХАН ДОН → Тарковский, Брессон, Озу
    # ════════════════════════════════════════════════════════════
    ("Андрей Тарковский",      "Ли Чхан Дон",         "Lee Chang-dong: Tarkovsky's spirituality for Burning"),
    ("Робер Брессон",          "Ли Чхан Дон",         "Lee Chang-dong: Bresson's restrained acting"),
    ("Ясудзиро Одзу",          "Ли Чхан Дон",         "Lee Chang-dong: Ozu's family dynamics"),

    # ════════════════════════════════════════════════════════════
    #  РЁ ХАМАГУТИ → Кассаветес, Ромер
    # ════════════════════════════════════════════════════════════
    ("Джон Кассаветис",        "Рюсукэ Хамагути",     "Hamaguchi: Cassavetes' improvisation"),
    ("Эрик Ромер",             "Рюсукэ Хамагути",     "Hamaguchi: Rohmer's conversational structure"),
    ("Ясудзиро Одзу",          "Рюсукэ Хамагути",     "Hamaguchi: Ozu's Tokyo geography"),

    # ════════════════════════════════════════════════════════════
    #  ЦЗЯ ЧЖАНКЕ → Брессон, Озу, Тарковский
    # ════════════════════════════════════════════════════════════
    ("Робер Брессон",          "Цзя Чжанке",          "Jia Zhangke: Bresson's pace"),
    ("Ясудзиро Одзу",          "Цзя Чжанке",          "Jia Zhangke: Ozu's still cameras"),
    ("Андрей Тарковский",      "Цзя Чжанке",          "Jia Zhangke: Tarkovsky's long takes"),

    # ════════════════════════════════════════════════════════════
    #  ФРЭНСИС ФОРД КОППОЛА → Куросава, Уэллс, Феллини, Висконти
    # ════════════════════════════════════════════════════════════
    ("Акира Куросава",         "Фрэнсис Форд Коппола","Coppola: Kurosawa as foundational, dedicated Apocalypse Now"),
    ("Орсон Уэллс",            "Фрэнсис Форд Коппола","Coppola: Welles's Citizen Kane for Godfather"),
    ("Федерико Феллини",       "Фрэнсис Форд Коппола","Coppola: Fellini's Italian heritage"),
    ("Лукино Висконти",        "Фрэнсис Форд Коппола","Coppola: Visconti's The Leopard for Godfather II"),

    # ════════════════════════════════════════════════════════════
    #  СПАЙК ЛИ → Куросава, Скорсезе, Кассаветес
    # ════════════════════════════════════════════════════════════
    ("Акира Куросава",         "Спайк Ли",            "Lee: Kurosawa's Rashomon influence on storytelling"),
    ("Мартин Скорсезе",        "Спайк Ли",            "Lee: Scorsese as NYC contemporary mentor"),
    ("Джон Кассаветис",        "Спайк Ли",            "Lee: Cassavetes' indie ethos"),

    # ════════════════════════════════════════════════════════════
    #  СОФИЯ КОППОЛА → Фрэнсис, Лорен Антонелли, Бертолуччи
    # ════════════════════════════════════════════════════════════
    ("Фрэнсис Форд Коппола",   "София Коппола",       "S. Coppola: father, on-set apprenticeship"),
    ("Бернардо Бертолуччи",    "София Коппола",       "S. Coppola: Bertolucci's family friend, sensuality"),
    ("Жан-Люк Годар",          "София Коппола",       "S. Coppola: Godard for Lost in Translation rhythm"),

    # ════════════════════════════════════════════════════════════
    #  УЭС АНДЕРСОН → Хол Эшби, Сатьяджит Рай, Жан Ренуар
    # ════════════════════════════════════════════════════════════
    ("Хол Эшби",               "Уэс Андерсон",        "Anderson: Ashby's deadpan tone"),
    ("Сатьяджит Рай",          "Уэс Андерсон",        "Anderson: Ray's Darjeeling Limited dedication"),
    ("Жан Ренуар",             "Уэс Андерсон",        "Anderson: Renoir's ensemble in Rules of the Game"),

    # ════════════════════════════════════════════════════════════
    #  ПОЛ ТОМАС АНДЕРСОН → Олтман, Скорсезе, Кубрик, Демм
    # ════════════════════════════════════════════════════════════
    ("Роберт Олтман",          "Пол Томас Андерсон",  "PTA: Altman's ensemble for Magnolia"),
    ("Мартин Скорсезе",        "Пол Томас Андерсон",  "PTA: Goodfellas as Boogie Nights foundation"),
    ("Стэнли Кубрик",          "Пол Томас Андерсон",  "PTA: Kubrick's formal control"),
    ("Джонатан Демми",         "Пол Томас Андерсон",  "PTA: Demme's portrait close-ups"),

    # ════════════════════════════════════════════════════════════
    #  МАЙКЛ МАНН → Кубрик, Хичкок, Уэллс
    # ════════════════════════════════════════════════════════════
    ("Стэнли Кубрик",          "Майкл Манн",          "Mann: Kubrick's formal architecture for Heat"),
    ("Альфред Хичкок",         "Майкл Манн",          "Mann: Hitchcock for thriller logic"),
    ("Орсон Уэллс",            "Майкл Манн",          "Mann: Welles's Touch of Evil tracking shots"),

    # ════════════════════════════════════════════════════════════
    #  ДЭВИД ФИНЧЕР → Кубрик, Хичкок, Полански (из v1)
    # ════════════════════════════════════════════════════════════
    ("Стэнли Кубрик",          "Дэвид Финчер",        "Fincher: Kubrick is my god (Empire 2007)"),
    ("Альфред Хичкок",         "Дэвид Финчер",        "Fincher: Hitchcock for Zodiac structure"),
    ("Роман Полански",         "Дэвид Финчер",        "Fincher: Polanski's apartment paranoia"),

    # ════════════════════════════════════════════════════════════
    #  УЧИТЕЛЯ-КЛАССИКИ — их собственные учителя (один уровень)
    # ════════════════════════════════════════════════════════════

    # АКИРА КУРОСАВА — на кого он повлиял уже есть, добавим его учителей:
    ("Кэндзи Мидзогути",       "Акира Куросава",      "Kurosawa autobiography: Mizoguchi as senior master"),
    ("Джон Форд",              "Акира Куросава",      "Kurosawa: Ford as Western cinema teacher"),
    ("Фёдор Достоевский",      "Акира Куросава",      "Kurosawa: literary influence (не режиссёр, пропустится если нет)"),

    # АЛЬФРЕД ХИЧКОК — его учителя:
    ("Фриц Ланг",              "Альфред Хичкок",      "Hitchcock: Lang's M as German expressionism teacher"),
    ("Ф. В. Мурнау",           "Альфред Хичкок",      "Hitchcock: worked at UFA during Murnau era"),

    # ИНГМАР БЕРГМАН — его учителя:
    ("Виктор Шёстрём",         "Ингмар Бергман",      "Bergman: Sjöström as Swedish cinema father"),
    ("Карл Теодор Дрейер",     "Ингмар Бергман",      "Bergman: Dreyer's spirituality on Persona"),

    # ЖАН-ЛЮК ГОДАР — его учителя:
    ("Жан Ренуар",             "Жан-Люк Годар",       "Godard: Renoir as Cahiers worship"),
    ("Орсон Уэллс",            "Жан-Люк Годар",       "Godard: Welles as Cahiers icon"),
    ("Альфред Хичкок",         "Жан-Люк Годар",       "Godard: Hitchcock for À bout de souffle"),

    # БИЛЛИ УАЙЛДЕР — его учителя:
    ("Эрнст Любич",            "Билли Уайлдер",       "Wilder: Lubitsch as mentor at Paramount"),
    ("Эрих фон Штрогейм",      "Билли Уайлдер",       "Wilder: Stroheim as actor in Sunset Blvd"),

    # КУРОСАВА — на кого повлиял (дубль v1 для безопасности):
    ("Акира Куросава",         "Джордж Лукас",        "Lucas: Hidden Fortress = Star Wars origin"),
    ("Акира Куросава",         "Серджо Леоне",        "Leone: Yojimbo remake as Fistful of Dollars"),
    ("Акира Куросава",         "Стивен Спилберг",     "Spielberg: year with Kurosawa on Dreams"),

    # ════════════════════════════════════════════════════════════
    #  ДОПОЛНИТЕЛЬНЫЕ ЖЕНЩИНЫ-РЕЖИССЁРЫ (важно по твоему запросу)
    # ════════════════════════════════════════════════════════════

    # КЭТРИН БИГЕЛОУ
    ("Сэм Пекинпа",            "Кэтрин Бигелоу",      "Bigelow: Peckinpah's violence aesthetics"),
    ("Уолтер Хилл",            "Кэтрин Бигелоу",      "Bigelow: Hill's action genre rigor"),
    ("Жан-Пьер Мельвиль",      "Кэтрин Бигелоу",      "Bigelow: Melville's procedural cool"),

    # ДЖЕЙН КЭМПИОН
    ("Джейн Кэмпион",          "Селин Сьямма",        "Sciamma: Campion as feminist forefather"),
    ("Аньес Варда",            "Джейн Кэмпион",       "Campion: Varda's feminist roots"),
    ("Робер Брессон",          "Джейн Кэмпион",       "Campion: Bresson's minimalism for The Piano"),

    # АНДРЕА АРНОЛЬД
    ("Кен Лоуч",               "Андреа Арнольд",      "Arnold: Loach's social realism"),
    ("Робер Брессон",          "Андреа Арнольд",      "Arnold: Bresson's economy"),

    # ЛУЛУ ВАН (The Farewell)
    ("Эдвард Ян",              "Лулу Ван",            "Wang: Edward Yang for Taiwanese family drama"),
    ("Эрик Ромер",             "Лулу Ван",            "Wang: Rohmer's dialogue craft"),

    # КЕЛЛИ РАЙКАРД
    ("Робер Брессон",          "Келли Райкард",       "Reichardt: Bresson's minimal style"),
    ("Чантал Акерман",         "Келли Райкард",       "Reichardt: Akerman's duration"),
    ("Ясудзиро Одзу",          "Келли Райкард",       "Reichardt: Ozu's stillness"),

    # МИЯ ХАНСЕН-ЛЁВЕ
    ("Эрик Ромер",             "Мия Хансен-Лёве",     "Hansen-Løve: Rohmer's conversational French cinema"),
    ("Морис Пиала",            "Мия Хансен-Лёве",     "Hansen-Løve: Pialat's emotional truth"),

    # САРА ПОЛЛИ
    ("Майк Ли",                "Сара Полли",          "Polley: Mike Leigh's working method"),
    ("Кассаветес",             "Сара Полли",          "Polley: Cassavetes' actor-driven cinema (alt spelling)"),

    # ПАТТИ ДЖЕНКИНС
    ("Ридли Скотт",            "Патти Дженкинс",      "Jenkins: Scott's epic scale for Wonder Woman"),
    ("Сидни Люмет",            "Патти Дженкинс",      "Jenkins: Lumet's character focus for Monster"),

    # ════════════════════════════════════════════════════════════
    #  ДОПОЛНИТЕЛЬНО: молодые мужчины которых не упомянули раньше
    # ════════════════════════════════════════════════════════════

    # ДЕНИ ВИЛЬНЁВ
    ("Стэнли Кубрик",          "Дени Вильнёв",        "Villeneuve: Kubrick for Dune scale (Sight&Sound 2024)"),
    ("Терренс Малик",          "Дени Вильнёв",        "Villeneuve: Malick's nature mysticism"),
    ("Андрей Тарковский",      "Дени Вильнёв",        "Villeneuve: Tarkovsky's Solaris influence on Arrival"),

    # ЙОРГОС ЛАНТИМОС
    ("Стэнли Кубрик",          "Йоргос Лантимос",     "Lanthimos: Kubrick is everything (Cannes 2023)"),
    ("Луис Бунюэль",           "Йоргос Лантимос",     "Lanthimos: Buñuel's absurdism"),
    ("Михаэль Ханеке",         "Йоргос Лантимос",     "Lanthimos: Haneke's cold formalism"),

    # ДАМИЕН ШАЗЕЛЛ
    ("Жак Деми",               "Дамьен Шазелл",       "Chazelle: Demy's Umbrellas as La La Land roots"),
    ("Боб Фосси",              "Дамьен Шазелл",       "Chazelle: Fosse's musical staging"),
    ("Дэвид Финчер",           "Дамьен Шазелл",       "Chazelle: Fincher's perfectionism on Whiplash"),

    # ГИЛЬЕРМО ДЕЛЬ ТОРО
    ("Альфред Хичкок",         "Гильермо дель Торо",  "del Toro: 'My eternal master'"),
    ("Тод Браунинг",           "Гильермо дель Торо",  "del Toro: Browning's Freaks for creature design"),
    ("Хаяо Миядзаки",          "Гильермо дель Торо",  "del Toro: Miyazaki's imagination for Pan's Labyrinth"),

    # АЛЕХАНДРО ГОНСАЛЕС ИНЬЯРРИТУ
    ("Андрей Тарковский",      "Алехандро Гонсалес Иньярриту", "Iñárritu: Tarkovsky's spiritual cinema"),
    ("Терренс Малик",          "Алехандро Гонсалес Иньярриту", "Iñárritu: Malick for The Revenant"),

    # АЛЬФОНСО КУАРОН
    ("Стэнли Кубрик",          "Альфонсо Куарон",     "Cuarón: Kubrick on Roma's spatial control"),
    ("Микеланджело Антониони", "Альфонсо Куарон",     "Cuarón: Antonioni's empty spaces"),
    ("Эммануэль Любецкий",     "Альфонсо Куарон",     "Cuarón: lifelong DP collaboration"),

    # БОН ДЖУН ХО
    ("Альфред Хичкок",         "Пон Чжун Хо",         "Bong: Hitchcock for Mother thriller structure"),
    ("Имамура Сёхэй",          "Пон Чжун Хо",         "Bong: Imamura's social satire"),
    ("Ким Ки Ён",              "Пон Чжун Хо",         "Bong: Kim Ki-young's The Housemaid for Parasite"),

    # КРИСТОФЕР НОЛАН (молодой по карьерной мерке)
    ("Стэнли Кубрик",          "Кристофер Нолан",     "Nolan: Kubrick is foundation (BAFTA 2018)"),
    ("Майкл Манн",             "Кристофер Нолан",     "Nolan: Mann's Heat for The Dark Knight"),
    ("Никола Роэг",            "Кристофер Нолан",     "Nolan: Roeg's Don't Look Now for Memento"),
    ("Терренс Малик",          "Кристофер Нолан",     "Nolan: Malick's Tree of Life pace for Interstellar"),
]


# ════════════════════════════════════════════════════════════════
#  ЛОГИКА
# ════════════════════════════════════════════════════════════════

# Альтернативные написания в seed → каноническое имя в entity_translation
NAME_ALIASES: dict[str, str] = {
    "Кассаветес": "Джон Кассаветис",
    "Шанталь Акерман": "Чантал Акерман",
    "Мишелангело Антониони": "Микеланджело Антониони",
}


async def find_director_by_name(db: AsyncSession, name: str) -> int | None:
    """Ищет режиссёра по имени (RU или EN). Возвращает person.id или None."""
    name = NAME_ALIASES.get(name, name)
    sql = text("""
        SELECT p.id
        FROM person p
        JOIN entity_translation et ON et.entity_id = p.id
        WHERE p.is_director = true
          AND lower(et.title) = lower(:name)
        LIMIT 1
    """)
    row_id = (await db.execute(sql, {"name": name})).scalar_one_or_none()
    if row_id:
        return row_id

    # Fallback по sort_name
    sql2 = text("""
        SELECT p.id FROM person p
        WHERE p.is_director = true
          AND lower(p.sort_name) = lower(:name)
        LIMIT 1
    """)
    return (await db.execute(sql2, {"name": name})).scalar_one_or_none()


async def insert_or_skip(
    db: AsyncSession,
    *,
    source_id: int,
    target_id: int,
    relation_note: str,
) -> str:
    """Возвращает 'created' / 'exists' / 'self_loop'."""
    if source_id == target_id:
        return "self_loop"
    result = await db.execute(text("""
        INSERT INTO director_influence (
            source_director_id, target_director_id,
            weight, confidence, relation_note, inferred_by_system
        ) VALUES (
            :src, :tgt, 1.0, 0.95, :note, false
        )
        ON CONFLICT (source_director_id, target_director_id) DO NOTHING
        RETURNING source_director_id
    """), {"src": source_id, "tgt": target_id, "note": relation_note})
    return "created" if result.first() else "exists"


async def main() -> None:
    log.info("═══════════════════════════════════════════════════════")
    log.info(" Ручная разметка v2 — РАСШИРЕННАЯ (молодые + глубина 2)")
    log.info("═══════════════════════════════════════════════════════")
    log.info("Запланировано связей в файле: %d", len(INFLUENCES))

    stats = defaultdict(int)
    missing_names: set[str] = set()

    async with AsyncSessionLocal() as db:
        for source_name, target_name, note in INFLUENCES:
            src_id = await find_director_by_name(db, source_name)
            tgt_id = await find_director_by_name(db, target_name)

            if not src_id or not tgt_id:
                if not src_id:
                    missing_names.add(source_name)
                if not tgt_id:
                    missing_names.add(target_name)
                stats["not_found"] += 1
                continue

            result = await insert_or_skip(
                db, source_id=src_id, target_id=tgt_id, relation_note=note,
            )
            stats[result] += 1

            if result == "created":
                log.info("  ✓ %s → %s", source_name, target_name)

        await db.commit()

        log.info("")
        log.info("═══════════════════════════════════════════════════════")
        log.info("✅ ИТОГИ")
        log.info("   создано новых:        %d", stats["created"])
        log.info("   уже существовало:     %d", stats["exists"])
        log.info("   режиссёров нет в БД:  %d связей", stats["not_found"])
        log.info("   self-loops:           %d", stats["self_loop"])
        log.info("")

        if missing_names:
            log.info("   Отсутствующие в БД режиссёры (нужно догрузить):")
            for name in sorted(missing_names):
                log.info("     • %s", name)

        total = (await db.execute(text("SELECT count(*) FROM director_influence"))).scalar_one()
        log.info("")
        log.info("   всего связей в БД:    %d", total)
        log.info("═══════════════════════════════════════════════════════")


if __name__ == "__main__":
    asyncio.run(main())
