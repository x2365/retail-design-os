"""Payments (contractor KP/finance) and retail-point (ТТ) summary views."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .. import aggregates, models, schemas, security, serializers
from ..database import get_db

router = APIRouter(tags=["finance"])
ReadDep = Depends(security.get_current_user)
AdminDep = Depends(security.require_roles(models.Role.admin))


@router.get("/budget/log", response_model=list[schemas.BudgetLogEntryOut])
def budget_log(limit: int = 50, db: Session = Depends(get_db), _admin: models.User = AdminDep):
    rows = db.scalars(
        select(models.AuditLog)
        .where(models.AuditLog.entity_type.in_(["task", "group"]))
        .order_by(models.AuditLog.id.desc())
        .limit(min(limit, 200))
    ).all()
    return [
        {
            "id": r.id,
            "who": r.user_name,
            "task": r.entity_code,
            "field": r.field,
            "old": r.old_value,
            "new": r.new_value,
            "at": r.created_at.strftime("%d.%m.%y %H:%M") if r.created_at else "",
        }
        for r in rows
    ]


@router.patch("/groups/{code}/budget", response_model=schemas.GroupOut)
def update_group_budget(
    code: str,
    payload: schemas.GroupBudgetUpdate,
    db: Session = Depends(get_db),
    admin: models.User = AdminDep,
):
    group = db.scalar(select(models.Group).where(models.Group.code == code))
    if not group:
        raise HTTPException(404, f"Группа {code} не найдена")
    old = group.budget_planned or 0
    new = payload.budget_planned
    if old != new:
        db.add(
            models.AuditLog(
                user_id=admin.id,
                user_name=admin.full_name,
                entity_type="group",
                entity_code=group.code,
                field="План группы",
                old_value=f"{old // 100:,}".replace(",", " ") + " ₽",
                new_value=f"{new // 100:,}".replace(",", " ") + " ₽",
            )
        )
        group.budget_planned = new
    db.commit()
    db.refresh(group)
    return group


@router.get("/payments", response_model=list[schemas.PaymentOut])
def list_payments(db: Session = Depends(get_db), _user: models.User = ReadDep):
    rows = db.scalars(
        select(models.Payment)
        .options(selectinload(models.Payment.task).selectinload(models.Task.brand))
        .order_by(models.Payment.id)
    ).all()
    # последний КП-файл (kind=kp) по каждой задаче — для ссылки на экране оплат
    task_ids = [p.task_id for p in rows]
    kp_docs: dict[int, models.Document] = {}
    if task_ids:
        for d in db.scalars(
            select(models.Document)
            .where(models.Document.task_id.in_(task_ids), models.Document.kind == models.DocKind.kp)
            .order_by(models.Document.id)
        ).all():
            assert d.task_id is not None  # filtered by task_id.in_(task_ids) above
            kp_docs[d.task_id] = d  # перезапись → останется самый поздний
    out = []
    for p in rows:
        item = serializers.payment_to_out(p)
        kp_doc = kp_docs.get(p.task_id)
        item["kp_doc_id"] = kp_doc.id if kp_doc else None
        item["kp_doc_name"] = kp_doc.filename if kp_doc else None
        out.append(item)
    return out


@router.post("/payments", status_code=201, response_model=schemas.PaymentOut)
def upsert_payment(
    payload: schemas.PaymentUpsert,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.require_roles(models.Role.manager)),
):
    task = db.scalar(select(models.Task).where(models.Task.code == payload.task))
    if not task:
        raise HTTPException(404, f"Задача {payload.task} не найдена")
    from ..timeutils import to_utc_datetime

    kp_dt = to_utc_datetime(payload.kp_date) if payload.kp_date else None
    pay = db.scalar(select(models.Payment).where(models.Payment.task_id == task.id))
    if pay is None:
        pay = models.Payment(task_id=task.id)
        db.add(pay)
    pay.contractor = payload.contractor
    pay.kp_date = kp_dt
    pay.currency = payload.currency or "RUB"
    pay.sample = payload.sample
    pay.tirazh = payload.tirazh
    pay.prepaid = payload.prepaid
    pay.balance = payload.balance
    pay.status = payload.status
    db.commit()
    db.refresh(pay)
    return serializers.payment_to_out(pay)


@router.get("/tt", response_model=list[schemas.TTOut])
def list_retail_points(db: Session = Depends(get_db), _user: models.User = ReadDep):
    """Per-task ТТ delivery summary (only tasks that actually ship to TT)."""
    tasks = db.scalars(
        select(models.Task)
        .options(selectinload(models.Task.brand))
        .order_by(models.Task.deadline_tt.asc().nullslast())
    ).all()
    counts = aggregates.counts_for_tasks(db, [t.id for t in tasks])
    return [serializers.task_to_tt(t, counts[t.id]) for t in tasks if counts[t.id]["tt_total"] > 0]
