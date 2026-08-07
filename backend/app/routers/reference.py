"""Reference data: groups (brands moved to brands.py with full CRUD)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db

router = APIRouter(tags=["reference"])
ReadDep = Depends(security.get_current_user)


@router.get("/groups", response_model=list[schemas.GroupOut])
def list_groups(db: Session = Depends(get_db), _user: models.User = ReadDep):
    groups = db.scalars(select(models.Group).order_by(models.Group.code)).all()
    spent_rows = db.execute(
        select(models.Brand.group_id, func.coalesce(func.sum(models.Task.budget), 0))
        .select_from(models.Task)
        .join(models.Brand, models.Task.brand_id == models.Brand.id)
        .group_by(models.Brand.group_id)
    ).all()
    spent: dict[int, int] = {group_id: total for group_id, total in spent_rows}
    out = []
    for g in groups:
        go = schemas.GroupOut.model_validate(g)
        go.budget_spent = int(spent.get(g.id, 0))  # реальное «освоено» = сумма бюджетов задач
        out.append(go)
    return out
