"""Перечисления домена и константы этапов (без ORM-зависимостей)."""

from __future__ import annotations

import enum


class TaskStage(enum.IntEnum):
    """Производственный конвейер (BUSINESS_RULES §2). Значения 1..12 —
    числовой порядок сохранён, чтобы не ломать сортировку/Gantt/диапазоны."""

    BRIEF_RECEIVED = 1
    SKETCH = 2
    DESIGN_APPROVAL = 3
    PRE_PRODUCTION = 4
    PRODUCTION = 5
    QUALITY_CONTROL = 6
    PACKING = 7
    READY_FOR_DELIVERY = 8
    DELIVERY = 9
    INSTALLATION = 10
    FINAL_APPROVAL = 11
    CLOSED = 12


STAGE_LABELS: dict[TaskStage, str] = {
    TaskStage.BRIEF_RECEIVED: "ТЗ получено",
    TaskStage.SKETCH: "Разработка дизайна",
    TaskStage.DESIGN_APPROVAL: "Согласования",
    TaskStage.PRE_PRODUCTION: "SUMMARY",
    TaskStage.PRODUCTION: "Бюджет и КП",
    TaskStage.QUALITY_CONTROL: "Документы",
    TaskStage.PACKING: "Образец и Производство",
    TaskStage.READY_FOR_DELIVERY: "Готов к отгрузке",
    TaskStage.DELIVERY: "Доставка",
    TaskStage.INSTALLATION: "Монтаж",
    TaskStage.FINAL_APPROVAL: "Распределение по ТТ",
    TaskStage.CLOSED: "Закрыт",
}

# Backward-compatible ordered list of Russian labels (used by /dashboard/meta).
STAGES: list[str] = [STAGE_LABELS[s] for s in TaskStage]
FIRST_STAGE = int(TaskStage.BRIEF_RECEIVED)
LAST_STAGE = int(TaskStage.CLOSED)

# Task.payment_status is a free string column, not an enum type — this is
# the single source of truth for valid values + labels, shared by the manual
# PATCH /tasks/{code} path and the 1С webhook (routers/integrations.py).
PAYMENT_STATUS_LABELS: dict[str, str] = {
    "unpaid": "—",
    "registry": "Отправлен в реестр",
    "queued": "Заведён на оплату",
    "prepaid": "Предоплачен",
    "paid": "Оплачено",
}


class Role(str, enum.Enum):
    admin = "admin"  # полный доступ
    manager = "manager"  # ведёт задачи, доставки
    brand = "brand"  # представитель бренда: просмотр + согласования
    retailer = "retailer"  # ритейлер: просмотр + подтверждение ТТ
    shipment_manager = "shipment_manager"  # отдел отгрузки: регионы/статусы доставок
    viewer = "viewer"  # только чтение


class ApprovalStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class DeliveryStatus(str, enum.Enum):
    pending = "pending"  # ещё не отгружено / ждём
    delivered = "delivered"  # получили в полном объёме (✓)
    partial = "partial"  # неполный объём (~)
    missing = "missing"  # не получили (✗)


class ShipmentRegion(str, enum.Enum):
    """Регион/направление отгрузки (П4)."""

    local = "local"  # локальная доставка по умолчанию
    rc = "rc"  # распределительный центр (РЦ)
    cis = "cis"  # СНГ
    middle_east = "middle_east"  # Middle East


SHIPMENT_REGION_LABELS: dict[ShipmentRegion, str] = {
    ShipmentRegion.local: "Локально",
    ShipmentRegion.rc: "РЦ",
    ShipmentRegion.cis: "СНГ",
    ShipmentRegion.middle_east: "Middle East",
}


class DocKind(str, enum.Enum):
    brief = "brief"  # ТЗ бренда
    kp = "kp"  # КП подрядчика
    sketch = "sketch"  # Эскизы
    model3d = "model3d"  # 3D-модель
    photo = "photo"  # Фото продукта
    nomenclature = "nomenclature"  # Заполненный ШК Excel / номенклатура
    layout = "layout"  # Раскладка ШК
    ds = "ds"  # ДС (доп. соглашение)
    invoice = "invoice"  # Счёт
    waybill = "waybill"  # Накладная (отгрузка)
    registry = "registry"  # Реестр (отгрузка)
    planogram = "planogram"  # Планограмма (pdf/jpg)
    other = "other"  # Прочее


__all__ = [
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
]
