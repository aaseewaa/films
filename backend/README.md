# FMW — backend (API)

FastAPI + async SQLAlchemy + PostgreSQL. Часть [дипломного проекта FMW](../README.md).

## Быстрый старт

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # затем отредактируйте DATABASE_URL и SECRET_KEY
uvicorn app.main:app --reload
```

API: `http://localhost:8000` · OpenAPI: `/docs`

## Переменные окружения

Шаблон: [`.env.example`](.env.example). Скопируйте в `.env` и заполните.

| Переменная | Обязательно | Описание |
|------------|-------------|----------|
| `DATABASE_URL` | да | PostgreSQL + `asyncpg`, напр. `postgresql+asyncpg://user:pass@localhost:5432/films` |
| `SECRET_KEY` | да (в проде) | Секрет JWT; не используйте dev-значение на сервере |
| `CORS_ORIGINS` | нет | Origin фронта (`http://localhost:5173`) |
| `TMDB_API_KEY` | нет | Новинки через TMDB и скрипты загрузки |
| `APP_NAME`, `APP_DEBUG`, `JWT_EXPIRE_MINUTES`, … | нет | См. комментарии в `.env.example` |

## Схема БД

Из корня репозитория:

```bash
psql "$DATABASE_URL_SYNC" -f schema_actual.sql
```

(для `psql` используйте URL без `+asyncpg`, либо отдельную переменную с синхронным драйвером.)

## Фронтенд

```bash
cd front
npm install
npm run dev
```

Vite: `http://localhost:5173`, прокси `/api` → бэкенд.

Подробнее: [front/README.md](../front/README.md).

## Тесты

```bash
cd backend
source venv/bin/activate
pytest -q                  # все автотесты
pytest -q tests/unit       # модульные (без БД)
pytest -q -m integration   # REST API
pytest -q -m "not db"       # без проверки PostgreSQL
```

Запускайте из каталога `backend`. Структура и уровни — в [tests/README.md](tests/README.md).

| Папка | Уровень |
|-------|---------|
| `tests/unit/` | Модульный (pytest) |
| `tests/integration/` | Интеграционный (httpx + FastAPI) |
| `tests/manual/` | Функциональный (чек-листы) |
| `tests/performance/` | Нагрузочный (SQL, замеры) |

## Структура

- `app/api/` — тонкие роуты
- `app/services/` — бизнес-логика
- `app/schemas/` — Pydantic-ответы
- `app/models/` — ORM (схема БД, миграции/скрипты)
- `scripts/` — загрузка данных (не нужны для запуска API)
- `tests/` — автотесты и ручные чек-листы
