"""
ПАТЧ для backend/scripts/tmdb_client.py.

Добавь этот метод в класс TmdbClient (рядом с movie_full, top_rated_movies).
Если уже есть — пропусти.
"""


# ─── НОВЫЙ МЕТОД ─── вставь в класс TmdbClient
async def movie_images(self, film_id: int) -> dict:
    """
    Возвращает все изображения фильма из TMDB.

    Структура ответа:
      {
        "id": 123,
        "backdrops": [
          {
            "file_path": "/abc.jpg",
            "aspect_ratio": 1.778,
            "width": 1920,
            "height": 1080,
            "vote_average": 5.4,
            "vote_count": 12,
            "iso_639_1": null    # null = без языка (универсальный)
          },
          ...
        ],
        "posters": [...]  # их не используем, у нас уже есть
      }

    include_image_language=en,null — берём английские + универсальные
    (без локализованных текстов на постерах).
    """
    return await self._get(
        f"/movie/{film_id}/images",
        {"include_image_language": "en,null"},
    )
