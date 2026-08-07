"""Tasks API — the core resource (filtering, pagination, RBAC-protected writes)."""

from __future__ import annotations

import datetime as dt
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session, selectinload

from .. import aggregates, models, schemas, security, serializers
from ..config import get_settings
from ..database import get_db
from ..services import audit, library, task_stage
from ..timeutils import to_utc_datetime

router = APIRouter(prefix="/tasks", tags=["tasks"])
settings = get_settings()

STAGE_BANDS = {
    "dev": [1, 2],
    "approval": [3, 4, 5, 6],
    "production": [7, 8],
    "logistics": [9, 10, 11, 12],
}

# any authenticated user may read
ReadDep = Depends(security.get_current_user)
# only managers/admins may write
WriteDep = Depends(security.require_roles(models.Role.manager))
# deleting a task is irreversible (wipes its whole history) — admin only
AdminDep = Depends(security.require_roles(models.Role.admin))
# prep/kp/sample gate decisions: each gate has its own real-world approver
# (see Role docstrings in models/enums.py) — manager/admin may always decide
# any gate; brand/retailer are further restricted to their own gate below.
ApproveDep = Depends(
    security.require_roles(models.Role.manager, models.Role.brand, models.Role.retailer)
)

# Which role owns which gate literal, across prep-/kp-/sample-approval. "zya"
# and "network" are both the retail-chain's sign-off (same real-world actor,
# different stage); "director" is the brand's budget sign-off on the KP.
_BRAND_GATES = {"brand", "director"}
_RETAILER_GATES = {"zya", "network"}


def _check_gate_role(user: models.User, gate: str) -> None:
    if user.role in (models.Role.manager, models.Role.admin):
        return
    if user.role == models.Role.brand and gate in _BRAND_GATES:
        return
    if user.role == models.Role.retailer and gate in _RETAILER_GATES:
        return
    raise HTTPException(
        403, f"Роль «{user.role.value}» не может согласовывать гейт «{gate or 'все сразу'}»"
    )


def _base_query():
    return select(models.Task).options(
        selectinload(models.Task.brand).selectinload(models.Brand.group),
        selectinload(models.Task.members),
        selectinload(models.Task.stage_approval_rows),
    )


@router.get("", response_model=schemas.Page[schemas.TaskOut])
def list_tasks(
    db: Session = Depends(get_db),
    _user: models.User = ReadDep,
    group: str | None = Query(None),
    band: str | None = Query(None),
    urgent: bool | None = None,
    due_within: int | None = Query(None, ge=0),
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(settings.default_page_size, ge=1, le=settings.max_page_size),
):
    stmt = _base_query()
    count_stmt = select(func.count()).select_from(models.Task)

    filters = []
    if group:
        filters.append(models.Task.brand.has(models.Brand.group.has(code=group)))
    if band and band in STAGE_BANDS:
        filters.append(models.Task.stage.in_(STAGE_BANDS[band]))
    if urgent is not None:
        filters.append(models.Task.urgent.is_(urgent))
    if due_within is not None:
        cutoff = dt.date.today() + dt.timedelta(days=due_within)
        filters.append(models.Task.deadline_tt <= cutoff)
    if search:
        like = f"%{search}%"
        filters.append(or_(models.Task.name.ilike(like), models.Task.code.ilike(like)))

    for f in filters:
        stmt = stmt.where(f)
        count_stmt = count_stmt.where(f)

    total = db.scalar(count_stmt) or 0
    stmt = stmt.order_by(models.Task.deadline_tt.asc().nullslast())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    tasks = db.scalars(stmt).all()

    counts = aggregates.counts_for_tasks(db, [t.id for t in tasks])
    return schemas.Page(
        items=[serializers.task_to_out(t, counts[t.id]) for t in tasks],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{code}", response_model=schemas.TaskOut)
def get_task(code: str, db: Session = Depends(get_db), _user: models.User = ReadDep):
    task = db.scalar(_base_query().where(models.Task.code == code))
    if not task:
        raise HTTPException(404, f"Task {code} not found")
    return serializers.task_to_out(task, aggregates.counts_for_task(db, task.id))


def _next_code(db: Session) -> str:
    """Next RD-xxx code. Must be derived from the highest existing numeric
    suffix, NOT a row count — a count-based scheme collides with an existing
    code the moment any task has ever been deleted (count drops, but the
    higher codes are still there), which throws a UNIQUE-constraint 500."""
    max_n = 40
    for code in db.scalars(select(models.Task.code)).all():
        suffix = code.rsplit("-", 1)[-1]
        if suffix.isdigit():
            max_n = max(max_n, int(suffix))
    return f"RD-{max_n + 1:03d}"


@router.post("", response_model=schemas.TaskOut, status_code=201)
def create_task(
    payload: schemas.TaskCreate, db: Session = Depends(get_db), user: models.User = WriteDep
):
    brand = db.scalar(select(models.Brand).where(models.Brand.name == payload.brand))
    if not brand:
        raise HTTPException(422, f"Unknown brand '{payload.brand}'")

    task = models.Task(
        code=_next_code(db),
        name=payload.name,
        brand_id=brand.id,
        stage=payload.stage,
        urgent=payload.urgent,
        currency=payload.currency,
        production_cost=payload.production_cost or payload.budget,
        budget=payload.budget,
        sample_cost=payload.sample_cost,
        tirazh_cost=payload.tirazh_cost,
        prepaid=payload.prepaid,
        deadline_tt=to_utc_datetime(payload.deadline),
        launch_date=to_utc_datetime(payload.launch),
    )
    if payload.brief_data:
        task.brief_data = json.dumps(payload.brief_data, ensure_ascii=False)
    dims = (
        payload.dimensions
        or (payload.brief_data.get("dimensions") if payload.brief_data else "")
        or ""
    ).strip()
    if dims:
        task.dimensions = dims[:120]
    if payload.team:
        members = list(
            db.scalars(
                select(models.TeamMember).where(models.TeamMember.name.in_(payload.team))
            ).all()
        )
        existing = {m.name for m in members}
        for name in payload.team:
            if name not in existing:
                m = models.TeamMember(name=name)
                db.add(m)
                members.append(m)
        task.members = members

    db.add(task)
    db.flush()  # need task.id / fields for the card
    library.ensure_library_card(db, task)  # every new ТЗ → карточка в библиотеке (1:1)
    task_stage.record_creation(db, task, user_id=user.id)  # исходная запись истории
    db.commit()
    task = db.scalar(_base_query().where(models.Task.id == task.id))
    return serializers.task_to_out(task, aggregates.counts_for_task(db, task.id))


@router.delete("/{code}", status_code=204)
def delete_task(code: str, db: Session = Depends(get_db), user: models.User = AdminDep):
    """Безвозвратно удаляет задачу и всё связанное: оплату, доставки, документы,
    комментарии, номенклатуру, согласования, историю этапов. Carточка
    библиотеки (Equipment), если задача была запущена оттуда, не удаляется —
    у неё своя жизнь (times_produced, другие проекты).

    Comment/NomenclatureItem/Payment/Approval удаляются здесь явно (bulk
    delete), а не через ORM-каскад: у SQLite (локально/тесты) FK-констрейнты
    не включены, а Comment/NomenclatureItem не имеют relationship на Task
    вовсе — полагаться на DB-level ondelete здесь нельзя."""
    task = db.scalar(select(models.Task).where(models.Task.code == code))
    if not task:
        raise HTTPException(404, f"Task {code} not found")
    audit.log_deletion(
        db,
        user,
        entity_type="task",
        entity_code=task.code,
        description=f"{task.code} · {task.name}",
    )
    db.execute(delete(models.Comment).where(models.Comment.task_id == task.id))
    db.execute(delete(models.NomenclatureItem).where(models.NomenclatureItem.task_id == task.id))
    db.execute(delete(models.Payment).where(models.Payment.task_id == task.id))
    db.execute(delete(models.Approval).where(models.Approval.task_id == task.id))
    db.delete(task)
    db.commit()


@router.patch("/{code}", response_model=schemas.TaskOut)
def update_task(
    code: str,
    payload: schemas.TaskUpdate,
    db: Session = Depends(get_db),
    user: models.User = WriteDep,
):
    task = db.scalar(_base_query().where(models.Task.code == code))
    if not task:
        raise HTTPException(404, f"Task {code} not found")
    data = payload.model_dump(exclude_unset=True)
    # Stage changes go through the transition state machine (forward +1, revert back)
    # and are logged to task_stage_history.
    new_stage = data.pop("stage", None)
    if new_stage is not None and new_stage != task.stage:
        try:
            task_stage.apply_transition(db, task, new_stage, user_id=user.id)
        except ValueError as e:
            raise HTTPException(422, str(e)) from e
    field_map = {"deadline": "deadline_tt", "launch": "launch_date"}
    for key in (
        "deadline",
        "launch",
        "shipment_ship_date",
        "shipment_acceptance_date",
        "rc_arrival_date",
        "sample_deadline",
        "production_end_date",
        "sample_received_date",
    ):
        if key in data:
            data[key] = to_utc_datetime(data[key])
    if "sample_status" in data and data["sample_status"] not in ("unpaid", "paid", "prepaid"):
        raise HTTPException(400, "Недопустимый статус образца")

    # Бюджетные поля (в копейках) может менять ТОЛЬКО администратор; каждое
    # изменение пишется в журнал (audit_log) с прежним и новым значением.
    MONEY_FIELDS = {
        "budget": "Итого бюджет",
        "sample_cost": "Образец",
        "tirazh_cost": "Тираж",
        "prepaid": "Предоплата",
        "production_cost": "Себестоимость",
    }
    money_in_payload = [k for k in MONEY_FIELDS if k in data]
    if money_in_payload and user.role != models.Role.admin:
        raise HTTPException(403, "Бюджет может менять только администратор")
    for key in money_in_payload:
        old = getattr(task, key) or 0
        new = data[key] or 0
        if old != new:
            db.add(
                models.AuditLog(
                    user_id=user.id,
                    user_name=user.full_name,
                    entity_type="task",
                    entity_code=task.code,
                    field=MONEY_FIELDS[key],
                    old_value=f"{old // 100:,}".replace(",", " ") + " ₽",
                    new_value=f"{new // 100:,}".replace(",", " ") + " ₽",
                )
            )

    # Статус оплаты — ручной ввод (manager/admin); пишем в журнал.
    PAY_LABELS = {
        "unpaid": "\u2014",
        "registry": "Отправлен в реестр",
        "queued": "Заведён на оплату",
        "prepaid": "Предоплачен",
        "paid": "Оплачено",
    }
    if "payment_status" in data:
        ps = data["payment_status"]
        if ps not in PAY_LABELS:
            raise HTTPException(400, "Недопустимый статус оплаты")
        if (task.payment_status or "unpaid") != ps:
            db.add(
                models.AuditLog(
                    user_id=user.id,
                    user_name=user.full_name,
                    entity_type="task",
                    entity_code=task.code,
                    field="Статус оплаты",
                    old_value=PAY_LABELS.get(task.payment_status or "unpaid", "—"),
                    new_value=PAY_LABELS[ps],
                )
            )

    # Полный бриф (JSON): сохраняем строкой, синхронизируем размеры для SUMMARY/КП.
    if "brief_data" in data:
        brief = data.pop("brief_data") or {}
        task.brief_data = json.dumps(brief, ensure_ascii=False)
        dims = (brief.get("dimensions") or "").strip()
        if dims:
            task.dimensions = dims[:120]

    if "shk_data" in data:
        task.shk_data = json.dumps(data.pop("shk_data") or {}, ensure_ascii=False)

    if "stage_responsible" in data:
        task.stage_responsible = json.dumps(data.pop("stage_responsible") or {}, ensure_ascii=False)

    # Команда проекта (ручное назначение менеджером): заменяем участников.
    if "team" in data:
        names = data.pop("team") or []
        members = (
            list(
                db.scalars(select(models.TeamMember).where(models.TeamMember.name.in_(names))).all()
            )
            if names
            else []
        )
        existing = {m.name for m in members}
        for nm in names:
            if nm not in existing:
                m = models.TeamMember(name=nm)
                db.add(m)
                members.append(m)
        task.members = members

    for key, value in data.items():
        setattr(task, field_map.get(key, key), value)
    db.commit()
    db.refresh(task)
    return serializers.task_to_out(task, aggregates.counts_for_task(db, task.id))


# ---- per-stage approval ("Согласовано" на вкладке этапа) -------------------
@router.patch("/{code}/stage-approval", response_model=schemas.TaskOut)
def set_stage_approval(
    code: str,
    payload: schemas.StageApprovalUpdate,
    db: Session = Depends(get_db),
    user: models.User = WriteDep,
):
    task = db.scalar(_base_query().where(models.Task.code == code))
    if not task:
        raise HTTPException(404, f"Task {code} not found")
    row = db.scalar(
        select(models.TaskStageApproval).where(
            models.TaskStageApproval.task_id == task.id,
            models.TaskStageApproval.stage == payload.stage,
        )
    )
    now = dt.datetime.now(dt.UTC)
    blocked_reasons: list[str] = []
    advancing = payload.approved and payload.stage == task.stage and task.stage < models.LAST_STAGE

    # Если это согласование ТЕКУЩЕГО этапа (с переходом дальше) — сперва проверяем
    # внутренние согласования карточки. Если не пройдены — не ставим «✓» и не двигаем.
    if advancing:
        pre = task_stage.check_stage_preconditions(db, task, task.stage)
        nxt = task_stage.next_stage(task.stage)
        if nxt == models.LAST_STAGE:
            pre = pre + task_stage.check_close_preconditions(db, task)
        if pre:
            db.refresh(task)
            out = serializers.task_to_out(task, aggregates.counts_for_task(db, task.id))
            out.blocked_reasons = pre
            return out

    if row is None:
        row = models.TaskStageApproval(task_id=task.id, stage=payload.stage)
        db.add(row)
    row.approved = payload.approved
    row.user_id = user.id
    row.approved_at = now if payload.approved else None
    # Workflow rule: approving the task's CURRENT stage advances it to the next.
    if advancing:
        nxt = task_stage.next_stage(task.stage)
        try:
            task_stage.apply_transition(
                db,
                task,
                nxt,
                user_id=user.id,
                comment=f"авто-переход: согласован этап {payload.stage}",
            )
        except ValueError:
            blocked_reasons = task_stage.check_stage_preconditions(db, task, task.stage)
            if nxt == models.LAST_STAGE:
                blocked_reasons = blocked_reasons + task_stage.check_close_preconditions(db, task)
            if not blocked_reasons:
                blocked_reasons = ["переход заблокирован"]
    db.commit()
    db.refresh(task)
    out = serializers.task_to_out(task, aggregates.counts_for_task(db, task.id))
    out.blocked_reasons = blocked_reasons
    return out


# ---- stage transition history (журнал переходов) --------------------------
@router.get("/{code}/history", response_model=list[schemas.StageHistoryOut])
def task_stage_history(code: str, db: Session = Depends(get_db), _user: models.User = ReadDep):
    task = db.scalar(select(models.Task).where(models.Task.code == code))
    if not task:
        raise HTTPException(404, f"Task {code} not found")
    rows = db.scalars(
        select(models.TaskStageHistory)
        .options(selectinload(models.TaskStageHistory.user))
        .where(models.TaskStageHistory.task_id == task.id)
        .order_by(models.TaskStageHistory.id.asc())
    ).all()
    return [serializers.stage_history_to_out(h) for h in rows]


# ---- per-task deliveries (ТТ) ---------------------------------------------
@router.get("/{code}/deliveries", response_model=list[schemas.DeliveryOut])
def task_deliveries(code: str, db: Session = Depends(get_db), _user: models.User = ReadDep):
    task = db.scalar(select(models.Task).where(models.Task.code == code))
    if not task:
        raise HTTPException(404, f"Task {code} not found")
    rows = db.scalars(
        select(models.Delivery)
        .options(selectinload(models.Delivery.task), selectinload(models.Delivery.retail_point))
        .where(models.Delivery.task_id == task.id)
        .order_by(models.Delivery.id)
    ).all()
    return [serializers.delivery_to_out(d) for d in rows]


@router.post("/{code}/distribute", response_model=list[schemas.DeliveryOut], status_code=201)
def distribute_task(
    code: str,
    payload: schemas.DistributeRequest,
    db: Session = Depends(get_db),
    _user: models.User = WriteDep,
):
    """Раздать задачу по торговым точкам (создать Delivery per точка). Без
    этого шага задача может закрыться, ни разу не отгрузившись ни в одну
    ТТ — «не все ТТ доставлены» проверяет только СУЩЕСТВУЮЩИЕ Delivery."""
    task = db.scalar(select(models.Task).where(models.Task.code == code))
    if not task:
        raise HTTPException(404, f"Task {code} not found")
    already = db.scalar(
        select(func.count()).select_from(models.Delivery).where(models.Delivery.task_id == task.id)
    )
    if already:
        raise HTTPException(409, f"Задача уже распределена по ТТ ({already})")

    if payload.point_ids:
        points = db.scalars(
            select(models.RetailPoint).where(models.RetailPoint.id.in_(payload.point_ids))
        ).all()
        missing = set(payload.point_ids) - {p.id for p in points}
        if missing:
            raise HTTPException(404, f"Точки не найдены: {sorted(missing)}")
    else:
        points = db.scalars(
            select(models.RetailPoint).order_by(models.RetailPoint.code).limit(payload.count)
        ).all()
        if not points:
            raise HTTPException(409, "В каталоге нет торговых точек")

    for p in points:
        db.add(
            models.Delivery(
                task_id=task.id, retail_point_id=p.id, qty_expected=payload.qty_expected
            )
        )
    db.commit()

    rows = db.scalars(
        select(models.Delivery)
        .options(selectinload(models.Delivery.task), selectinload(models.Delivery.retail_point))
        .where(models.Delivery.task_id == task.id)
        .order_by(models.Delivery.id)
    ).all()
    return [serializers.delivery_to_out(d) for d in rows]


# ---- комментарии к задаче (с автором) -------------------------------------
@router.get("/{code}/comments", response_model=list[schemas.CommentOut])
def list_comments(code: str, db: Session = Depends(get_db), _user: models.User = ReadDep):
    task = db.scalar(select(models.Task).where(models.Task.code == code))
    if not task:
        raise HTTPException(404, f"Task {code} not found")
    rows = db.scalars(
        select(models.Comment).where(models.Comment.task_id == task.id).order_by(models.Comment.id)
    ).all()
    return [
        {
            "id": c.id,
            "author": c.author_name or "—",
            "text": c.text,
            "at": c.created_at.strftime("%d.%m.%y %H:%M") if c.created_at else "",
        }
        for c in rows
    ]


@router.post("/{code}/comments", status_code=201, response_model=schemas.CommentOut)
def add_comment(
    code: str,
    payload: schemas.CommentCreate,
    db: Session = Depends(get_db),
    user: models.User = ReadDep,
):
    task = db.scalar(select(models.Task).where(models.Task.code == code))
    if not task:
        raise HTTPException(404, f"Task {code} not found")
    c = models.Comment(
        task_id=task.id, author_id=user.id, author_name=user.full_name, text=payload.text.strip()
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return {
        "id": c.id,
        "author": c.author_name,
        "text": c.text,
        "at": c.created_at.strftime("%d.%m.%y %H:%M") if c.created_at else "",
    }


# ---- согласование на этапе «Подготовка» (бренд + ЗЯ) ----------------------
@router.post("/{code}/prep-approval", response_model=schemas.TaskOut)
def prep_approval(
    code: str,
    payload: schemas.PrepApproval,
    db: Session = Depends(get_db),
    user: models.User = ApproveDep,
):
    task = db.scalar(select(models.Task).where(models.Task.code == code))
    if not task:
        raise HTTPException(404, f"Task {code} not found")
    if payload.gate not in ("brand", "zya"):
        raise HTTPException(400, "gate must be 'brand' or 'zya'")
    _check_gate_role(user, payload.gate)
    now = dt.datetime.now(dt.UTC)
    if payload.gate == "brand":
        task.prep_brand_approved_at = now if payload.approved else None
        task.prep_brand_approved_by = user.full_name if payload.approved else ""
    else:
        task.prep_zya_approved_at = now if payload.approved else None
        task.prep_zya_approved_by = user.full_name if payload.approved else ""
    # «Не согласовано» с комментарием → фиксируем причину и наращиваем итерацию дизайна
    if not payload.approved and payload.comment.strip():
        gate_ru = "Бренд" if payload.gate == "brand" else "ЗЯ"
        db.add(
            models.Comment(
                task_id=task.id,
                author_id=user.id,
                author_name=user.full_name,
                text=f"[{gate_ru}] Не согласовано: {payload.comment.strip()}",
            )
        )
        task.design_iteration = (task.design_iteration or 1) + 1
    # Оба согласования получены и задача на «Согласованиях» (этап 3) → дальше (4).
    if task.prep_brand_approved_at and task.prep_zya_approved_at and task.stage == 3:
        try:
            task_stage.apply_transition(
                db, task, 4, user_id=user.id, comment="Авто-переход: оба согласования получены"
            )
        except ValueError as e:
            raise HTTPException(409, str(e)) from e
    db.commit()
    db.refresh(task)
    return serializers.task_to_out(task, aggregates.counts_for_task(db, task.id))


# ---- согласование КП (менеджер + директор бренда) -------------------------
@router.post("/{code}/kp-approval", response_model=schemas.TaskOut)
def kp_approval(
    code: str,
    payload: schemas.KpApproval,
    db: Session = Depends(get_db),
    user: models.User = ApproveDep,
):
    task = db.scalar(select(models.Task).where(models.Task.code == code))
    if not task:
        raise HTTPException(404, f"Task {code} not found")
    if payload.gate not in ("manager", "director", "network"):
        raise HTTPException(400, "gate must be 'manager', 'director' or 'network'")
    _check_gate_role(user, payload.gate)
    now = dt.datetime.now(dt.UTC)
    if payload.gate == "manager":
        task.kp_manager_approved_at = now if payload.approved else None
        task.kp_manager_approved_by = user.full_name if payload.approved else ""
    elif payload.gate == "director":
        task.kp_director_approved_at = now if payload.approved else None
        task.kp_director_approved_by = user.full_name if payload.approved else ""
    else:
        task.kp_network_approved_at = now if payload.approved else None
        task.kp_network_approved_by = user.full_name if payload.approved else ""
    # Согласования КП (финансы/бренд) и задача на «КП» (5) → в «Документы» (6).
    # Сеть здесь не требуется — её согласование уже получено на этапе 3.
    if task.kp_manager_approved_at and task.kp_director_approved_at and task.stage == 5:
        try:
            task_stage.apply_transition(
                db,
                task,
                6,
                user_id=user.id,
                comment="Авто-переход: КП согласовано (финансы, бренд)",
            )
        except ValueError as e:
            raise HTTPException(409, str(e)) from e
    db.commit()
    db.refresh(task)
    return serializers.task_to_out(task, aggregates.counts_for_task(db, task.id))


# ---- утверждение образца (этап «Образец и Производство») ------------------
@router.post("/{code}/sample-approval", response_model=schemas.TaskOut)
def sample_approval(
    code: str,
    payload: schemas.SampleApproval,
    db: Session = Depends(get_db),
    user: models.User = ApproveDep,
):
    task = db.scalar(select(models.Task).where(models.Task.code == code))
    if not task:
        raise HTTPException(404, f"Task {code} not found")
    now = dt.datetime.now(dt.UTC)
    gate = (payload.gate or "").lower()
    if gate not in ("", "qc", "brand", "network"):
        raise HTTPException(400, "gate must be 'qc', 'brand', 'network' or empty")
    # empty gate = legacy "approve all three at once" — only the full
    # manager/admin owner of the sample stage may do that in one shot.
    _check_gate_role(user, gate)

    def set_gate(attr_at, attr_by):
        setattr(task, attr_at, now if payload.approved else None)
        setattr(task, attr_by, user.full_name if payload.approved else "")

    if gate == "qc":
        set_gate("sample_qc_approved_at", "sample_qc_approved_by")
    elif gate == "brand":
        set_gate("sample_brand_approved_at", "sample_brand_approved_by")
    elif gate == "network":
        set_gate("sample_network_approved_at", "sample_network_approved_by")
    else:
        # legacy: «утвердить образец» целиком — ставит/снимает все три гейта
        for at, by in (
            ("sample_qc_approved_at", "sample_qc_approved_by"),
            ("sample_brand_approved_at", "sample_brand_approved_by"),
            ("sample_network_approved_at", "sample_network_approved_by"),
        ):
            set_gate(at, by)

    # сводный флаг «образец утверждён» = все три согласования
    all_three = (
        task.sample_qc_approved_at
        and task.sample_brand_approved_at
        and task.sample_network_approved_at
    )
    if all_three:
        task.sample_approved_at = now
        task.sample_approved_by = "КК + Бренд + Сеть"
    else:
        task.sample_approved_at = None
        task.sample_approved_by = ""

    # Переход на следующий этап выполняется вручную кнопкой «Принято в работу»
    # (после того как проставлены все три согласования). Авто-перехода нет.
    db.commit()
    db.refresh(task)
    return serializers.task_to_out(task, aggregates.counts_for_task(db, task.id))


# ---- назначение участников с контактами (почта + Telegram) ----------------
@router.post("/{code}/team", response_model=schemas.TaskOut)
def assign_team(
    code: str,
    payload: schemas.TeamAssign,
    db: Session = Depends(get_db),
    _user: models.User = WriteDep,
):
    task = db.scalar(select(models.Task).where(models.Task.code == code))
    if not task:
        raise HTTPException(404, f"Task {code} not found")
    members = []
    for m in payload.members:
        nm = m.name.strip()
        if not nm:
            continue
        tm = db.scalar(select(models.TeamMember).where(models.TeamMember.name == nm))
        if not tm:
            tm = models.TeamMember(name=nm)
            db.add(tm)
        # обновляем контакты, если переданы
        if m.email is not None:
            tm.email = m.email.strip()
        if m.telegram is not None:
            tm.telegram = m.telegram.strip()
        members.append(tm)
    task.members = members
    db.commit()
    db.refresh(task)
    return serializers.task_to_out(task, aggregates.counts_for_task(db, task.id))
