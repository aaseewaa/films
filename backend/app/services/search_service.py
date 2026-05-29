"""
Сервис поиска: гибридный (fulltext + fuzzy).

Архитектура:
  1. fulltext_search — через tsvector + ts_rank, морфологический поиск
  2. fuzzy_search — через pg_trgm, для опечаток и частичных совпадений
  3. hybrid_search — комбинирует оба, fallback на fuzzy если fulltext пуст

Особенности:
  - Автодетекция языка запроса (ru / en) для правильного search_config
  - Адаптивный порог similarity: 0.2 для кириллицы, 0.3 для латиницы
  - word_similarity (оператор %>) для длинных названий — компенсирует
    разницу длин запроса и поля
"""
from __future__ import annotations

import re
from typing import Literal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


# ─── Утилиты детекции языка и скрипта ─────────────────────────────

def has_cyrillic(s: str) -> bool:
    """Содержит ли строка кириллические символы."""
    return any("\u0400" <= ch <= "\u04FF" for ch in s)


def detect_language(query: str) -> Literal["ru", "en"]:
    """Простой детектор: если есть кириллица — ru, иначе en."""
    return "ru" if has_cyrillic(query) else "en"


def _normalize_match_text(s: str) -> str:
    """Та же нормализация, что в SQL (_NORM_TITLE_SQL), для ранжирования в Python."""
    s = s.lower()
    for ch in "-–—":
        s = s.replace(ch, " ")
    s = re.sub(r"[^а-яёa-z0-9]+", " ", s)
    return " ".join(s.split())


def fuzzy_threshold(query: str) -> float:
    """Адаптивный порог similarity под скрипт запроса."""
    base = 0.2 if has_cyrillic(query) else 0.3
    if len(_normalize_match_text(query).split()) >= 2:
        return min(base, 0.12)
    return base


def _rank_score(query: str, hit: dict) -> float:
    """
    Поднимает точные и почти точные совпадения по имени/названию.
    Иначе «София Коппола» проигрывает «Фрэнсис Форд Коппола» по ts_rank.
    """
    base = float(hit.get("score") or 0)
    qn = _normalize_match_text(query)
    tn = _normalize_match_text(hit.get("title") or "")
    if not qn or not tn:
        return base

    if qn == tn:
        return base + 1000.0

    q_tokens = qn.split()
    if q_tokens and all(tok in tn.split() or tok in tn for tok in q_tokens):
        return base + 200.0

    if len(q_tokens) >= 2 and q_tokens[0] in tn and q_tokens[-1] in tn:
        return base + 120.0

    if hit.get("entity_type") == "person" and len(q_tokens) >= 2 and q_tokens[-1] in tn:
        return base + 15.0

    return base


def get_search_config(lang: str) -> str:
    """Маппинг 'ru'/'en' в конфигурацию tsvector."""
    return {"ru": "russian", "en": "english"}.get(lang, "simple")


# Нормализация для сравнения названий: дефисы → пробелы, нижний регистр.
_NORM_TITLE_SQL = """
    trim(both ' ' from regexp_replace(
        lower(translate({field}, '-–—', '   ')),
        '[^а-яёa-z0-9]+', ' ', 'g'
    ))
"""


# ─── Сервис поиска ────────────────────────────────────────────────


class SearchService:
    """Гибридный поиск по entity_translation."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def hybrid_search(
        self,
        *,
        query: str,
        lang: str | None = None,
        entity_type: str | None = None,
        limit: int = 20,
        offset: int = 0,
        genre_code: str | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
    ) -> dict:
        """
        Гибридный поиск.

        Стратегия:
          1. Запускаем fulltext (морфологический)
          2. Если результатов мало (<3) — добавляем fuzzy и объединяем
          3. Каждый результат имеет match_type: fulltext / fuzzy / exact

        Возвращает dict готовый для SearchResponse.
        """
        if not query or not query.strip():
            return {
                "query": query,
                "detected_language": lang or "en",
                "items": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
                "used_strategies": [],
            }

        query = query.strip()
        detected_lang = lang or detect_language(query)

        used_strategies: list[str] = []
        fetch_lim = limit + offset + 30
        pool: dict[int, dict] = {}

        def _absorb(hits: list[dict]) -> None:
            for h in hits:
                eid = h["entity_id"]
                prev = pool.get(eid)
                if prev is None or h["score"] > prev["score"]:
                    pool[eid] = h

        # Шаг 0: триграммы по названию
        title_hits = await self._title_search(
            query=query,
            lang=detected_lang,
            entity_type=entity_type,
            genre_code=genre_code,
            year_from=year_from,
            year_to=year_to,
            limit=fetch_lim,
        )
        if title_hits:
            used_strategies.append("title")
        _absorb(title_hits)

        # Шаг 1: полнотекстовый
        fulltext_hits = await self._fulltext_search(
            query=query,
            lang=detected_lang,
            entity_type=entity_type,
            genre_code=genre_code,
            year_from=year_from,
            year_to=year_to,
            limit=fetch_lim,
        )
        if fulltext_hits:
            used_strategies.append("fulltext")
        _absorb(fulltext_hits)

        # Шаг 2: fuzzy всегда — опечатки («коппала» / «коппола»)
        fuzzy_hits = await self._fuzzy_search(
            query=query,
            lang=detected_lang,
            entity_type=entity_type,
            genre_code=genre_code,
            year_from=year_from,
            year_to=year_to,
            limit=fetch_lim,
            exclude_ids=set(),
        )
        if fuzzy_hits:
            used_strategies.append("fuzzy")
        _absorb(fuzzy_hits)

        # Шаг 3: если по-русски пусто — пробуем en (имя в латинице в БД)
        if not pool and detected_lang == "ru":
            for alt_lang in ("en",):
                _absorb(
                    await self._title_search(
                        query=query,
                        lang=alt_lang,
                        entity_type=entity_type,
                        genre_code=genre_code,
                        year_from=year_from,
                        year_to=year_to,
                        limit=fetch_lim,
                    )
                )
                _absorb(
                    await self._fuzzy_search(
                        query=query,
                        lang=alt_lang,
                        entity_type=entity_type,
                        genre_code=genre_code,
                        year_from=year_from,
                        year_to=year_to,
                        limit=fetch_lim,
                        exclude_ids=set(),
                    )
                )
            if pool:
                used_strategies.append("lang_en_fallback")

        merged = list(pool.values())
        for h in merged:
            h["score"] = _rank_score(query, h)
        merged.sort(key=lambda h: h["score"], reverse=True)

        total = len(merged)
        items = merged[offset : offset + limit]

        return {
            "query": query,
            "detected_language": detected_lang,
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
            "used_strategies": used_strategies,
        }

    # ─── Поиск по названию (нормализация + trigram) ─────────────
    async def _title_search(
        self,
        *,
        query: str,
        lang: str,
        entity_type: str | None,
        genre_code: str | None,
        year_from: int | None,
        year_to: int | None,
        limit: int,
    ) -> list[dict]:
        norm_q = _NORM_TITLE_SQL.format(field=":q")
        norm_title = _NORM_TITLE_SQL.format(field="et.title")
        threshold = fuzzy_threshold(query)

        sql = f"""
            SELECT
                e.id              AS entity_id,
                e.entity_type::text AS entity_type,
                et.title,
                et.summary,
                e.primary_image_url AS img_primary,
                e.thumbnail_url     AS img_thumb,
                f.release_year,
                p.is_director,
                p.is_actor,
                GREATEST(
                    similarity({norm_q}, {norm_title}),
                    word_similarity({norm_q}, {norm_title}),
                    word_similarity({norm_title}, {norm_q})
                ) AS score,
                'exact' AS match_type
            FROM entity_translation et
            JOIN entity e ON e.id = et.entity_id
            JOIN language l ON l.id = et.language_id
            LEFT JOIN film   f ON f.id = e.id AND e.entity_type = 'film'
            LEFT JOIN person p ON p.id = e.id AND e.entity_type = 'person'
            WHERE l.code = :lang
              AND e.status = 'published'
              AND GREATEST(
                    similarity({norm_q}, {norm_title}),
                    word_similarity({norm_q}, {norm_title}),
                    word_similarity({norm_title}, {norm_q})
                  ) > :threshold
        """
        params: dict = {"q": query, "lang": lang, "threshold": threshold}

        if entity_type:
            sql += " AND e.entity_type::text = :etype"
            params["etype"] = entity_type
        if year_from:
            sql += " AND (f.release_year IS NULL OR f.release_year >= :yfrom)"
            params["yfrom"] = year_from
        if year_to:
            sql += " AND (f.release_year IS NULL OR f.release_year <= :yto)"
            params["yto"] = year_to
        if genre_code:
            sql += """
                AND EXISTS (
                  SELECT 1 FROM entity_taxonomy ex
                  JOIN taxonomy_term tt ON tt.id = ex.term_id
                  WHERE ex.entity_id = e.id AND tt.code = :gcode
                )
            """
            params["gcode"] = genre_code

        sql += " ORDER BY score DESC LIMIT :lim"
        params["lim"] = limit

        result = await self.db.execute(text(sql), params)
        return [self._row_to_hit(r) for r in result.mappings().all()]

    # ─── Fulltext через tsvector ────────────────────────────────
    async def _fulltext_search(
        self,
        *,
        query: str,
        lang: str,
        entity_type: str | None,
        genre_code: str | None,
        year_from: int | None,
        year_to: int | None,
        limit: int,
    ) -> list[dict]:
        config = get_search_config(lang)

        # Индекс search_tsv строится по et.search_config (часто 'simple'),
        # поэтому матчим и по конфигу строки, и по языковому конфигу запроса.
        sql = """
            SELECT
                e.id              AS entity_id,
                e.entity_type::text AS entity_type,
                et.title,
                et.summary,
                e.primary_image_url AS img_primary,
                e.thumbnail_url     AS img_thumb,
                f.release_year,
                p.is_director,
                p.is_actor,
                GREATEST(
                    ts_rank(et.search_tsv, plainto_tsquery(et.search_config, :q)),
                    ts_rank(et.search_tsv, plainto_tsquery(:cfg, :q))
                ) AS score,
                'fulltext' AS match_type
            FROM entity_translation et
            JOIN entity e ON e.id = et.entity_id
            JOIN language l ON l.id = et.language_id
            LEFT JOIN film   f ON f.id = e.id AND e.entity_type = 'film'
            LEFT JOIN person p ON p.id = e.id AND e.entity_type = 'person'
            WHERE l.code = :lang
              AND e.status = 'published'
              AND (
                et.search_tsv @@ plainto_tsquery(et.search_config, :q)
                OR et.search_tsv @@ plainto_tsquery(:cfg, :q)
              )
        """
        params: dict = {"cfg": config, "q": query, "lang": lang}

        if entity_type:
            sql += " AND e.entity_type::text = :etype"
            params["etype"] = entity_type
        if year_from:
            sql += " AND (f.release_year IS NULL OR f.release_year >= :yfrom)"
            params["yfrom"] = year_from
        if year_to:
            sql += " AND (f.release_year IS NULL OR f.release_year <= :yto)"
            params["yto"] = year_to
        if genre_code:
            sql += """
                AND EXISTS (
                  SELECT 1 FROM entity_taxonomy ex
                  JOIN taxonomy_term tt ON tt.id = ex.term_id
                  WHERE ex.entity_id = e.id AND tt.code = :gcode
                )
            """
            params["gcode"] = genre_code

        sql += " ORDER BY score DESC LIMIT :lim"
        params["lim"] = limit

        result = await self.db.execute(text(sql), params)
        return [self._row_to_hit(r) for r in result.mappings().all()]

    # ─── Fuzzy через pg_trgm ────────────────────────────────────
    async def _fuzzy_search(
        self,
        *,
        query: str,
        lang: str,
        entity_type: str | None,
        genre_code: str | None,
        year_from: int | None,
        year_to: int | None,
        limit: int,
        exclude_ids: set[int],
    ) -> list[dict]:
        # Чуть ниже порог, чем у title — подхватываем слабые совпадения по названию/описанию.
        threshold = fuzzy_threshold(query) * 0.75
        norm_q = _NORM_TITLE_SQL.format(field=":q")
        norm_title = _NORM_TITLE_SQL.format(field="et.title")
        norm_summary = _NORM_TITLE_SQL.format(field="COALESCE(et.summary, '')")

        sql = f"""
            SELECT
                e.id              AS entity_id,
                e.entity_type::text AS entity_type,
                et.title,
                et.summary,
                e.primary_image_url AS img_primary,
                e.thumbnail_url     AS img_thumb,
                f.release_year,
                p.is_director,
                p.is_actor,
                GREATEST(
                    similarity({norm_q}, {norm_title}),
                    word_similarity({norm_q}, {norm_title}),
                    word_similarity({norm_title}, {norm_q}),
                    similarity({norm_q}, {norm_summary})
                ) AS score,
                'fuzzy' AS match_type
            FROM entity_translation et
            JOIN entity e ON e.id = et.entity_id
            JOIN language l ON l.id = et.language_id
            LEFT JOIN film   f ON f.id = e.id AND e.entity_type = 'film'
            LEFT JOIN person p ON p.id = e.id AND e.entity_type = 'person'
            WHERE l.code = :lang
              AND e.status = 'published'
              AND GREATEST(
                    similarity({norm_q}, {norm_title}),
                    word_similarity({norm_q}, {norm_title}),
                    word_similarity({norm_title}, {norm_q}),
                    similarity({norm_q}, {norm_summary})
                  ) > :threshold
        """
        params: dict = {"q": query, "lang": lang, "threshold": threshold}

        if exclude_ids:
            sql += " AND e.id != ALL(:exclude)"
            params["exclude"] = list(exclude_ids)
        if entity_type:
            sql += " AND e.entity_type::text = :etype"
            params["etype"] = entity_type
        if year_from:
            sql += " AND (f.release_year IS NULL OR f.release_year >= :yfrom)"
            params["yfrom"] = year_from
        if year_to:
            sql += " AND (f.release_year IS NULL OR f.release_year <= :yto)"
            params["yto"] = year_to
        if genre_code:
            sql += """
                AND EXISTS (
                  SELECT 1 FROM entity_taxonomy ex
                  JOIN taxonomy_term tt ON tt.id = ex.term_id
                  WHERE ex.entity_id = e.id AND tt.code = :gcode
                )
            """
            params["gcode"] = genre_code

        sql += " ORDER BY score DESC LIMIT :lim"
        params["lim"] = limit

        result = await self.db.execute(text(sql), params)
        return [self._row_to_hit(r) for r in result.mappings().all()]

    # ─── Маппинг строки в SearchHit-словарь ──────────────────────
    @staticmethod
    def _row_to_hit(row) -> dict:
        return {
            "entity_id": row["entity_id"],
            "entity_type": row["entity_type"],
            "title": row["title"],
            "summary": row["summary"],
            "images": {
                "primary": row["img_primary"],
                "thumbnail": row["img_thumb"],
            },
            "release_year": row.get("release_year"),
            "is_director": row.get("is_director"),
            "is_actor": row.get("is_actor"),
            "score": float(row["score"]) if row["score"] else 0.0,
            "match_type": row["match_type"],
        }
