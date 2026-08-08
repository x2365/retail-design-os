"""External-system integrations (1С и т.п.) — service-token auth, same
pattern as routers/internal.py's reminders endpoint: no user session, a
shared secret in a header instead. Disabled (403) until the corresponding
*_SERVICE_TOKEN setting is configured, since no real external system is
wired up yet — this is the receiving side of a future push from 1С.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import aggregates, models, schemas, serializers
from ..config import get_settings
from ..database import get_db

router = APIRouter(prefix="/internal/1c", tags=["integrations"])


def _require_onec_token(x_service_token: str) -> None:
    s = get_settings()
    if not s.onec_service_token:
        raise HTTPException(403, "1С endpoint disabled (no service token configured)")
    if x_service_token != s.onec_service_token:
        raise HTTPException(401, "Invalid service token")


@router.post("/payment-status", response_model=schemas.TaskOut)
def onec_payment_status(
    payload: schemas.OneCPaymentStatusUpdate,
    db: Session = Depends(get_db),
    x_service_token: str = Header(default=""),
):
    """1С пушит сюда фактический статус оплаты по задаче — тот же
    payment_status, что редактируется вручную на «Оплаты / КП»
    (routers/tasks.py:update_task), но без пользовательской сессии и с
    отдельной пометкой в журнале (кто внёс изменение — «1С», не менеджер)."""
    _require_onec_token(x_service_token)
    task = db.scalar(select(models.Task).where(models.Task.code == payload.task))
    if not task:
        raise HTTPException(404, f"Task {payload.task} not found")
    if payload.status not in models.PAYMENT_STATUS_LABELS:
        raise HTTPException(400, "Недопустимый статус оплаты")
    if (task.payment_status or "unpaid") != payload.status:
        db.add(
            models.AuditLog(
                user_id=None,
                user_name="1С (автоматически)",
                entity_type="task",
                entity_code=task.code,
                field="Статус оплаты",
                old_value=models.PAYMENT_STATUS_LABELS.get(task.payment_status or "unpaid", "—"),
                new_value=models.PAYMENT_STATUS_LABELS[payload.status],
            )
        )
    task.payment_status = payload.status
    db.commit()
    db.refresh(task)
    return serializers.task_to_out(task, aggregates.counts_for_task(db, task.id))
