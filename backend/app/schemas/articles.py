"""
Pydantic-схемы для API статей.

Статьи - это сущность entity с entity_type='article'.
Заголовок и тело - в entity_translation.
Связи с фильмами/режиссёрами через article_entity_link.

article_link_type enum:
  - about     -- статья про эту сущность (главный субъект)
  - mentions  -- упоминание
  - reviews   -- статья-рецензия
  - analyzes  -- анализ
  - interview -- интервью
  - cites     -- цитирование
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import ImageURLs


ArticleLinkType = Literal["about", "mentions", "reviews", "analyzes", "interview", "cites"]


class ArticleEntityRef(BaseModel):
    """Ссылка на сущность из статьи (упомянутый режиссёр / фильм)."""
    entity_id: int
    entity_type: Literal["film", "person", "article", "collection"]
    title: str
    link_type: ArticleLinkType
    images: ImageURLs = ImageURLs()

    model_config = ConfigDict(from_attributes=True)


class ArticleSummary(BaseModel):
    """Краткая инфа о статье для журнальной сетки /articles."""
    id: int
    slug: str
    article_type: str  # essay, review, analysis, interview - varchar в БД
    title: str
    summary: str | None = None
    cover_image: str | None = None
    reading_time_min: int | None = None
    is_featured: bool = False
    published_at: str | None = None  # ISO timestamp
    main_subject: ArticleEntityRef | None = None  # главный режиссёр статьи

    model_config = ConfigDict(from_attributes=True)


class ArticleDetail(BaseModel):
    """Полная статья с телом, обложкой и связанными сущностями."""
    id: int
    slug: str
    article_type: str
    title: str
    summary: str | None = None
    body: str | None = None  # длинный текст эссе
    cover_image: str | None = None
    reading_time_min: int | None = None
    is_featured: bool = False
    published_at: str | None = None
    author_name: str | None = None  # display_name автора (или 'Редакция')
    related_entities: list[ArticleEntityRef] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ArticlesListResponse(BaseModel):
    """Ответ /api/articles."""
    items: list[ArticleSummary]
    total: int
    limit: int
    offset: int
