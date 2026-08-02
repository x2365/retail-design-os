"""Справочник подрядчиков (для выбора на этапе КП)."""
from __future__ import annotations

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class Contractor(Base, TimestampMixin):
    __tablename__ = "contractors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    contact: Mapped[str] = mapped_column(String(200), default="", server_default="")
    details: Mapped[str] = mapped_column(Text, default="", server_default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")


__all__ = ["Contractor"]
