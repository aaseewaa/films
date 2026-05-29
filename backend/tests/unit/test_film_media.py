"""Вид медиа: фильм / мультфильм / сериал."""
from app.film_media import film_media_kind


def test_series_from_metadata():
    assert film_media_kind([], {"media_type": "tv"}) == "сериал"
    assert film_media_kind([], {"content_type": "series"}) == "сериал"


def test_animation_from_genres():
    assert film_media_kind(["Анимация"], {}) == "мультфильм"
    assert film_media_kind(["Animation"], {}) == "мультфильм"


def test_default_is_film():
    assert film_media_kind(["Драма"], {}) == "фильм"
