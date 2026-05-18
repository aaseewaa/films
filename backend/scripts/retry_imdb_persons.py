"""
Догрузить персон по списку IMDb id (для tgt_miss из лога Wikidata).

Пример — вытащить imdb из лога:
  grep 'tgt NOT in DB' wikidata.log | sed -n 's/.*(\\(nm[0-9]*\\)).*/\\1/p' | sort -u > misses.txt

Запуск:
  python -m scripts.retry_imdb_persons --file misses.txt
  python -m scripts.retry_imdb_persons --imdb nm0000123,nm0000151
"""
from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from app.config import settings
from app.database import AsyncSessionLocal
from scripts.load_wikidata_influences_v2 import (
    find_person_by_imdb,
    get_languages,
    load_person_via_tmdb,
)
from scripts.tmdb_client import TmdbClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
log = logging.getLogger("retry-imdb")


def parse_imdb_list(raw: str) -> list[str]:
    parts = raw.replace("\n", ",").split(",")
    return [p.strip() for p in parts if p.strip().startswith("nm")]


async def main(imdb_ids: list[str]) -> None:
    if not settings.tmdb_api_key:
        raise SystemExit("TMDB_API_KEY не задан")
    if not imdb_ids:
        raise SystemExit("Список imdb пуст")

    log.info("IMDb id к обработке: %d", len(imdb_ids))
    ok, miss, existed = 0, 0, 0

    async with AsyncSessionLocal() as db:
        languages = await get_languages(db)

    async with TmdbClient(api_key=settings.tmdb_api_key) as tmdb:
        for imdb in imdb_ids:
            async with AsyncSessionLocal() as db:
                existing = await find_person_by_imdb(db, imdb)
                if existing:
                    log.info("✓ уже в БД: %s → person_id=%s", imdb, existing)
                    existed += 1
                    continue
                pid = await load_person_via_tmdb(
                    db, tmdb, imdb, fallback_name=imdb, languages=languages,
                )
                if pid:
                    await db.commit()
                    log.info("✓ догружен: %s → person_id=%s", imdb, pid)
                    ok += 1
                else:
                    log.warning("✗ TMDB find miss: %s", imdb)
                    miss += 1

    log.info("─── DONE ─── existed=%d loaded=%d miss=%d", existed, ok, miss)
    if ok or existed:
        log.info("затем снова: python -m scripts.load_wikidata_influences_v2")


def cli() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--imdb", type=str, default="", help="nm123,nm456")
    p.add_argument("--file", type=Path, default=None, help="По одному imdb на строку")
    args = p.parse_args()

    ids: list[str] = []
    if args.imdb:
        ids.extend(parse_imdb_list(args.imdb))
    if args.file and args.file.exists():
        ids.extend(
            line.strip()
            for line in args.file.read_text().splitlines()
            if line.strip().startswith("nm")
        )
    ids = list(dict.fromkeys(ids))
    asyncio.run(main(ids))


if __name__ == "__main__":
    cli()
