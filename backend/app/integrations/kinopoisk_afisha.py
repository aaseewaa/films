"""
Парсер афиши Кинопоиска: фильмы в прокате в городе + ссылки на билеты.

URL: https://www.kinopoisk.ru/afisha/city/{kp_city_id}/
Кэш на диске (TTL), чтобы не дёргать сайт на каждый запрос.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from app.integrations.city_ref import CityRef

log = logging.getLogger(__name__)

KP_BASE = "https://www.kinopoisk.ru"
FILM_HREF_RE = re.compile(r"/film/(\d+)/")
FILM_ID_JSON_RE = re.compile(
    r'"(?:filmId|kpFilmId|movieId)":\s*(\d{4,9})',
)
CINEMA_HREF_RE = re.compile(r"/afisha/city/\d+/cinema/(\d+)/")
# Служебные id Кинопоиска — не фильмы
SKIP_KP_IDS = frozenset({1, 2, 3, 4, 5, 10, 100, 1000})

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}


@dataclass
class KinopoiskAfishaFilm:
    kinopoisk_id: int
    title: str
    ticket_url: str
    cinemas: list[str] = field(default_factory=list)
    tmdb_id: int | None = None


class KinopoiskAfishaParser:
    """HTTP + HTML-парсинг страницы афиши по городу."""

    def __init__(
        self,
        *,
        cache_dir: Path | str = "app/cache/kinopoisk",
        cache_ttl_sec: int = 6 * 3600,
        timeout: float = 25.0,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl_sec = cache_ttl_sec
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "KinopoiskAfishaParser":
        self._client = httpx.AsyncClient(
            headers=DEFAULT_HEADERS,
            timeout=self._timeout,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, *exc) -> None:
        if self._client:
            await self._client.aclose()

    def _cache_path(self, city: CityRef) -> Path:
        digest = hashlib.md5(city.kp_city_id.encode()).hexdigest()[:10]
        return self.cache_dir / f"afisha_city_{city.kp_city_id}_{digest}.json"

    def _read_cache(self, path: Path) -> list[KinopoiskAfishaFilm] | None:
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            path.unlink(missing_ok=True)
            return None
        if time.time() - payload.get("fetched_at", 0) > self.cache_ttl_sec:
            return None
        return [
            KinopoiskAfishaFilm(
                kinopoisk_id=int(item["kinopoisk_id"]),
                title=item["title"],
                ticket_url=item["ticket_url"],
                cinemas=item.get("cinemas") or [],
            )
            for item in payload.get("items", [])
        ]

    def _write_cache(self, path: Path, items: list[KinopoiskAfishaFilm]) -> None:
        path.write_text(
            json.dumps(
                {
                    "fetched_at": time.time(),
                    "items": [
                        {
                            "kinopoisk_id": f.kinopoisk_id,
                            "title": f.title,
                            "ticket_url": f.ticket_url,
                            "cinemas": f.cinemas,
                        }
                        for f in items
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    async def fetch_city_afisha(self, city: CityRef) -> list[KinopoiskAfishaFilm]:
        cache_path = self._cache_path(city)
        cached = self._read_cache(cache_path)
        if cached is not None:
            return cached

        assert self._client is not None
        url = f"{KP_BASE}/afisha/city/{city.kp_city_id}/"
        log.info("kinopoisk afisha fetch %s", url)

        items: list[KinopoiskAfishaFilm] = []
        urls = [
            f"{KP_BASE}/afisha/city/{city.kp_city_id}/",
            f"{KP_BASE}/afisha/{city.slug}/",
        ]
        for url in urls:
            try:
                resp = await self._client.get(url)
                resp.raise_for_status()
                parsed = parse_afisha_html(resp.text, city=city)
                if parsed:
                    items = parsed
                    log.info("kinopoisk afisha ok %s (%d films)", url, len(items))
                    break
                log.info("kinopoisk afisha no films in %s (len=%d)", url, len(resp.text))
            except httpx.HTTPError as exc:
                log.warning("kinopoisk afisha failed %s: %s", url, exc)

        if items:
            self._write_cache(cache_path, items)
        elif cache_path.exists():
            cache_path.unlink(missing_ok=True)
        return items


def parse_afisha_html(html: str, *, city: CityRef) -> list[KinopoiskAfishaFilm]:
    """
    Извлекает фильмы и кинотеатры со страницы афиши.
    Работает и по сырому HTML (ссылки /film/{id}/), и через BeautifulSoup.
    """
    by_id: dict[int, KinopoiskAfishaFilm] = {}
    cinema_names: dict[str, str] = {}

    soup = BeautifulSoup(html, "html.parser")

    for a in soup.find_all("a", href=True):
        href = a["href"]
        cinema_m = CINEMA_HREF_RE.search(href)
        if cinema_m:
            name = _clean_text(a.get_text())
            if name:
                cinema_names[cinema_m.group(1)] = name
            continue

        film_m = FILM_HREF_RE.search(href)
        if not film_m:
            continue
        kp_id = int(film_m.group(1))
        if kp_id in SKIP_KP_IDS:
            continue
        title = _clean_text(a.get_text()) or f"Фильм {kp_id}"
        _upsert_film(by_id, kp_id=kp_id, title=title, city=city)

    # Дополнительно — regex по всему HTML (SPA часто отдаёт id только в JSON)
    for kp_id in {int(m.group(1)) for m in FILM_HREF_RE.finditer(html)}:
        _upsert_film(by_id, kp_id=kp_id, title=f"Фильм {kp_id}", city=city)

    for m in FILM_ID_JSON_RE.finditer(html):
        kp_id = int(m.group(1))
        if kp_id in SKIP_KP_IDS:
            continue
        _upsert_film(by_id, kp_id=kp_id, title=f"Фильм {kp_id}", city=city)

    # Привязка кинотеатров к фильмам по близости в тексте (эвристика)
    _attach_cinemas_from_blocks(soup, by_id, cinema_names)

    return list(by_id.values())


def _upsert_film(
    by_id: dict[int, KinopoiskAfishaFilm],
    *,
    kp_id: int,
    title: str,
    city: CityRef,
) -> None:
    ticket_url = f"{KP_BASE}/film/{kp_id}/afisha/city/{city.kp_city_id}/"
    prev = by_id.get(kp_id)
    if prev is None or (len(title) > len(prev.title) and not title.startswith("Фильм ")):
        by_id[kp_id] = KinopoiskAfishaFilm(
            kinopoisk_id=kp_id,
            title=title,
            ticket_url=ticket_url,
            cinemas=prev.cinemas if prev else [],
        )


def _attach_cinemas_from_blocks(
    soup: BeautifulSoup,
    films: dict[int, KinopoiskAfishaFilm],
    cinema_names: dict[str, str],
) -> None:
    """Пытается найти названия кинотеатров рядом с карточкой фильма."""
    for block in soup.select("[class*='cinema'], [class*='schedule'], [data-test-id]"):
        block_text = block.get_text(" ", strip=True)
        block_films = {int(m.group(1)) for m in FILM_HREF_RE.finditer(str(block))}
        block_cinemas: list[str] = []
        for m in CINEMA_HREF_RE.finditer(str(block)):
            cid = m.group(1)
            if cid in cinema_names:
                block_cinemas.append(cinema_names[cid])
        if not block_films or not block_cinemas:
            continue
        for fid in block_films:
            if fid in films:
                merged = list(dict.fromkeys(films[fid].cinemas + block_cinemas))
                films[fid].cinemas = merged[:8]
        if block_cinemas and not block_films and len(block_text) < 120:
            pass  # только кинотеатр без фильма — пропускаем


def _clean_text(value: str) -> str:
    text = re.sub(r"\s+", " ", value or "").strip()
    if len(text) < 2 or text.isdigit():
        return ""
    skip = {"купить билет", "билеты", "сеансы", "все сеансы", "подробнее"}
    if text.lower() in skip:
        return ""
    return text
