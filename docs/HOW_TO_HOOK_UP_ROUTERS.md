# Как подключить новые роутеры

В твоём файле `backend/app/main.py` нужно добавить **2 import-а** и **2 include_router**.

## Шаг 1: импорты

Найди наверху файла раздел с импортами роутеров. Должно быть что-то такое:

```python
from app.api.search import router as search_router
from app.api.entity import router as entity_router
from app.api.catalog import router as catalog_router
from app.api.auth import router as auth_router
from app.api.user_data import router as user_data_router
from app.api.graph import router as graph_router
from app.api.recommendations import router as recommendations_router
```

Добавь после них:

```python
from app.api.collections import router as collections_router
from app.api.articles import router as articles_router
```

## Шаг 2: include_router

Ниже в коде есть набор `app.include_router(...)`. Например:

```python
app.include_router(search_router)
app.include_router(entity_router)
app.include_router(catalog_router)
app.include_router(auth_router)
app.include_router(user_data_router)
app.include_router(graph_router)
app.include_router(recommendations_router)
```

Добавь после них:

```python
app.include_router(collections_router)
app.include_router(articles_router)
```

Всё. После сохранения uvicorn перезагрузится сам, и в Swagger появятся **2 новые группы**: `collections` и `articles`.
