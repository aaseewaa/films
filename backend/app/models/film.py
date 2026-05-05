"""
Film наследует id от Entity (1:1 join). FilmPerson — связь фильма и персон
(режиссёр / актёр / сценарист / etc.).
"""
from datetime import date, datetime

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import ENUM as PgEnum

from app.models.base import (
    Base,
    BigInteger,
    Boolean,
    Date,
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


FILM_PERSON_ROLE_ENUM = PgEnum(
    "director",
    "writer",
    "actor",
    "cinematographer",
    "producer",
    "composer",
    "editor",
    "production_designer",
    "costume_designer",
    "voice_actor",
    name="film_person_role",
    create_type=False,
)


class Film(Base):
    __tablename__ = "film"

    # PK = FK на entity.id
    id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("entity.id", ondelete="CASCADE"), primary_key=True
    )
    release_year: Mapped[int | None] = mapped_column(SmallInteger)
    release_date: Mapped[date | None] = mapped_column(Date)
    runtime_min: Mapped[int | None] = mapped_column(Integer)
    original_language_id: Mapped[int | None] = mapped_column(
        SmallInteger, ForeignKey("language.id")
    )
    age_rating: Mapped[str | None] = mapped_column(String(20))
    sort_title: Mapped[str | None] = mapped_column(String(255))
    extra_metadata: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    # ─── Связи ─────────────────────────────────────────────────────
    entity: Mapped["Entity"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Entity", foreign_keys=[id], lazy="joined"
    )
    cast_and_crew: Mapped[list["FilmPerson"]] = relationship(
        "FilmPerson",
        back_populates="film",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Film #{self.id} ({self.release_year}) '{self.sort_title}'>"


class FilmPerson(Base):
    __tablename__ = "film_person"
    __table_args__ = (
        CheckConstraint(
            "billing_order IS NULL OR billing_order >= 0", name="film_person_billing_nonneg"
        ),
    )

    film_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("film.id", ondelete="CASCADE"), primary_key=True
    )
    person_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("person.id", ondelete="CASCADE"), primary_key=True
    )
    role_type: Mapped[str] = mapped_column(FILM_PERSON_ROLE_ENUM, primary_key=True)

    character_name: Mapped[str | None] = mapped_column(String(255))
    billing_order: Mapped[int | None] = mapped_column(SmallInteger)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    note: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False, default=1.00)
    source_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    # ─── Связи ─────────────────────────────────────────────────────
    film: Mapped["Film"] = relationship("Film", back_populates="cast_and_crew")
    person: Mapped["Person"] = relationship("Person", back_populates="filmography")  # type: ignore[name-defined]  # noqa: F821

    def __repr__(self) -> str:
        return f"<FilmPerson film={self.film_id} person={self.person_id} as {self.role_type}>"
