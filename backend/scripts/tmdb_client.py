"""
Клиент TMDB API.

Возможности:
  - rate-limit (TMDB разрешает ~50 запросов в секунду, но мы держим скромно)
  - кэш сырых ответов на диск (повторный запуск не дёргает API заново)
  - retry на 429 / 5xx
  - получение фильма сразу на двух языках одним классом-обёрткой

Использование:
    async with TmdbClient(api_key=..., cache_dir=...) as tmdb:
        films = await tmdb.popular_movies(pages=15)
        full = await tmdb.movie_full(film_id=27205)  # 'Inception'
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from pathlib import Path
from typing import Any

import httpx

log = logging.getLogger(__name__)

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"


class TmdbClient:
    """Async-клиент TMDB с кэшем и rate-limit."""

    def __init__(
        self,
        api_key: str,
        *,
        cache_dir: Path | str = "scripts/cache/tmdb",
        rate_limit_per_sec: float = 25.0,
        timeout: float = 20.0,
    ) -> None:
        if not api_key or len(api_key) < 10:
            raise ValueError("TMDB_API_KEY не задан или некорректен. Проверь .env")

        self.api_key = api_key
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._semaphore = asyncio.Semaphore(int(rate_limit_per_sec))
        self._client: httpx.AsyncClient | None = None
        self._timeout = timeout

    # ─── Контекстный менеджер ──────────────────────────────────────
    async def __aenter__(self) -> "TmdbClient":
        self._client = httpx.AsyncClient(
            base_url=TMDB_BASE,
            timeout=self._timeout,
            headers={"Accept": "application/json"},
        )
        return self

    async def __aexit__(self, *exc) -> None:
        if self._client:
            await self._client.aclose()

    # ─── Низкоуровневый запрос с кэшем и retry ──────────────────────
    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict:
        """GET с автокэшем и retry на 429/5xx."""
        params = {**(params or {}), "api_key": self.api_key}
        cache_key = self._cache_key(path, params)
        cached = self._read_cache(cache_key)
        if cached is not None:
            return cached

        assert self._client is not None, "use 'async with TmdbClient(...)'"

        async with self._semaphore:
            for attempt in range(5):
                try:
                    resp = await self._client.get(path, params=params)
                except httpx.RequestError as exc:
                    log.warning("tmdb network error %s, retry %s", exc, attempt + 1)
                    await asyncio.sleep(1 + attempt)
                    continue

                if resp.status_code == 429:
                    wait = int(resp.headers.get("Retry-After", "1"))
                    log.warning("tmdb rate-limit, wait %ss", wait)
                    await asyncio.sleep(wait)
                    continue

                if resp.status_code >= 500:
                    log.warning("tmdb 5xx %s, retry", resp.status_code)
                    await asyncio.sleep(1 + attempt)
                    continue

                if resp.status_code == 404:
                    return {}

                resp.raise_for_status()
                data = resp.json()
                self._write_cache(cache_key, data)
                return data

        raise RuntimeError(f"TMDB {path} failed after retries")

    # ─── Кэш ───────────────────────────────────────────────────────
    def _cache_key(self, path: str, params: dict) -> str:
        # api_key не должен попадать в имя файла
        safe_params = {k: v for k, v in params.items() if k != "api_key"}
        raw = f"{path}?{json.dumps(safe_params, sort_keys=True)}"
        digest = hashlib.md5(raw.encode()).hexdigest()[:12]
        safe_path = path.replace("/", "_").strip("_")
        return f"{safe_path}__{digest}.json"

    def _read_cache(self, key: str) -> dict | None:
        f = self.cache_dir / key
        if f.exists():
            try:
                return json.loads(f.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                f.unlink(missing_ok=True)
        return None

    def _write_cache(self, key: str, data: dict) -> None:
        f = self.cache_dir / key
        f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # ─── Высокоуровневые методы ────────────────────────────────────
    async def popular_movies(self, *, pages: int = 10, language: str = "en-US") -> list[dict]:
        """Топ популярных фильмов TMDB. Каждая страница = 20 фильмов."""
        results: list[dict] = []
        for page in range(1, pages + 1):
            data = await self._get(
                "/movie/popular", {"language": language, "page": page}
            )
            results.extend(data.get("results", []))
        return results

    async def movie_full(self, film_id: int, *, language: str) -> dict:
        """
        Полная инфа о фильме на одном языке + credits + images + keywords.
        TMDB позволяет дёрнуть всё одним запросом через append_to_response.
        """
        return await self._get(
            f"/movie/{film_id}",
            {
                "language": language,
                "append_to_response": "credits,external_ids,keywords",
            },
        )

    async def person_full(self, person_id: int, *, language: str) -> dict:
        return await self._get(
            f"/person/{person_id}",
            {"language": language, "append_to_response": "external_ids"},
        )

    async def genres(self, *, language: str = "en-US") -> list[dict]:
        data = await self._get("/genre/movie/list", {"language": language})
        return data.get("genres", [])

    # ─── Утилиты ───────────────────────────────────────────────────
    @staticmethod
    def image_url(path: str | None, size: str = "w500") -> str | None:
        if not path:
            return None
        return f"{TMDB_IMAGE_BASE}/{size}{path}"
