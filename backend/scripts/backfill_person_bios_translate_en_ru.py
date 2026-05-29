"""
Перевод EN-биографий персон в RU (entity_translation.description/summary).

Берёт непустой EN description, если RU пустой. Нужен пакет:
    pip install deep-translator

Запуск (из backend/, venv):
    python -m scripts.backfill_person_bios_translate_en_ru --dry-run --limit 5
    python -m scripts.backfill_person_bios_translate_en_ru --all-persons --limit 500
    python -m scripts.backfill_person_bios_translate_en_ru --all-persons

Сначала лучше: backfill_person_bios_tmdb_ru и backfill_person_bios_wikipedia --lang ru
(нативные тексты качественнее машинного перевода).
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import re

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from scripts.backfill_person_bios_wikipedia import get_languages, update_bio

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
log = logging.getLogger("backfill-translate-ru")

# Лимит Google Translate через deep-translator
MAX_CHUNK = 4500
PAUSE_SEC = 0.6


def _chunk_text(text: str, max_len: int = MAX_CHUNK) -> list[str]:
    if len(text) <= max_len:
        return [text]
    parts: list[str] = []
    for block in re.split(r"\n{2,}", text):
        block = block.strip()
        if not block:
            continue
        if len(block) <= max_len:
            parts.append(block)
            continue
        for para in re.split(r"(?<=[.!?])\s+", block):
            if not para:
                continue
            if len(para) <= max_len:
                parts.append(para)
            else:
                for i in range(0, len(para), max_len):
                    parts.append(para[i : i + max_len])
    return parts or [text[:max_len]]


def translate_en_ru(text: str) -> str:
    from deep_translator import GoogleTranslator

    translator = GoogleTranslator(source="en", target="ru")
    chunks = _chunk_text(text.strip())
    out: list[str] = []
    for chunk in chunks:
        out.append(translator.translate(chunk))
    return "\n\n".join(s.strip() for s in out if s and s.strip())


async def fetch_candidates(
    db: AsyncSession,
    *,
    limit: int | None,
    only_directors: bool,
    min_en_len: int,
) -> list[dict]:
    role_filter = "p.is_director = true" if only_directors else "true"
    sql = f"""
        SELECT
            p.id AS person_id,
            COALESCE(et_ru.title, et_en.title, p.sort_name) AS name,
            et_en.description AS description_en
        FROM person p
        JOIN entity e ON e.id = p.id
        JOIN entity_translation et_en
            ON et_en.entity_id = p.id
           AND et_en.language_id = (SELECT id FROM language WHERE code = 'en' LIMIT 1)
        LEFT JOIN entity_translation et_ru
            ON et_ru.entity_id = p.id
           AND et_ru.language_id = (SELECT id FROM language WHERE code = 'ru' LIMIT 1)
        WHERE e.entity_type = 'person'
          AND e.status = 'published'
          AND {role_filter}
          AND coalesce(trim(et_ru.description), '') = ''
          AND coalesce(trim(et_en.description), '') <> ''
          AND length(trim(et_en.description)) >= :min_len
        ORDER BY p.id
    """
    if limit:
        sql += f" LIMIT {int(limit)}"
    rows = (
        await db.execute(text(sql), {"min_len": int(min_en_len)})
    ).mappings().all()
    return [dict(r) for r in rows]


async def main(
    *,
    limit: int | None,
    dry_run: bool,
    only_directors: bool,
    min_en_len: int,
    min_ru_len: int,
    pause: float,
) -> None:
    try:
        from deep_translator import GoogleTranslator  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "Установите: pip install deep-translator\n"
            "Затем повторите запуск."
        ) from exc

    async with AsyncSessionLocal() as db:
        languages = await get_languages(db)
        rows = await fetch_candidates(
            db,
            limit=limit,
            only_directors=only_directors,
            min_en_len=min_en_len,
        )

    log.info("к переводу: %d (dry_run=%s)", len(rows), dry_run)
    if "ru" not in languages:
        raise SystemExit("В БД нет language.code = 'ru'")

    stats = {"updated": 0, "too_short": 0, "errors": 0}

    for i, row in enumerate(rows):
        pid = row["person_id"]
        name = row["name"] or "?"
        src = (row["description_en"] or "").strip()
        try:
            translated = translate_en_ru(src)
            if len(translated) < min_ru_len:
                stats["too_short"] += 1
                continue
            if dry_run:
                log.info(
                    "[%d] %s — EN %d → RU %d симв.",
                    i,
                    name,
                    len(src),
                    len(translated),
                )
                stats["updated"] += 1
                continue
            async with AsyncSessionLocal() as db:
                if await update_bio(
                    db,
                    person_id=pid,
                    language_id=languages["ru"],
                    description=translated,
                    force=False,
                ):
                    await db.commit()
                    stats["updated"] += 1
                    if stats["updated"] % 50 == 0:
                        log.info("  … переведено %d", stats["updated"])
        except Exception as exc:
            stats["errors"] += 1
            log.warning("[%d] %s: %s", i, name, exc)
        if pause:
            await asyncio.sleep(pause)

    log.info("─── DONE ───")
    log.info("обновлено RU:        %d", stats["updated"])
    log.info("короткий перевод:   %d", stats["too_short"])
    log.info("ошибок:             %d", stats["errors"])
    log.info("после прогона: python -m scripts.generate_embeddings")


def cli() -> None:
    p = argparse.ArgumentParser(description="Перевод EN biography → RU (Google via deep-translator)")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--all-persons", action="store_true")
    p.add_argument("--min-en-len", type=int, default=40)
    p.add_argument("--min-ru-len", type=int, default=40)
    p.add_argument("--pause", type=float, default=PAUSE_SEC)
    args = p.parse_args()
    asyncio.run(
        main(
            limit=args.limit,
            dry_run=args.dry_run,
            only_directors=not args.all_persons,
            min_en_len=args.min_en_len,
            min_ru_len=args.min_ru_len,
            pause=args.pause,
        )
    )


if __name__ == "__main__":
    cli()
