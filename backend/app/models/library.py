"""Библиотека проектов/изделий (Equipment)."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .ops import Document
    from .reference import Brand


class Equipment(Base, TimestampMixin):
    """Библиотека существующего оборудования бренда (готовые изделия/SKU),
    из которых можно запускать новые производственные задачи."""

    __tablename__ = "equipment"
    __table_args__ = (Index("ix_equipment_brand", "brand_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(
        String(40), default="other"
    )  # display/stand/corner/shelf/container/other
    description: Mapped[str] = mapped_column(String(500), default="")
    dimensions: Mapped[str] = mapped_column(String(80), default="")  # "45×45×120 мм"
    currency: Mapped[str] = mapped_column(String(8), default="RUB")
    est_budget: Mapped[int] = mapped_column(Integer, default=0)
    est_sample: Mapped[int] = mapped_column(Integer, default=0)
    est_tirazh: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    times_produced: Mapped[int] = mapped_column(Integer, default=0)
    # П8: отгрузка на РЦ
    rc_ship_date: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rc_remainder: Mapped[int] = mapped_column(Integer, default=0)  # остаток на РЦ, шт

    brand: Mapped[Brand] = relationship(back_populates="equipment")
    documents: Mapped[list[Document]] = relationship(
        back_populates="equipment", cascade="all, delete-orphan"
    )


__all__ = ["Equipment"]
