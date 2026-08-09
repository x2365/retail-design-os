"""Approvals queue (auth required; decisions need brand/retailer/manager role)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas, security, serializers
from ..database import get_db

router = APIRouter(prefix="/approvals", tags=["approvals"])
ReadDep = Depends(security.get_current_user)
DecideDep = Depends(
    security.require_roles(models.Role.manager, models.Role.brand, models.Role.retailer)
)


def _derived_approvals(db: Session) -> list[dict]:
    """Согласования, ожидающие решения, выводим из задач на этапах-гейтах.

    Этап 3 «Согласования», 4 «Бюджет и КП», 6 «Образец» — пока гейты не закрыты,
    задача висит в очереди и ведёт в карточку (решение принимается там).
    """
    out: list[dict] = []
    tasks = db.scalars(
        select(models.Task)
        .where(models.Task.stage.in_([3, 4, 6]))
        .order_by(models.Task.deadline_tt.is_(None), models.Task.deadline_tt)
    ).all()
    COLORS = {3: "#06d6a0", 4: "#f59e0b", 6: "#8b5cf6"}
    for t in tasks:
        brand = t.brand.name if t.brand else ""
        if t.stage == 3:
            if t.prep_brand_approved_at and t.prep_zya_approved_at:
                continue
            type_ = "Согласование"
            role = "Бренд / Сеть"
        elif t.stage == 4:
            if t.kp_manager_approved_at and t.kp_director_approved_at and t.kp_network_approved_at:
                continue
            type_ = "КП"
            role = "Финансы / Бренд / Сеть"
        else:  # stage 6
            if (
                t.sample_qc_approved_at
                and t.sample_brand_approved_at
                and t.sample_network_approved_at
            ):
                continue
            type_ = "Образец"
            role = "КК / Бренд / Сеть"
        av = (brand[:2] if brand else (t.code[-2:] if t.code else "??")).upper()
        out.append(
            {
                "id": -t.id,  # отрицательный id = производное (решение в карточке)
                "from_name": f"Команда {brand}" if brand else t.code,
                "role": role,
                "summary": f"{t.code} — {t.name}",
                "type": type_,
                "avatar": av,
                "color": COLORS.get(t.stage, "#5b6af0"),
                "status": "pending",
                "comment": "",
                "task": t.code,
            }
        )
    return out


@router.get("", response_model=list[schemas.ApprovalOut])
def list_approvals(
    status: str = "pending", db: Session = Depends(get_db), _user: models.User = ReadDep
):
    stmt = select(models.Approval)
    if status != "all":
        stmt = stmt.where(models.Approval.status == models.ApprovalStatus(status))
    rows = db.scalars(stmt.order_by(models.Approval.id)).all()
    real = [serializers.approval_to_out(a) for a in rows]
    # производные «ожидающие» из задач (показываем при pending/all)
    derived = _derived_approvals(db) if status in ("pending", "all") else []
    return derived + real


def _set_status(approval_id: int, status: models.ApprovalStatus, db: Session):
    a = db.get(models.Approval, approval_id)
    if not a:
        raise HTTPException(404, f"Approval {approval_id} not found")
    a.status = status
    db.commit()
    db.refresh(a)
    return serializers.approval_to_out(a)


@router.post("/{approval_id}/approve")
def approve(approval_id: int, db: Session = Depends(get_db), _user: models.User = DecideDep):
    return _set_status(approval_id, models.ApprovalStatus.approved, db)


@router.post("/{approval_id}/reject")
def reject(approval_id: int, db: Session = Depends(get_db), _user: models.User = DecideDep):
    return _set_status(approval_id, models.ApprovalStatus.rejected, db)


@router.post("/{approval_id}/comment")
def comment_approval(
    approval_id: int,
    payload: schemas.ApprovalComment,
    db: Session = Depends(get_db),
    _user: models.User = DecideDep,
):
    a = db.get(models.Approval, approval_id)
    if not a:
        raise HTTPException(404, f"Approval {approval_id} not found")
    a.comment = (payload.comment or "").strip() or None
    db.commit()
    db.refresh(a)
    return serializers.approval_to_out(a)
