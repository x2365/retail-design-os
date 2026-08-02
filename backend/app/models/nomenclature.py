"""Номенклатура / штрих-коды по задаче (П3)."""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .task import Task


class NomenclatureStatus(str, enum.Enum):
    draft = "draft"  # черновик
    sent_to_rc = "sent_to_rc"  # направлено на РЦ
    registered = "registered"  # заведено в РЦ


NOMENCLATURE_STATUS_LABELS: dict[NomenclatureStatus, str] = {
    NomenclatureStatus.draft: "Черновик",
    NomenclatureStatus.sent_to_rc: "Направлено на РЦ",
    NomenclatureStatus.registered: "Заведено",
}


class NomenclatureItem(Base, TimestampMixin):
    """Позиция номенклатуры (ШК) задачи. Выгружается в Excel-шаблон для РЦ."""

    __tablename__ = "nomenclature_items"
    __table_args__ = (Index("ix_nomenclature_task", "task_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    sku: Mapped[str] = mapped_column(String(64), default="")
    barcode: Mapped[str] = mapped_column(String(64), default="")
    name: Mapped[str] = mapped_column(String(200), default="")
    qty: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[NomenclatureStatus] = mapped_column(
        Enum(NomenclatureStatus), default=NomenclatureStatus.draft, index=True
    )

    task: Mapped[Task] = relationship()


__all__ = ["NomenclatureItem", "NomenclatureStatus", "NOMENCLATURE_STATUS_LABELS"]
