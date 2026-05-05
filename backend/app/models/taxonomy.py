"""
TaxonomyTerm — справочник терминов: жанры, страны, теги, языки, темы.
Используется через entity_taxonomy для связи с фильмами/персонами.
"""
from datetime import datetime

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import ENUM as PgEnum

from app.models.base import (
    Base,
    BigInteger,
    Boolean,
    DateTime,
    Integer,
    JSONB,
    Mapped,
    Numeric,
    SmallInteger,
    String,
    Text,
    mapped_column,
    relationship,
    text,
)


TAXONOMY_TYPE_ENUM = PgEnum(
    "genre",
    "country",
    "language",
    "tag",
    "theme",
    "keyword",
    "movement",
    name="taxonomy_type",
    create_type=False,
)


class TaxonomyTerm(Base):
    __tablename__ = "taxonomy_term"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    term_type: Mapped[str] = mapped_column(TAXONOMY_TYPE_ENUM, nullable=False)
    code: Mapped[str | None] = mapped_column(String(64))
    iso_code: Mapped[str | None] = mapped_column(String(8))
    parent_term_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("taxonomy_term.id")
    )
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    extra_metadata: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    # ─── Связи ─────────────────────────────────────────────────────
    translations: Mapped[list["TaxonomyTermTranslation"]] = relationship(
        "TaxonomyTermTranslation",
        back_populates="term",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<TaxonomyTerm {self.term_type}/{self.code}>"


class TaxonomyTermTranslation(Base):
    __tablename__ = "taxonomy_term_translation"

    term_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("taxonomy_term.id", ondelete="CASCADE"), primary_key=True
    )
    language_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("language.id"), primary_key=True
    )
    slug: Mapped[str | None] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # ─── Связи ─────────────────────────────────────────────────────
    term: Mapped["TaxonomyTerm"] = relationship("TaxonomyTerm", back_populates="translations")


class EntityTaxonomy(Base):
    """Связь сущности с термином (жанр у фильма, страна у фильма, тег у персоны)."""

    __tablename__ = "entity_taxonomy"

    entity_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("entity.id", ondelete="CASCADE"), primary_key=True
    )
    term_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("taxonomy_term.id", ondelete="CASCADE"), primary_key=True
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    weight: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False, default=1.00)
    source_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
