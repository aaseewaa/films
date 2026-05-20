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

Запуск:
    cd backend
    source venv/bin/activate
    python -m scripts.load_wikidata_influences_v3
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal

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


# ════════════════════════════════════════════════════════
#  ШАБЛОНЫ SPARQL для каждого свойства
# ════════════════════════════════════════════════════════
SPARQL_TEMPLATES = {
    # P802: «у X есть ученик Y» → влияние X→Y
    "P802": """
SELECT ?student ?studentLabel WHERE {{
  VALUES ?master {{ {qids} }}
  ?master wdt:P802 ?student .
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
""",
    # P2099: «у X есть известный ученик Y» → влияние X→Y
    "P2099": """
SELECT ?student ?studentLabel WHERE {{
  VALUES ?master {{ {qids} }}
  ?master wdt:P2099 ?student .
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
""",
    # P184: «у X есть научрук Y» → влияние Y→X (обратное направление!)
    "P184": """
SELECT ?advisor ?advisorLabel WHERE {{
  VALUES ?student {{ {qids} }}
  ?student wdt:P184 ?advisor .
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
""",
    # P1066: «X — ученик Y» → влияние Y→X
    "P1066": """
SELECT ?master ?masterLabel WHERE {{
  VALUES ?student {{ {qids} }}
  ?student wdt:P1066 ?master .
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
""",
}


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


async def get_directors_with_wikidata(db: AsyncSession) -> list[tuple[int, str]]:
    """Возвращает [(person_id, wikidata_qid), ...] для всех режиссёров."""
    sql = text("""
        SELECT p.id, e.external_ids->>'wikidata' AS qid
        FROM person p
        JOIN entity e ON e.id = p.id
        WHERE p.is_director = true
          AND e.external_ids ? 'wikidata'
        ORDER BY p.id
    """)
    rows = (await db.execute(sql)).all()
    return [(row[0], row[1]) for row in rows if row[1]]


async def get_qid_to_person_id_map(db: AsyncSession) -> dict[str, int]:
    """Возвращает {QID: person_id} для всех персон с wikidata."""
    sql = text("""
        SELECT p.id, e.external_ids->>'wikidata' AS qid
        FROM person p
        JOIN entity e ON e.id = p.id
        WHERE p.is_director = true
          AND e.external_ids ? 'wikidata'
    """)
    rows = (await db.execute(sql)).all()
    return {row[1]: row[0] for row in rows if row[1]}


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


async def process_property(
    client: httpx.AsyncClient,
    qid_to_pid: dict[str, int],
    *,
    property_code: str,
) -> dict:
    """
    Обрабатывает одно свойство (P802, P184, P1066, P2099).
    Возвращает статистику {created, skipped, errors}.
    """
    template = SPARQL_TEMPLATES[property_code]
    stats = {"created": 0, "skipped": 0, "errors": 0, "queries": 0}

    qids_in_db = list(qid_to_pid.keys())
    log.info("─── %s ─── (режиссёров с QID: %d)", property_code, len(qids_in_db))

    # Бьём на батчи
    for batch_start in range(0, len(qids_in_db), BATCH_SIZE):
        batch = qids_in_db[batch_start : batch_start + BATCH_SIZE]
        qids_str = " ".join(f"wd:{q}" for q in batch)
        query = template.format(qids=qids_str)

        try:
            results = await sparql_query(client, query)
            stats["queries"] += 1
        except Exception as exc:
            log.warning("  batch %d failed: %s", batch_start, exc)
            stats["errors"] += 1
            await asyncio.sleep(BATCH_PAUSE_SEC * 2)
            continue

        # Парсим результаты
        # Wikidata возвращает related Q-id вместе с QID исходного режиссёра
        # Нам нужно найти КАКОЙ из batch QID связан с КАКИМ результирующим
        # Для этого делаем доп. запрос — но проще: использовать SELECT с обеими переменными
        # У нас в шаблоне только результирующая переменная, нужно переделать запрос
        # → переделываю запросы чтобы возвращали обе стороны
        pass

        await asyncio.sleep(BATCH_PAUSE_SEC)

    return stats


# ════════════════════════════════════════════════════════
#  ПЕРЕРАБОТАННЫЕ SPARQL — возвращают ОБЕ стороны
# ════════════════════════════════════════════════════════
SPARQL_TEMPLATES_V2 = {
    # P802 + P2099: X имеет ученика Y → X влиял на Y
    "P802_or_P2099_outgoing": """
SELECT ?master ?student WHERE {{
  VALUES ?master {{ {qids} }}
  {{ ?master wdt:P802 ?student . }}
  UNION
  {{ ?master wdt:P2099 ?student . }}
}}
""",
    # P184 + P1066: X имеет учителя Y → Y влиял на X
    "P184_or_P1066_incoming": """
SELECT ?student ?master WHERE {{
  VALUES ?student {{ {qids} }}
  {{ ?student wdt:P184 ?master . }}
  UNION
  {{ ?student wdt:P1066 ?master . }}
}}
""",
}


def extract_qid(entity_url: str) -> str | None:
    """Извлекает Q12345 из URL http://www.wikidata.org/entity/Q12345"""
    if not entity_url:
        return None
    return entity_url.rsplit("/", 1)[-1]


async def process_property_v2(
    client: httpx.AsyncClient,
    qid_to_pid: dict[str, int],
    *,
    query_key: str,
    direction: str,  # "outgoing" — этот человек влиял на других; "incoming" — на него влияли
) -> dict:
    """
    Обрабатывает запрос. Возвращает статистику и сразу пишет в БД.
    """
    template = SPARQL_TEMPLATES_V2[query_key]
    stats = {"created": 0, "skipped": 0, "errors": 0, "queries": 0, "raw_pairs": 0}

    qids_in_db = list(qid_to_pid.keys())
    log.info("─── %s [%s] ─── (режиссёров с QID: %d)",
             query_key, direction, len(qids_in_db))

    for batch_start in range(0, len(qids_in_db), BATCH_SIZE):
        batch = qids_in_db[batch_start : batch_start + BATCH_SIZE]
        qids_str = " ".join(f"wd:{q}" for q in batch)
        query = template.format(qids=qids_str)

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
                # Определяем какая переменная где, в зависимости от направления
                if direction == "outgoing":
                    # source=master, target=student
                    src_qid = extract_qid(r.get("master", {}).get("value"))
                    tgt_qid = extract_qid(r.get("student", {}).get("value"))
                else:  # incoming
                    # source=master (учитель), target=student (наш режиссёр)
                    src_qid = extract_qid(r.get("master", {}).get("value"))
                    tgt_qid = extract_qid(r.get("student", {}).get("value"))

                if not src_qid or not tgt_qid:
                    continue

                # Обе стороны должны быть в нашей БД
                src_pid = qid_to_pid.get(src_qid)
                tgt_pid = qid_to_pid.get(tgt_qid)

                if not src_pid or not tgt_pid:
                    stats["skipped"] += 1
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


async def main() -> None:
    log.info("═══════════════════════════════════════════════════")
    log.info(" Wikidata Influences v3 — P802 + P184 + P1066 + P2099")
    log.info("═══════════════════════════════════════════════════")

    # Получаем мап QID → person_id
    async with AsyncSessionLocal() as db:
        qid_to_pid = await get_qid_to_person_id_map(db)
    log.info("режиссёров с Wikidata QID: %d", len(qid_to_pid))

    if not qid_to_pid:
        log.warning("Нет режиссёров с Wikidata QID — нечего обрабатывать")
        return

    total = {"created": 0, "skipped": 0, "errors": 0, "queries": 0}

    async with httpx.AsyncClient() as client:
        # 1) Outgoing: эти режиссёры — учителя; результат — их ученики
        stats1 = await process_property_v2(
            client, qid_to_pid,
            query_key="P802_or_P2099_outgoing",
            direction="outgoing",
        )
        for k in total:
            total[k] += stats1.get(k, 0)
        log.info("  P802/P2099: создано связей %d (skipped: %d)",
                 stats1["created"], stats1["skipped"])

        # 2) Incoming: эти режиссёры — ученики; результат — их учителя
        stats2 = await process_property_v2(
            client, qid_to_pid,
            query_key="P184_or_P1066_incoming",
            direction="incoming",
        )
        for k in total:
            total[k] += stats2.get(k, 0)
        log.info("  P184/P1066: создано связей %d (skipped: %d)",
                 stats2["created"], stats2["skipped"])

    log.info("")
    log.info("═══════════════════════════════════════════════════")
    log.info("✅ Готово")
    log.info("   новых связей создано: %d", total["created"])
    log.info("   пропущено (нет в БД): %d", total["skipped"])
    log.info("   ошибок:               %d", total["errors"])
    log.info("   SPARQL запросов:      %d", total["queries"])
    log.info("═══════════════════════════════════════════════════")

    # Финальная статистика
    async with AsyncSessionLocal() as db:
        cnt = (await db.execute(text("SELECT count(*) FROM director_influence"))).scalar_one()
        log.info("Всего связей в БД: %d", cnt)


if __name__ == "__main__":
    asyncio.run(main())
