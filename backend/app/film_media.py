"""Определение вида медиа для фильма (фильм / мультфильм / сериал)."""
from __future__ import annotations


def film_media_kind(genres: list[str], extra: dict | None) -> str:
    meta = extra or {}
    media = str(meta.get("media_type") or meta.get("content_type") or "").lower()
    if media in ("tv", "series", "сериал"):
        return "сериал"
    blob = " ".join(genres).lower()
    if "анимац" in blob or "animation" in blob:
        return "мультфильм"
    return "фильм"
