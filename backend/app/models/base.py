"""
Общие импорты и типы для всех ORM-моделей.

Никакой логики тут нет — это просто чтобы остальные файлы моделей
не дублировали одни и те же import'ы.
"""
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

__all__ = [
    "Base",
    "BigInteger",
    "Boolean",
    "Date",
    "DateTime",
    "ForeignKey",
    "Integer",
    "JSONB",
    "Mapped",
    "Numeric",
    "SmallInteger",
    "String",
    "Text",
    "date",
    "datetime",
    "mapped_column",
    "relationship",
    "text",
]
