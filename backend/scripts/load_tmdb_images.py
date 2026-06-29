"""
Загрузчик кадров из фильмов (backdrops + stills) с TMDB.

Что делает для каждого фильма в БД:
  1. Запрашивает GET /movie/{tmdb_id}/images
  2. Из массива backdrops берёт:
     - Лучший (топ-1 по vote_average) → entity.primary_backdrop_url
     - Топ-10 следующих → entity_media + media_asset с role='still'
  3. Идемпотентно: если у фильма уже есть backdrop — пропускает.
     Используй --force для перезаписи.

Запуск:
    cd backend
    source venv/bin/activate
    
    # Тестово на 10 фильмах:
    python -m scripts.load_tmdb_images --limit 10
    
    # Полный прогон:
    python -m scripts.load_tmdb_images
    
    # Перезаписать всё:
    python -m scripts.load_tmdb_images --force
"""
from __future__ import annotations

import argparse
import asyncio
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from scripts.tmdb_client import TmdbClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
log = logging.getLogger("images")
logging.getLogger("httpx").setLevel(logging.WARNING)

# ─── Конфиг ────────────────────────────────────────────────
MAX_STILLS_PER_FILM = 10      # кадров на фильм (галерея)
TMDB_IMAGE_BASE_BACKDROP = "https://image.tmdb.org/t/p/w1280"   # большие
TMDB_IMAGE_BASE_STILL = "https://image.tmdb.org/t/p/w780"       # средние для галереи
DEFAULT_PAUSE_SEC = 0.15       # ~6-7 запросов/сек (TMDB лимит 40/сек)


# ─── Утилиты ───────────────────────────────────────────────
def tmdb_image_url(path: str | None, base: str) -> str | None:
    """Превращает '/abc.jpg' в полную URL TMDB CDN."""
    if not path:
        return None
    if not path.startswith("/"):
        path = "/" + path
    return f"{base}{path}"


def image_basename(url: str | None) -> str | None:
    if not url:
        return None
    name = url.rstrip("/").rsplit("/", 1)[-1].split("?", 1)[0]
    return name or None


def pick_best_backdrop(
    backdrops: list[dict[str, Any]],
    *,
    poster_path: str | None,
    poster_url: str | None,
) -> dict[str, Any] | None:
    """Лучший кадр: не афиша, предпочитаем горизонтальные."""
    if not backdrops:
        return None

    poster_names = {
        name
        for name in (image_basename(poster_path), image_basename(poster_url))
        if name
    }

    def score(item: dict[str, Any]) -> tuple[float, float, float]:
        width = item.get("width") or 0
        height = max(item.get("height") or 1, 1)
        ratio = width / height
        landscape_bonus = 1.0 if ratio >= 1.5 else 0.0
        poster_penalty = -10.0 if image_basename(item.get("file_path")) in poster_names else 0.0
        return (
            poster_penalty + landscape_bonus,
            item.get("vote_average") or 0,
            item.get("vote_count") or 0,
        )

    return max(backdrops, key=score)


# ─── БД ────────────────────────────────────────────────────
async def get_films_to_process(
    db: AsyncSession,
    *,
    force: bool,
    limit: int | None,
) -> list[tuple[int, str]]:
    """
    Возвращает [(entity_id, tmdb_id), ...] — фильмы для обработки.
    Если не --force — только те у кого primary_backdrop_url ещё пуст.
    """
    where_extra = "" if force else "AND e.primary_backdrop_url IS NULL"
    limit_extra = f"LIMIT {int(limit)}" if limit else ""

    sql = text(f"""
        SELECT e.id, e.external_ids->>'tmdb' AS tmdb_id
        FROM entity e
        JOIN film f ON f.id = e.id
        WHERE e.entity_type = 'film'
          AND e.external_ids ? 'tmdb'
          {where_extra}
        ORDER BY e.id
        {limit_extra}
    """)
    rows = (await db.execute(sql)).mappings().all()
    return [(r["id"], r["tmdb_id"]) for r in rows]


async def upsert_media_asset(
    db: AsyncSession,
    *,
    url: str,
    width: int | None,
    height: int | None,
    external_id: str | None = None,
) -> int:
    """
    Создаёт запись в media_asset или возвращает существующую по url.
    Возвращает media_id.
    """
    # Ищем существующую
    existing = await db.execute(
        text("SELECT id FROM media_asset WHERE url = :url LIMIT 1"),
        {"url": url},
    )
    row = existing.first()
    if row:
        return row[0]

    # Создаём
    result = await db.execute(text("""
        INSERT INTO media_asset (
            url, source_kind, external_id, width, height, format, mime_type
        ) VALUES (
            :url, 'tmdb', :ext_id, :w, :h, 'jpg', 'image/jpeg'
        )
        RETURNING id
    """), {
        "url": url,
        "ext_id": external_id,
        "w": width,
        "h": height,
    })
    return result.scalar_one()


async def link_entity_media(
    db: AsyncSession,
    *,
    entity_id: int,
    media_id: int,
    role: str,
    is_primary: bool = False,
    position: int = 0,
) -> bool:
    """
    Связывает entity с media_asset. Возвращает True если создано новое.
    Идемпотентно.
    """
    # Проверка существования
    existing = await db.execute(text("""
        SELECT 1 FROM entity_media
        WHERE entity_id = :eid AND media_id = :mid AND role = CAST(:r AS media_role)
        LIMIT 1
    """), {"eid": entity_id, "mid": media_id, "r": role})
    if existing.first():
        return False

    await db.execute(text("""
        INSERT INTO entity_media (
            entity_id, media_id, role, is_primary, position
        ) VALUES (
            :eid, :mid, CAST(:r AS media_role), :prim, :pos
        )
    """), {
        "eid": entity_id,
        "mid": media_id,
        "r": role,
        "prim": is_primary,
        "pos": position,
    })
    return True


async def process_film(
    db: AsyncSession,
    tmdb: TmdbClient,
    *,
    entity_id: int,
    tmdb_id: str,
) -> dict:
    """Обработка одного фильма. Возвращает счётчики."""
    stats = {"backdrop": False, "stills": 0, "error": None}

    poster_row = await db.execute(
        text("SELECT primary_image_url FROM entity WHERE id = :id"),
        {"id": entity_id},
    )
    poster_url = poster_row.scalar_one_or_none()

    try:
        images = await tmdb.movie_images(int(tmdb_id))
    except Exception as exc:
        stats["error"] = f"TMDB API: {exc}"
        return stats

    backdrops = images.get("backdrops") or []
    if not backdrops:
        log.info("    [%d] нет backdrops в TMDB", entity_id)
        return stats

    poster_paths = [
        p.get("file_path")
        for p in (images.get("posters") or [])
        if p.get("file_path")
    ]
    poster_path = poster_paths[0] if poster_paths else None

    best = pick_best_backdrop(
        backdrops,
        poster_path=poster_path,
        poster_url=poster_url,
    )
    if not best:
        log.info("    [%d] не удалось выбрать backdrop", entity_id)
        return stats

    # Остальные backdrops — в галерею stills (без выбранного hero-кадра)
    best_path = best.get("file_path")
    stills_pool = [
        item for item in backdrops
        if item.get("file_path") != best_path
    ][:MAX_STILLS_PER_FILM]

    # 1) ЛУЧШИЙ backdrop → primary_backdrop_url
    best_url = tmdb_image_url(best.get("file_path"), TMDB_IMAGE_BASE_BACKDROP)
    if best_url:
        await db.execute(text("""
            UPDATE entity SET primary_backdrop_url = :url WHERE id = :id
        """), {"url": best_url, "id": entity_id})

        # Также пишем в entity_media для архитектурной целостности
        media_id = await upsert_media_asset(
            db,
            url=best_url,
            width=best.get("width"),
            height=best.get("height"),
            external_id=best.get("file_path"),
        )
        await link_entity_media(
            db,
            entity_id=entity_id,
            media_id=media_id,
            role="backdrop",
            is_primary=True,
            position=0,
        )
        stats["backdrop"] = True

    # 2) Следующие N → stills (галерея)
    for pos, still in enumerate(stills_pool, start=1):
        still_url = tmdb_image_url(still.get("file_path"), TMDB_IMAGE_BASE_STILL)
        if not still_url:
            continue

        media_id = await upsert_media_asset(
            db,
            url=still_url,
            width=still.get("width"),
            height=still.get("height"),
            external_id=still.get("file_path"),
        )
        created = await link_entity_media(
            db,
            entity_id=entity_id,
            media_id=media_id,
            role="still",
            is_primary=False,
            position=pos,
        )
        if created:
            stats["stills"] += 1

    return stats


# ─── Main ──────────────────────────────────────────────────
async def main(
    *,
    limit: int | None,
    force: bool,
    pause_sec: float,
) -> None:
    if not settings.tmdb_api_key:
        raise SystemExit("TMDB_API_KEY не задан в .env")

    log.info("─── Loader кадров фильмов (TMDB images) ───")
    log.info("force=%s, limit=%s, pause=%.2fs", force, limit, pause_sec)

    # Список фильмов
    async with AsyncSessionLocal() as db:
        films = await get_films_to_process(db, force=force, limit=limit)
    log.info("к обработке фильмов: %d", len(films))
    if not films:
        log.info("Нечего делать (все обработаны). Используй --force для перезаписи.")
        return

    totals = {
        "processed": 0,
        "with_backdrop": 0,
        "stills_total": 0,
        "errors": 0,
    }

    async with TmdbClient(api_key=settings.tmdb_api_key) as tmdb:
        for idx, (entity_id, tmdb_id) in enumerate(films, start=1):
            log.info("[%d/%d] film id=%d tmdb=%s", idx, len(films), entity_id, tmdb_id)

            # Каждый фильм — отдельная транзакция (чтобы ошибка одного
            # не отравила сессию для остальных)
            async with AsyncSessionLocal() as db:
                try:
                    stats = await process_film(
                        db, tmdb, entity_id=entity_id, tmdb_id=tmdb_id,
                    )
                    await db.commit()

                    totals["processed"] += 1
                    if stats["backdrop"]:
                        totals["with_backdrop"] += 1
                    totals["stills_total"] += stats["stills"]

                    if stats["error"]:
                        totals["errors"] += 1
                        log.warning("  ⚠ %s", stats["error"])
                    else:
                        log.info(
                            "  ✓ backdrop=%s stills=%d",
                            "yes" if stats["backdrop"] else "no",
                            stats["stills"],
                        )
                except Exception as exc:
                    await db.rollback()
                    totals["errors"] += 1
                    log.exception("  FAILED: %s", exc)

            # Пауза между запросами к TMDB
            if idx < len(films):
                await asyncio.sleep(pause_sec)

            # Каждые 50 фильмов — промежуточная статистика
            if idx % 50 == 0:
                log.info(
                    "  ─── промежуточно: %d/%d, backdrops=%d, stills=%d, errors=%d",
                    idx, len(films),
                    totals["with_backdrop"],
                    totals["stills_total"],
                    totals["errors"],
                )

    log.info("─── DONE ───")
    log.info("обработано фильмов:      %d", totals["processed"])
    log.info("с backdrop:              %d", totals["with_backdrop"])
    log.info("всего stills (кадров):   %d", totals["stills_total"])
    log.info("ошибок:                  %d", totals["errors"])


def cli() -> None:
    parser = argparse.ArgumentParser(
        description="Догрузка backdrop + stills из TMDB в entity_media + entity.primary_backdrop_url",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Обработать только первые N фильмов (для теста)",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Перезаписать backdrop даже если уже загружен",
    )
    parser.add_argument(
        "--pause", type=float, default=DEFAULT_PAUSE_SEC,
        help=f"Пауза между запросами TMDB в секундах (default {DEFAULT_PAUSE_SEC})",
    )
    args = parser.parse_args()
    asyncio.run(main(
        limit=args.limit,
        force=args.force,
        pause_sec=max(0.0, args.pause),
    ))


if __name__ == "__main__":
    cli()
