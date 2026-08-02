"""Служебные эндпоинты напоминаний.

- POST /api/internal/run-reminders — обход+рассылка, защищён сервис-токеном
  (для cron/launchd). Если токен в настройках пуст — эндпоинт выключен (403).
- POST /api/me/telegram — текущий пользователь привязывает свой Telegram chat_id
  (получить можно, написав боту; онбординг — на стороне эксплуатации).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..config import get_settings
from ..database import get_db
from ..services import reminders

router = APIRouter(tags=["notifications"])


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
