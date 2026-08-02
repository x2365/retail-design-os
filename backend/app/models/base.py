"""Базовые элементы ORM: Base и общий TimestampMixin."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class TimestampMixin:
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False,
    )


__all__ = ["Base", "TimestampMixin"]
