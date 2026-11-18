"""Authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..config import get_settings
from ..database import get_db
from ..rate_limit import limiter

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/login", response_model=schemas.Token)
@limiter.limit(settings.login_rate_limit)
def login(
    request: Request, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    # OAuth2 form uses 'username' — we treat it as email.
    user = security.authenticate(db, form.username, form.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = security.create_access_token(user)
    return schemas.Token(access_token=token, user=schemas.UserOut.model_validate(user))


@router.post("/demo", response_model=schemas.Token)
def demo_login(db: Session = Depends(get_db)):
    """Passwordless sign-in as the configured demo user (DEMO_AUTOLOGIN_EMAIL).

    Lets the public demo open straight into the app. Off unless configured.
    """
    email = settings.demo_autologin_email
    user = db.scalar(select(models.User).where(models.User.email == email)) if email else None
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Демо-вход выключен")
    token = security.create_access_token(user)
    return schemas.Token(access_token=token, user=schemas.UserOut.model_validate(user))


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(security.get_current_user)):
    return schemas.UserOut.model_validate(user)
