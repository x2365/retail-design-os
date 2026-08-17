"""Служебные эндпоинты напоминаний и точки сброса демо-данных.

- POST /api/internal/run-reminders — обход+рассылка, защищён сервис-токеном
  (для cron/launchd). Если токен в настройках пуст — эндпоинт выключен (403).
- POST /api/internal/snapshot/take — сохранить текущее состояние БД как точку
  сброса (админ, из UI).
- GET  /api/internal/snapshot — метаданные текущей точки сброса (админ).
- POST /api/internal/snapshot/restore — откатить БД к точке сброса прямо
  сейчас (админ, из UI — кнопка "Сбросить сейчас").
- POST /api/internal/run-snapshot-reset — то же самое, но для внешнего cron
  (защищён сервис-токеном, не требует логина — см. services/snapshot.py и
  render.yaml про настройку внешнего расписания).
- POST /api/me/telegram — текущий пользователь привязывает свой Telegram chat_id
  (получить можно, написав боту; онбординг — на стороне эксплуатации).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..config import get_settings
from ..database import get_db
from ..services import reminders, snapshot

router = APIRouter(tags=["notifications"])
SnapshotAdminDep = Depends(security.require_roles(models.Role.admin))


@router.post("/internal/run-reminders")
def run_reminders_endpoint(
    db: Session = Depends(get_db),
    x_service_token: str = Header(default=""),
):
    s = get_settings()
    if not s.reminders_service_token:
        raise HTTPException(403, "Reminders endpoint disabled (no service token configured)")
    if x_service_token != s.reminders_service_token:
        raise HTTPException(401, "Invalid service token")
    return reminders.run_reminders(db)


def _snapshot_out(snap: models.DataSnapshot | None) -> schemas.SnapshotOut:
    if snap is None:
        return schemas.SnapshotOut(taken_at=None, size_bytes=0)
    return schemas.SnapshotOut(taken_at=snap.taken_at, size_bytes=snap.size_bytes)


@router.get("/internal/snapshot", response_model=schemas.SnapshotOut)
def get_snapshot_endpoint(db: Session = Depends(get_db), _user: models.User = SnapshotAdminDep):
    return _snapshot_out(snapshot.get_snapshot(db))


@router.post("/internal/snapshot/take", response_model=schemas.SnapshotOut)
def take_snapshot_endpoint(db: Session = Depends(get_db), _user: models.User = SnapshotAdminDep):
    try:
        snap = snapshot.take_snapshot(db)
    except RuntimeError as e:
        raise HTTPException(500, str(e)) from e
    return _snapshot_out(snap)


@router.post("/internal/snapshot/restore", response_model=schemas.SnapshotOut)
def restore_snapshot_endpoint(
    db: Session = Depends(get_db), _user: models.User = SnapshotAdminDep
):
    try:
        snap = snapshot.restore_snapshot(db)
    except RuntimeError as e:
        raise HTTPException(500, str(e)) from e
    return _snapshot_out(snap)


@router.post("/internal/run-snapshot-reset", response_model=schemas.SnapshotOut)
def run_snapshot_reset_endpoint(
    db: Session = Depends(get_db),
    x_service_token: str = Header(default=""),
):
    s = get_settings()
    if not s.snapshot_reset_service_token:
        raise HTTPException(403, "Snapshot reset endpoint disabled (no service token configured)")
    if x_service_token != s.snapshot_reset_service_token:
        raise HTTPException(401, "Invalid service token")
    try:
        snap = snapshot.restore_snapshot(db)
    except RuntimeError as e:
        raise HTTPException(500, str(e)) from e
    return _snapshot_out(snap)


@router.post("/me/telegram", response_model=schemas.UserOut)
def set_my_telegram(
    payload: schemas.TelegramLink,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    user.telegram_chat_id = (payload.chat_id or "").strip() or None
    db.commit()
    db.refresh(user)
    return user
