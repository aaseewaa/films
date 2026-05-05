"""
DirectorInfluence — связь "режиссёр повлиял на режиссёра".

Это твоя ключевая фишка для диплома: семантический граф влияний между
режиссёрами с обоснованием через source_id (источник: Wikidata, статья,
интервью). Связи имеют направление, вес (1-5), доверие (0-1) и аспекты
влияния (визуальный стиль, монтаж, нарратив, и т.д.).
"""
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import ENUM as PgEnum

from app.models.base import (
    Base,
    BigInteger,
    Boolean,
    DateTime,
    Mapped,
    Numeric,
    SmallInteger,
    Text,
    mapped_column,
    relationship,
    text,
)


# Enum для аспектов влияния (соответствует public.influence_aspect)
INFLUENCE_ASPECT_ENUM = PgEnum(
    "visual_style",
    "narrative",
    "editing",
    "themes",
    "characters",
    "cinematography",
    "sound",
    "production_design",
    "directing_method",
    "genre",
    "other",
    name="influence_aspect",
    create_type=False,
)


class DirectorInfluence(Base):
    """A повлиял на B: source → target."""

    __tablename__ = "director_influence"
    __table_args__ = (
        CheckConstraint("source_director_id <> target_director_id", name="director_influence_check"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="director_influence_confidence_check"),
        CheckConstraint("weight >= 1 AND weight <= 5", name="director_influence_weight_check"),
        UniqueConstraint(
            "source_director_id", "target_director_id",
            name="director_influence_source_director_id_target_director_id_key",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    source_director_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("person.id", ondelete="CASCADE"), nullable=False
    )
    target_director_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("person.id", ondelete="CASCADE"), nullable=False
    )

    weight: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=3)
    confidence: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False, default=0.50)
    relation_note: Mapped[str | None] = mapped_column(Text)
    inferred_by_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by_user_id: Mapped[int | None] = mapped_column(BigInteger)

    influence_period_start: Mapped[int | None] = mapped_column(SmallInteger)
    influence_period_end: Mapped[int | None] = mapped_column(SmallInteger)
    influence_aspects: Mapped[list[str]] = mapped_column(
        ARRAY(INFLUENCE_ASPECT_ENUM),
        nullable=False,
        server_default=text("ARRAY[]::influence_aspect[]"),
    )
    key_film_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("film.id", ondelete="SET NULL"))
    is_acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    def __repr__(self) -> str:
        return (
            f"<DirectorInfluence #{self.id}: "
            f"{self.source_director_id} → {self.target_director_id} "
            f"(weight={self.weight}, conf={self.confidence})>"
        )
