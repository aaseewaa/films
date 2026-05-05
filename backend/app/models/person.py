"""
Person — режиссёры, актёры, сценаристы.
Как и Film, наследует id от Entity.
"""
from datetime import date

from sqlalchemy import ForeignKey

from app.models.base import (
    Base,
    BigInteger,
    Boolean,
    Date,
    JSONB,
    Mapped,
    String,
    Text,
    mapped_column,
    relationship,
    text,
)


class Person(Base):
    __tablename__ = "person"

    id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("entity.id", ondelete="CASCADE"), primary_key=True
    )
    birth_date: Mapped[date | None] = mapped_column(Date)
    death_date: Mapped[date | None] = mapped_column(Date)
    birth_place: Mapped[str | None] = mapped_column(Text)
    is_director: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_actor: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    primary_profession: Mapped[str | None] = mapped_column(String(100))
    gender: Mapped[str | None] = mapped_column(String(30))
    sort_name: Mapped[str | None] = mapped_column(String(255))
    extra_metadata: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    # ─── Связи ─────────────────────────────────────────────────────
    entity: Mapped["Entity"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Entity", foreign_keys=[id], lazy="joined"
    )
    filmography: Mapped[list["FilmPerson"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "FilmPerson", back_populates="person", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Person #{self.id} '{self.sort_name}'>"
