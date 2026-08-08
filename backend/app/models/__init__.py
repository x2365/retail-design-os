"""ORM-модели — персистентный домен.

Пакет разбит по доменам (base/enums/reference/library/task/ops), но все
публичные имена ре-экспортируются здесь, чтобы внешние импорты не менялись:
    from .. import models;  models.Task
    from ..models import Task, TaskStage, Base

Масштабирование:
- Вычисляемые значения (days_left, progress, счётчики ТТ) НЕ хранятся.
- FK и часто фильтруемые колонки индексируются.
- Новые модели добавляются в соответствующий модуль пакета и в __all__.
"""

from __future__ import annotations

from .audit import AuditLog
from .base import Base, TimestampMixin
from .comment import Comment
from .contractor import Contractor
from .enums import (
    FIRST_STAGE,
    LAST_STAGE,
    PAYMENT_STATUS_LABELS,
    SHIPMENT_REGION_LABELS,
    STAGE_LABELS,
    STAGES,
    ApprovalStatus,
    DeliveryStatus,
    DocKind,
    Role,
    ShipmentRegion,
    TaskStage,
)
from .library import Equipment
from .nomenclature import (
    NOMENCLATURE_STATUS_LABELS,
    NomenclatureItem,
    NomenclatureStatus,
)
from .notification import Notification
from .ops import Approval, Delivery, Document, Payment
from .reference import Brand, Group, RetailPoint, TaskMember, TeamMember, User
from .task import Task, TaskStageApproval, TaskStageHistory

__all__ = [
    # base
    "Base",
    "TimestampMixin",
    # enums / constants
    "TaskStage",
    "STAGE_LABELS",
    "STAGES",
    "FIRST_STAGE",
    "LAST_STAGE",
    "PAYMENT_STATUS_LABELS",
    "Role",
    "ApprovalStatus",
    "DeliveryStatus",
    "DocKind",
    "ShipmentRegion",
    "SHIPMENT_REGION_LABELS",
    "NomenclatureStatus",
    "NOMENCLATURE_STATUS_LABELS",
    # reference
    "User",
    "Group",
    "Brand",
    "TeamMember",
    "TaskMember",
    "RetailPoint",
    # library
    "Equipment",
    # task
    "Task",
    "TaskStageHistory",
    "TaskStageApproval",
    # ops
    "Delivery",
    "Approval",
    "Payment",
    "Document",
    # nomenclature
    "NomenclatureItem",
    # notifications
    "Notification",
    # audit
    "AuditLog",
    # comments
    "Comment",
    # contractors
    "Contractor",
]
