"""Журнал уведомлений/напоминаний (engine рассылки ответственным за этап)."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .reference import User
    from .task import Task


class Notification(Base, TimestampMixin):
    """Одно логическое напоминание одному пользователю по одной задаче/правилу.

    Журнал служит для идемпотентности (UNIQUE dedup_key), истории и ретраев.
    Реальная доставка (email/telegram) — отдельным диспетчером; здесь хранится
    статус и какие каналы отработали.
    """

    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user", "user_id"),
        Index("ix_notifications_status", "status"),
        Index("ix_notifications_dedup", "dedup_key", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    task_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True, index=True
    )
    stage: Mapped[int | None] = mapped_column(nullable=True)
    rule: Mapped[str] = mapped_column(String(32))  # stage_stuck | deadline | approval_pending
    message: Mapped[str] = mapped_column(String(500))
    dedup_key: Mapped[str] = mapped_column(String(160))  # UNIQUE — не слать одно и то же дважды
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|sent|failed
    channels: Mapped[str] = mapped_column(String(120), default="")  # какие каналы отработали
    sent_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User | None] = relationship(lazy="joined")
    task: Mapped[Task | None] = relationship(lazy="joined")


__all__ = ["Notification"]
