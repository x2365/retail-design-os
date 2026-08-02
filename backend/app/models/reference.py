"""Справочные сущности: пользователи, группы, бренды, команда, торговые точки."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin
from .enums import Role

if TYPE_CHECKING:  # только для тайп-чекеров; в рантайме связи резолвятся реестром
    from .library import Equipment
    from .task import Task


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.viewer, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(40), nullable=True)


class Group(Base, TimestampMixin):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(8), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    color: Mapped[str] = mapped_column(String(16))
    budget_planned: Mapped[int] = mapped_column(Integer, default=0)
    budget_spent: Mapped[int] = mapped_column(Integer, default=0)

    brands: Mapped[list[Brand]] = relationship(back_populates="group")


class Brand(Base, TimestampMixin):
    __tablename__ = "brands"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id", ondelete="RESTRICT"), index=True)

    group: Mapped[Group] = relationship(back_populates="brands")
    tasks: Mapped[list[Task]] = relationship(back_populates="brand")
    equipment: Mapped[list[Equipment]] = relationship(
        back_populates="brand", cascade="all, delete-orphan"
    )


class TeamMember(Base, TimestampMixin):
    __tablename__ = "team_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(80), default="Менеджер")
    email: Mapped[str] = mapped_column(String(160), default="", server_default="")
    telegram: Mapped[str] = mapped_column(String(80), default="", server_default="")


class TaskMember(Base):
    __tablename__ = "task_members"
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True
    )
    member_id: Mapped[int] = mapped_column(
        ForeignKey("team_members.id", ondelete="CASCADE"), primary_key=True
    )


class RetailPoint(Base, TimestampMixin):
    """Catalog of retail points (торговые точки)."""

    __tablename__ = "retail_points"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True)  # TT-001
    name: Mapped[str] = mapped_column(String(160))
    city: Mapped[str] = mapped_column(String(80), default="", index=True)
    address: Mapped[str] = mapped_column(String(200), default="")


__all__ = ["User", "Group", "Brand", "TeamMember", "TaskMember", "RetailPoint"]
