"""
Клиент Wikipedia MediaWiki API (вводные абзацы статей).

Использование:
    async with WikipediaClient() as wiki:
        text = await wiki.fetch_intro("en", "Steven_Spielberg")
        batch = await wiki.fetch_intros_batch("en", ["A", "B"])
"""
from __future__ import annotations

import asyncio
import logging
from urllib.parse import quote

import httpx

log = logging.getLogger(__name__)

WIKI_API = {
    "en": "https://en.wikipedia.org/w/api.php",
    "ru": "https://ru.wikipedia.org/w/api.php",
}

USER_AGENT = "FilmsDB-Diploma/0.1 (educational; contact: local-dev)"
BATCH_SIZE = 15
MAX_RETRIES = 6


class WikipediaClient:
    def __init__(self, *, pause_sec: float = 1.2) -> None:
        self._pause = pause_sec
        self._client: httpx.AsyncClient | None = None
        self.rate_limited = 0

    async def __aenter__(self) -> "WikipediaClient":
        self._client = httpx.AsyncClient(
            timeout=60.0,
            headers={"User-Agent": USER_AGENT},
        )
        return self

    async def __aexit__(self, *exc) -> None:
        if self._client:
            await self._client.aclose()

    async def _get(self, lang: str, params: dict) -> dict | None:
        assert self._client is not None
        lang = lang.lower()
        if lang not in WIKI_API:
            return None

        for attempt in range(MAX_RETRIES):
            resp = await self._client.get(WIKI_API[lang], params=params)
            if resp.status_code == 200:
                await asyncio.sleep(self._pause)
                return resp.json()

            if resp.status_code in (429, 503):
                self.rate_limited += 1
                retry_after = resp.headers.get("Retry-After")
                wait = float(retry_after) if retry_after and retry_after.isdigit() else min(
                    5 * (2**attempt), 120
                )
                log.warning(
                    "wikipedia %s: HTTP %s, пауза %.0fs (%d/%d)",
                    lang,
                    resp.status_code,
                    wait,
                    attempt + 1,
                    MAX_RETRIES,
                )
                await asyncio.sleep(wait)
                continue

            log.warning("wikipedia %s: HTTP %s %s", lang, resp.status_code, resp.text[:120])
            return None

        log.error("wikipedia %s: исчерпаны попытки (params=%s)", lang, params.get("action"))
        return None

    async def fetch_intro(self, lang: str, title: str) -> str | None:
        """Первый абзац одной статьи."""
        batch = await self.fetch_intros_batch(lang, [title])
        return batch.get(title.replace(" ", "_")) or batch.get(title)

    async def fetch_intros_batch(self, lang: str, titles: list[str]) -> dict[str, str]:
        """
        До BATCH_SIZE статей за один запрос.
        Ключи — нормализованные заголовки из ответа API.
        """
        if not titles:
            return {}

        normalized = [t.replace(" ", "_") for t in titles if t.strip()]
        result: dict[str, str] = {}

        for i in range(0, len(normalized), BATCH_SIZE):
            chunk = normalized[i : i + BATCH_SIZE]
            data = await self._get(
                lang,
                {
                    "action": "query",
                    "format": "json",
                    "prop": "extracts",
                    "explaintext": 1,
                    "exintro": 1,
                    "exsectionformat": "plain",
                    "redirects": 1,
                    "titles": "|".join(chunk),
                },
            )
            if not data:
                continue
            pages = (data.get("query") or {}).get("pages") or {}
            for page in pages.values():
                if page.get("missing"):
                    continue
                title_key = (page.get("title") or "").replace(" ", "_")
                extract = (page.get("extract") or "").strip()
                if not title_key or not extract:
                    continue
                for key in {title_key, title_key.replace("_", " ")}:
                    result[key] = extract
                norm = title_key.lower()
                for orig in chunk:
                    if orig.replace(" ", "_").lower() == norm:
                        result[orig] = extract
                        result[orig.replace(" ", "_")] = extract

        return result

    async def search_title(self, lang: str, query: str) -> str | None:
        """opensearch → лучший заголовок статьи или None."""
        data = await self._get(
            lang,
            {
                "action": "opensearch",
                "format": "json",
                "search": query,
                "limit": 1,
                "namespace": 0,
            },
        )
        if not data or len(data) < 2 or not data[1]:
            return None
        return data[1][0]

    @staticmethod
    def article_url(lang: str, title: str) -> str:
        host = "en.wikipedia.org" if lang == "en" else "ru.wikipedia.org"
        return f"https://{host}/wiki/{quote(title.replace(' ', '_'))}"
