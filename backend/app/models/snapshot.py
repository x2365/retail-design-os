"""Точка сброса демо-данных: полный pg_dump БД (кроме себя же и alembic_version),
хранится в самой БД, а не на диске — Render free tier стирает диск веб-сервиса
при каждом рестарте/деплое, а строка в Postgres переживает это. См.
services/snapshot.py — там же объяснение, почему pg_dump/pg_restore, а не
ручная сериализация таблиц построчно."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Integer, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class DataSnapshot(Base, TimestampMixin):
    __tablename__ = "data_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    taken_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    payload: Mapped[bytes] = mapped_column(LargeBinary)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)


__all__ = ["DataSnapshot"]
