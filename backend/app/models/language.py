"""
Справочник языков. Простая таблица — нужна для FK во всех переводах.
"""
from app.models.base import (
    Base,
    Boolean,
    DateTime,
    Mapped,
    SmallInteger,
    String,
    mapped_column,
)


class Language(Base):
    __tablename__ = "language"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    locale_code: Mapped[str | None] = mapped_column(String(20), unique=True)
    english_name: Mapped[str] = mapped_column(String(100), nullable=False)
    native_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped["DateTime"] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )

    def __repr__(self) -> str:
        return f"<Language {self.code}>"
