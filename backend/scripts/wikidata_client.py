"""
Клиент Wikidata Query Service (SPARQL).

Использование:
    async with WikidataClient() as wd:
        rows = await wd.director_influences(min_films=2)
        for row in rows:
            print(row["source_imdb"], row["target_imdb"])
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from pathlib import Path

import httpx

log = logging.getLogger(__name__)

WDQS_ENDPOINT = "https://query.wikidata.org/sparql"


# ─── SPARQL-запрос ────────────────────────────────────────────────
# Берём пары (source режиссёр, target режиссёр) где:
#  - target.influencedBy = source (P737)
#  - оба являются режиссёрами (P106 = Q2526255 film director)
#  - оба имеют IMDb ID (P345) — нужно для маппинга к нашей БД
#  - target снял минимум `min_films` фильмов (фильтр шума)
#
# wikibase:label достаёт читаемые имена для логов и debug.

SPARQL_INFLUENCES = """
SELECT DISTINCT ?source ?sourceLabel ?sourceImdb
                ?target ?targetLabel ?targetImdb
WHERE {
  ?target wdt:P737 ?source .

  # Оба должны быть кинорежиссёрами
  ?target wdt:P106 wd:Q2526255 .
  ?source wdt:P106 wd:Q2526255 .

  # У обоих должен быть IMDb id — без него к нашей БД не привязать
  ?target wdt:P345 ?targetImdb .
  ?source wdt:P345 ?sourceImdb .

  # Фильтр: имена должны начинаться с "nm" (это IMDb id персон,
  # а не фильмов, у которых формат "tt0000000")
  FILTER(STRSTARTS(?targetImdb, "nm"))
  FILTER(STRSTARTS(?sourceImdb, "nm"))

  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
LIMIT 5000
"""


class WikidataClient:
    """Async-клиент Wikidata SPARQL с кэшем."""

    def __init__(
        self,
        *,
        cache_dir: Path | str = "scripts/cache/wikidata",
        timeout: float = 90.0,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._client: httpx.AsyncClient | None = None
        self._timeout = timeout

    async def __aenter__(self) -> "WikidataClient":
        # User-Agent обязателен для WDQS, иначе блокируют
        self._client = httpx.AsyncClient(
            timeout=self._timeout,
            headers={
                "Accept": "application/sparql-results+json",
                "User-Agent": "FilmsDB-Diploma/0.1 (educational; student project)",
            },
        )
        return self

    async def __aexit__(self, *exc) -> None:
        if self._client:
            await self._client.aclose()

    async def _query(self, sparql: str) -> list[dict]:
        """Выполнить SPARQL-запрос с кэшем. Возвращает bindings."""
        digest = hashlib.md5(sparql.encode()).hexdigest()[:12]
        cache_file = self.cache_dir / f"query_{digest}.json"

        if cache_file.exists():
            log.info("wikidata: using cached result %s", cache_file.name)
            cached_data = json.loads(cache_file.read_text(encoding="utf-8"))
            return cached_data.get("results", {}).get("bindings", [])

        assert self._client is not None
        log.info("wikidata: running SPARQL query (this may take 30-60s)")

        for attempt in range(3):
            try:
                resp = await self._client.post(
                    WDQS_ENDPOINT,
                    data={"query": sparql, "format": "json"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    cache_file.write_text(
                        json.dumps(data, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    return data.get("results", {}).get("bindings", [])
                elif resp.status_code in (429, 503):
                    wait = 5 * (attempt + 1)
                    log.warning(
                        "wikidata: rate-limit/overload (%s), wait %ss",
                        resp.status_code, wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    log.error("wikidata: %s %s", resp.status_code, resp.text[:200])
                    resp.raise_for_status()
            except httpx.RequestError as exc:
                log.warning("wikidata: network error %s, attempt %s", exc, attempt + 1)
                await asyncio.sleep(5)

        raise RuntimeError("Wikidata query failed after 3 retries")

    async def director_influences(self) -> list[dict[str, str]]:
        """
        Возвращает список словарей вида:
            {
              "source_imdb": "nm0000033",   # IMDb id режиссёра-источника
              "source_label": "Alfred Hitchcock",
              "source_qid": "Q7374",         # Wikidata Q-id
              "target_imdb": "nm0000229",
              "target_label": "Steven Spielberg",
              "target_qid": "Q8877",
            }
        """
        bindings = await self._query(SPARQL_INFLUENCES)
        result: list[dict[str, str]] = []
        for row in bindings:
            try:
                # SPARQL JSON: каждое значение — dict с "value"
                source_uri = row["source"]["value"]  # http://www.wikidata.org/entity/Qxxx
                target_uri = row["target"]["value"]
                result.append({
                    "source_qid": source_uri.rsplit("/", 1)[-1],
                    "source_label": row["sourceLabel"]["value"],
                    "source_imdb": row["sourceImdb"]["value"],
                    "target_qid": target_uri.rsplit("/", 1)[-1],
                    "target_label": row["targetLabel"]["value"],
                    "target_imdb": row["targetImdb"]["value"],
                })
            except KeyError:
                continue
        return result
