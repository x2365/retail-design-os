"""Журнал изменений (аудит) — кто, когда и что поменял.

Сейчас используется для правок бюджета (только админ), но модель универсальна:
entity_type/entity_code + поле + старое/новое значение.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .reference import User


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_log"
    __table_args__ = (Index("ix_audit_entity", "entity_type", "entity_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    user_name: Mapped[str] = mapped_column(String(150), default="")   # денормализовано для отображения
    entity_type: Mapped[str] = mapped_column(String(24))             # task | group
    entity_code: Mapped[str] = mapped_column(String(32))
    field: Mapped[str] = mapped_column(String(40))                   # человекочитаемая подпись поля
    old_value: Mapped[str] = mapped_column(String(120), default="")
    new_value: Mapped[str] = mapped_column(String(120), default="")

    user: Mapped["User | None"] = relationship(lazy="joined")


__all__ = ["AuditLog"]
