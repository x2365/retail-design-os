"""Справочник подрядчиков."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas, security, serializers
from ..database import get_db

router = APIRouter(tags=["contractors"])
ReadDep = Depends(security.get_current_user)
WriteDep = Depends(security.require_roles(models.Role.manager))


@router.get("/contractors", response_model=list[schemas.ContractorOut])
def list_contractors(db: Session = Depends(get_db), _user: models.User = ReadDep):
    rows = db.scalars(
        select(models.Contractor).where(models.Contractor.is_active == True).order_by(models.Contractor.name)  # noqa: E712
    ).all()
    return [serializers.contractor_to_out(c) for c in rows]


@router.post("/contractors", response_model=schemas.ContractorOut, status_code=201)
def create_contractor(payload: schemas.ContractorCreate,
                      db: Session = Depends(get_db), _user: models.User = WriteDep):
    name = payload.name.strip()
    if db.scalar(select(models.Contractor).where(models.Contractor.name == name)):
        raise HTTPException(409, "Подрядчик с таким названием уже есть")
    details = payload.details or {}
    # контакт по умолчанию подтянем из деталей (телефон/почта), если не задан
    contact = payload.contact.strip()
    if not contact:
        contact = (details.get("Контактный номер телефона") or details.get("Электронная почта") or "").strip()
    ct = models.Contractor(
        name=name, contact=contact[:200],
        details=json.dumps(details, ensure_ascii=False) if details else "",
        is_active=True,
    )
    db.add(ct)
    db.commit()
    db.refresh(ct)
    return serializers.contractor_to_out(ct)
