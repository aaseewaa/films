# Загрузчик кадров из фильмов

Догружает в БД для каждого фильма:
- **Основной backdrop** — широкий кадр на всю ширину карточки фильма (1280×720)
- **До 10 stills** — кадры из фильма для галереи в табе «Кадры» (780×x)

Источник — TMDB API endpoint `/movie/{id}/images`.

## Что в архиве

```
migration_backdrop.sql        ← SQL миграция (добавить колонку + enum)
tmdb_client_patch.py          ← новый метод для tmdb_client.py
load_tmdb_images.py           ← сам скрипт загрузки
```

## Шаги применения (по порядку!)

### Шаг 1 — миграция БД

Открой **pgAdmin**, подключись к БД `FilmsDB_diplom`, открой **Query Tool** и выполни **`migration_backdrop.sql`** целиком.

Что делает:
- Добавляет колонку `entity.primary_backdrop_url`
- Проверяет/добавляет `'backdrop'` и `'still'` в enum `media_role`
- Проверяет/добавляет `'tmdb'` в enum `media_source_kind`
- Идемпотентно — можно запускать несколько раз

В конце должна быть строка `primary_backdrop_url | text` в результате.

### Шаг 2 — обновить TMDB-клиент

Открой `backend/scripts/tmdb_client.py`.

Найди в классе `TmdbClient` метод `movie_full` или `top_rated_movies` (любой существующий async-метод).

**Сразу после него** вставь метод из файла `tmdb_client_patch.py`:

```python
async def movie_images(self, film_id: int) -> dict:
    """
    Возвращает все изображения фильма из TMDB.
    """
    return await self._get(
        f"/movie/{film_id}/images",
        {"include_image_language": "en,null"},
    )
```

Сохрани.

### Шаг 3 — положить скрипт

```bash
cp load_tmdb_images.py ~/Desktop/films_money_weed/backend/scripts/
```

### Шаг 4 — тестовый прогон (10 фильмов)

```bash
cd ~/Desktop/films_money_weed/backend
source venv/bin/activate
python -m scripts.load_tmdb_images --limit 10
```

Ожидаемый результат:
```
─── Loader кадров фильмов (TMDB images) ───
force=False, limit=10, pause=0.15s
к обработке фильмов: 10
[1/10] film id=... tmdb=...
  ✓ backdrop=yes stills=10
...
─── DONE ───
обработано фильмов:      10
с backdrop:              10
всего stills (кадров):   ~100
ошибок:                  0
```

Если **0 ошибок** — продолжаем. Если **ошибки** — пришли последние 20 строк лога.

### Шаг 5 — проверить в БД

В pgAdmin Query Tool:

```sql
-- Сколько фильмов получили backdrop
SELECT count(*) FROM entity 
WHERE entity_type='film' AND primary_backdrop_url IS NOT NULL;
-- Ожидаемо: 10 (после теста), потом 531 (после полного прогона)

-- Сколько всего кадров загружено
SELECT count(*) FROM entity_media WHERE role = 'still';
-- Ожидаемо: ~100 (после теста), ~5000 (после полного)

-- Один пример
SELECT e.id, e.primary_backdrop_url, et.title
FROM entity e
JOIN entity_translation et ON et.entity_id = e.id
  AND et.language_id = (SELECT id FROM language WHERE code='ru')
WHERE e.primary_backdrop_url IS NOT NULL
LIMIT 3;
```

Открой `primary_backdrop_url` в браузере — должен показать **широкий кадр** из фильма.

### Шаг 6 — полный прогон

Если тест прошёл — гонишь все 531 фильм:

```bash
python -m scripts.load_tmdb_images
```

Время: **~2-3 минуты** на 531 фильм (0.15 сек пауза + ~0.2 сек на запрос).

После окончания должна быть статистика:
```
обработано фильмов:      531
с backdrop:              510-530   (некоторые фильмы могут не иметь backdrop в TMDB)
всего stills (кадров):   4000-5000
ошибок:                  0-5       (редкие отказы TMDB, не критично)
```

## Что после

Когда кадры загружены — приходи, я напишу:
1. **Endpoint** `GET /api/film/{id}/images` для отдачи галереи
2. **Endpoint** `GET /api/entity/{id}` обновим — добавим `backdrop_url` в ответ
3. **FilmPage.tsx** с большим backdrop наверху, табами, sticky-шапкой

## Возможные проблемы

### `column "primary_backdrop_url" of relation "entity" already exists`
Это значит миграция уже запущена. Не проблема — `IF NOT EXISTS` защищает. Просто пропускай.

### `invalid input value for enum media_role: "backdrop"`
Значит ALTER TYPE не сработал. Проверь в pgAdmin:
```sql
SELECT enumlabel FROM pg_enum WHERE enumtypid = 'media_role'::regtype;
```
Должны быть `poster`, `backdrop`, `still`, `profile`, и т.д.

### Очень медленно
Скрипт делает 1 запрос на фильм. 531 фильм × 0.35 сек = **3 минуты**. Это нормально.

### TMDB returns 429 (rate limit)
Увеличь паузу: `python -m scripts.load_tmdb_images --pause 0.5`

### `no backdrops в TMDB` для некоторых фильмов
Это нормально — у некоторых старых/малоизвестных фильмов TMDB не имеет картинок. Эти фильмы останутся без backdrop, в карточке потом фолбэк на постер.
