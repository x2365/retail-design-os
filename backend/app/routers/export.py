"""CSV exports (registry-style) for budgets and retail-point deliveries.

Returns UTF-8 CSV with a BOM so Excel opens Cyrillic correctly. Streamed so
large datasets don't buffer fully in memory.
"""

from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .. import aggregates, models, security
from ..database import get_db

router = APIRouter(prefix="/export", tags=["export"])
ReadDep = Depends(security.get_current_user)


def _csv_response(rows: list[list], filename: str) -> StreamingResponse:
    buf = io.StringIO()
    buf.write("\ufeff")  # BOM for Excel
    writer = csv.writer(buf, delimiter=";")
    writer.writerows(rows)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/budgets.csv")
def export_budgets(db: Session = Depends(get_db), _user: models.User = ReadDep):
    tasks = db.scalars(
        select(models.Task)
        .options(selectinload(models.Task.brand).selectinload(models.Brand.group))
        .order_by(models.Task.code)
    ).all()
    rows: list[list[object]] = [
        [
            "Код",
            "Задача",
            "Бренд",
            "Группа",
            "Валюта",
            "Образец",
            "Тираж",
            "Бюджет",
            "Предоплата",
            "Этап",
        ]
    ]
    for t in tasks:
        rows.append(
            [
                t.code,
                t.name,
                t.brand.name,
                t.brand.group.code,
                t.currency,
                t.sample_cost,
                t.tirazh_cost,
                t.budget,
                t.prepaid,
                t.stage_name,
            ]
        )
    return _csv_response(rows, "budgets.csv")


@router.get("/retail-points.csv")
def export_points(db: Session = Depends(get_db), _user: models.User = ReadDep):
    points = db.scalars(select(models.RetailPoint).order_by(models.RetailPoint.code)).all()
    counts = aggregates.point_counts(db, [p.id for p in points])
    rows: list[list[object]] = [
        ["Код", "Название", "Город", "Адрес", "Позиций отгружено", "Проблемных"]
    ]
    for p in points:
        c = counts[p.id]
        rows.append([p.code, p.name, p.city, p.address, c["deliveries_total"], c["problems"]])
    return _csv_response(rows, "retail-points.csv")


@router.get("/deliveries.csv")
def export_deliveries(db: Session = Depends(get_db), _user: models.User = ReadDep):
    st = {
        "delivered": "Получено",
        "partial": "Неполный объём",
        "missing": "Не получено",
        "pending": "Ожидает",
    }
    rows: list[list[object]] = [
        ["Точка", "Город", "Задача", "Изделие", "Статус", "Получено", "Ожидается"]
    ]
    deliveries = db.scalars(
        select(models.Delivery)
        .options(
            selectinload(models.Delivery.retail_point),
            selectinload(models.Delivery.task),
        )
        .order_by(models.Delivery.retail_point_id, models.Delivery.id)
    ).all()
    for d in deliveries:
        rows.append(
            [
                d.retail_point.code,
                d.retail_point.city,
                d.task.code,
                d.task.name,
                st.get(d.status.value, d.status.value),
                d.qty_received,
                d.qty_expected,
            ]
        )
    return _csv_response(rows, "deliveries.csv")
