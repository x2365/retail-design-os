"""Authentication endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=schemas.Token)
def login(
    form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
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


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(security.get_current_user)):
    return schemas.UserOut.model_validate(user)
