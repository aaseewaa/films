"""
Entity — базовая таблица для всех сущностей (фильм, персона, статья, коллекция).
EntityTranslation — мультиязычные тексты с автообновлением tsvector (через триггер в БД).

Архитектурный приём: все "именованные" сущности (Film, Person, ...) наследуют
PK = entity.id. То есть когда создаёшь фильм — сначала вставляешь в entity,
получаешь id, потом этим же id вставляешь в film.
"""
from datetime import datetime

from sqlalchemy import ForeignKey, UniqueConstraint

from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.dialects.postgresql import REGCONFIG, TSVECTOR

from app.models.base import (
    Base,
    BigInteger,
    DateTime,
    JSONB,
    Mapped,
    SmallInteger,
    String,
    Text,
    mapped_column,
    relationship,
    text,
)


# ─── Enum-типы (соответствуют public.entity_type, etc.) ────────────
# Параметр create_type=False важен: типы УЖЕ есть в БД, SQLAlchemy
# не должен пытаться их создавать заново.

ENTITY_TYPE_ENUM = PgEnum(
    "film",
    "person",
    "article",
    "collection",
    "studio",
    "award",
    "cluster",
    "taxonomy_term",
    name="entity_type",
    create_type=False,
)

PUBLICATION_STATUS_ENUM = PgEnum(
    "draft",
    "published",
    "archived",
    name="publication_status",
    create_type=False,
)

ACCESS_LEVEL_ENUM = PgEnum(
    "public",
    "registered",
    "premium",
    "internal",
    name="access_level",
    create_type=False,
)


class Entity(Base):
    """Базовая запись для любой именованной сущности."""

    __tablename__ = "entity"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    entity_type: Mapped[str] = mapped_column(ENTITY_TYPE_ENUM, nullable=False)
    status: Mapped[str] = mapped_column(
        PUBLICATION_STATUS_ENUM, nullable=False, server_default="draft"
    )
    access_level: Mapped[str] = mapped_column(
        ACCESS_LEVEL_ENUM, nullable=False, server_default="public"
    )

    primary_image_url: Mapped[str | None] = mapped_column(Text)
    thumbnail_url: Mapped[str | None] = mapped_column(Text)
    official_url: Mapped[str | None] = mapped_column(Text)

    external_ids: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    extra_metadata: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    created_by_user_id: Mapped[int | None] = mapped_column(BigInteger)
    updated_by_user_id: Mapped[int | None] = mapped_column(BigInteger)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # ─── Связи ─────────────────────────────────────────────────────
    translations: Mapped[list["EntityTranslation"]] = relationship(
        "EntityTranslation",
        back_populates="entity",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Entity #{self.id} ({self.entity_type})>"


class EntityTranslation(Base):
    """Перевод сущности на конкретный язык. tsvector обновляется триггером БД."""

    __tablename__ = "entity_translation"
    __table_args__ = (
        UniqueConstraint("language_id", "slug"),
    )

    entity_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("entity.id", ondelete="CASCADE"), primary_key=True
    )
    language_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("language.id"), primary_key=True
    )

    # search_config — это regconfig, тип Postgres-специфический.
    # Мы его не задаём из Python (он либо стоит default 'simple', либо триггер
    # в БД сам выбирает конфигурацию по language). Поэтому НЕ описываем здесь.

    search_config: Mapped[str | None] = mapped_column(
        REGCONFIG, server_default=text("'simple'::regconfig")
    )

    slug: Mapped[str] = mapped_column(String(255), nullable=False)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    body: Mapped[str | None] = mapped_column(Text)

    # search_tsv заполняется триггером entity_translation_search_biu — мы его
    # не трогаем из Python. Поэтому мапим как readonly-поле через TSVECTOR.
    search_tsv: Mapped[str] = mapped_column(TSVECTOR, server_default=text("''::tsvector"))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    # ─── Связи ─────────────────────────────────────────────────────
    entity: Mapped["Entity"] = relationship("Entity", back_populates="translations")

    def __repr__(self) -> str:
        return f"<Translation entity={self.entity_id} lang={self.language_id} '{self.title}'>"
