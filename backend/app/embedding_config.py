"""
Общие настройки семантического поиска (модель, префиксы, пороги, сбор текста).

Модель intfloat/multilingual-e5-small:
  - 384 измерения (как у старой MiniLM — менять тип vector в БД не нужно)
  - префиксы query: / passage: — запрос и документ в одном пространстве, но разных «ролях»
  - после смены модели: python -m scripts.generate_embeddings --force
"""
from __future__ import annotations

MODEL_NAME = "intfloat/multilingual-e5-small"
QUERY_PREFIX = "query: "
PASSAGE_PREFIX = "passage: "

# Ниже порога не показываем в семантическом поиске (0.38 ≈ 38% в UI)
MIN_SEMANTIC_SIMILARITY = 0.38

# Сколько фильмов из фильмографии добавляем в текст эмбеддинга персоны
PERSON_FILMOGRAPHY_LIMIT = 8


def build_film_passage_text(
    title: str | None,
    summary: str | None,
    description: str | None,
) -> str:
    """Текст документа для фильма (без префикса passage:)."""
    parts: list[str] = []
    if title:
        t = title.strip()
        parts.extend([t, t])

    body = (summary or description or "").strip()
    if body:
        parts.append(body[:1000])

    return " | ".join(parts) if parts else ""


def build_person_passage_text(
    *,
    title: str | None,
    summary: str | None,
    description: str | None,
    is_director: bool = False,
    is_actor: bool = False,
    birth_place: str | None = None,
    filmography_lines: list[str] | None = None,
) -> str:
    """Текст документа для персоны: роли, био, фильмография."""
    parts: list[str] = []

    roles: list[str] = []
    if is_director:
        roles.append("режиссёр")
    if is_actor:
        roles.append("актёр")
    if roles:
        parts.append(", ".join(roles))

    if title:
        t = title.strip()
        parts.extend([t, t])

    if birth_place:
        parts.append(birth_place.strip()[:200])

    body = (summary or description or "").strip()
    if body:
        parts.append(body[:800])

    if filmography_lines:
        parts.append("фильмы: " + "; ".join(filmography_lines[:PERSON_FILMOGRAPHY_LIMIT]))

    return " | ".join(parts) if parts else ""


def wrap_passage(text: str) -> str:
    if not text:
        return ""
    return PASSAGE_PREFIX + text


def wrap_query(text: str) -> str:
    q = text.strip()
    if not q:
        return ""
    return QUERY_PREFIX + q
