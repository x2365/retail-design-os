"""Aggregate helpers — TT (delivery) counts per task.

Counts are computed with a single grouped query for a set of task ids, avoiding
N+1 queries when serializing task lists.
"""

from __future__ import annotations

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from . import models

DS = models.DeliveryStatus


def _counts_select():
    return select(
        models.Delivery.task_id.label("task_id"),
        func.count().label("total"),
        func.sum(case((models.Delivery.status == DS.delivered, 1), else_=0)).label("ok"),
        func.sum(case((models.Delivery.status == DS.partial, 1), else_=0)).label("partial"),
        func.sum(case((models.Delivery.status == DS.missing, 1), else_=0)).label("miss"),
    ).group_by(models.Delivery.task_id)


def counts_for_tasks(db: Session, task_ids: list[int]) -> dict[int, dict]:
    """Return {task_id: {total, ok, partial, miss}} for the given task ids."""
    if not task_ids:
        return {}
    rows = db.execute(_counts_select().where(models.Delivery.task_id.in_(task_ids))).all()
    out: dict[int, dict] = {}
    for r in rows:
        out[r.task_id] = {
            "tt_total": int(r.total or 0),
            "tt_ok": int(r.ok or 0),
            "tt_partial": int(r.partial or 0),
            "tt_miss": int(r.miss or 0),
        }
    # tasks with zero deliveries
    for tid in task_ids:
        out.setdefault(tid, {"tt_total": 0, "tt_ok": 0, "tt_partial": 0, "tt_miss": 0})
    return out


def counts_for_task(db: Session, task_id: int) -> dict:
    return counts_for_tasks(db, [task_id])[task_id]


def tt_unconfirmed_total(db: Session) -> int:
    """partial + missing across all deliveries (KPI 'ТТ без подтв.')."""
    val = db.scalar(
        select(
            func.coalesce(
                func.sum(
                    case(
                        (models.Delivery.status.in_([DS.partial, DS.missing]), 1),
                        else_=0,
                    )
                ),
                0,
            )
        )
    )
    return int(val or 0)


def point_counts(db: Session, point_ids: list[int]) -> dict[int, dict]:
    """Return {point_id: {total, problems}} where problems = partial + missing."""
    if not point_ids:
        return {}
    rows = db.execute(
        select(
            models.Delivery.retail_point_id.label("pid"),
            func.count().label("total"),
            func.sum(
                case((models.Delivery.status.in_([DS.partial, DS.missing]), 1), else_=0)
            ).label("problems"),
        )
        .where(models.Delivery.retail_point_id.in_(point_ids))
        .group_by(models.Delivery.retail_point_id)
    ).all()
    out: dict[int, dict] = {}
    for r in rows:
        out[r.pid] = {"deliveries_total": int(r.total or 0), "problems": int(r.problems or 0)}
    for pid in point_ids:
        out.setdefault(pid, {"deliveries_total": 0, "problems": 0})
    return out
