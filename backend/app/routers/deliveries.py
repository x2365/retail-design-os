"""Retail-point catalog and individual delivery confirmation."""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas, security, serializers
from ..config import get_settings
from ..database import get_db

router = APIRouter(tags=["retail"])
settings = get_settings()

ReadDep = Depends(security.get_current_user)
# retailers, shipment managers (and managers/admin) may confirm deliveries
ConfirmDep = Depends(
    security.require_roles(models.Role.manager, models.Role.retailer, models.Role.shipment_manager)
)
# only managers/admin manage the points catalog
ManageDep = Depends(security.require_roles(models.Role.manager))


@router.get("/retail-points", response_model=schemas.Page[schemas.RetailPointOut])
def list_points(
    db: Session = Depends(get_db),
    _user: models.User = ReadDep,
    search: str | None = None,
    problems_only: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(settings.default_page_size, ge=1, le=settings.max_page_size),
):
    from .. import aggregates  # local import to avoid cycle at module load

    stmt = select(models.RetailPoint)
    count_stmt = select(func.count()).select_from(models.RetailPoint)
    if search:
        like = f"%{search}%"
        cond = models.RetailPoint.name.ilike(like) | models.RetailPoint.city.ilike(like)
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)

    # When filtering by problems we need counts across the whole (search-filtered)
    # set, so compute over all matching points, then paginate in Python.
    if problems_only:
        all_points = db.scalars(stmt.order_by(models.RetailPoint.code)).all()
        counts = aggregates.point_counts(db, [p.id for p in all_points])
        flagged = [p for p in all_points if counts[p.id]["problems"] > 0]
        total = len(flagged)
        page_rows = flagged[(page - 1) * page_size : (page - 1) * page_size + page_size]
        items = [
            schemas.RetailPointOut(
                id=p.id,
                code=p.code,
                name=p.name,
                city=p.city,
                address=p.address,
                deliveries_total=counts[p.id]["deliveries_total"],
                problems=counts[p.id]["problems"],
            )
            for p in page_rows
        ]
        return schemas.Page(items=items, total=total, page=page, page_size=page_size)

    total = db.scalar(count_stmt) or 0
    rows = db.scalars(
        stmt.order_by(models.RetailPoint.code).offset((page - 1) * page_size).limit(page_size)
    ).all()
    counts = aggregates.point_counts(db, [p.id for p in rows])
    items = [
        schemas.RetailPointOut(
            id=p.id,
            code=p.code,
            name=p.name,
            city=p.city,
            address=p.address,
            deliveries_total=counts[p.id]["deliveries_total"],
            problems=counts[p.id]["problems"],
        )
        for p in rows
    ]
    return schemas.Page(items=items, total=total, page=page, page_size=page_size)


@router.patch("/deliveries/{delivery_id}", response_model=schemas.DeliveryOut)
def update_delivery(
    delivery_id: int,
    payload: schemas.DeliveryUpdate,
    db: Session = Depends(get_db),
    user: models.User = ConfirmDep,
):
    d = db.scalar(
        select(models.Delivery)
        .options(selectinload(models.Delivery.task), selectinload(models.Delivery.retail_point))
        .where(models.Delivery.id == delivery_id)
    )
    if not d:
        raise HTTPException(404, f"Delivery {delivery_id} not found")

    if payload.status is not None:
        try:
            d.status = models.DeliveryStatus(payload.status)
        except ValueError as exc:
            raise HTTPException(422, f"Invalid status '{payload.status}'") from exc
        d.confirmed_at = (
            dt.datetime.now(dt.UTC) if d.status != models.DeliveryStatus.pending else None
        )
    if payload.qty_received is not None:
        d.qty_received = payload.qty_received
    if payload.region is not None:
        try:
            d.region = models.ShipmentRegion(payload.region)
        except ValueError as exc:
            raise HTTPException(422, f"Invalid region '{payload.region}'") from exc
    if payload.note is not None:
        d.note = payload.note
    if payload.installed is not None:
        if payload.installed and d.status != models.DeliveryStatus.delivered:
            raise HTTPException(422, "Нельзя отметить монтаж: доставка ещё не подтверждена")
        d.installed_at = dt.datetime.now(dt.UTC) if payload.installed else None
        d.installed_by = user.full_name if payload.installed else ""

    db.commit()
    db.refresh(d)
    return serializers.delivery_to_out(d)


# ---- retail point catalog management --------------------------------------
def _next_point_code(db: Session) -> str:
    n = db.scalar(select(func.count()).select_from(models.RetailPoint)) or 0
    return f"TT-{n + 1:03d}"


@router.post("/retail-points", response_model=schemas.RetailPointOut, status_code=201)
def create_point(
    payload: schemas.RetailPointCreate,
    db: Session = Depends(get_db),
    _user: models.User = ManageDep,
):
    code = (payload.code or "").strip() or _next_point_code(db)
    if db.scalar(select(models.RetailPoint).where(models.RetailPoint.code == code)):
        raise HTTPException(409, f"Точка с кодом {code} уже существует")
    p = models.RetailPoint(code=code, name=payload.name, city=payload.city, address=payload.address)
    db.add(p)
    db.commit()
    db.refresh(p)
    return schemas.RetailPointOut.model_validate(p)


@router.patch("/retail-points/{point_id}", response_model=schemas.RetailPointOut)
def update_point(
    point_id: int,
    payload: schemas.RetailPointUpdate,
    db: Session = Depends(get_db),
    _user: models.User = ManageDep,
):
    p = db.get(models.RetailPoint, point_id)
    if not p:
        raise HTTPException(404, "Точка не найдена")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return schemas.RetailPointOut.model_validate(p)


@router.delete("/retail-points/{point_id}", status_code=204)
def delete_point(point_id: int, db: Session = Depends(get_db), _user: models.User = ManageDep):
    p = db.get(models.RetailPoint, point_id)
    if not p:
        raise HTTPException(404, "Точка не найдена")
    cnt = (
        db.scalar(
            select(func.count())
            .select_from(models.Delivery)
            .where(models.Delivery.retail_point_id == point_id)
        )
        or 0
    )
    if cnt:
        raise HTTPException(409, f"Нельзя удалить: в точку есть отгрузки ({cnt}).")
    db.delete(p)
    db.commit()


@router.get("/retail-points/{point_id}/deliveries", response_model=list[schemas.PointDeliveryOut])
def point_deliveries(point_id: int, db: Session = Depends(get_db), _user: models.User = ReadDep):
    """Что отгружено в конкретную ТТ: список изделий/задач со статусом."""
    p = db.get(models.RetailPoint, point_id)
    if not p:
        raise HTTPException(404, "Точка не найдена")
    rows = db.scalars(
        select(models.Delivery)
        .options(selectinload(models.Delivery.task).selectinload(models.Task.equipment))
        .where(models.Delivery.retail_point_id == point_id)
        .order_by(models.Delivery.id)
    ).all()
    return [
        schemas.PointDeliveryOut(
            id=d.id,
            task=d.task.code,
            task_name=d.task.name,
            equipment=(d.task.equipment.name if d.task.equipment else None),
            status=d.status.value,
            region=d.region.value,
            region_label=models.SHIPMENT_REGION_LABELS.get(d.region, d.region.value),
            qty_expected=d.qty_expected,
            qty_received=d.qty_received,
            confirmed_at=d.confirmed_at.isoformat() if d.confirmed_at else None,
            installed_at=d.installed_at.isoformat() if d.installed_at else None,
            installed_by=d.installed_by,
        )
        for d in rows
    ]
