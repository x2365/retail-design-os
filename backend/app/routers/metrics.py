"""Flow-метрики процесса (Lead Time, Throughput, WIP, Rework Rate) —
вычисляются из уже существующих данных (TaskStageHistory, Task.stage),
ничего нового не пишем и не храним отдельно.

Conversion Rate / Cost per Outcome / Customer Outcome сознательно не входят
сюда — для них в модели данных не хватает конкретных полей (нет состояния
«задача отменена/потеряна», Task.production_cost никогда не заполняется
через UI, нет сигнала об удовлетворённости клиента). См. историю сессии для
разбора, что именно понадобится для каждой из них.
"""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db

router = APIRouter(prefix="/metrics", tags=["metrics"])
ReadDep = Depends(security.get_current_user)


def _utc(d: dt.datetime) -> dt.datetime:
    return d if d.tzinfo else d.replace(tzinfo=dt.UTC)


@router.get("", response_model=schemas.MetricsOut)
def metrics(db: Session = Depends(get_db), _user: models.User = ReadDep):
    # WIP — сколько активных (не закрытых) задач стоит на каждом этапе сейчас.
    wip_by_stage: dict[int, int] = dict.fromkeys(range(models.FIRST_STAGE, models.LAST_STAGE), 0)
    wip_rows = db.execute(
        select(models.Task.stage, func.count())
        .where(models.Task.stage < models.LAST_STAGE)
        .group_by(models.Task.stage)
    ).all()
    for stage, count in wip_rows:
        wip_by_stage[stage] = count

    # Пары (создана, закрыта) для каждой когда-либо закрытой задачи — основа
    # для Lead Time и Throughput.
    closed_rows = db.execute(
        select(models.Task.created_at, models.TaskStageHistory.created_at)
        .join(models.TaskStageHistory, models.TaskStageHistory.task_id == models.Task.id)
        .where(models.TaskStageHistory.to_stage == models.LAST_STAGE)
    ).all()

    lead_times_days = [
        (_utc(closed_at) - _utc(created_at)).total_seconds() / 86400
        for created_at, closed_at in closed_rows
        if created_at is not None and closed_at is not None
    ]
    lead_time_avg_days = (
        round(sum(lead_times_days) / len(lead_times_days), 1) if lead_times_days else None
    )

    # Throughput — сколько задач закрылось за каждую из последних 8 недель
    # (понедельник — начало недели).
    today = dt.datetime.now(dt.UTC).date()
    monday_this_week = today - dt.timedelta(days=today.weekday())
    closed_dates = [_utc(closed_at).date() for _, closed_at in closed_rows if closed_at is not None]
    throughput_by_week = []
    for i in range(7, -1, -1):
        week_start = monday_this_week - dt.timedelta(weeks=i)
        week_end = week_start + dt.timedelta(days=7)
        count = sum(1 for d in closed_dates if week_start <= d < week_end)
        throughput_by_week.append(
            schemas.ThroughputWeekOut(week=week_start.strftime("%d.%m"), count=count)
        )

    # Rework Rate — доля переходов НАЗАД (возврат на предыдущий этап) среди
    # всех переходов между этапами (переход при создании задачи, from_stage
    # IS NULL, не считается).
    total_transitions = (
        db.scalar(
            select(func.count())
            .select_from(models.TaskStageHistory)
            .where(models.TaskStageHistory.from_stage.is_not(None))
        )
        or 0
    )
    rework_transitions = (
        db.scalar(
            select(func.count())
            .select_from(models.TaskStageHistory)
            .where(
                models.TaskStageHistory.from_stage.is_not(None),
                models.TaskStageHistory.to_stage < models.TaskStageHistory.from_stage,
            )
        )
        or 0
    )
    rework_rate = (
        round(rework_transitions / total_transitions * 100, 1) if total_transitions else 0.0
    )

    return schemas.MetricsOut(
        wip_by_stage=wip_by_stage,
        lead_time_avg_days=lead_time_avg_days,
        throughput_by_week=throughput_by_week,
        rework_rate=rework_rate,
        total_transitions=total_transitions,
    )
