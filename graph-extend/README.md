# Расширение графа влияний — финальный набор

Три инструмента для **максимального** заполнения графа из всех доступных источников:

```
wikidata/load_wikidata_influences_v3.py    ← P802+P184+P1066+P2099
manual/seed_manual_influences.py            ← 50+ экспертных связей
semantic/semantic_radial_service.py         ← гибридный endpoint (explicit+semantic)
semantic/graph_endpoint_patch.py            ← патч для api/graph.py
```

---

## Шаги (по порядку)

### Шаг 0 — убедись что уже прогнала Wikidata v2

Если ещё не сделала — сначала:
```bash
cd ~/Desktop/films_money_weed/backend
source venv/bin/activate
python -m scripts.load_wikidata_influences_v2
```
Ожидание: ~30-45 минут. Прирост: ~310 → 500-700 связей.

### Шаг 1 — Wikidata v3 (P802 + P184 + P1066 + P2099)

```bash
cp wikidata/load_wikidata_influences_v3.py backend/scripts/
python -m scripts.load_wikidata_influences_v3
```

Ожидание: ~15-25 минут.
Прирост: +50-150 связей (зависит от плотности этих свойств).
Это **редкие** свойства Wikidata, не у всех режиссёров заполнены.

### Шаг 2 — Ручная экспертная разметка

```bash
cp manual/seed_manual_influences.py backend/scripts/
python -m scripts.seed_manual_influences
```

Ожидание: 1-2 минуты.
Прирост: +40-55 связей (если все режиссёры из списка есть в БД).

В скрипте 55 связей. Каждая основана на:
- Цитатах режиссёров в интервью
- Книгах киноведов (Scorsese's Personal Journey, Tarkovsky's Sculpting in Time)
- Документированных учителях/учениках

Если какого-то режиссёра нет в БД — связь пропускается с сообщением.

### Шаг 3 — Семантический endpoint

#### 3.1. Положить сервис

```bash
cp semantic/semantic_radial_service.py backend/app/services/
```

#### 3.2. Обновить роутер

Открой `backend/app/api/graph.py`:

**Добавь импорт** наверху (рядом с существующим `from app.services.radial_graph_service`):

```python
from app.services.semantic_radial_service import SemanticRadialService
```

**Добавь endpoint** в самый конец файла (из `graph_endpoint_patch.py`):

```python
@router.get(
    "/director/{center_id}/semantic-radial",
    summary="Гибридный радиальный граф (explicit + semantic neighbors)",
)
async def director_semantic_radial(
    center_id: int,
    top_n: Annotated[int, Query(ge=1, le=8, description="Сколько узлов вокруг центра")] = 4,
    lang: Annotated[Literal["ru", "en"], Query()] = "ru",
    db: AsyncSession = Depends(get_db),
):
    service = SemanticRadialService(db)
    result = await service.get_radial(center_id, top_n=top_n, lang=lang)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Режиссёр {center_id} не найден или не помечен как is_director",
        )
    return result
```

#### 3.3. Проверь в Swagger

```
GET /api/graph/director/3243/semantic-radial?top_n=4&lang=ru
```

Структура ответа:
```json
{
  "center": {"id": 3243, "name": "Альфред Хичкок", "image": "..."},
  "neighbors": [
    {
      "id": 3417,
      "name": "Дэвид Линч",
      "image": "...",
      "weight": 1.0,
      "films_count": 3,
      "link_kind": "explicit",
      "link_label": "вдохновитель"
    },
    {
      "id": 5430,
      "name": "Дени Вильнёв",
      "image": "...",
      "similarity": 0.87,
      "films_count": 5,
      "link_kind": "semantic",
      "link_label": "близкий по духу"
    }
  ],
  "explicit_count": 1,
  "semantic_count": 3,
  "top_n_requested": 4
}
```

### Шаг 4 — Обновить фронт (HomePage.tsx)

В существующем `HomePage.tsx` поменять URL запроса.

**Было** (если использовался обычный /radial):
```ts
const { data } = await getRadialGraph(centerId, 4);
// URL: /api/graph/director/{id}/radial
```

**Стало**:
```ts
const { data } = await axios.get(
  `/api/graph/director/${centerId}/semantic-radial`,
  { params: { top_n: 4, lang: 'ru' } }
);
```

И в SVG-рендере узлов:

```tsx
const isExplicit = neighbor.link_kind === 'explicit';

// Обводка
strokeColor = isExplicit ? '#F6D77E' : 'rgba(232, 223, 200, 0.4)';
strokeDasharray = isExplicit ? undefined : '4 4';   // пунктир для semantic

// Лёгкая подпись внизу узла (опционально)
<text fontSize={9} fill="rgba(232, 223, 200, 0.6)">
  {neighbor.link_label}  {/* "вдохновитель" или "близкий по духу" */}
</text>
```

---

## Что должно получиться к концу вечера

Прогрессия:
- **Сейчас**: 310 связей
- **+ Wikidata v2** (если ещё не): ~500-700
- **+ Wikidata v3** (P802+P184+...): ~550-800
- **+ Manual seed**: ~600-855

**Гибридный граф работает для ЛЮБОГО режиссёра** — даже если у него нет реальных связей, добавляются 4 семантически близких. На фронте они визуально отличаются.

---

## Защита диплома: что говорить

> «Граф влияний реализован как **гибридная** структура двух типов связей:
>
> **Эксплицитные связи** — это подтверждённые факты влияния, собранные из:
>   - Wikidata properties: P737 (influenced by), P941 (inspired by),
>     P802 (student), P184 (doctoral advisor), P1066 (student of), P2099 (notable student)
>   - Экспертной разметки на основе публичных интервью режиссёров (~55 связей)
>
> **Семантические связи** — это обнаруженное сходство между биографиями
> режиссёров через 384-мерные эмбеддинги (multilingual-MiniLM-L12-v2) и
> косинусное расстояние в pgvector. Используются как fallback когда
> у режиссёра нет эксплицитных связей в БД.
>
> Это типичный паттерн современных knowledge graph (Google KG,
> Wikidata Embeddings, ConceptNet) — комбинировать структурированные
> факты и неявную семантику. В UI пользователь визуально различает
> два типа связей: эксплицитные показаны жирной обводкой, семантические — пунктиром.»

---

## Если что-то не работает

### Wikidata v3 возвращает мало связей
Это **нормально**. P802/P184/P1066/P2099 — редкие свойства. В Wikidata они заполнены только у самых документированных режиссёров (Куросава, Скорсезе, Уэллс).

### Семантический endpoint падает с ошибкой про pgvector
Проверь что у тебя есть эмбеддинги:
```sql
SELECT count(*) FROM entity_translation WHERE embedding IS NOT NULL;
```
Должно быть >10000. Если 0 — запусти `python -m scripts.generate_embeddings`.

### Семантический endpoint возвращает странные «близкие по духу»
Это может произойти если у режиссёра очень короткая биография в БД,
и эмбеддинг получился неинформативный. Семантика тут — **best effort**,
не идеал.
