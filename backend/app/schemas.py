"""Pydantic schemas (API contract). Clean snake_case; the frontend adapter maps
these to whatever keys its render functions expect."""

from __future__ import annotations

import datetime as dt
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


# ---- Auth ------------------------------------------------------------------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    telegram_chat_id: str | None = None


class TelegramLink(BaseModel):
    chat_id: str = Field(default="", max_length=40)


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=150)
    role: str
    password: str = Field(min_length=6, max_length=128)


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=150)
    role: str | None = None
    is_active: bool | None = None


class PasswordReset(BaseModel):
    new_password: str = Field(min_length=6, max_length=128)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6, max_length=128)


# ---- Groups / Brands -------------------------------------------------------
class GroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    code: str
    name: str
    color: str
    budget_planned: int
    budget_spent: int


class GroupBudgetUpdate(BaseModel):
    budget_planned: int = Field(ge=0)  # копейки


class BudgetLogEntryOut(BaseModel):
    id: int
    who: str
    entity_type: str
    task: str
    field: str
    old: str
    new: str
    at: str


class CommentCreate(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class CommentOut(BaseModel):
    id: int
    author: str
    text: str
    at: str


class PrepApproval(BaseModel):
    gate: str  # "brand" | "zya"
    approved: bool = True
    comment: str = ""  # причина при «не согласовано»


class KpApproval(BaseModel):
    gate: str  # "manager"|"director"|"network" (финансы/бренд/сеть)
    approved: bool = True


class SampleApproval(BaseModel):
    gate: str | None = None  # qc|brand|network|None(legacy=all)
    approved: bool = True


class TeamMemberAssign(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(default="", max_length=160)
    telegram: str = Field(default="", max_length=80)


class TeamAssign(BaseModel):
    members: list[TeamMemberAssign] = []


class ContractorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    contact: str = Field(default="", max_length=200)
    details: dict = {}


class ContractorOut(BaseModel):
    id: int
    name: str
    contact: str = ""
    details: dict = {}
    is_active: bool = True


class PaymentUpsert(BaseModel):
    task: str  # код задачи (RD-xxx)
    contractor: str = Field(default="", max_length=160)
    kp_date: dt.date | None = None
    currency: str = "RUB"
    sample: str = Field(default="", max_length=80)
    tirazh: str = Field(default="", max_length=80)
    prepaid: str = Field(default="", max_length=80)
    balance: str = Field(default="", max_length=80)
    status: str = Field(default="", max_length=80)


# ---- Tasks -----------------------------------------------------------------
class TaskOut(BaseModel):
    code: str
    name: str
    brand: str
    group: str
    created_at: str | None = None
    stage: int = Field(ge=1, le=10)
    urgent: bool = False
    currency: str = "RUB"
    production_cost: int = Field(default=0, ge=0)
    budget: int = Field(default=0, ge=0)
    sample_cost: int = Field(default=0, ge=0)
    tirazh_cost: int = Field(default=0, ge=0)
    tirazh_qty: int = Field(default=0, ge=0)
    prepaid: int = Field(default=0, ge=0)
    tt_total: int = Field(default=0, ge=0)
    tt_ok: int = 0
    tt_partial: int = 0
    tt_miss: int = 0
    days_left: int
    progress_pct: int
    stage_name: str
    stage_code: str
    deadline: str | None = None
    launch: str | None = None
    team: list[str] = []
    stage_approvals: dict[str, bool] = {}
    shipment_order_no: str = ""
    shipment_ship_date: str | None = None
    shipment_acceptance_date: str | None = None
    payment_status: str = "unpaid"
    article: str = ""
    dimensions: str = ""
    packaging_primary: str = ""
    packaging_secondary: str = ""
    rc_arrival: str | None = None
    equipment_kind: str | None = None
    brief_data: dict = {}
    shk_data: dict = {}
    stage_responsible: dict = {}
    team_detail: list[dict] = []
    prep_brand_approved: bool = False
    prep_brand_by: str = ""
    design_iteration: int = 1
    prep_zya_approved: bool = False
    prep_zya_by: str = ""
    kp_contractor: str = ""
    kp_manager_approved: bool = False
    kp_manager_by: str = ""
    kp_director_approved: bool = False
    kp_director_by: str = ""
    kp_network_approved: bool = False
    kp_network_by: str = ""
    sample_status: str = "unpaid"
    sample_deadline: str | None = None
    sample_received: bool = False
    sample_received_date: str | None = None
    sample_qc_approved: bool = False
    sample_qc_by: str = ""
    sample_brand_approved: bool = False
    sample_brand_by: str = ""
    sample_network_approved: bool = False
    sample_network_by: str = ""
    sample_approved: bool = False
    sample_approved_by: str = ""
    production_end: str | None = None
    production_days_left: int | None = None
    blocked_reasons: list[str] = []


class StageApprovalUpdate(BaseModel):
    stage: int = Field(ge=1, le=10)
    approved: bool


class StageHistoryOut(BaseModel):
    id: int
    from_stage: int | None = None
    from_stage_label: str | None = None
    to_stage: int
    to_stage_label: str
    user: str | None = None
    comment: str | None = None
    at: str


class TaskCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    brand: str
    stage: int = Field(default=1, ge=1, le=10)
    urgent: bool = False
    currency: str = "RUB"
    production_cost: int = Field(default=0, ge=0)
    budget: int = Field(default=0, ge=0)
    sample_cost: int = Field(default=0, ge=0)
    tirazh_cost: int = Field(default=0, ge=0)
    tirazh_qty: int = Field(default=0, ge=0)
    prepaid: int = Field(default=0, ge=0)
    deadline: dt.date | None = None
    launch: dt.date | None = None
    team: list[str] = []
    brief_data: dict = {}
    dimensions: str = Field(default="", max_length=120)


class TaskUpdate(BaseModel):
    name: str | None = None
    stage: int | None = Field(default=None, ge=1, le=10)
    urgent: bool | None = None
    production_cost: int | None = Field(default=None, ge=0)
    budget: int | None = Field(default=None, ge=0)
    sample_cost: int | None = Field(default=None, ge=0)
    tirazh_cost: int | None = Field(default=None, ge=0)
    tirazh_qty: int | None = Field(default=None, ge=0)
    prepaid: int | None = Field(default=None, ge=0)
    payment_status: str | None = None
    article: str | None = Field(default=None, max_length=80)
    dimensions: str | None = Field(default=None, max_length=120)
    packaging_primary: str | None = Field(default=None, max_length=160)
    packaging_secondary: str | None = Field(default=None, max_length=160)
    rc_arrival_date: dt.date | None = None
    brief_data: dict | None = None
    shk_data: dict | None = None
    stage_responsible: dict | None = None
    deadline: dt.date | None = None
    launch: dt.date | None = None
    team: list[str] | None = None
    kp_contractor: str | None = Field(default=None, max_length=160)
    sample_status: str | None = None
    sample_deadline: dt.date | None = None
    sample_received: bool | None = None
    sample_received_date: dt.date | None = None
    production_end_date: dt.date | None = None
    shipment_order_no: str | None = Field(default=None, max_length=64)
    shipment_ship_date: dt.date | None = None
    shipment_acceptance_date: dt.date | None = None


# ---- External integrations (1С и т.п.) -------------------------------------
class OneCPaymentStatusUpdate(BaseModel):
    task: str  # код задачи (RD-xxx)
    status: str  # unpaid|registry|queued|prepaid|paid


# ---- Approvals -------------------------------------------------------------
class ApprovalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    from_name: str
    role: str
    summary: str
    type: str
    avatar: str
    color: str
    status: str
    comment: str | None = None
    task: str | None = None


class ApprovalComment(BaseModel):
    comment: str = Field(default="", max_length=500)


# ---- Payments --------------------------------------------------------------
class PaymentOut(BaseModel):
    id: str
    brand: str
    name: str
    contractor: str
    kp_date: str | None
    sample: str
    tirazh: str
    prepaid: str
    balance: str
    currency: str
    status: str
    payment_status: str
    kp_doc_id: int | None = None
    kp_doc_name: str | None = None


# ---- Retail points & deliveries (ТТ) ---------------------------------------
class RetailPointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    city: str
    address: str
    deliveries_total: int = 0
    problems: int = 0


class RetailPointCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    city: str = ""
    address: str = ""
    code: str | None = None  # auto-generated if omitted


class RetailPointUpdate(BaseModel):
    name: str | None = None
    city: str | None = None
    address: str | None = None


class PointDeliveryOut(BaseModel):
    """A delivery seen from the retail-point side: what equipment shipped here."""

    id: int
    task: str
    task_name: str
    equipment: str | None = None
    status: str
    region: str = "local"
    region_label: str = "Локально"
    qty_expected: int
    qty_received: int
    confirmed_at: str | None = None
    arrival_date: str | None = None
    installed_at: str | None = None
    installed_by: str = ""


class DeliveryOut(BaseModel):
    id: int
    task: str
    point_code: str
    point_name: str
    city: str
    status: str
    region: str = "local"
    region_label: str = "Локально"
    qty_expected: int
    qty_received: int
    confirmed_at: str | None = None
    arrival_date: str | None = None
    note: str = ""
    installed_at: str | None = None
    installed_by: str = ""


class DeliveryUpdate(BaseModel):
    status: str | None = None  # pending|delivered|partial|missing
    region: str | None = None  # local|rc|cis|middle_east
    qty_received: int | None = Field(default=None, ge=0)
    note: str | None = None
    arrival_date: dt.date | None = None  # дата прихода в ТТ (пока вводится вручную)
    installed: bool | None = None  # монтаж подтверждён/снят (требует status=delivered)


class DistributeRequest(BaseModel):
    """Раздать задачу по торговым точкам — создаёт по одной Delivery на
    точку. Явный список точек — приоритетнее; иначе берутся первые `count`
    точек каталога (по коду)."""

    point_ids: list[int] | None = None
    count: int = Field(default=30, ge=1, le=500)
    qty_expected: int = Field(default=1, ge=1)


# ---- Brands (CRUD) ---------------------------------------------------------
class BrandOut(BaseModel):
    id: int
    name: str
    group: str
    active_tasks: int = 0
    equipment_count: int = 0


class BrandCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    group: str  # group code A/B/C


class BrandUpdate(BaseModel):
    name: str | None = None
    group: str | None = None


# ---- Equipment library -----------------------------------------------------
class EquipmentOut(BaseModel):
    id: int
    brand: str
    group: str
    name: str
    kind: str
    kind_label: str
    description: str
    dimensions: str
    currency: str
    est_budget: int
    est_sample: int
    est_tirazh: int
    is_active: bool
    times_produced: int
    rc_ship_date: str | None = None
    rc_remainder: int = 0
    task_code: str | None = None
    cover_document_id: int | None = None


class EquipmentCreate(BaseModel):
    brand: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=200)
    kind: str = "other"
    description: str = ""
    dimensions: str = ""
    currency: str = "RUB"
    est_budget: int = Field(default=0, ge=0)
    est_sample: int = Field(default=0, ge=0)
    est_tirazh: int = Field(default=0, ge=0)


class EquipmentUpdate(BaseModel):
    name: str | None = None
    kind: str | None = None
    description: str | None = None
    dimensions: str | None = None
    currency: str | None = None
    est_budget: int | None = Field(default=None, ge=0)
    est_sample: int | None = Field(default=None, ge=0)
    est_tirazh: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    rc_ship_date: dt.date | None = None
    rc_remainder: int | None = Field(default=None, ge=0)


class ProduceRequest(BaseModel):
    """Launch a production task from a library item."""

    name: str | None = None  # override name; default = equipment name
    deadline: dt.date | None = None
    launch: dt.date | None = None
    team: list[str] = []
    tt_total: int = Field(default=0, ge=0)


# ---- Nomenclature / barcodes (П3) -----------------------------------------
class NomenclatureItemOut(BaseModel):
    id: int
    task: str
    sku: str
    barcode: str
    name: str
    qty: int
    status: str
    status_label: str


class NomenclatureItemCreate(BaseModel):
    sku: str = Field(default="", max_length=64)
    barcode: str = Field(default="", max_length=64)
    name: str = Field(default="", max_length=200)
    qty: int = Field(default=0, ge=0)


class NomenclatureItemUpdate(BaseModel):
    sku: str | None = Field(default=None, max_length=64)
    barcode: str | None = Field(default=None, max_length=64)
    name: str | None = Field(default=None, max_length=200)
    qty: int | None = Field(default=None, ge=0)
    status: str | None = None  # draft|sent_to_rc|registered


class DocumentOut(BaseModel):
    id: int
    task: str | None = None
    equipment_id: int | None = None
    kind: str
    kind_label: str
    stage: int | None = None
    filename: str
    content_type: str
    size: int
    uploaded_by: str | None = None
    created_at: str
    download_url: str


class TTOut(BaseModel):
    task: str
    brand: str
    name: str
    tt_total: int
    tt_ok: int
    tt_partial: int
    tt_miss: int
    days_left: int


# ---- Dashboard -------------------------------------------------------------
class DashboardKpis(BaseModel):
    active_tasks: int
    due_soon: int
    completed: int
    budget_total: int
    budget_spent: int
    tt_unconfirmed: int
    brands_count: int
    groups_count: int
    points_total: int = 0
    on_time_rate: int | None = None


# ---- Flow-метрики процесса (Lead Time / Throughput / WIP / Rework) --------
class ThroughputWeekOut(BaseModel):
    week: str  # начало недели, "dd.mm"
    count: int


class MetricsOut(BaseModel):
    wip_by_stage: dict[int, int]
    lead_time_avg_days: float | None
    throughput_by_week: list[ThroughputWeekOut]
    rework_rate: float
    total_transitions: int


# ---- Assistant copilot -------------------------------------------------------
class AssistantStatusOut(BaseModel):
    enabled: bool
    model: str


class AssistantAnswerOut(BaseModel):
    answer: str
    used_tools: list[str] = []
    error: str | None = None
    disabled: bool = False
