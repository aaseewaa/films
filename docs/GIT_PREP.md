# Git перед сдачей диплома (FMW)

Краткий чеклист: что **не** попадает в репозиторий, что **нужно** закоммитить, как разбить историю.

---

## Не коммитить

| Путь / тип | Почему |
|------------|--------|
| `backend/.env`, `front/.env` | Секреты и пароли БД |
| `backend/venv/`, `.venv/` | Виртуальное окружение |
| `node_modules/`, `front/dist/`, `front/.vite/` | Сборка и зависимости |
| `__pycache__/`, `*.pyc`, `.pytest_cache/` | Кэш Python / pytest |
| `backend/scripts/cache/` | Кэш ответов TMDB (большие JSON) |
| `uploads/`, `backend/uploads/` | Аватары пользователей |
| `.cursor/`, `.DS_Store` | IDE / macOS |

Всё перечисленное уже в [`.gitignore`](../.gitignore). Шаблон настроек: `backend/.env.example` — **можно и нужно** коммитить.

Проверка перед `git add`:

```bash
git status
git check-ignore -v backend/.env backend/.pytest_cache front/node_modules
```

Если что-то из «не коммитить» уже в индексе (попало раньше):

```bash
git rm -r --cached backend/.pytest_cache   # пример
git rm --cached backend/.env               # если случайно добавили
```

---

## Что должно быть в репозитории

- `README.md`, `backend/README.md`, `front/README.md`
- `backend/.env.example`, `schema_actual.sql`
- `backend/app/`, `backend/tests/`, `backend/conftest.py`, `backend/pytest.ini`
- `front/src/`, `front/package.json`, `front/package-lock.json`
- `docs/` (отчёт, этот файл)
- Скрипты `backend/scripts/` (без `scripts/cache/`)

---

## Рекомендуемые коммиты (порядок)

Один свалочный коммит на защите хуже, чем 3–5 осмысленных. Пример:

```bash
# 1. Документация и шаблон окружения
git add README.md backend/README.md front/README.md backend/.env.example docs/
git commit -m "docs: корневой README, FMW, .env.example"

# 2. Тесты backend
git add backend/pytest.ini backend/conftest.py backend/tests/
git commit -m "test: структура pytest (unit, integration, manual)"

# 3. Backend — фичи и рефакторинг
git add backend/app/ backend/scripts/article_link_rules.py backend/scripts/README.md
git commit -m "feat(backend): API, security, film media, article links"

# 4. Frontend
git add front/
git commit -m "feat(front): страницы, граф, NotFound, типы API"

# 5. Остальное (если есть)
git status
```

Подставьте свои сообщения под фактический diff. Перед каждым `git add` смотрите `git diff --stat`.

---

## Перед push / сдачей

```bash
cd backend && source venv/bin/activate && pytest -q tests/unit
cd ../front && npm run build
cd .. && git status   # нет лишних untracked вроде .pytest_cache
```

Убедитесь, что в удалённом репозитории нет `.env` и `node_modules` (история: `git log --all -- backend/.env` — пусто).

---

## Если `git status` очень долгий

Часто виноват огромный `node_modules` или кэш. Убедитесь, что они в `.gitignore`. Временно:

```bash
git status -uno          # без списка untracked
git status -- front/ backend/ docs/ README.md
```

---

## Связанные файлы

- [README.md](../README.md) — быстрый старт
- [backend/.env.example](../backend/.env.example) — переменные окружения
