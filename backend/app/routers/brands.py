"""Brands: list + full CRUD (create / rename / move group / delete)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas, security
from ..database import get_db
from ..services import audit

router = APIRouter(prefix="/brands", tags=["brands"])
ReadDep = Depends(security.get_current_user)
WriteDep = Depends(security.require_roles(models.Role.manager))


def _to_out(db: Session, b: models.Brand) -> dict:
    active = (
        db.scalar(
            select(func.count())
            .select_from(models.Task)
            .where(models.Task.brand_id == b.id, models.Task.stage < models.LAST_STAGE)
        )
        or 0
    )
    eq = (
        db.scalar(
            select(func.count())
            .select_from(models.Equipment)
            .where(models.Equipment.brand_id == b.id)
        )
        or 0
    )
    return {
        "id": b.id,
        "name": b.name,
        "group": b.group.code,
        "active_tasks": active,
        "equipment_count": eq,
    }


def _group_by_code(db: Session, code: str) -> models.Group:
    g = db.scalar(select(models.Group).where(models.Group.code == code))
    if not g:
        raise HTTPException(422, f"Группа '{code}' не найдена")
    return g


@router.get("", response_model=list[schemas.BrandOut])
def list_brands(db: Session = Depends(get_db), _user: models.User = ReadDep):
    brands = db.scalars(
        select(models.Brand).options(selectinload(models.Brand.group)).order_by(models.Brand.id)
    ).all()
    return [_to_out(db, b) for b in brands]


@router.post("", response_model=schemas.BrandOut, status_code=201)
def create_brand(
    payload: schemas.BrandCreate, db: Session = Depends(get_db), _user: models.User = WriteDep
):
    if db.scalar(select(models.Brand).where(models.Brand.name == payload.name)):
        raise HTTPException(409, f"Бренд '{payload.name}' уже существует")
    group = _group_by_code(db, payload.group)
    brand = models.Brand(name=payload.name, group_id=group.id)
    db.add(brand)
    db.commit()
    db.refresh(brand)
    return _to_out(db, brand)


@router.patch("/{brand_id}", response_model=schemas.BrandOut)
def update_brand(
    brand_id: int,
    payload: schemas.BrandUpdate,
    db: Session = Depends(get_db),
    _user: models.User = WriteDep,
):
    brand = db.get(models.Brand, brand_id)
    if not brand:
        raise HTTPException(404, "Бренд не найден")
    if payload.name is not None:
        clash = db.scalar(
            select(models.Brand).where(
                models.Brand.name == payload.name, models.Brand.id != brand_id
            )
        )
        if clash:
            raise HTTPException(409, f"Бренд '{payload.name}' уже существует")
        brand.name = payload.name
    if payload.group is not None:
        brand.group_id = _group_by_code(db, payload.group).id
    db.commit()
    db.refresh(brand)
    return _to_out(db, brand)


@router.delete("/{brand_id}", status_code=204)
def delete_brand(brand_id: int, db: Session = Depends(get_db), user: models.User = WriteDep):
    brand = db.get(models.Brand, brand_id)
    if not brand:
        raise HTTPException(404, "Бренд не найден")
    # Task.brand_id is NOT NULL with ondelete=RESTRICT (unlike equipment_id,
    # which is nullable + SET NULL) — a task keeps its brand forever, closed
    # or not, so this counts every task regardless of stage. There is no
    # "close them first" workaround: the FK physically blocks the DELETE
    # while any task row still points here.
    task_count = (
        db.scalar(
            select(func.count()).select_from(models.Task).where(models.Task.brand_id == brand_id)
        )
        or 0
    )
    if task_count:
        raise HTTPException(
            409,
            f"Нельзя удалить: у бренда есть задачи ({task_count}), включая архивные/закрытые. "
            "У задачи всегда должен быть бренд — перенести их на другой бренд сейчас нельзя.",
        )
    audit.log_deletion(
        db, user, entity_type="brand", entity_code=brand.name, description=f"Бренд «{brand.name}»"
    )
    db.delete(brand)  # cascades equipment
    db.commit()
