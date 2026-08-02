"""Equipment library + launching production tasks from a library item."""

from __future__ import annotations

import datetime as dt
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .. import aggregates, models, schemas, security, serializers
from ..database import get_db
from ..services import library, task_stage
from ..timeutils import to_utc_datetime

router = APIRouter(prefix="/equipment", tags=["equipment"])
ReadDep = Depends(security.get_current_user)
WriteDep = Depends(security.require_roles(models.Role.manager))

KIND_LABELS = {
    "display": "Дисплей",
    "stand": "Подставка",
    "corner": "Корнер",
    "shelf": "Полка",
    "container": "Ёмкость",
    "other": "Прочее",
}
ALLOWED_KINDS = set(KIND_LABELS)


def _check_kind(kind: str) -> str:
    if kind not in ALLOWED_KINDS:
        raise HTTPException(422, f"Недопустимый тип. Разрешены: {', '.join(sorted(ALLOWED_KINDS))}")
    return kind


_RENDER_KINDS = (models.DocKind.photo, models.DocKind.model3d)


def _linked_task(db: Session, eq_id: int):
    """Связанная задача карточки (1:1 по смыслу; берём самую раннюю)."""
    return db.scalar(
        select(models.Task)
        .where(models.Task.equipment_id == eq_id)
        .order_by(models.Task.id)
        .limit(1)
    )


def _cover_doc_id(db: Session, eq_id: int, task_id: int | None) -> int | None:
    """Авто-обложка: свежий документ-фото/рендер карточки или связанной задачи."""
    cond = models.Document.equipment_id == eq_id
    if task_id is not None:
        cond = cond | (models.Document.task_id == task_id)
    return db.scalar(
        select(models.Document.id)
        .where(cond, models.Document.kind.in_(_RENDER_KINDS))
        .order_by(models.Document.id.desc())
        .limit(1)
    )


def _to_out(e: models.Equipment, db: Session) -> dict:
    task = _linked_task(db, e.id)
    return {
        "id": e.id,
        "brand": e.brand.name,
        "group": e.brand.group.code,
        "name": e.name,
        "kind": e.kind,
        "kind_label": KIND_LABELS.get(e.kind, "Прочее"),
        "description": e.description,
        "dimensions": e.dimensions,
        "currency": e.currency,
        "est_budget": e.est_budget,
        "est_sample": e.est_sample,
        "est_tirazh": e.est_tirazh,
        "is_active": e.is_active,
        "times_produced": e.times_produced,
        "rc_ship_date": e.rc_ship_date.isoformat() if e.rc_ship_date else None,
        "rc_remainder": e.rc_remainder,
        "task_code": task.code if task else None,
        "cover_document_id": _cover_doc_id(db, e.id, task.id if task else None),
    }


def _base():
    return select(models.Equipment).options(
        selectinload(models.Equipment.brand).selectinload(models.Brand.group)
    )


@router.get("", response_model=list[schemas.EquipmentOut])
def list_equipment(
    db: Session = Depends(get_db),
    _user: models.User = ReadDep,
    brand: str | None = None,
    active_only: bool = False,
    q: str | None = Query(default=None, description="поиск по названию или ШК/SKU"),
):
    stmt = _base()
    if brand:
        stmt = stmt.where(models.Equipment.brand.has(models.Brand.name == brand))
    if active_only:
        stmt = stmt.where(models.Equipment.is_active.is_(True))
    if q and q.strip():
        like = f"%{q.strip()}%"
        # карточки, у связанной задачи которых есть ШК/SKU по запросу
        bc_ids = (
            select(models.Task.equipment_id)
            .join(models.NomenclatureItem, models.NomenclatureItem.task_id == models.Task.id)
            .where(
                models.Task.equipment_id.is_not(None),
                models.NomenclatureItem.barcode.ilike(like)
                | models.NomenclatureItem.sku.ilike(like),
            )
        )
        stmt = stmt.where(models.Equipment.name.ilike(like) | models.Equipment.id.in_(bc_ids))
    rows = db.scalars(stmt.order_by(models.Equipment.id)).all()
    return [_to_out(e, db) for e in rows]


@router.post("", response_model=schemas.EquipmentOut, status_code=201)
def create_equipment(
    payload: schemas.EquipmentCreate, db: Session = Depends(get_db), _user: models.User = WriteDep
):
    brand = db.scalar(select(models.Brand).where(models.Brand.name == payload.brand))
    if not brand:
        raise HTTPException(422, f"Бренд '{payload.brand}' не найден")
    _check_kind(payload.kind)
    e = models.Equipment(
        brand_id=brand.id,
        name=payload.name,
        kind=payload.kind,
        description=payload.description,
        dimensions=payload.dimensions,
        currency=payload.currency,
        est_budget=payload.est_budget,
        est_sample=payload.est_sample,
        est_tirazh=payload.est_tirazh,
    )
    db.add(e)
    db.commit()
    e = db.scalar(_base().where(models.Equipment.id == e.id))
    return _to_out(e, db)


@router.patch("/{eq_id}", response_model=schemas.EquipmentOut)
def update_equipment(
    eq_id: int,
    payload: schemas.EquipmentUpdate,
    db: Session = Depends(get_db),
    _user: models.User = WriteDep,
):
    e = db.scalar(_base().where(models.Equipment.id == eq_id))
    if not e:
        raise HTTPException(404, "Оборудование не найдено")
    data = payload.model_dump(exclude_unset=True)
    if "kind" in data:
        _check_kind(data["kind"])
    if "rc_ship_date" in data:
        data["rc_ship_date"] = to_utc_datetime(data["rc_ship_date"])
    for k, v in data.items():
        setattr(e, k, v)
    db.commit()
    db.refresh(e)
    return _to_out(e, db)


@router.get("/{eq_id}/detail")
def card_detail(eq_id: int, db: Session = Depends(get_db), _user: models.User = ReadDep):
    """Детальная карточка: обложка, скаляры, файлы по слотам (свои + задачи), номенклатура.

    Слоты: render (фото/рендер), brief (ТЗ), ds (ДС), invoice (счёт),
    planogram (планограмма), other (прочее). ШК — отдельно как таблица номенклатуры.
    """
    e = db.scalar(_base().where(models.Equipment.id == eq_id))
    if not e:
        raise HTTPException(404, "Карточка не найдена")
    card = _to_out(e, db)
    task = _linked_task(db, e.id)
    task_id = task.id if task else None

    # все документы карточки + связанной задачи
    cond = models.Document.equipment_id == e.id
    if task_id is not None:
        cond = cond | (models.Document.task_id == task_id)
    docs = db.scalars(select(models.Document).where(cond).order_by(models.Document.id)).all()

    slot_map = {
        models.DocKind.photo: "render",
        models.DocKind.model3d: "render",
        models.DocKind.brief: "brief",
        models.DocKind.ds: "ds",
        models.DocKind.invoice: "invoice",
        models.DocKind.planogram: "planogram",
    }
    slots: dict[str, list] = {
        "render": [],
        "brief": [],
        "ds": [],
        "invoice": [],
        "planogram": [],
        "other": [],
    }
    for d in docs:
        bucket = slot_map.get(d.kind, "other")
        slots[bucket].append(
            {
                "id": d.id,
                "kind": d.kind.value,
                "filename": d.filename,
                "stage": d.stage,
                "content_type": d.content_type,
                "size": d.size,
                "source": "card" if d.equipment_id == e.id else "task",
            }
        )

    nomenclature = []
    if task is not None:
        items = db.scalars(
            select(models.NomenclatureItem)
            .where(models.NomenclatureItem.task_id == task_id)
            .order_by(models.NomenclatureItem.id)
        ).all()
        nomenclature = [
            {
                "id": n.id,
                "sku": n.sku,
                "barcode": n.barcode,
                "name": n.name,
                "qty": n.qty,
                "status": n.status.value,
                "status_label": models.NOMENCLATURE_STATUS_LABELS.get(n.status, n.status.value),
            }
            for n in items
        ]

    return {
        "card": card,
        "task_code": card["task_code"],
        "slots": slots,
        "nomenclature": nomenclature,
    }


def delete_equipment(eq_id: int, db: Session = Depends(get_db), _user: models.User = WriteDep):
    e = db.get(models.Equipment, eq_id)
    if not e:
        raise HTTPException(404, "Оборудование не найдено")
    db.delete(e)
    db.commit()


def _next_task_code(db: Session) -> str:
    last = db.scalar(select(func.count()).select_from(models.Task)) or 0
    return f"RD-{40 + last + 1:03d}"


@router.post("/{eq_id}/produce", response_model=schemas.TaskOut, status_code=201)
def produce(
    eq_id: int,
    payload: schemas.ProduceRequest,
    db: Session = Depends(get_db),
    user: models.User = WriteDep,
):
    """Создаёт производственную задачу (RD-xxx) на основе изделия из библиотеки."""
    e = db.scalar(_base().where(models.Equipment.id == eq_id))
    if not e:
        raise HTTPException(404, "Оборудование не найдено")
    if not e.is_active:
        raise HTTPException(409, "Изделие в архиве — нельзя запустить в производство")

    task = models.Task(
        code=_next_task_code(db),
        name=payload.name or e.name,
        brand_id=e.brand_id,
        # Привязываем новый проект к ИСХОДНОЙ карточке библиотеки — это
        # производственный запуск того же изделия, новая карточка не нужна
        # (иначе в библиотеке появлялся дубль).
        equipment_id=e.id,
        stage=1,
        currency=e.currency,
        production_cost=e.est_budget,
        budget=e.est_budget,
        sample_cost=e.est_sample,
        tirazh_cost=e.est_tirazh,
        deadline_tt=to_utc_datetime(payload.deadline),
        launch_date=to_utc_datetime(payload.launch),
    )
    if payload.team:
        existing = list(
            db.scalars(
                select(models.TeamMember).where(models.TeamMember.name.in_(payload.team))
            ).all()
        )
        names = {m.name for m in existing}
        for n in payload.team:
            if n not in names:
                m = models.TeamMember(name=n)
                db.add(m)
                existing.append(m)
        task.members = existing

    e.times_produced += 1  # счётчик запусков у исходной карточки
    # Предзаполняем ТЗ (brief_data) из карточки изделия, чтобы задача не стартовала с пустым ТЗ.
    _kind_map = {
        "shelf": "полка",
        "stand": "стойка",
        "corner": "корнер",
        "display": "дисплей",
        "container": "контейнер",
    }
    brief = {
        "group": e.brand.group.code,
        "brand": e.brand.name,
        "product_name": e.name,
        "construction_type": _kind_map.get(e.kind, ""),
        "dimensions": e.dimensions or "",
        "deliverables": e.description or "",
        "fill_date": dt.datetime.now(dt.UTC).date().isoformat(),
    }
    task.dimensions = e.dimensions or ""
    task.brief_data = json.dumps(brief, ensure_ascii=False)
    db.add(task)
    db.flush()
    library.ensure_library_card(
        db, task
    )  # вернёт исходную карточку (task.equipment_id уже задан) — дубль не создаётся
    task_stage.record_creation(db, task, user_id=user.id)  # исходная запись истории
    db.commit()

    reloaded = db.scalar(
        select(models.Task)
        .options(
            selectinload(models.Task.brand).selectinload(models.Brand.group),
            selectinload(models.Task.members),
        )
        .where(models.Task.id == task.id)
    )
    assert reloaded is not None
    return serializers.task_to_out(reloaded, aggregates.counts_for_task(db, reloaded.id))
