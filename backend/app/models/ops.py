"""Операционные сущности: поставки, согласования, оплаты, документы."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin
from .enums import ApprovalStatus, DeliveryStatus, DocKind, ShipmentRegion

if TYPE_CHECKING:
    from .library import Equipment
    from .reference import RetailPoint, User
    from .task import Task


class Delivery(Base, TimestampMixin):
    """One row per (task, retail_point): the equipment delivery to a store."""

    __tablename__ = "deliveries"
    __table_args__ = (
        UniqueConstraint("task_id", "retail_point_id", name="uq_delivery_task_point"),
        Index("ix_deliveries_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    retail_point_id: Mapped[int] = mapped_column(
        ForeignKey("retail_points.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[DeliveryStatus] = mapped_column(
        Enum(DeliveryStatus), default=DeliveryStatus.pending
    )
    region: Mapped[ShipmentRegion] = mapped_column(
        Enum(ShipmentRegion), default=ShipmentRegion.local, index=True
    )
    qty_expected: Mapped[int] = mapped_column(Integer, default=0)
    qty_received: Mapped[int] = mapped_column(Integer, default=0)
    confirmed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str] = mapped_column(String(300), default="")
    # Дата прихода в ТТ — вручную (в перспективе подгружается из внешней
    # системы "АХ", интеграции пока нет).
    arrival_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    installed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    installed_by: Mapped[str] = mapped_column(String(150), default="")

    task: Mapped[Task] = relationship(back_populates="deliveries")
    retail_point: Mapped[RetailPoint] = relationship(lazy="joined")


class Approval(Base, TimestampMixin):
    __tablename__ = "approvals"
    __table_args__ = (Index("ix_approvals_status", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"), index=True, nullable=True
    )
    from_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(80))
    summary: Mapped[str] = mapped_column(String(300))
    type: Mapped[str] = mapped_column(String(40))
    avatar: Mapped[str] = mapped_column(String(4), default="")
    color: Mapped[str] = mapped_column(String(16), default="#5b6af0")
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus), default=ApprovalStatus.pending
    )
    comment: Mapped[str | None] = mapped_column(String(500), nullable=True)

    task: Mapped[Task | None] = relationship(back_populates="approvals")


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), unique=True, index=True
    )
    contractor: Mapped[str] = mapped_column(String(160))
    kp_date: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="RUB")
    kp_amount: Mapped[str] = mapped_column(String(80), default="")
    sample: Mapped[str] = mapped_column(String(80), default="")
    tirazh: Mapped[str] = mapped_column(String(80), default="")
    prepaid: Mapped[str] = mapped_column(String(80), default="")
    balance: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(80), default="")

    task: Mapped[Task] = relationship(back_populates="payment")


class Document(Base, TimestampMixin):
    """Файл, привязанный либо к задаче (документ этапа), либо к карточке
    библиотеки (полный файл проекта). Ровно один из task_id/equipment_id задан."""

    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_task", "task_id"),
        Index("ix_documents_equipment", "equipment_id"),
        CheckConstraint(
            "task_id IS NOT NULL OR equipment_id IS NOT NULL",
            name="ck_documents_owner",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), index=True, nullable=True
    )
    equipment_id: Mapped[int | None] = mapped_column(
        ForeignKey("equipment.id", ondelete="CASCADE"), index=True, nullable=True
    )
    kind: Mapped[DocKind] = mapped_column(Enum(DocKind), default=DocKind.other)
    stage: Mapped[int | None] = mapped_column(
        Integer, nullable=True, index=True
    )  # 1..10 (tab it belongs to)
    filename: Mapped[str] = mapped_column(String(255))  # original name shown to user
    storage_name: Mapped[str] = mapped_column(String(255))  # uuid-based name on disk
    content_type: Mapped[str] = mapped_column(String(120), default="application/octet-stream")
    size: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    task: Mapped[Task | None] = relationship(back_populates="documents")
    equipment: Mapped[Equipment | None] = relationship(back_populates="documents")
    uploaded_by: Mapped[User | None] = relationship(lazy="joined")


__all__ = ["Delivery", "Approval", "Payment", "Document"]
