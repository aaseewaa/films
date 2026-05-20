"""
Патч для backend/app/api/graph.py

Добавляет новый endpoint /api/graph/director/{id}/semantic-radial

Этот endpoint работает как обычный /radial, но:
  - Если у режиссёра есть top_n+ эксплицитных учителей — отдаёт их (как обычный /radial)
  - Если меньше — добирает семантически похожими

В ответе каждый neighbor имеет поле link_kind:
  "explicit"  — реальный учитель
  "semantic"  — семантическая близость

На фронте можно рисовать explicit с золотой обводкой, semantic пунктиром.
"""

# ─── ВСТАВЬ В САМЫЙ ВЕРХ backend/app/api/graph.py к существующим импортам:
#
#   from app.services.semantic_radial_service import SemanticRadialService
#

# ─── ВСТАВЬ В КОНЕЦ backend/app/api/graph.py:

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
    """
    Гибридный радиальный граф.

    Сначала тянет реальных учителей из director_influence.
    Если их меньше top_n — добирает семантически похожих режиссёров
    через cosine distance эмбеддингов биографий.

    Каждый neighbor имеет:
      - link_kind: "explicit" | "semantic"
      - link_label: "вдохновитель" | "близкий по духу"
      - weight (для explicit) ИЛИ similarity (для semantic)

    Размер ответа: всегда top_n узлов (центр + top_n соседей),
    если в БД хватает данных (эмбеддинги для семантики обязательны).
    """
    service = SemanticRadialService(db)
    result = await service.get_radial(center_id, top_n=top_n, lang=lang)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Режиссёр {center_id} не найден или не помечен как is_director",
        )
    return result
