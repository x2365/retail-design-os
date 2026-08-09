"""Задача (Task) и связанные с этапами таблицы (история, согласования)."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin
from .enums import STAGE_LABELS, TaskStage

if TYPE_CHECKING:
    from .library import Equipment
    from .ops import Approval, Delivery, Document, Payment
    from .reference import Brand, TeamMember, User


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_stage", "stage"),
        Index("ix_tasks_deadline", "deadline_tt"),
        CheckConstraint("stage >= 1 AND stage <= 10", name="ck_tasks_stage_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id", ondelete="RESTRICT"), index=True)
    equipment_id: Mapped[int | None] = mapped_column(
        ForeignKey("equipment.id", ondelete="SET NULL"), nullable=True, index=True
    )

    stage: Mapped[int] = mapped_column(Integer, default=1)
    urgent: Mapped[bool] = mapped_column(Boolean, default=False)
    deadline_tt: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    launch_date: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    currency: Mapped[str] = mapped_column(String(8), default="RUB")
    # Канонический показатель стоимости (копейки) — источник для KPI бренда.
    production_cost: Mapped[int] = mapped_column(Integer, default=0)
    # Детализация (тоже в копейках):
    budget: Mapped[int] = mapped_column(Integer, default=0)
    sample_cost: Mapped[int] = mapped_column(Integer, default=0)
    tirazh_cost: Mapped[int] = mapped_column(Integer, default=0)
    prepaid: Mapped[int] = mapped_column(Integer, default=0)
    # Статус оплаты — РУЧНОЙ ввод (позже может приходить из 1С): unpaid/partial/paid.
    payment_status: Mapped[str] = mapped_column(
        String(16), default="unpaid", server_default="unpaid"
    )

    # Данные ТЗ (этап 1) — заполняет менеджер; артикул — ключ для будущей
    # автоподстановки из таблицы запусков (Я.Диск).
    article: Mapped[str] = mapped_column(String(80), default="", server_default="")
    dimensions: Mapped[str] = mapped_column(String(120), default="", server_default="")
    packaging_primary: Mapped[str] = mapped_column(String(160), default="", server_default="")
    packaging_secondary: Mapped[str] = mapped_column(String(160), default="", server_default="")
    rc_arrival_date: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Полный бриф/ТЗ как JSON (структура шаблона POSM): хранится строкой.
    brief_data: Mapped[str] = mapped_column(Text, default="", server_default="")
    # Карточка ШК (данные для маркировки продукции) как JSON.
    shk_data: Mapped[str] = mapped_column(Text, default="", server_default="")
    # Ответственные за этап: JSON {номер_этапа: [имена]}.
    stage_responsible: Mapped[str] = mapped_column(Text, default="", server_default="")

    # Этап «Подготовка»: два согласования (бренд + коллеги ЗЯ); оба → в производство.
    prep_brand_approved_by: Mapped[str] = mapped_column(String(150), default="", server_default="")
    prep_brand_approved_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    design_iteration: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    prep_zya_approved_by: Mapped[str] = mapped_column(String(150), default="", server_default="")
    prep_zya_approved_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Этап «КП»: выбранный подрядчик + согласования (менеджер + директор бренда) → в ДС/Счёт.
    kp_contractor: Mapped[str] = mapped_column(String(160), default="", server_default="")
    kp_manager_approved_by: Mapped[str] = mapped_column(String(150), default="", server_default="")
    kp_manager_approved_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    kp_director_approved_by: Mapped[str] = mapped_column(String(150), default="", server_default="")
    kp_director_approved_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    kp_network_approved_by: Mapped[str] = mapped_column(String(150), default="", server_default="")
    kp_network_approved_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Этап «Образец и Производство»: образец + сроки производства.
    sample_status: Mapped[str] = mapped_column(
        String(16), default="unpaid", server_default="unpaid"
    )  # unpaid|paid|in_tirazh
    sample_deadline: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sample_approved_by: Mapped[str] = mapped_column(String(150), default="", server_default="")
    sample_approved_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sample_received: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    sample_received_date: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sample_qc_approved_by: Mapped[str] = mapped_column(String(150), default="", server_default="")
    sample_qc_approved_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sample_brand_approved_by: Mapped[str] = mapped_column(
        String(150), default="", server_default=""
    )
    sample_brand_approved_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sample_network_approved_by: Mapped[str] = mapped_column(
        String(150), default="", server_default=""
    )
    sample_network_approved_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    production_end_date: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Этап «Отгрузочные документы» (бывш. Упаковка):
    shipment_order_no: Mapped[str] = mapped_column(String(64), default="")
    shipment_ship_date: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    shipment_acceptance_date: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    brand: Mapped[Brand] = relationship(back_populates="tasks")
    equipment: Mapped[Equipment | None] = relationship(lazy="joined")
    members: Mapped[list[TeamMember]] = relationship(secondary="task_members", lazy="selectin")
    approvals: Mapped[list[Approval]] = relationship(back_populates="task")
    payment: Mapped[Payment | None] = relationship(back_populates="task", uselist=False)
    deliveries: Mapped[list[Delivery]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    documents: Mapped[list[Document]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    stage_history: Mapped[list[TaskStageHistory]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskStageHistory.id",
    )
    stage_approval_rows: Mapped[list[TaskStageApproval]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskStageApproval.stage",
    )

    @property
    def days_left(self) -> int:
        if not self.deadline_tt:
            return 0
        today = dt.datetime.now(dt.UTC).date()
        return (self.deadline_tt.date() - today).days

    @property
    def progress_pct(self) -> int:
        return round(self.stage / len(TaskStage) * 100)

    @property
    def stage_enum(self) -> TaskStage:
        return TaskStage(self.stage)

    @property
    def stage_code(self) -> str:
        return TaskStage(self.stage).name

    @property
    def stage_name(self) -> str:
        return STAGE_LABELS[TaskStage(self.stage)]


class TaskStageHistory(Base, TimestampMixin):
    """Лог переходов между этапами задачи (кто/когда/откуда-куда).

    from_stage = NULL для исходной записи при создании задачи.
    Пишется централизованно в services/task_stage.py.
    """

    __tablename__ = "task_stage_history"
    __table_args__ = (Index("ix_stage_history_task", "task_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    from_stage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    to_stage: Mapped[int] = mapped_column(Integer)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    comment: Mapped[str | None] = mapped_column(String(300), nullable=True)

    task: Mapped[Task] = relationship(back_populates="stage_history")
    user: Mapped[User | None] = relationship(lazy="joined")


class TaskStageApproval(Base, TimestampMixin):
    """Согласование («Согласовано») по конкретному этапу задачи.

    Заменяет прежнее JSON-поле tasks.stage_approvals. Одна строка на пару
    (task, stage); UNIQUE(task_id, stage). Хранит, кто и когда согласовал.
    """

    __tablename__ = "task_stage_approvals"
    __table_args__ = (
        UniqueConstraint("task_id", "stage", name="uq_stage_approval_task_stage"),
        Index("ix_stage_approval_task", "task_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    stage: Mapped[int] = mapped_column(Integer)  # 1..10
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    comment: Mapped[str | None] = mapped_column(String(300), nullable=True)
    approved_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    task: Mapped[Task] = relationship(back_populates="stage_approval_rows")
    user: Mapped[User | None] = relationship(lazy="joined")


__all__ = ["Task", "TaskStageHistory", "TaskStageApproval"]
