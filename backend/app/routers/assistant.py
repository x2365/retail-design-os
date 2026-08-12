"""Эндпоинт ассистента-копайлота (требует авторизацию, только чтение)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..config import get_settings
from ..database import get_db
from ..rate_limit import limiter
from ..services import assistant as assistant_svc

settings = get_settings()

router = APIRouter(prefix="/assistant", tags=["assistant"])
ReadDep = Depends(security.get_current_user)


class AssistantQuery(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    screen: str | None = None
    filters: dict | None = None


@router.get("/status", response_model=schemas.AssistantStatusOut)
def assistant_status(_user: models.User = ReadDep) -> dict:
    return {"enabled": settings.llm_enabled, "model": settings.llm_model}


@router.post("", response_model=schemas.AssistantAnswerOut)
@limiter.limit("10/minute")
def ask_assistant(
    request: Request,
    body: AssistantQuery,
    db: Session = Depends(get_db),
    _user: models.User = ReadDep,
) -> dict:
    return assistant_svc.run_assistant(db, body.query, body.screen, body.filters)
