# Тесты backend

| Уровень | Папка | Назначение | Средства |
|---------|-------|------------|----------|
| Модульный | `unit/` | Отдельные функции сервисов, парсеры, security | pytest |
| Интеграционный | `integration/` | REST API через ASGI | pytest, httpx, pytest-asyncio |
| Функциональный | `manual/` | Пользовательские сценарии | Чек-листы |
| Нагрузочный | `performance/` | Время отклика | SQL + замеры (см. README) |

## Запуск

Из каталога `backend` (нужен `.env` с `DATABASE_URL` для интеграционных тестов с меткой `db`):

```bash
source venv/bin/activate
pytest -q                    # все автотесты
pytest -q tests/unit         # только модульные (без поднятия приложения целиком для БД)
pytest -q -m integration     # только REST
pytest -q -m "not db"        # без проверки PostgreSQL
```
