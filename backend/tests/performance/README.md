# Нагрузочное тестирование

Измерение времени отклика типовых SQL-запросов и эндпоинтов. Запускать на копии БД, не на проде.

## SQL (psql)

```sql
\timing on
EXPLAIN ANALYZE
SELECT f.entity_id, ft.title
FROM film f
JOIN entity_translation ft ON ft.entity_id = f.entity_id AND ft.language_code = 'ru'
ORDER BY f.popularity DESC NULLS LAST
LIMIT 24;
```

## API (time)

```bash
# health без БД
time curl -s -o /dev/null -w "%{http_code} %{time_total}s\n" http://localhost:8000/health

# каталог (нужна БД)
time curl -s -o /dev/null -w "%{http_code} %{time_total}s\n" \
  "http://localhost:8000/api/films?limit=24&sort=popularity"
```

Автоматизированные нагрузочные сценарии (locust, k6) можно добавить в этот каталог по мере необходимости.
