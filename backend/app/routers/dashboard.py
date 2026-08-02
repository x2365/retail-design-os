"""Dashboard aggregates. Computed in the database with aggregate queries rather
than pulling every row into the app — this keeps the endpoint O(1) on payload
size regardless of how many tasks exist."""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import aggregates, models, schemas, security
from ..database import get_db

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/kpis", response_model=schemas.DashboardKpis)
def kpis(db: Session = Depends(get_db), _user: models.User = Depends(security.get_current_user)):
    today = dt.date.today()
    soon = today + dt.timedelta(days=14)

    active = (
        db.scalar(select(func.count()).select_from(models.Task).where(models.Task.stage < 12)) or 0
    )
    due_soon = (
        db.scalar(
            select(func.count())
            .select_from(models.Task)
            .where(models.Task.stage < 12)
            .where(models.Task.deadline_tt.is_not(None))
            .where(models.Task.deadline_tt <= soon)
        )
        or 0
    )
    completed = (
        db.scalar(select(func.count()).select_from(models.Task).where(models.Task.stage == 12)) or 0
    )
    tt_unconfirmed = aggregates.tt_unconfirmed_total(db)
    budget_total = db.scalar(select(func.coalesce(func.sum(models.Group.budget_planned), 0))) or 0
    # «Освоено» = суммарная себестоимость задач (реальные данные, а не засеянное число).
    budget_spent = db.scalar(select(func.coalesce(func.sum(models.Task.production_cost), 0))) or 0
    brands_count = db.scalar(select(func.count()).select_from(models.Brand)) or 0
    groups_count = db.scalar(select(func.count()).select_from(models.Group)) or 0
    points_total = db.scalar(select(func.count()).select_from(models.RetailPoint)) or 0

    # On-time: доля закрытых задач, попавших в дедлайн (по факту перехода на этап 12).
    on_time_rate = None
    if completed:
        rows = db.execute(
            select(models.Task.deadline_tt, func.max(models.TaskStageHistory.created_at))
            .join(models.TaskStageHistory, models.TaskStageHistory.task_id == models.Task.id)
            .where(models.Task.stage == 12, models.TaskStageHistory.to_stage == 12)
            .group_by(models.Task.id)
        ).all()
        done = [(dl, cl) for dl, cl in rows if dl is not None and cl is not None]
        if done:

            def _utc(d):
                return d if d.tzinfo else d.replace(tzinfo=dt.UTC)

            on_t = sum(1 for dl, cl in done if _utc(cl) <= _utc(dl))
            on_time_rate = round(on_t / len(done) * 100)

    return schemas.DashboardKpis(
        active_tasks=active,
        due_soon=due_soon,
        completed=completed,
        budget_total=budget_total,
        budget_spent=budget_spent,
        tt_unconfirmed=tt_unconfirmed,
        brands_count=brands_count,
        groups_count=groups_count,
        points_total=points_total,
        on_time_rate=on_time_rate,
    )


@router.get("/meta")
def meta():
    """Static reference: the 12-stage pipeline labels."""
    return {"stages": models.STAGES}
