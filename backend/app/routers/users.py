"""Управление пользователями (только админ) + смена своего пароля.

- GET    /api/users               — список (админ)
- POST   /api/users               — создать (админ)
- PATCH  /api/users/{id}          — изменить ФИО/роль/активность (админ)
- POST   /api/users/{id}/password — сбросить пароль пользователю (админ)
- POST   /api/me/password         — сменить свой пароль (любой вошедший)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db

router = APIRouter(tags=["users"])

AdminDep = Depends(security.require_roles(models.Role.admin))


def _role(value: str) -> models.Role:
    try:
        return models.Role(value)
    except ValueError as exc:
        raise HTTPException(400, f"Недопустимая роль: {value}") from exc


@router.get("/users", response_model=list[schemas.UserOut])
def list_users(db: Session = Depends(get_db), admin: models.User = AdminDep):
    return list(db.scalars(select(models.User).order_by(models.User.id)).all())


@router.post("/users", response_model=schemas.UserOut, status_code=201)
def create_user(
    payload: schemas.UserCreate, db: Session = Depends(get_db), admin: models.User = AdminDep
):
    email = payload.email.lower().strip()
    if db.scalar(select(models.User).where(models.User.email == email)):
        raise HTTPException(409, "Пользователь с таким email уже существует")
    user = models.User(
        email=email,
        full_name=payload.full_name.strip(),
        role=_role(payload.role),
        hashed_password=security.hash_password(payload.password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=schemas.UserOut)
def update_user(
    user_id: int,
    payload: schemas.UserUpdate,
    db: Session = Depends(get_db),
    admin: models.User = AdminDep,
):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()
    if payload.role is not None:
        user.role = _role(payload.role)
    if payload.is_active is not None:
        if user.id == admin.id and payload.is_active is False:
            raise HTTPException(400, "Нельзя деактивировать собственную учётную запись")
        user.is_active = payload.is_active
    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/password", response_model=schemas.UserOut)
def reset_password(
    user_id: int,
    payload: schemas.PasswordReset,
    db: Session = Depends(get_db),
    admin: models.User = AdminDep,
):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    user.hashed_password = security.hash_password(payload.new_password)
    db.commit()
    db.refresh(user)
    return user


@router.post("/me/password", response_model=schemas.UserOut)
def change_my_password(
    payload: schemas.PasswordChange,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    if not security.verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(400, "Текущий пароль неверен")
    user.hashed_password = security.hash_password(payload.new_password)
    db.commit()
    db.refresh(user)
    return user
