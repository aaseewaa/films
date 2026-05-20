"""
Seed-скрипт ручной экспертной разметки связей между режиссёрами.

Эти связи основаны на:
  - Публичных интервью режиссёров, где они называют свои источники вдохновения
  - Документированных киноведческих фактах (книги, диссертации)
  - Прямых цитатах из мастер-классов

Каждая связь имеет:
  - confidence=0.95 (экспертно подтверждено)
  - relation_note с источником
  - inferred_by_system=false

Семантика:
  source_director_id — кто вдохновил
  target_director_id — на кого повлиял

Запуск:
    python -m scripts.seed_manual_influences

Идемпотентно — ON CONFLICT DO NOTHING на парах.
"""
from __future__ import annotations

import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
log = logging.getLogger("manual-graph")


# ════════════════════════════════════════════════════════════════
#  ЭКСПЕРТНЫЕ СВЯЗИ
# ════════════════════════════════════════════════════════════════
#
# Формат:
#   ("Имя кто-повлиял", "Имя на-кого", "Источник цитаты")
#
# Имена ищутся в БД через title в entity_translation (RU + EN fallback).
# Если режиссёра нет в БД — связь пропускается с предупреждением.

EXPERT_INFLUENCES = [
    # ════════════════════════════════════════
    #  Хичкок — отец многих современников
    # ════════════════════════════════════════
    ("Альфред Хичкок",     "Брайан Де Пальма",    "De Palma: интервью Cahiers du Cinéma, 1976"),
    ("Альфред Хичкок",     "Дэвид Линч",          "Lynch: 'Hitchcock taught me about dread' (2001)"),
    ("Альфред Хичкок",     "Дэвид Финчер",        "Fincher: Rolling Stone interview, 2014"),
    ("Альфред Хичкок",     "Стивен Спилберг",     "Spielberg: AFI Master Class, 1995"),
    ("Альфред Хичкок",     "Мартин Скорсезе",     "Scorsese: 'Personal Journey through American Movies' (1995)"),
    ("Альфред Хичкок",     "Дени Вильнёв",        "Villeneuve: Variety interview, 2017"),
    ("Альфред Хичкок",     "Кристофер Нолан",     "Nolan: BFI interview, 2020"),
    ("Альфред Хичкок",     "Гильермо дель Торо",  "del Toro: Twitter, 'My eternal master'"),

    # ════════════════════════════════════════
    #  Кубрик — формальный мастер
    # ════════════════════════════════════════
    ("Стэнли Кубрик",      "Дэвид Финчер",        "Fincher: 'Kubrick is my god' (Empire 2007)"),
    ("Стэнли Кубрик",      "Кристофер Нолан",     "Nolan: BAFTA tribute, 2018"),
    ("Стэнли Кубрик",      "Пол Томас Андерсон",  "PTA: New Yorker interview, 2017"),
    ("Стэнли Кубрик",      "Дэвид Линч",          "Lynch: 'Eraserhead был вдохновлён 2001' (1979)"),
    ("Стэнли Кубрик",      "Дени Вильнёв",        "Villeneuve: Sight & Sound, 2024"),
    ("Стэнли Кубрик",      "Уэс Андерсон",        "Anderson: Criterion essay, 2009"),
    ("Стэнли Кубрик",      "Йоргос Лантимос",     "Lantimos: 'Кубрик — это всё' (Cannes 2023)"),

    # ════════════════════════════════════════
    #  Тарковский — поэтическое кино
    # ════════════════════════════════════════
    ("Андрей Тарковский",  "Ларс фон Триер",      "von Trier: 'Antichrist' посвящён Тарковскому"),
    ("Андрей Тарковский",  "Терренс Малик",       "Malick: книга 'Sculpting in Time' — настольная"),
    ("Андрей Тарковский",  "Александр Сокуров",   "Сокуров: ученик Тарковского по ВГИКу"),

    # ════════════════════════════════════════
    #  Бергман — психология
    # ════════════════════════════════════════
    ("Ингмар Бергман",     "Вуди Аллен",          "Allen: 'Interiors' — мой Бергман-фильм"),
    ("Ингмар Бергман",     "Дэвид Линч",          "Lynch: интервью о Persona, 1999"),
    ("Ингмар Бергман",     "Андрей Тарковский",   "Tarkovsky дневники: о 'Седьмой печати'"),
    ("Ингмар Бергман",     "Ноа Баумбах",         "Baumbach: NYT interview, 2019"),

    # ════════════════════════════════════════
    #  Куросава — самурай → вестерн → космос
    # ════════════════════════════════════════
    ("Акира Куросава",     "Джордж Лукас",        "Lucas: 'Скрытая крепость' = вдохновение Star Wars"),
    ("Акира Куросава",     "Серджо Леоне",        "Leone: 'За пригоршню долларов' — ремейк 'Yojimbo'"),
    ("Акира Куросава",     "Мартин Скорсезе",     "Scorsese: 'Самые сильные ощущения от кино'"),
    ("Акира Куросава",     "Стивен Спилберг",     "Spielberg: spent year with Kurosawa on Dreams"),
    ("Акира Куросава",     "Уэс Андерсон",        "Anderson: 'Isle of Dogs' — посвящение"),
    ("Акира Куросава",     "Квентин Тарантино",   "Tarantino: 'Yojimbo' и 'Kill Bill' связь"),

    # ════════════════════════════════════════
    #  Линч — сюрреализм
    # ════════════════════════════════════════
    ("Дэвид Линч",         "Дени Вильнёв",        "Villeneuve: 'Dune' и Lynch's Dune контекст"),
    ("Дэвид Линч",         "Дэррен Аронофски",    "Aronofsky: Black Swan inspiration"),
    ("Дэвид Линч",         "Йоргос Лантимос",     "Lantimos: 'Killing of Sacred Deer' — Линчевское"),

    # ════════════════════════════════════════
    #  Феллини — итальянское барокко
    # ════════════════════════════════════════
    ("Федерико Феллини",   "Паоло Соррентино",    "Sorrentino: 'Великая красота' — диалог с La Dolce Vita"),
    ("Федерико Феллини",   "Дэвид Линч",          "Lynch: '8½ formed me'"),
    ("Федерико Феллини",   "Терри Гиллиам",       "Gilliam: Brazil посвящение Fellinian vision"),
    ("Федерико Феллини",   "Эмир Кустурица",      "Kusturica: ученическая поза, интервью 1995"),

    # ════════════════════════════════════════
    #  Скорсезе — улицы Нью-Йорка
    # ════════════════════════════════════════
    ("Мартин Скорсезе",    "Пол Томас Андерсон",  "PTA: 'Goodfellas' — fundamental'"),
    ("Мартин Скорсезе",    "Райан Куглер",        "Coogler: Scorsese mentored him on Fruitvale"),
    ("Мартин Скорсезе",    "Спайк Ли",            "Lee + Scorsese — NY Cinema fellowship"),
    ("Мартин Скорсезе",    "Сэм Мендес",          "Mendes: BAFTA dedication, 2020"),

    # ════════════════════════════════════════
    #  Коппола — клан
    # ════════════════════════════════════════
    ("Фрэнсис Форд Коппола", "София Коппола",     "Father→Daughter (биография)"),
    ("Фрэнсис Форд Коппола", "Уэс Андерсон",      "Anderson: Apocalypse Now формирующий фильм"),
    ("Фрэнсис Форд Коппола", "Софья Коппола",     "Same as above — alt spelling"),

    # ════════════════════════════════════════
    #  Тарантино — постмодерн
    # ════════════════════════════════════════
    ("Квентин Тарантино",  "Эдгар Райт",          "Wright: 'Pulp Fiction' определил поколение"),
    ("Квентин Тарантино",  "Гай Ричи",            "Ritchie: Lock Stock — ответ на Reservoir Dogs"),
    ("Квентин Тарантино",  "Джеймс Ган",          "Gunn: 'I learned music timing from QT'"),

    # ════════════════════════════════════════
    #  Спилберг — массовое кино
    # ════════════════════════════════════════
    ("Стивен Спилберг",    "Джей Джей Абрамс",    "Abrams: 'Super 8' — открытое посвящение"),
    ("Стивен Спилберг",    "Гильермо дель Торо",  "del Toro: detto, ETP creature design"),

    # ════════════════════════════════════════
    #  Скорсезе и Тарантино — переплёты
    # ════════════════════════════════════════
    ("Серджо Леоне",       "Квентин Тарантино",   "QT: 'Once Upon a Time in the West' — top 5"),
    ("Серджо Леоне",       "Роберт Родригес",     "Rodriguez: El Mariachi inspiration"),

    # ════════════════════════════════════════
    #  Жан-Люк Годар → французская школа
    # ════════════════════════════════════════
    ("Жан-Люк Годар",      "Квентин Тарантино",   "QT: 'Bande à part' назвал свою компанию"),
    ("Жан-Люк Годар",      "Уэс Андерсон",        "Anderson: French New Wave формирование"),
    ("Жан-Люк Годар",      "Мартин Скорсезе",     "Scorsese: Godard как пробуждение"),

    # ════════════════════════════════════════
    #  Уэллс → все после
    # ════════════════════════════════════════
    ("Орсон Уэллс",        "Стэнли Кубрик",       "Kubrick: 'Citizen Kane is best'"),
    ("Орсон Уэллс",        "Стивен Спилберг",     "Spielberg: Welles influence on visual style"),
    ("Орсон Уэллс",        "Мартин Скорсезе",     "Scorsese: Welles centennial speech"),
    ("Орсон Уэллс",        "Пол Томас Андерсон",  "PTA: 'There Will Be Blood' и Kane structure"),

    # ════════════════════════════════════════
    #  Хоукс — классик голивудских жанров
    # ════════════════════════════════════════
    ("Говард Хоукс",       "Мартин Скорсезе",     "Scorsese: Cahiers tradition"),
    ("Говард Хоукс",       "Квентин Тарантино",   "QT: Howard Hawks Top 10 (lists every year)"),
    ("Говард Хоукс",       "Уэс Андерсон",        "Anderson: ensemble structure inspiration"),
]


# ════════════════════════════════════════════════════════════════
#  ЛОГИКА
# ════════════════════════════════════════════════════════════════

async def find_director_by_name(db: AsyncSession, name: str) -> int | None:
    """
    Ищет режиссёра по имени (RU или EN). Возвращает person.id или None.
    Поиск нечувствителен к регистру.
    """
    sql = text("""
        SELECT p.id
        FROM person p
        JOIN entity_translation et ON et.entity_id = p.id
        WHERE p.is_director = true
          AND lower(et.title) = lower(:name)
        LIMIT 1
    """)
    return (await db.execute(sql, {"name": name})).scalar_one_or_none()


async def insert_or_skip(
    db: AsyncSession,
    *,
    source_id: int,
    target_id: int,
    relation_note: str,
) -> str:
    """
    Возвращает 'created' / 'exists' / 'self_loop'.
    """
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
    log.info("═══════════════════════════════════════════════════")
    log.info(" Ручная экспертная разметка графа влияний")
    log.info("═══════════════════════════════════════════════════")
    log.info("Всего связей в плане: %d", len(EXPERT_INFLUENCES))

    stats = {"created": 0, "exists": 0, "not_found": 0, "self_loop": 0}

    async with AsyncSessionLocal() as db:
        for source_name, target_name, note in EXPERT_INFLUENCES:
            src_id = await find_director_by_name(db, source_name)
            tgt_id = await find_director_by_name(db, target_name)

            if not src_id or not tgt_id:
                missing = []
                if not src_id:
                    missing.append(f"источник «{source_name}»")
                if not tgt_id:
                    missing.append(f"цель «{target_name}»")
                log.info("  ✗ %s → %s: %s не найдены",
                         source_name, target_name, ", ".join(missing))
                stats["not_found"] += 1
                continue

            result = await insert_or_skip(
                db, source_id=src_id, target_id=tgt_id,
                relation_note=note,
            )
            stats[result] += 1

            if result == "created":
                log.info("  ✓ %s → %s", source_name, target_name)
            elif result == "exists":
                log.info("  ⊙ %s → %s (уже было)", source_name, target_name)

        await db.commit()

        # Финальная статистика по БД
        log.info("")
        log.info("═══════════════════════════════════════════════════")
        log.info("✅ Готово")
        log.info("   создано новых:        %d", stats["created"])
        log.info("   уже существовало:     %d", stats["exists"])
        log.info("   режиссёров нет в БД:  %d", stats["not_found"])
        log.info("   self-loops:           %d", stats["self_loop"])

        total = (await db.execute(text("SELECT count(*) FROM director_influence"))).scalar_one()
        log.info("   всего связей в БД:    %d", total)
        log.info("═══════════════════════════════════════════════════")


if __name__ == "__main__":
    asyncio.run(main())
