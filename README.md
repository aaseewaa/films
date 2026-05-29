# FMW

Информационная система о кинематографе: поиск и подбор фильмов и персон, **граф влияний режиссёров**, **семантический поиск** (pgvector), журнал статей, коллекции, новинки и личный кабинет.

Дипломный проект. Исходный код: [github.com/aaseewaa/films](https://github.com/aaseewaa/films).

**Стек:** PostgreSQL 17 + pgvector · FastAPI · React 18 · TypeScript

---

## Возможности

| Область | Описание |
|--------|----------|
| Граф | Интерактивный граф влияний на главной; подграф режиссёра с настраиваемой глубиной |
| Поиск | Полнотекстовый и семантический поиск по сущностям (фильмы, персоны, статьи) |
| Каталог | Фильмы, жанры, карточки сущностей, рекомендации |
| Контент | Журнал статей, подборки, блок новинок / афиша |
| Пользователь | Регистрация, JWT, избранное, оценки, история просмотров |

Языки интерфейса и данных: **русский** и **английский**.

---

## Быстрый старт

Нужны: **PostgreSQL 17** с расширением **pgvector**, **Python 3.11+**, **Node.js 18+**.

### 1. База данных

Создайте пустую БД и примените схему из корня репозитория:

```bash
createdb films
psql films -f schema_actual.sql
```

Для `psql` используйте обычный URL PostgreSQL (без драйвера `asyncpg`). Данные для демо загружаются отдельно — см. [backend/scripts/README.md](backend/scripts/README.md).

### 2. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Создайте `backend/.env` из шаблона:

```bash
cp .env.example .env
# отредактируйте DATABASE_URL и SECRET_KEY
```

```bash
uvicorn app.main:app --reload
```

API: [http://localhost:8000](http://localhost:8000) · OpenAPI: [http://localhost:8000/docs](http://localhost:8000/docs)

Подробнее: [backend/README.md](backend/README.md).

### 3. Frontend

В **отдельном** терминале:

```bash
cd front
npm install
npm run dev
```

Сайт: [http://localhost:5173](http://localhost:5173). Запросы `/api/*` проксируются на backend (см. `front/vite.config.ts`).

Подробнее: [front/README.md](front/README.md).

### Проверка

- Главная (`/`) — граф режиссёров (нужны данные в БД).
- `/docs` на backend — список эндпоинтов.
- Автотесты backend (без полной БД): `cd backend && pytest -q tests/unit`.

---

## Структура репозитория

```
films_money_weed/
├── backend/           # FastAPI, ORM, бизнес-логика, REST API
│   ├── app/           #   api/, services/, models/, schemas/
│   ├── scripts/       #   загрузка данных (TMDB, Wikidata, эмбеддинги)
│   └── tests/         #   unit, integration, manual, performance
├── front/             # React + Vite + TypeScript
├── schema_actual.sql  # актуальная схема PostgreSQL (pg_dump)
├── docs/              # журнал разработки и вспомогательные заметки
├── graph-extend/      # архив: патчи расширения графа (Wikidata, semantic)
├── radial/            # архив: альтернативная вёрстка главной (радиальный граф)
└── images-loader/     # архив: скрипт загрузки backdrop/stills из TMDB
```

**Для запуска приложения** достаточно `backend/`, `front/` и настроенной БД. Папки `graph-extend/`, `radial/`, `images-loader/` — вспомогательные материалы и пошаговые инструкции; их содержимое либо уже перенесено в `backend/scripts` и `backend/app`, либо применяется вручную по README внутри папки.

---

## Документация

| Файл | Назначение |
|------|------------|
| [backend/README.md](backend/README.md) | API, переменные окружения, тесты |
| [front/README.md](front/README.md) | Фронтенд, структура `src/`, дизайн-токены |
| [backend/scripts/README.md](backend/scripts/README.md) | Загрузка и обновление данных в БД |
| [backend/tests/README.md](backend/tests/README.md) | Уровни тестирования |
| [docs/WEEKLY_REPORT.md](docs/WEEKLY_REPORT.md) | Журнал разработки, архитектурные решения (для защиты) |
| [docs/GIT_PREP.md](docs/GIT_PREP.md) | Git перед сдачей: что коммитить, что игнорировать |

---

## Архитектура (кратко)

- **Единая сущность** `entity` с дочерними таблицами `film`, `person`, `article`, `collection` — полиморфные связи, переводы, медиа, эмбеддинги через один `entity_id`.
- **Граф влияний** — таблица `director_influence`, API `/api/graph/...`.
- **Семантика** — эмбеддинги в pgvector (модель и размерность — в `backend/app/embedding_config.py`).

Схема БД: `schema_actual.sql`. Детали проектирования — в [docs/WEEKLY_REPORT.md](docs/WEEKLY_REPORT.md).

---

## Основные маршруты UI

| URL | Страница |
|-----|----------|
| `/` | Главная, граф влияний |
| `/films`, `/film/:id` | Каталог и карточка фильма |
| `/director/:id` | Карточка персоны (режиссёр и др.) |
| `/search` | Поиск |
| `/articles`, `/article/:slug` | Журнал |
| `/collections`, `/collection/:id` | Подборки |
| `/news` | Новинки |
| `/me`, `/me/favorites`, … | Личный кабинет |

---

## Лицензия и автор

Учебный проект. При использовании кода или данных третьих сторон (TMDB, Wikidata и др.) соблюдайте условия соответствующих API и лицензий.
