"""
API: статьи.
GET /api/articles                - список (журнальная сетка)
GET /api/article/{slug}          - статья по slug
GET /api/article/by-id/{id}      - статья по id
"""
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.articles import ArticleDetail, ArticlesListResponse
from app.services.articles_service import ArticlesService

router = APIRouter(tags=["articles"])


@router.get(
    "/api/articles",
    response_model=ArticlesListResponse,
    summary="Список статей (журнальная сетка)",
)
async def list_articles(
    only_featured: Annotated[bool, Query(description="Только избранные")] = False,
    article_type: Annotated[
        Optional[str],
        Query(description="Фильтр по типу: essay, review, analysis, interview"),
    ] = None,
    for_entity_id: Annotated[
        Optional[int],
        Query(description="Только статьи связанные с этой сущностью"),
    ] = None,
    lang: Annotated[Literal["ru", "en"], Query()] = "ru",
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
    db: AsyncSession = Depends(get_db),
) -> ArticlesListResponse:
    """
    Журнальная сетка статей. Сортировка: избранные → дата → id.
    На карточке режиссёра можно использовать `?for_entity_id={person_id}`
    чтобы получить все статьи про этого режиссёра.
    """
    service = ArticlesService(db)
    result = await service.list_articles(
        lang=lang,
        only_featured=only_featured,
        article_type=article_type,
        for_entity_id=for_entity_id,
        limit=limit, offset=offset,
    )
    return ArticlesListResponse(**result)


@router.get(
    "/api/article/by-id/{article_id}",
    response_model=ArticleDetail,
    summary="Статья по ID",
)
async def get_article_by_id(
    article_id: int,
    lang: Annotated[Literal["ru", "en"], Query()] = "ru",
    db: AsyncSession = Depends(get_db),
) -> ArticleDetail:
    service = ArticlesService(db)
    result = await service.get_article_by_id(article_id, lang=lang)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Статья {article_id} не найдена")
    return ArticleDetail(**result)


@router.get(
    "/api/article/{slug}",
    response_model=ArticleDetail,
    summary="Статья по slug",
)
async def get_article_by_slug(
    slug: str,
    lang: Annotated[Literal["ru", "en"], Query()] = "ru",
    db: AsyncSession = Depends(get_db),
) -> ArticleDetail:
    """Получить статью по slug (URL-дружественный идентификатор)."""
    service = ArticlesService(db)
    result = await service.get_article_by_slug(slug, lang=lang)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Статья '{slug}' не найдена")
    return ArticleDetail(**result)
